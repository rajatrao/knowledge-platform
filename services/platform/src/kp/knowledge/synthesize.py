"""Grounded synthesis. create_deep_agent runs for Ollama or a configured cloud key."""

from __future__ import annotations

import asyncio
import json
import logging
import re

from kp.agent import skills as skill_mod
from kp.agent.sandbox import SandboxUnavailable
from kp.config import get_settings
from kp.flow import event
from kp.knowledge.citations import filter_citations
from kp.llm import CloudKeyRequired, resolve_llm
from kp.knowledge.retrieve import Bundle
from kp.labels import BLOCKER_CAUSE, CAUSE_LABELS

logger = logging.getLogger(__name__)

_ANSWER_SHAPE = (
    "Write the answer as short paragraphs separated by a blank line. "
    "When listing several signals or items, put each on its own line starting with '- '. "
    "Do not use HTML. "
    "If the instructions require FACT, TREND, POSSIBLE EXPLANATION, and UNKNOWN, keep those labels. "
    "Do not invent a single primary cause when staffing and inventory both coincide. "
    "suggested_questions is an array of 1 to 3 short complete questions the user could ask next, "
    "grounded in these same records. "
    "Each one is a full question, not a vague prompt such as 'Want to know more?'. "
    "Do not repeat a suggested question as the last line of the answer."
)
_QUESTION_START = re.compile(
    r"^(what|why|how|when|where|which|who|is|are|can|should|do|does|did)\b",
    re.I,
)
_VAGUE_QUESTION = re.compile(
    r"^(want to know more|tell me more|anything else|more details|want more detail)\??$",
    re.I,
)
_BULLET_LINE = re.compile(r"^\s*[-*]\s+(.*\S)\s*$")
_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\([^)]+\)")


def _ceo(bundle: Bundle) -> tuple[str, list[dict]]:
    lines = [
        "The top customer complaint themes are listed below. Each theme links to its investigation page, where the recommended actions are the sentences copied from internal documents."
    ]
    citations = []
    for theme in bundle.payload["themes"]:
        lines.append(f"- [{theme['name']}](/investigations/{theme['slug']})")
        citations.append(
            {
                "id": f"iss_{theme['slug']}",
                "kind": "issue",
                "quote": theme["description"],
            }
        )
    return "\n".join(lines), citations


def _ops(bundle: Bundle) -> tuple[str, list[dict]]:
    lines = ["Operational problems driving customer complaints, in counted order:"]
    citations = []
    mappings = []
    for index, blocker in enumerate(bundle.payload["blockers"], start=1):
        lines.append(f"{index}. {blocker['label']} ({blocker['count']})")
        cause = BLOCKER_CAUSE[blocker["key"]]
        mappings.append(CAUSE_LABELS[cause].lower())
        needle = CAUSE_LABELS[cause].casefold()
        complaint = next(
            (
                record_id
                for (kind, record_id) in bundle.records
                if kind == "complaint" and needle in bundle.records[(kind, record_id)]["text"].casefold()
            ),
            None,
        )
        if complaint is None:
            complaint = next((record_id for (kind, record_id) in bundle.records if kind == "complaint"), None)
        if complaint:
            citations.append(
                {
                    "id": complaint,
                    "kind": "complaint",
                    "quote": bundle.records[("complaint", complaint)]["text"],
                }
            )
    lines.append(
        "These line up with customer complaints about " + ", ".join(mappings) + "."
    )
    return "\n".join(lines), citations


def _engineer(bundle: Bundle) -> tuple[str, list[dict]]:
    incidents = {row["technical_issue"]: row for row in bundle.payload["related_incidents"]}
    lines = ["Customer complaints related to technical incidents, from the retrieved evidence:"]
    citations = []
    for issue in bundle.payload["technical_issues"]:
        incident = incidents.get(issue["key"])
        if incident:
            lines.append(f"- {issue['label']} ({issue['complaint_count']}), including {incident['id']}")
            citations.append({"id": incident["id"], "kind": "incident", "quote": incident["summary"]})
        else:
            lines.append(f"- {issue['label']} ({issue['complaint_count']})")
    return "\n".join(lines), citations


