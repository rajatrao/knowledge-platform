"""Knowledge and evidence loaded before synthesis. Nothing here is invented."""

from __future__ import annotations

from sqlalchemy.orm import Session

from kp.labels import BLOCKER_CAUSE, BLOCKER_LABELS, CAUSE_LABELS, PERSONA_SKILLS
from kp.models import Complaint, Document, Incident, KnowledgeItem
from kp.read_models import engineering_dashboard, marketing_dashboard, operations_dashboard, theme_index


class Bundle:
    def __init__(self, skill: str, payload: dict):
        self.skill = skill
        self.payload = payload
        self.records: dict[tuple[str, str], dict] = {}
        self.skill_text = ""
        self.role = ""
        self.selected_ids: list[str] = []

    def add(self, kind: str, record_id: str, text: str, document_id: str | None = None) -> None:
        self.records[(kind, record_id)] = {"text": text, "document_id": document_id}


def retrieve(db: Session, persona: str, skill: str) -> Bundle:
    if skill == "customer-complaints":
        payload = theme_index(db)
        bundle = Bundle(skill, payload)
        for theme in payload["themes"]:
            bundle.add("issue", f"iss_{theme['slug']}", f"{theme['name']}\n{theme['description']}")
            items = db.query(KnowledgeItem).filter(KnowledgeItem.issue_id == f"iss_{theme['slug']}").all()
            for item in items:
                bundle.add("knowledge_item", item.id, item.body, item.document_id)
    elif skill == "complaint-drivers":
        payload = operations_dashboard(db)
        bundle = Bundle(skill, payload)
        for blocker in payload["blockers"]:
            cause = BLOCKER_CAUSE[blocker["key"]]
            complaints = (
                db.query(Complaint)
                .filter(Complaint.cause == cause)
                .order_by(Complaint.created_at.desc())
                .limit(3)
                .all()
            )
            for complaint in complaints:
                bundle.add("complaint", complaint.id, complaint.text, complaint.document_id)
            for record in blocker["records"][:5]:
                document = db.get(Document, record["id"])
                if document:
                    bundle.add("document", document.id, document.body)
    elif skill == "complaint-incidents":
        payload = engineering_dashboard(db)
        bundle = Bundle(skill, payload)
        for issue in payload["technical_issues"]:
            bundle.add("issue", f"iss_{issue['key']}", f"{issue['label']}\n{issue['key']}")
            for record in issue["records"][:3]:
                bundle.add("complaint", record["complaint_id"], record["text"], record["document_id"])
        for incident in payload["related_incidents"]:
            row = db.get(Incident, incident["id"])
            if row:
                bundle.add("incident", row.id, row.summary)
    elif skill == "value-language":
        payload = marketing_dashboard(db)
        bundle = Bundle(skill, payload)
        for theme in payload["value_themes"]:
            for record in theme["records"][:3]:
                bundle.add("complaint", record["complaint_id"], record["text"], record["document_id"])
            docs = (
                db.query(Document)
                .filter(Document.theme == "value_language", Document.cause == theme["key"])
                .all()
            )
            for doc in docs:
                bundle.add("knowledge_item", f"ki_{doc.id}", doc.recommended_action or doc.body, doc.id)
                bundle.add("document", doc.id, doc.body)
    else:
        allowed = PERSONA_SKILLS[persona]
        return retrieve(db, persona, allowed)
    bundle.role = persona
    bundle.payload["blocker_labels"] = BLOCKER_LABELS
    bundle.payload["cause_labels"] = CAUSE_LABELS
    return bundle


_COMPANY_TERMS = (
    "revenue",
    "ercot",
    "grid",
    "savings",
    "fleet",
    "mwh",
    "settlement",
    "company performance",
    "installed homes",
    "quarter",
    "historical",
    "annual",
    "yearly",
    "2020",
    "2021",
    "2022",
    "2023",
    "2024",
    "2025",
    "warehouse",
    "inventory",
    "on-hand",
    "on hand",
    "sku",
    "forecast",
    "shortage",
    "shortfall",
    "days of cover",
    "stock",
)
def _quarterly_doc(document_id: str) -> bool:
    return document_id in {"doc_perf_quarters", "doc_rev_quarters"} or document_id.startswith(
        ("doc_qp_", "doc_qr_")
    )
_INVENTORY_DOCS = {"doc_wh_onhand", "doc_wh_forecast"}
_OUTAGE_TERMS = ("outage", "outages", "blackout", "lost power", "power loss")
_ERCOT_DOCS = {"doc_ercot_20260915", "doc_ercot_2026"}
_ERCOT_TERMS = ("ercot", "lz_", "settlement price", "system load")
_INVENTORY_TERMS = (
    "warehouse",
    "inventory",
    "on-hand",
    "on hand",
    "sku",
    "forecast",
    "shortage",
    "shortfall",
    "days of cover",
    "cabinet",
    "stock",
)
_HISTORY_TERMS = ("quarter", "historical", "annual", "yearly", "2020", "2021", "2022", "2023", "2024", "2025", "2026")


def _normalized_query(query: str) -> str:
    return (query or "").casefold().replace("quater", "quarter")


