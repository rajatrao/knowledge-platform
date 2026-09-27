"""Per-ask intent routers. openJev does not fall back to the LLM."""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass

import httpx

from kp.config import get_settings
from kp.labels import PERSONA_SKILLS
from kp.llm import CloudKeyRequired, build_openai_compatible_client, resolve_llm
from kp.onboarding.fields import (
    extract_customer_params,
    extract_params,
    kind_for_workflow,
    parse_specialist,
    specialist_catalog,
)
from kp.reports.intents import CUSTOMER_ONBOARD_WORKFLOW, ONBOARD_WORKFLOW, allowed_workflow, catalog_workflows

WORKFLOW_NAME = ONBOARD_WORKFLOW
CUSTOMER_WORKFLOW_NAME = CUSTOMER_ONBOARD_WORKFLOW


class JevUnavailable(RuntimeError):
    """router=jev was requested and the local openJev service did not answer."""


@dataclass
class Telemetry:
    router: str
    model: str
    latency_ms: int
    input_tokens: int
    output_tokens: int
    estimated_cost_usd: float

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass
class RouteDecision:
    kind: str
    name: str
    params: dict
    reason: str
    telemetry: Telemetry

    def as_dict(self) -> dict:
        return {"kind": self.kind, "name": self.name, "params": self.params, "reason": self.reason}


def _tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _cost(model: str, input_tokens: int, output_tokens: int, local: bool = False) -> float:
    if local:
        return 0.0
    prices = {
        "deterministic-router": (0.0, 0.0),
        "gpt-4o-mini": (0.15 / 1_000_000, 0.60 / 1_000_000),
        "jev-router": (0.10 / 1_000_000, 0.0),
    }
    input_price, output_price = prices.get(model, (0.15 / 1_000_000, 0.60 / 1_000_000))
    return round(input_tokens * input_price + output_tokens * output_price, 6)


def load_skill(path) -> dict:
    text = path.read_text()
    _, front, body = text.split("---", 2)
    meta: dict[str, str] = {}
    for line in front.strip().splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        meta[key.strip()] = value.strip().strip('"')
    meta["body"] = body.strip()
    return meta


def catalog_for(persona: str) -> dict:
    settings = get_settings()
    skill_name = PERSONA_SKILLS[persona]
    skill = load_skill(settings.skills_root / "functions" / persona / skill_name / "SKILL.md")
    brief = load_skill(settings.skills_root / "foundational" / "base-power-orientation" / "SKILL.md")
    return {
        "workflows": [
            {
                "name": WORKFLOW_NAME,
                "description": (
                    "Onboard an employee, not a customer. "
                    "Params: name, email, and role (ceo, operations_manager, engineer, marketing)."
                ),
                "params": ["name", "email", "role"],
            },
            {
                "name": CUSTOMER_WORKFLOW_NAME,
                "description": (
                    "Onboard a company or household customer, not an employee. "
                    "Params: name, email, city, and system type "
                    "(whole-home battery, commercial storage, backup)."
                ),
                "params": ["name", "email", "city", "system_type"],
            },
            *specialist_catalog(),
            *catalog_workflows(persona),
        ],
        "skills": [
            {"name": skill["name"], "description": skill["description"]},
            {"name": brief["name"], "description": brief["description"]},
        ],
    }


def _extracted(name: str, query: str) -> dict:
    if name == CUSTOMER_WORKFLOW_NAME:
        return extract_customer_params(query)
    kind = kind_for_workflow(name)
    if kind:
        return parse_specialist(kind, query)
    return extract_params(query)


def _decision(router: str, model: str, kind: str, name: str, params: dict, reason: str, prompt: str, started: float, output_tokens: int | None = None, local: bool = False, input_tokens: int | None = None) -> RouteDecision:
    if input_tokens is None:
        input_tokens = _tokens(prompt)
    if output_tokens is None:
        output_tokens = _tokens(json.dumps({"kind": kind, "name": name, "params": params, "reason": reason}))
    return RouteDecision(
        kind=kind,
        name=name,
        params=params,
        reason=reason,
        telemetry=Telemetry(
            router=router,
            model=model,
            latency_ms=int((time.perf_counter() - started) * 1000),
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            estimated_cost_usd=_cost(model, input_tokens, output_tokens, local=local),
        ),
    )