def _marketing(bundle: Bundle) -> tuple[str, list[dict]]:
    lines = ["Customers describe why they value Base Power in these themes."]
    citations = []
    for theme in bundle.payload["value_themes"]:
        sample = theme["records"][0]
        lines.append(f"{theme['label']}: \"{sample['quote']}\" ({sample['id']})")
        citations.append(
            {
                "id": sample["complaint_id"],
                "kind": "complaint",
                "quote": sample["quote"],
                "document_id": sample["document_id"],
            }
        )
    return "\n".join(lines), citations


def grounded_answer(bundle: Bundle, query: str = "", prior: str = "") -> tuple[str, list[dict]]:
    if prior:
        from kp.knowledge.artifacts import _forecast_points

        if _forecast_points(prior):
            return prior, []
    company = _company_grounded(bundle, query)
    if company is not None:
        return company
    field = _field_ops_grounded(bundle, query)
    if field is not None:
        return field
    engineering = _engineering_grounded(bundle, query)
    if engineering is not None:
        return engineering
    executive = _executive_grounded(bundle, query)
    if executive is not None:
        return executive
    if bundle.skill == "customer-complaints":
        return _ceo(bundle)
    if bundle.skill == "complaint-drivers":
        return _ops(bundle)
    if bundle.skill == "complaint-incidents":
        return _engineer(bundle)
    if bundle.skill == "value-language":
        return _marketing(bundle)
    return "I do not have a skill for that question.", []


def _company_grounded(bundle: Bundle, query: str) -> tuple[str, list[dict]] | None:
    from kp.knowledge.retrieve import _finance_query, _normalized_query

    text = _normalized_query(query)
    if not _finance_query(text):
        return None
    want_revenue = "revenue" in text
    prefixes = ["doc_qr_", "doc_qp_"] if want_revenue else ["doc_qp_", "doc_qr_"]
    if "performance" not in text:
        prefixes = ["doc_qr_"]
    elif "revenue" not in text:
        prefixes = ["doc_qp_"]
    chosen = _matching_records(bundle, prefixes)
    if not chosen:
        return None
    named = [
        f"{year} {quarter}"
        for year in ("2020", "2021", "2022", "2023", "2024", "2025", "2026", "2027", "2028", "2029")
        for quarter in ("q1", "q2", "q3", "q4")
        if year in text and quarter in text
    ]
    specific = [item for item in chosen if any(label in item[1]["text"].casefold() for label in named)]
    future = any(year in text for year in ("2027", "2028", "2029"))
    if future and not specific:
        # Fallback only. The model writes the forecast from these records.
        latest = [item for item in chosen if "forecast" in item[1]["text"].casefold()] or [chosen[-1]]
        cited = latest[:1]
        lines = ["The latest stored figure is:"]
        citations = []
        for record_id, record in cited:
            body = " ".join(record["text"].split())
            lines.append(body)
            citations.append({"id": record_id, "kind": "knowledge_item", "quote": record["text"]})
        return "\n".join(lines), citations
    cited = specific[:3] if specific else [chosen[0]]
    if not specific and chosen[-1][0] != chosen[0][0]:
        cited.append(chosen[-1])
    lines = ["Quarterly company figures from the retrieved records:"]
    citations = []
    for record_id, record in cited:
        body = " ".join(record["text"].split())
        lines.append(body)
        citations.append({"id": record_id, "kind": "knowledge_item", "quote": record["text"]})
    return "\n".join(lines), citations


def _field_ops_grounded(bundle: Bundle, query: str) -> tuple[str, list[dict]] | None:
    from kp.knowledge.field_ops import FIELD_OPS_KIND, field_ops_query

    if not field_ops_query(query):
        return None
    rows = [(record_id, record) for (kind, record_id), record in bundle.records.items() if kind == FIELD_OPS_KIND]
    if not rows:
        return None
    lines = ["Field operations rows retrieved for this question:"]
    citations = []
    for record_id, record in rows:
        body = " ".join(record["text"].split())
        lines.append(body)
        citations.append({"id": record_id, "kind": FIELD_OPS_KIND, "quote": record["text"]})
    return "\n".join(lines), citations


