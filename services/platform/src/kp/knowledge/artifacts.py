"""Chart artifacts for report asks. Onboarding never calls this."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from kp.auth import session_dir
from kp.knowledge.context import refers_to_prior
from kp.models import Artifact, KnowledgeSession
from kp.read_models import engineering_dashboard, marketing_dashboard, operations_dashboard, theme_index
from kp.storage import write_session_bytes

REPORT_RE = re.compile(r"\b(report|chart|graph)\b", re.I)


def is_report(query: str) -> bool:
    return REPORT_RE.search(query or "") is not None


def _spec(title: str, values: list[dict], y_title: str = "Count") -> dict:
    return {
        "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
        "mark": "bar",
        "title": title,
        "data": {"values": values},
        "encoding": {
            "x": {"field": "label", "type": "nominal", "title": None, "sort": None},
            "y": {"field": "count", "type": "quantitative", "title": y_title},
        },
    }


def _png(title: str, values: list[dict]) -> bytes:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    ax.bar([row["label"] for row in values], [row["count"] for row in values], color="#145c45")
    ax.set_title(title)
    fig.tight_layout()
    buffer = __import__("io").BytesIO()
    fig.savefig(buffer, format="png", dpi=120)
    plt.close(fig)
    return buffer.getvalue()


def _series(db: Session, persona: str) -> tuple[str, list[dict]]:
    if persona == "operations_manager":
        payload = operations_dashboard(db)
        return "Operational blockers", [
            {"label": row["label"], "count": row["count"]} for row in payload["blockers"]
        ]
    if persona == "engineer":
        payload = engineering_dashboard(db)
        return "Technical issues", [
            {"label": row["label"], "count": row["complaint_count"]} for row in payload["technical_issues"]
        ]
    if persona == "marketing":
        payload = marketing_dashboard(db)
        return "Customer sentiment", [
            {"label": row["label"], "count": row["count"]} for row in payload["sentiment"]
        ]
    payload = theme_index(db)
    return "Customer complaint themes", [
        {"label": row["name"], "count": row["complaint_count"]} for row in payload["themes"]
    ]


_FORECAST_GRID = re.compile(
    r"(20\d{2})(?:\s+Q([1-4]))?\s+forecast revenue:\s+grid services\s+\$([0-9]+(?:\.[0-9]+)?)\s+million",
    re.I,
)


def _forecast_points(answer: str) -> list[dict]:
    """Grid-services figures the model wrote. A year with no quarter stays a year."""
    points = []
    for year, quarter, amount in _FORECAST_GRID.findall(answer or ""):
        label = f"{year} Q{quarter}" if quarter else year
        points.append({"label": label, "count": float(amount)})
    return points


def _company_charts(query: str, answer: str = "") -> list[tuple[str, list[dict], str]]:
    """One revenue chart, or separate past and forecast charts when both are asked."""
    from kp.corpus.performance import FORECAST_2026_Q4, QUARTERS

    projected = _forecast_points(answer)
    if projected:
        history = [
            {"label": row[0].replace("-", " "), "count": row[5]}
            for row in QUARTERS
            if row[0] >= "2022-Q1"
        ]
        history.append({"label": "2026 Q4", "count": FORECAST_2026_Q4[5]})
        seen = {row["label"] for row in projected}
        history = [row for row in history if row["label"] not in seen]
        y_title = "Grid services ($ million)"
        return [
            ("Past quarterly revenue", history, y_title),
            ("Forecast quarterly revenue", projected, y_title),
        ]
    single = _company_chart(query)
    return [single] if single else []


def _company_chart(query: str, answer: str = "") -> tuple[str, list[dict], str] | None:
    """Chart the quarterly company series instead of complaint themes."""
    from kp.corpus.performance import FORECAST_2026_Q4, QUARTERS
    from kp.knowledge.retrieve import _finance_query, _normalized_query
    text = _normalized_query(query)
    if not _finance_query(text):
        return None
    rows = [row for row in QUARTERS if row[0] >= "2022"]
    if "revenue" in text:
        if "forecast" in text:
            rows = [*rows, FORECAST_2026_Q4]
        return (
            "Quarterly grid services revenue",
            [{"label": row[0].replace("-", " "), "count": row[5]} for row in rows],
            "Grid services ($ million)",
        )
    return (
        "Quarterly installed homes",
        [{"label": row[0].replace("-", " "), "count": row[1]} for row in rows],
        "Installed homes",
    )


def _store_chart(db: Session, session: KnowledgeSession, title: str, values: list[dict], y_title: str) -> dict | None:
    if not values:
        return None
    spec = _spec(title, values, y_title)
    if "mark" not in spec or "encoding" not in spec or "data" not in spec:
        return None
    artifact_id = uuid.uuid4().hex[:12]
    relative_spec = f"workspace/artifacts/{artifact_id}.vega.json"
    relative_png = f"workspace/artifacts/{artifact_id}.png"
    write_session_bytes(session.id, relative_spec, __import__("json").dumps(spec, indent=2).encode())
    write_session_bytes(session.id, relative_png, _png(title, values))
    session_dir(session.id)
    db.add(
        Artifact(
            id=str(uuid.uuid4()),
            session_id=session.id,
            artifact_id=artifact_id,
            kind="chart",
            chart_type="bar",
            title=title,
            spec=spec,
            created_at=datetime.now(timezone.utc),
        )
    )
    db.flush()
    return {
        "id": artifact_id,
        "kind": "chart",
        "chart_type": "bar",
        "title": title,
        "spec": spec,
        "data_uri": f"/v1/sessions/{session.id}/artifacts/{artifact_id}",
        "image_uri": f"/v1/sessions/{session.id}/artifacts/{artifact_id}.png",
    }


def _outage_charts(query: str) -> list[tuple[str, list[dict], str]] | None:
    """Monthly customer outages. A complaint-theme chart is the wrong series for this question."""
    from kp.corpus.outages import MONTHS
    from kp.knowledge.retrieve import _outage_query

    text = (query or "").casefold()
    if not _outage_query(text):
        return None
    months = list(MONTHS)
    count = re.search(r"\b(?:last|past)\s+(\d+)\s+months?\b", text)
    if count:
        months = months[-int(count.group(1)) :]
    elif re.search(r"\blast month\b", text):
        months = months[-1:]
    values = [{"label": row[1], "count": row[2]} for row in months]
    return [("Customer outages", values, "Customers")]


def chart_plans(query: str, answer: str = "", prior: str = "") -> list[tuple[str, list[dict], str]] | None:
    """Charts for this ask. None means the persona series, including complaint themes."""
    if not is_report(query):
        return []
    outages = _outage_charts(query)
    if outages:
        return outages
    if refers_to_prior(query):
        projected = _forecast_points(prior) or _forecast_points(answer)
        if projected:
            text = (query or "").casefold()
            if any(word in text for word in ("past", "history", "actual")):
                return _company_charts(query, prior or answer)
            title = "Forecast quarterly revenue" if any(" Q" in row["label"] for row in projected) else "Forecast revenue"
            return [(title, projected, "Grid services ($ million)")]
    charts = _company_charts(query, answer)
    if charts:
        return charts
    return None


def build_artifacts(
    db: Session,
    session: KnowledgeSession,
    _query: str,
    _answer: str = "",
    _prior: str = "",
    charts: list[dict] | None = None,
) -> list[dict]:
    # The model chooses the series. A missing chart is left blank rather than
    # replaced with the persona complaint themes.
    if not charts:
        return []
    planned = [(chart["title"], chart["values"], chart.get("y") or "Count") for chart in charts if chart.get("values")]
    stored = []
    for title, values, y_title in planned:
        artifact = _store_chart(db, session, title, values, y_title)
        if artifact:
            stored.append(artifact)
    return stored