def _coerce(persona: str, query: str, kind: str, name: str) -> tuple[str, str]:
    del kind, name
    chosen = allowed_workflow(persona, query)
    if chosen:
        return "workflow", chosen
    return "skill", PERSONA_SKILLS[persona]


def _load_object(content: str) -> dict | None:
    text = (content or "").strip()
    if not text:
        return None
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, dict):
        return None
    return payload


class LlmRouter:
    name = "llm"

    def route(self, persona: str, query: str, turns: list[dict]) -> RouteDecision:
        started = time.perf_counter()
        catalog = catalog_for(persona)
        prompt = json.dumps({"catalog": catalog, "turns": turns[-6:], "query": query})
        try:
            target = resolve_llm()
        except CloudKeyRequired:
            return self._deterministic(persona, query, prompt, started)
        return self._model(persona, query, prompt, started, target)

    def _deterministic(self, persona: str, query: str, prompt: str, started: float) -> RouteDecision:
        chosen = allowed_workflow(persona, query)
        params = _extracted(chosen or "", query)
        if chosen == CUSTOMER_WORKFLOW_NAME:
            kind, name = "workflow", CUSTOMER_WORKFLOW_NAME
            reason = "The message asks to onboard a customer."
        elif chosen == WORKFLOW_NAME:
            kind, name = "workflow", WORKFLOW_NAME
            reason = "The message asks to onboard an employee."
        elif chosen:
            kind, name = "workflow", chosen
            reason = f"The message asks for the {chosen} workflow."
        else:
            kind, name = "skill", PERSONA_SKILLS[persona]
            reason = "The message is a knowledge question for this persona."
        return _decision("llm", "deterministic-router", kind, name, params, reason, prompt, started)

    def _model(self, persona: str, query: str, prompt: str, started: float, target) -> RouteDecision:
        client = build_openai_compatible_client()
        body = client.chat_completion(
            [
                {
                    "role": "system",
                    "content": (
                        "Choose one route. Return one JSON object with kind (workflow or skill), "
                        "name, params, and reason. reason is at most 12 words. Use only the catalog."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            num_predict=96,
        )
        content = body["choices"][0]["message"]["content"]
        parsed = _load_object(content)
        if parsed is None:
            decision = self._deterministic(persona, query, prompt, started)
            decision.reason = "The model route was not valid JSON, so the deterministic route was used."
            return decision
        kind, name = _coerce(persona, query, parsed.get("kind", ""), parsed.get("name", ""))
        usage = body.get("usage") or {}
        raw_params = parsed.get("params")
        params = raw_params if isinstance(raw_params, dict) else {}
        reason = parsed.get("reason")
        if not isinstance(reason, str) or not reason.strip():
            reason = "LLM router decision."
        return _decision(
            "llm",
            target.model,
            kind,
            name,
            _extracted(name, query) | (params if isinstance(params, dict) else {}),
            reason,
            prompt,
            started,
            output_tokens=int(usage.get("completion_tokens") or _tokens(content)),
            local=target.provider == "ollama",
        )


# A workflow starts only when openJev assigns it most of the probability.
# Knowledge questions land near 0.3 across several labels; an explicit
# "issue trend report" or onboarding ask lands near 0.7.
WORKFLOW_MIN_PROBABILITY = 0.5


def _route_criteria(persona: str) -> dict[str, str]:
    criteria = {}
    for workflow in catalog_for(persona)["workflows"]:
        name = workflow["name"]
        if name == WORKFLOW_NAME:
            criteria[name] = (
                "Start onboard_employee only when the user explicitly asks to onboard an employee or new hire. "
                "Do not choose this for a customer, field technician, electrician, installer partner, contractor, "
                "warehouse associate, engineer onboard, operations manager onboard, new market, or warehouse launch."
            )
        elif name == CUSTOMER_WORKFLOW_NAME:
            criteria[name] = (
                "Start onboard_customer only when the user explicitly asks to onboard a customer, company, or household. "
                "Do not choose this for an employee or for field technician, installer, warehouse, engineer, "
                "operations manager, or market launch onboarding."
            )
        elif workflow.get("criteria"):
            criteria[name] = workflow["criteria"]
        else:
            criteria[name] = f"Start the {name} workflow only when the user explicitly asks to run it."
    criteria["knowledge"] = (
        "Answer from knowledge and skills. Use this for questions, charts, regions, "
        "complaints, revenue, and investigations unless the user asks to run a named workflow."
    )
    return criteria


def _openjev_state(persona: str, query: str, turns: list[dict]) -> str:
    recent = "\n".join(f"{turn.get('role', 'user')}: {turn.get('content', '')}" for turn in turns[-6:])
    parts = [f"Persona: {persona}"]
    if recent:
        parts.append(recent)
    parts.append(f"User: {query}")
    return "\n".join(parts)


def jev_systemone(state: str, questions: dict) -> dict:
    """One local openJev decision. A failed call is an error, not an LLM route."""
    settings = get_settings()
    base = settings.jev_base_url.rstrip("/")
    payload = {"model": settings.jev_model, "state": state, "questions": questions}
    headers = {}
    if settings.jev_api_key:
        headers["Authorization"] = f"Bearer {settings.jev_api_key}"
    url = f"{base}/v1/systemone"
    try:
        response = httpx.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise JevUnavailable(f"openJev at {base} returned {exc.response.status_code}") from exc
    except httpx.HTTPError as exc:
        raise JevUnavailable(f"openJev at {base} is unreachable") from exc
    parsed = response.json()
    if not isinstance(parsed, dict):
        raise JevUnavailable("openJev returned an unexpected decision")
    return parsed


class JevRouter:
    name = "jev"

    def route(self, persona: str, query: str, turns: list[dict]) -> RouteDecision:
        settings = get_settings()
        started = time.perf_counter()
        criteria = _route_criteria(persona)
        state = _openjev_state(persona, query, turns)
        parsed = jev_systemone(
            state,
            {
                "route": {
                    "type": "choice",
                    "instructions": (
                        "Which route should handle this message? "
                        "Choose knowledge unless the user explicitly asks to run one named workflow."
                    ),
                    "criteria": criteria,
                }
            },
        )
        route_answer = (parsed.get("answers") or {}).get("route") or {}
        choice = route_answer.get("choice")
        if not isinstance(choice, str) or not choice:
            raise JevUnavailable("openJev returned an unexpected decision")
        probabilities = route_answer.get("probabilities") or {}
        probability = probabilities.get(choice)
        workflow = (
            choice in criteria
            and choice != "knowledge"
            and isinstance(probability, (int, float))
            and probability >= WORKFLOW_MIN_PROBABILITY
        )
        if workflow:
            kind, name = "workflow", choice
        else:
            kind, name = "skill", PERSONA_SKILLS[persona]
        usage = parsed.get("usage") or {}
        confidence = route_answer.get("confidence")
        if workflow:
            if isinstance(confidence, (int, float)):
                reason = f"openJev chose {choice} (confidence {confidence:.2f})."
            else:
                reason = f"openJev chose {choice}."
        elif choice == "knowledge":
            reason = "openJev chose a knowledge skill."
        else:
            shown = f"{probability:.2f}" if isinstance(probability, (int, float)) else "n/a"
            reason = (
                f"openJev labeled {choice} at probability {shown}, "
                "below the workflow threshold, so this stays a knowledge skill."
            )
        return _decision(
            "jev",
            parsed.get("model") or settings.jev_model,
            kind,
            name,
            _extracted(name, query),
            reason,
            state,
            started,
            output_tokens=int(usage.get("output_tokens") or 0),
            local=True,
            input_tokens=int(usage["input_tokens"]) if usage.get("input_tokens") is not None else None,
        )


def router_for(name: str):
    if name == "jev":
        return JevRouter()
    if name == "llm":
        return LlmRouter()
    raise ValueError(name)