def _prefer_field_rows(
    query: str,
    bundle: Bundle,
    answer: str,
    citations: list[dict],
    charts: list[dict],
) -> tuple[str, list[dict], list[dict]]:
    """Keep a model answer only when it uses the retrieved field-ops rows."""
    from kp.knowledge.field_ops import FIELD_OPS_KIND, answer_uses_rows, field_ops_query

    if not field_ops_query(query):
        return answer, citations, charts
    rows = [record for (kind, _), record in bundle.records.items() if kind == FIELD_OPS_KIND]
    if not rows or answer_uses_rows(answer, rows):
        return answer, citations, charts
    grounded = _field_ops_grounded(bundle, query)
    if grounded is None:
        return answer, citations, []
    text, quotes = grounded
    return text, quotes, []


def _engineering_grounded(bundle: Bundle, query: str) -> tuple[str, list[dict]] | None:
    from kp.knowledge.engineering import ENGINEERING_KIND, engineering_query

    if not engineering_query(query):
        return None
    rows = [(record_id, record) for (kind, record_id), record in bundle.records.items() if kind == ENGINEERING_KIND]
    if not rows:
        return None
    lines = ["Engineering rows retrieved for this question:"]
    citations = []
    for record_id, record in rows:
        body = " ".join(record["text"].split())
        lines.append(body)
        citations.append({"id": record_id, "kind": ENGINEERING_KIND, "quote": record["text"]})
    return "\n".join(lines), citations


def _executive_grounded(bundle: Bundle, query: str) -> tuple[str, list[dict]] | None:
    from kp.knowledge.executive import EXECUTIVE_KIND, executive_query

    if not executive_query(query):
        return None
    rows = [(record_id, record) for (kind, record_id), record in bundle.records.items() if kind == EXECUTIVE_KIND]
    if not rows:
        return None
    lines = ["Executive rows retrieved for this question:"]
    citations = []
    for record_id, record in rows:
        body = " ".join(record["text"].split())
        lines.append(body)
        citations.append({"id": record_id, "kind": EXECUTIVE_KIND, "quote": record["text"]})
    return "\n".join(lines), citations


def _investigation_required(query: str, rows: list[dict]) -> bool:
    text = (query or "").casefold()
    for row in rows:
        body = row.get("text") or ""
        if "under investigation" not in body.casefold():
            continue
        incidents = re.findall(r"INC-\d{3}", body)
        if any(incident.casefold() in text for incident in incidents):
            return True
    return False


def _prefer_engineering_rows(
    query: str,
    bundle: Bundle,
    answer: str,
    citations: list[dict],
    charts: list[dict],
) -> tuple[str, list[dict], list[dict]]:
    from kp.knowledge.engineering import ENGINEERING_KIND, engineering_query

    if not engineering_query(query):
        return answer, citations, charts
    rows = [record for (kind, _), record in bundle.records.items() if kind == ENGINEERING_KIND]
    if not rows:
        return answer, citations, charts
    if _investigation_required(query, rows) and "under investigation" not in (answer or "").casefold():
        grounded = _engineering_grounded(bundle, query)
        if grounded is not None:
            text, quotes = grounded
            return text, quotes, []
    return answer, citations, charts


def _prefer_dataset_rows(
    query: str,
    bundle: Bundle,
    answer: str,
    citations: list[dict],
    charts: list[dict],
) -> tuple[str, list[dict], list[dict]]:
    answer, citations, charts = _prefer_field_rows(query, bundle, answer, citations, charts)
    return _prefer_engineering_rows(query, bundle, answer, citations, charts)


