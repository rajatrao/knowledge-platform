"""Postgres readers for persona reports. Counts are the rows that were read."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from kp.labels import BLOCKER_CAUSE, BLOCKER_LABELS, TECHNICAL_LABELS, VALUE_LABELS
from kp.models import Complaint, Document, Incident, IncidentComplaint, Issue, IssueComplaint

_SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}
_INSTALLATION_STATES = (
    ("at_risk", "At-risk installations"),
    ("open_incident", "Open operational incidents"),
    ("delayed", "Delayed installations"),
)
_SENTIMENTS = (
    ("positive", "Positive"),
    ("neutral", "Neutral"),
    ("negative", "Negative"),
)


def _iso(value) -> str:
    text = value.isoformat()
    if text.endswith("+00:00"):
        return text.replace("+00:00", "Z")
    return text


def _ignore(params: dict | None) -> None:
    """Reports have no required fields. Missing or extra params still read the full corpus."""
    del params


def issue_trend_report(db: Session, params: dict | None = None) -> dict:
    _ignore(params)
    issues = (
        db.query(Issue)
        .order_by(Issue.complaint_count.desc(), Issue.slug.asc())
        .all()
    )
    return {
        "workflow": "issue_trend_report",
        "issues": [
            {
                "id": issue.id,
                "slug": issue.slug,
                "name": issue.name,
                "kind": issue.kind,
                "complaint_count": issue.complaint_count,
                "trend": issue.trend,
                "severity": issue.severity,
                "first_seen": _iso(issue.first_seen),
                "last_seen": _iso(issue.last_seen),
            }
            for issue in issues
        ],
    }


def _complaint_ids_for_issue(db: Session, issue_id: str) -> list[str]:
    rows = (
        db.query(IssueComplaint.complaint_id)
        .filter(IssueComplaint.issue_id == issue_id)
        .order_by(IssueComplaint.complaint_id.asc())
        .all()
    )
    return [row[0] for row in rows]


def severity_digest(db: Session, params: dict | None = None) -> dict:
    _ignore(params)
    issues = db.query(Issue).all()
    grouped: dict[str, list[dict]] = {}
    for issue in issues:
        complaint_ids = _complaint_ids_for_issue(db, issue.id)
        grouped.setdefault(issue.severity, []).append(
            {
                "id": issue.id,
                "slug": issue.slug,
                "name": issue.name,
                "complaint_count": issue.complaint_count,
                "complaint_ids": complaint_ids,
            }
        )
    severities = []
    for severity in sorted(grouped, key=lambda name: (_SEVERITY_ORDER.get(name, 99), name)):
        rows = sorted(grouped[severity], key=lambda item: (-item["complaint_count"], item["slug"]))
        severities.append({"severity": severity, "issues": rows})
    return {"workflow": "severity_digest", "severities": severities}


def blocker_ranking(db: Session, params: dict | None = None) -> dict:
    _ignore(params)
    names = [
        row[0]
        for row in db.query(Document.blocker)
        .filter(Document.source_type == "operations_ticket", Document.blocker.isnot(None))
        .distinct()
        .all()
    ]
    blockers = []
    for name in names:
        tickets = (
            db.query(Document.id)
            .filter(Document.source_type == "operations_ticket", Document.blocker == name)
            .order_by(Document.id.asc())
            .all()
        )
        ticket_ids = [row[0] for row in tickets]
        cause = BLOCKER_CAUSE.get(name)
        if cause:
            complaints = (
                db.query(Complaint.id)
                .filter(Complaint.cause == cause)
                .order_by(Complaint.id.asc())
                .all()
            )
            complaint_ids = [row[0] for row in complaints]
        else:
            complaint_ids = []
        blockers.append(
            {
                "key": name,
                "label": BLOCKER_LABELS.get(name, name),
                "count": len(ticket_ids),
                "ticket_ids": ticket_ids,
                "complaint_ids": complaint_ids,
            }
        )
    blockers.sort(key=lambda item: (-item["count"], item["key"]))
    return {"workflow": "blocker_ranking", "blockers": blockers}


def installation_risk_report(db: Session, params: dict | None = None) -> dict:
    _ignore(params)
    groups = []
    for key, label in _INSTALLATION_STATES:
        rows = (
            db.query(Document.id)
            .filter(Document.source_type == "operations_ticket", Document.installation_state == key)
            .order_by(Document.id.asc())
            .all()
        )
        source_ids = [row[0] for row in rows]
        groups.append(
            {
                "key": key,
                "label": label,
                "count": len(source_ids),
                "source_ids": source_ids,
            }
        )
    return {"workflow": "installation_risk_report", "installations": groups}


def technical_issue_counts(db: Session, params: dict | None = None) -> dict:
    _ignore(params)
    issues = (
        db.query(Issue)
        .filter(Issue.kind == "technical")
        .order_by(Issue.complaint_count.desc(), Issue.slug.asc())
        .all()
    )
    technical = []
    for issue in issues:
        complaint_ids = _complaint_ids_for_issue(db, issue.id)
        if complaint_ids:
            linked = (
                db.query(Incident.id, func.count(IncidentComplaint.complaint_id))
                .join(IncidentComplaint, IncidentComplaint.incident_id == Incident.id)
                .filter(IncidentComplaint.complaint_id.in_(complaint_ids))
                .group_by(Incident.id)
                .order_by(func.count(IncidentComplaint.complaint_id).desc(), Incident.id.asc())
                .all()
            )
            incident_ids = [row[0] for row in linked]
        else:
            incident_ids = []
        technical.append(
            {
                "key": issue.slug,
                "label": TECHNICAL_LABELS.get(issue.slug, issue.name),
                "complaint_count": issue.complaint_count,
                "complaint_ids": complaint_ids,
                "incident_ids": incident_ids,
            }
        )
    return {"workflow": "technical_issue_counts", "technical_issues": technical}


def related_incident_report(db: Session, params: dict | None = None) -> dict:
    _ignore(params)
    incidents = db.query(Incident).order_by(Incident.id.asc()).all()
    ranked = []
    for incident in incidents:
        rows = (
            db.query(IncidentComplaint.complaint_id)
            .filter(IncidentComplaint.incident_id == incident.id)
            .order_by(IncidentComplaint.complaint_id.asc())
            .all()
        )
        complaint_ids = [row[0] for row in rows]
        ranked.append(
            {
                "id": incident.id,
                "summary": incident.summary,
                "technical_issue": incident.technical_issue,
                "linked_complaints": len(complaint_ids),
                "complaint_ids": complaint_ids,
            }
        )
    ranked.sort(key=lambda item: (-item["linked_complaints"], item["id"]))
    return {"workflow": "related_incident_report", "incidents": ranked}


def sentiment_breakdown(db: Session, params: dict | None = None) -> dict:
    _ignore(params)
    total = int(db.query(func.count(Complaint.id)).scalar() or 0)
    by_key: dict[str, list[Complaint]] = {}
    for row in db.query(Complaint).order_by(Complaint.id.asc()).all():
        if row.sentiment:
            by_key.setdefault(row.sentiment, []).append(row)
    ordered = [key for key, _label in _SENTIMENTS]
    for key in sorted(by_key):
        if key not in ordered:
            ordered.append(key)
    labels = dict(_SENTIMENTS)
    sentiments = []
    for key in ordered:
        rows = by_key.get(key, [])
        count = len(rows)
        sentiments.append(
            {
                "key": key,
                "label": labels.get(key, key),
                "count": count,
                "share": (count / total) if total else 0,
                "complaint_ids": [row.id for row in rows],
                "document_ids": [row.document_id for row in rows],
            }
        )
    return {"workflow": "sentiment_breakdown", "total": total, "sentiments": sentiments}


def value_theme_counts(db: Session, params: dict | None = None) -> dict:
    _ignore(params)
    rows = (
        db.query(Complaint)
        .filter(Complaint.value_theme.isnot(None))
        .order_by(Complaint.id.asc())
        .all()
    )
    grouped: dict[str, list[str]] = {}
    for row in rows:
        grouped.setdefault(row.value_theme, []).append(row.document_id)
    themes = [
        {
            "key": key,
            "label": VALUE_LABELS.get(key, key),
            "count": len(document_ids),
            "document_ids": document_ids,
        }
        for key, document_ids in grouped.items()
    ]
    themes.sort(key=lambda item: (-item["count"], item["key"]))
    return {"workflow": "value_theme_counts", "value_themes": themes}


READERS = {
    "issue_trend_report": issue_trend_report,
    "severity_digest": severity_digest,
    "blocker_ranking": blocker_ranking,
    "installation_risk_report": installation_risk_report,
    "technical_issue_counts": technical_issue_counts,
    "related_incident_report": related_incident_report,
    "sentiment_breakdown": sentiment_breakdown,
    "value_theme_counts": value_theme_counts,
}
