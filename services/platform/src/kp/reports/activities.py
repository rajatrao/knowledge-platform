"""Report activities. Each one reads Postgres and returns the query result."""

from __future__ import annotations

from temporalio import activity

from kp.db import SessionLocal
from kp.reports.queries import READERS


def _bind(name: str):
    @activity.defn(name=name)
    def run(params: dict | None = None) -> dict:
        db = SessionLocal()
        try:
            return READERS[name](db, params)
        finally:
            db.close()

    run.__name__ = name
    return run


issue_trend_report = _bind("issue_trend_report")
severity_digest = _bind("severity_digest")
blocker_ranking = _bind("blocker_ranking")
installation_risk_report = _bind("installation_risk_report")
technical_issue_counts = _bind("technical_issue_counts")
related_incident_report = _bind("related_incident_report")
sentiment_breakdown = _bind("sentiment_breakdown")
value_theme_counts = _bind("value_theme_counts")

REPORT_ACTIVITIES = [
    issue_trend_report,
    severity_digest,
    blocker_ranking,
    installation_risk_report,
    technical_issue_counts,
    related_incident_report,
    sentiment_breakdown,
    value_theme_counts,
]