def _finish_citations(query: str, bundle: Bundle, answer: str, citations: list[dict]) -> list[dict]:
    """Keep model quotes that match a row. If a field-ops answer names a row and the quote missed, copy that row."""
    from kp.knowledge.field_ops import FIELD_OPS_KIND, answer_uses_rows, field_ops_query

    kept = filter_citations(citations, bundle.records)
    if kept or not field_ops_query(query):
        return kept
    rows = [record for (kind, _), record in bundle.records.items() if kind == FIELD_OPS_KIND]
    if not rows or not answer_uses_rows(answer, rows):
        return kept
    folded = (answer or "").casefold()
    filled: list[dict] = []
    for (kind, record_id), record in bundle.records.items():
        if kind != FIELD_OPS_KIND or record_id.casefold() not in folded:
            continue
        quote = " ".join(record["text"].split()[:18])
        if quote not in record["text"]:
            continue
        filled.append({"id": record_id, "kind": kind, "quote": quote})
        if len(filled) == 3:
            break
    return filter_citations(filled, bundle.records)


def _matching_records(bundle: Bundle, prefixes: list[str]) -> list[tuple[str, dict]]:
    found = []
    for (kind, record_id), record in bundle.records.items():
        if kind != "knowledge_item":
            continue
        document_id = str(record.get("document_id") or "")
        if any(document_id.startswith(prefix) for prefix in prefixes):
            found.append((record_id, record))
    found.sort(key=lambda item: item[0])
    return found


def _chart_number(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"-?\d+(?:\.\d+)?", value.replace(",", ""))
        if match:
            return float(match.group(0))
    return None


def _chart_values(points: object) -> list[dict]:
    if not isinstance(points, list):
        return []
    values = []
    for point in points:
        if not isinstance(point, dict):
            continue
        label = point.get("label") or point.get("x") or point.get("name")
        count = point.get("count")
        if count is None:
            count = point.get("y")
        if count is None:
            count = point.get("value")
        number = _chart_number(count)
        if number is None or label is None or str(label).strip() == "":
            continue
        values.append({"label": str(label), "count": number})
    return values


def _charts_from_payload(raw: object) -> list[dict]:
    """Charts the model chose. The app draws these and does not pick a topic series."""
    items = raw if isinstance(raw, list) else [raw]
    charts = []
    for item in items:
        if not isinstance(item, dict):
            continue
        values = _chart_values(item.get("points") or item.get("values") or item.get("data"))
        if not values:
            continue
        charts.append(
            {
                "title": str(item.get("title") or "Chart"),
                "y": str(item.get("y") or "Count"),
                "values": values,
            }
        )
    return charts


def _payload_object(text: str) -> dict | None:
    match = re.search(r"\{.*\}", text, re.S)
    if not match:
        return None
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


def _plain_phrase(text: str) -> str:
    stripped = _MARKDOWN_LINK.sub(r"\1", text or "")
    return " ".join(stripped.split()).strip()


def _without_numbers(text: str) -> str:
    cleaned = re.sub(r"\d+(?:\.\d+)?%?", "", _plain_phrase(text))
    cleaned = re.sub(r"\(\s*\)", "", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" -,:;/")
    return cleaned


def normalize_suggested_questions(raw: object, *, limit: int = 3) -> list[str]:
    """Keep 1 to 3 complete questions. Drop blanks, duplicates, and vague prompts."""
    items = [raw] if isinstance(raw, str) else raw
    if not isinstance(items, list):
        return []
    kept: list[str] = []
    seen: set[str] = set()
    for item in items:
        if not isinstance(item, str):
            continue
        text = _plain_phrase(item).strip("\"'")
        if not text or len(text) > 200:
            continue
        if not text.endswith("?"):
            if _QUESTION_START.match(text):
                text = f"{text}?"
            else:
                continue
        if _VAGUE_QUESTION.match(text):
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        kept.append(text)
        if len(kept) >= limit:
            break
    return kept


def model_suggested_questions(text: str) -> list[str]:
    payload = _payload_object(text)
    if payload is None:
        return []
    return normalize_suggested_questions(payload.get("suggested_questions"))