def _asked_years(text: str) -> list[str]:
    """Years in the question. '2024 to 2026' includes 2025."""
    text = _normalized_query(text)
    catalog = [str(year) for year in range(2020, 2033)]
    present = [int(year) for year in catalog if year in text]
    ranged = len(present) >= 2 and (
        " to " in text or " through " in text or any(f"{year}-" in text or f"{year} -" in text for year in present)
    )
    if ranged:
        start, end = min(present), max(present)
        end = min(end, start + 8)
        return [str(year) for year in range(start, end + 1)]
    return [str(year) for year in present]


def _prompt_record_limit(query: str) -> int:
    """A multi-year revenue question needs every quarter, not the first six records."""
    from kp.knowledge.engineering import engineering_query
    from kp.knowledge.executive import executive_query
    from kp.knowledge.field_ops import field_ops_query

    text = _normalized_query(query)
    if not _finance_query(text) and not _outage_query(text):
        if engineering_query(text):
            return 32
        if executive_query(text):
            return 28
        if field_ops_query(text):
            return 24
    corpus = {"2020", "2021", "2022", "2023", "2024", "2025", "2026"}
    years = [year for year in _asked_years(query) if year in corpus]
    if len(years) >= 2:
        return min(20, len(years) * 4 + 1)
    return 6


def _finance_query(text: str) -> bool:
    """Company performance and revenue, including the quarterly misspelling."""
    complaint = any(
        word in text for word in ("complaint", "battery", "billing", "firmware", "installation", "app problem")
    )
    company = any(word in text for word in ("revenue", "company", "quarter", "fleet", "homes", "grid"))
    if "performance" in text and complaint and not company:
        return False
    return any(word in text for word in ("revenue", "performance", "quarter"))


def _outage_query(text: str) -> bool:
    return any(term in text for term in _OUTAGE_TERMS)


def include_company_records(db: Session, bundle: Bundle, query: str) -> None:
    """Put company or outage records ahead of complaint evidence when the question asks for them."""
    text = _normalized_query(query)
    outage = _outage_query(text)
    company = any(term in text for term in _COMPANY_TERMS) or _finance_query(text)
    if not outage and not company:
        return
    source_types = []
    if company:
        source_types.extend(("company_performance", "revenue", "ercot", "warehouse_inventory"))
    if outage:
        source_types.append("customer_outage")
    items = (
        db.query(KnowledgeItem)
        .join(Document, KnowledgeItem.document_id == Document.id)
        .filter(Document.source_type.in_(tuple(source_types)))
        .order_by(KnowledgeItem.id.asc())
        .all()
    )
    if not items:
        return
    items = sorted(items, key=lambda item: _company_sort_key(item, text))
    existing = list(bundle.records.items())
    bundle.records.clear()
    for item in items:
        bundle.add("knowledge_item", item.id, item.body, item.document_id)
    for key, value in existing:
        bundle.records.setdefault(key, value)


def _company_sort_key(item, text: str) -> tuple:
    """Quarterly performance and revenue come first for those questions."""
    text = _normalized_query(text)
    if _outage_query(text):
        document_id = str(item.document_id or "")
        if not document_id.startswith("doc_outage_"):
            return (2, item.id)
        if item.id == "ki_outage_summary":
            return (0, "")
        return (1, "".join(chr(255 - ord(char)) for char in item.id))
    if _finance_query(text) and not any(term in text for term in _ERCOT_TERMS):
        document_id = str(item.document_id or "")
        body = getattr(item, "body", "") or ""
        want_revenue = "revenue" in text
        want_performance = "performance" in text and not want_revenue
        if want_revenue and document_id.startswith("doc_qr_"):
            group = 0
        elif want_performance and document_id.startswith("doc_qp_"):
            group = 0
        elif document_id.startswith(("doc_qr_", "doc_qp_")):
            group = 1
        elif _quarterly_doc(document_id):
            group = 2
        else:
            group = 3
        corpus_years = ("2020", "2021", "2022", "2023", "2024", "2025", "2026")
        asked_years = _asked_years(text)
        named = [
            f"{year} {quarter.upper()}"
            for year in asked_years
            for quarter in ("q1", "q2", "q3", "q4")
            if quarter in text and year in corpus_years
        ]
        matched = bool(named) and any(label in body for label in named)
        in_span = any(year in body for year in asked_years if year in corpus_years)
        forecasting = "forecast" in text and "forecast" in body.casefold()
        latest_first = "forecast" in text or any(year not in corpus_years for year in asked_years)
        priority = 0 if matched or forecasting or in_span else 1
        chrono = item.id
        if latest_first and not matched:
            chrono = "".join(chr(255 - ord(char)) for char in item.id)
        return (group, priority, chrono)
    if any(term in text for term in _ERCOT_TERMS):
        return (0 if item.document_id in _ERCOT_DOCS else 1, item.id)
    if any(term in text for term in _INVENTORY_TERMS):
        return (0 if str(item.document_id).startswith("doc_wh_") else 1, item.id)
    quarterly = _quarterly_doc(item.document_id)
    if not any(term in text for term in _HISTORY_TERMS):
        return (0 if not quarterly else 1, item.id)
    years = [year for year in ("2020", "2021", "2022", "2023", "2024", "2025", "2026") if year in text]
    named = [
        f"{year} {quarter.upper()}"
        for year in years
        for quarter in ("q1", "q2", "q3", "q4")
        if quarter in text
    ]
    if quarterly and named and any(label in item.body for label in named):
        return (0, item.id)
    if quarterly and any(year in item.body for year in years):
        return (1 if named else 0, item.id)
    if quarterly:
        return (1, item.id)
    return (2, item.id)