def _trailing_question(answer: str) -> str | None:
    lines = [line.strip() for line in (answer or "").splitlines() if line.strip()]
    if not lines:
        return None
    last = lines[-1]
    if last.startswith("- ") or last.startswith("* "):
        return None
    if not last.endswith("?") or last.count("?") != 1:
        return None
    if ". " in last or "! " in last:
        return None
    return last


def derive_suggested_questions(query: str, answer: str, charts: list | None = None) -> list[str]:
    """At most two follow-ups from the question and answer. No invented figures."""
    suggestions: list[str] = []
    asked = " ".join((query or "").split()).casefold().rstrip("?")

    def add(text: str) -> None:
        if len(suggestions) >= 2:
            return
        chosen = normalize_suggested_questions([text], limit=1)
        if not chosen:
            return
        if chosen[0].casefold().rstrip("?") == asked:
            return
        if any(item.casefold() == chosen[0].casefold() for item in suggestions):
            return
        suggestions.append(chosen[0])

    def mentions_market(text: str) -> bool:
        return bool(re.search(r"\bmarkets?\b", text or "", re.I))

    trailing = _trailing_question(answer)
    if trailing:
        add(trailing)
    if mentions_market(query) or mentions_market(answer or ""):
        if not any(mentions_market(item) for item in suggestions):
            add("Which markets does this refer to?")
    for chart in charts or []:
        if not isinstance(chart, dict):
            continue
        title = _without_numbers(str(chart.get("title") or ""))
        if title and title.casefold() not in {"chart", "graph"}:
            add(f"What should we drill into in {title}?")
        else:
            add("What should we drill into in this chart?")
        break
    for line in (answer or "").splitlines():
        match = _BULLET_LINE.match(line)
        if not match:
            continue
        item = _without_numbers(match.group(1).rstrip("."))
        if item and len(item) <= 80:
            add(f"What else do the records say about {item}?")
            break
    if not suggestions:
        subject = _question_subject(query)
        if subject:
            add(f"What else do the records show about {subject}?")
        else:
            add("What else do the records show about this result?")
    return suggestions


def _question_subject(query: str) -> str | None:
    text = " ".join((query or "").split()).strip().rstrip("?")
    text = re.sub(
        r"^(please\s+)?((can|could|would)\s+you\s+)?(tell me\s+|show me\s+|explain\s+)?",
        "",
        text,
        flags=re.I,
    )
    text = re.sub(
        r"^(what|why|how|when|where|which|who)\b(\s+(is|are|was|were|do|does|did|about|should|can))?\s*",
        "",
        text,
        flags=re.I,
    )
    subject = _without_numbers(text)
    if not subject or len(subject) < 3 or len(subject) > 90:
        return None
    return subject


def _remember_suggestions(bundle: Bundle, content: str, parsed: tuple | None) -> None:
    bundle.suggested_questions = model_suggested_questions(content) if parsed else []


def _drop_suggestions_if_replaced(bundle: Bundle, original: str, answer: str) -> None:
    if answer != original:
        bundle.suggested_questions = []


def _parse_agent_payload(text: str) -> tuple[str, list[dict], list[dict]] | None:
    payload = _payload_object(text)
    if payload is None:
        return None
    answer = payload.get("answer")
    citations = payload.get("citations") or []
    if isinstance(answer, list):
        answer = "\n".join(str(item).strip() for item in answer if str(item).strip())
    if not isinstance(answer, str) or not isinstance(citations, list):
        return None
    normalized = []
    for item in citations:
        if not isinstance(item, dict):
            continue
        quote = item.get("quote") or item.get("text") or ""
        kind = item.get("kind") or "knowledge_item"
        normalized.append({**item, "quote": quote, "kind": kind})
    return answer, normalized, _charts_from_payload(payload.get("chart"))


async def synthesize(
    session_id: str,
    query: str,
    bundle: Bundle,
    router_name: str = "llm",
    prior: str = "",
) -> tuple[str, list[dict], list[dict]]:
    event("skills.start", session=session_id, role=bundle.role, selector=router_name)
    if router_name == "jev":
        selected = skill_mod.select_skills_with_jev(query, bundle.role)
    else:
        selected = skill_mod.select_skills(query, bundle.role)
    bundle.selected_ids = selected
    bundle.skill_text = skill_mod.skill_bodies(selected)
    event("skills.done", session=session_id, skills=",".join(selected))
    # Kept as the fallback when the model returns nothing usable. Company
    # questions still go through the LLM so the answer follows the question.
    answer, citations = grounded_answer(bundle, query, prior)
    charts: list[dict] = []
    bundle.suggested_questions = []
    settings = get_settings()
    try:
        target = resolve_llm()
    except CloudKeyRequired:
        target = None
    if target is None or (target.provider != "ollama" and not settings.llm_api_key):
        # A cloud model needs LLM_API_KEY. A test double can return skill ids
        # without one; the model is not called. Ollama does not need a key.
        event("synthesize.grounded", session=session_id, reason="no-model")
        return answer, _finish_citations(query, bundle, answer, citations), []
    try:
        from kp.agent.factory import create_session_agent

        prompt = (
            f"{bundle.skill_text}\n\n"
            "Use only the retrieved records below. Do not invent ids, counts, or quotes. "
            "Return JSON with keys answer, citations, and suggested_questions. "
            "Each citation has id, kind, and a verbatim quote. "
            f"{_ANSWER_SHAPE}\n\n"
            f"Question: {query}\n\nRecords:\n{json.dumps(_public_records(bundle, query))}"
        )
        event("agent.start", session=session_id, provider=target.provider, model=target.model)
        if target.provider == "ollama":
            from kp.agent.sandbox import K8sSandbox

            # The sandbox must exist for a knowledge ask. The answer itself is one
            # capped completion: the deep-agent tool prompt does not finish on
            # a local model before the deadline.
            K8sSandbox(session_id).provision()
            parsed = _ollama_completion(query, bundle, prior)
            if parsed:
                original = parsed[0]
                answer, citations, charts = _prefer_dataset_rows(query, bundle, *parsed)
                _drop_suggestions_if_replaced(bundle, original, answer)
                event("agent.done", session=session_id, parsed=True)
            else:
                charts = []
                bundle.suggested_questions = []
                event("agent.done", session=session_id, parsed=False)
            event("synthesize.done", session=session_id, citations=len(citations))
            return answer, _finish_citations(query, bundle, answer, citations), charts
        agent = await create_session_agent(session_id, selected, bundle.skill_text)
        result = await asyncio.wait_for(
            agent.ainvoke(
                {"messages": [{"role": "user", "content": prompt}]},
                config={"configurable": {"thread_id": session_id}, "recursion_limit": 6},
            ),
            timeout=150,
        )
        message = result["messages"][-1]
        content = message.content if isinstance(message.content, str) else json.dumps(message.content)
        parsed = _parse_agent_payload(content)
        _remember_suggestions(bundle, content, parsed)
        if parsed:
            original = parsed[0]
            answer, citations, charts = _prefer_dataset_rows(query, bundle, *parsed)
            _drop_suggestions_if_replaced(bundle, original, answer)
            event("agent.done", session=session_id, parsed=True)
        else:
            charts = []
            event("agent.done", session=session_id, parsed=False)
    except SandboxUnavailable:
        event("agent.failed", session=session_id, error="sandbox-unavailable")
        raise
    except TimeoutError:
        logger.exception("deep agent synthesis timed out; using the grounded answer")
        event("agent.timeout", session=session_id)
        bundle.suggested_questions = []
        answer, citations = grounded_answer(bundle, query, prior)
    except Exception as exc:
        logger.exception("deep agent synthesis failed; using the grounded answer")
        event("agent.failed", session=session_id, error=type(exc).__name__)
        bundle.suggested_questions = []
        answer, citations = grounded_answer(bundle, query, prior)
    event("synthesize.done", session=session_id, citations=len(citations))
    return answer, _finish_citations(query, bundle, answer, citations), charts


def _forecast_years(text: str) -> list[str]:
    """Future years named in the question. '2027 to 2030' fills in the years between."""
    found: list[int] = []
    for match in re.findall(r"20\d{2}", text):
        year = int(match)
        if year not in found:
            found.append(year)
    future = [year for year in found if year >= 2027]
    ranged = len(future) >= 2 and (
        re.search(r"\bto\b|\bthrough\b", text) or re.search(r"20\d{2}\s*-\s*20\d{2}", text)
    )
    if ranged:
        start, end = future[0], future[-1]
        if end < start:
            start, end = end, start
        end = min(end, start + 5)
        return [str(year) for year in range(start, end + 1)]
    if future:
        return [str(year) for year in future]
    return ["the next period"]


def _forecast_labels(query: str) -> list[str]:
    """Every quarter the question names. A plural 'quarters' ask covers the whole year."""
    text = (query or "").casefold().replace("quater", "quarter")
    years = _forecast_years(text)
    named = [quarter.upper() for quarter in ("q1", "q2", "q3", "q4") if quarter in text]
    if len(named) > 1 or "quarters" in text or "quarterly" in text:
        order = ["Q1", "Q2", "Q3", "Q4"]
        quarters = [quarter for quarter in order if quarter in named] or order
        return [f"{year} {quarter}" for year in years for quarter in quarters]
    if named:
        return [f"{year} {named[0]}" for year in years]
    return years


def _forecast_label(query: str) -> str:
    labels = _forecast_labels(query)
    return labels[0] if len(labels) == 1 else ", ".join(labels)


def _ollama_completion(query: str, bundle: Bundle, prior: str = "") -> tuple[str, list[dict], list[dict]] | None:
    from kp.llm import build_openai_compatible_client

    from kp.knowledge.retrieve import _asked_years, _prompt_record_limit

    records = _compact_records(bundle, limit=_prompt_record_limit(query), query=query)
    event("synthesize.prompt", session_records=len(records))
    kinds = {row["kind"] for row in records}
    forecasting = "forecast" in query.casefold() or "project" in query.casefold() or any(
        year in query for year in ("2027", "2028", "2029", "2030", "2031", "2032")
    )
    if forecasting:
        labels = _forecast_labels(query)
        lines = [
            f"{label} forecast revenue: grid services $X million, member bill savings $Y million, and new systems $Z million."
            for label in labels
        ]
        instructions = (
            "The records are quarterly revenue history. Forecast every period below from those figures. "
            "The answer value is one string, not an array. Write one sentence per period, in this order, with numbers filled in: "
            + " ".join(f"'{line}'" for line in lines)
            + " Then one sentence that these are forecasts, not stored records. "
            "Return an empty citations array."
        )
        sentence_limit = f"answer has one sentence per period ({len(labels)} periods) plus one short note."
        predict = 512 if len(labels) <= 4 else min(2048, 120 * len(labels))
    elif "field_ops" in kinds and "engineering" not in kinds and "executive" not in kinds:
        instructions = (
            "Answer only from the field operations records. Do not invent ids, cities, statuses, or quantities. "
            "Do not answer from customer complaints. "
            "Name each van id, technician id, status, city, and job id written in the records. "
            "A part with no van_inventory row has quantity 0. "
            "The answer value is one string, not an array."
        )
        sentence_limit = "answer is at most 4 short sentences."
        predict = 512
    elif "engineering" in kinds:
        instructions = (
            "Answer only from the engineering records. Do not invent a device id, fault, firmware note, or cause. "
            "If a record says the root cause is Under Investigation, say the root cause is under investigation. "
            "Do not turn a hypothesis into a confirmed cause. "
            "The answer value is one string, not an array."
        )
        sentence_limit = "answer is at most 5 short sentences."
        predict = 512
    elif "executive" in kinds:
        instructions = (
            "Answer from the executive records. "
            "The answer string must include these labels on their own lines: FACT, TREND, POSSIBLE EXPLANATION, and UNKNOWN. "
            "Do not rank a market as best. "
            "Do not name a primary cause when staffing and inventory both coincide with a decline. "
            "Company figures are the aggregate across markets, not one market row. "
            "The answer value is one string, not an array."
        )
        sentence_limit = "answer is at most 6 short sentences."
        predict = 700
    else:
        span = [year for year in _asked_years(query) if year in {"2020", "2021", "2022", "2023", "2024", "2025", "2026"}]
        if len(span) >= 2:
            instructions = (
                "Answer only from the records. Do not invent ids, counts, or quotes. "
                f"The records cover {span[0]} through {span[-1]}. "
                "Use every matching record, and include the figures written in each one. "
                "The answer value is one string, not an array."
            )
            sentence_limit = "answer includes the figures from every matching record."
            predict = min(2048, 100 * len(span) * 4)
        else:
            instructions = (
                "Answer only from the records. Do not invent ids, counts, or quotes. "
                "If the asked period is not in the records, say it is not in the records "
                "and cite the latest matching record."
            )
            sentence_limit = "answer is at most 4 short sentences."
            predict = 512
    wants_chart = re.search(r"\b(report|chart|graph)\b", query or "", re.I)
    if wants_chart:
        instructions += (
            " The question asks for a chart, so chart is required. Do not set chart to null when a record contains a number. "
            "Return chart as one object, or a list when more than one chart is needed. "
            "Each chart has title, y, and points. Each point has label and count. count is a number, copied from the records or the previous answer. "
            "The answer must include those same figures, not only the labels. "
            "Omit a point if that count is not written there. Do not use 0 unless a record says 0. "
            "When the question says last N months, chart only the N latest months named in the records. "
            "Do not chart customer complaint themes unless the question is about complaint themes."
        )
        predict = min(4096, max(predict + 1024, 2048))
    else:
        instructions += " Set chart to null."
    predict = min(4096, predict + 220)
    if prior:
        instructions = (
            "The question refers to the previous answer. Stay on that subject. "
            "Do not switch to customer complaint themes unless that previous answer is about complaints. "
            + instructions
        )
    payload = {"question": query, "records": records}
    if prior:
        payload["previous_answer"] = prior
    body = build_openai_compatible_client().chat_completion(
        [
            {
                "role": "system",
                "content": (
                    f"{instructions} "
                    "Return JSON with keys chart, answer, citations, and suggested_questions. Write the chart first. "
                    f"{sentence_limit} citations has at most 3 items. "
                    "Each citation has id, kind, and a quote of at most 20 words copied from a record. "
                    f"{_ANSWER_SHAPE}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(payload),
            },
        ],
        timeout=120,
        num_predict=predict,
        num_ctx=8192 if len(records) > 8 or predict > 1500 else None,
    )
    usage = body.get("usage") or {}
    event("synthesize.model", output_tokens=usage.get("output_tokens"))
    content = body["choices"][0]["message"]["content"] or ""
    parsed = _parse_agent_payload(content)
    _remember_suggestions(bundle, content, parsed)
    if parsed is None:
        event("synthesize.unparsed", output_tokens=usage.get("output_tokens"), content=content[:300])
    return parsed


def _compact_records(bundle: Bundle, limit: int = 6, chars: int = 180, query: str = "") -> list[dict]:
    from kp.knowledge.field_ops import prompt_records

    rows = []
    for (kind, record_id), record in prompt_records(bundle, query)[:limit]:
        text = " ".join(record["text"].split())
        cap = 700 if kind in {"engineering", "executive"} else chars
        if len(text) > cap:
            text = text[:cap] + "..."
        rows.append({"id": record_id, "kind": kind, "text": text, "document_id": record.get("document_id")})
    return rows


def _public_records(bundle: Bundle, query: str = "") -> list[dict]:
    from kp.knowledge.field_ops import prompt_records

    rows = []
    for (kind, record_id), record in prompt_records(bundle, query):
        rows.append({"id": record_id, "kind": kind, "text": record["text"], "document_id": record.get("document_id")})
    return rows
