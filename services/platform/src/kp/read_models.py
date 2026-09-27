"""Dashboard and investigation figures counted from Postgres rows."""

from __future__ import annotations

from sqlalchemy import func
from sqlalchemy.orm import Session

from kp.corpus.generate import VALUE_SENTENCES
from kp.labels import (
    BLOCKER_LABELS,
    CAUSE_LABELS,
    SAMPLE_QUESTIONS,
    TECHNICAL_LABELS,
    VALUE_LABELS,
)
from kp.persona_files import ceo_files, engineering_files, marketing_files, operations_files
from kp.models import Complaint, Document, Incident, IncidentComplaint, Issue, IssueComplaint
from kp.periods import AS_OF, CURRENT_START, PREVIOUS_START, period_of


def _iso(value) -> str:
    return value.isoformat().replace("+00:00", "Z")


def _doc_record(row: Document) -> dict:
    return {
        "id": row.id,
        "date": row.created_at.date().isoformat(),
        "region": row.region,
        "text": row.body,
        "blocker": row.blocker,
    }


def _complaint_record(row: Complaint) -> dict:
    return {
        "id": row.document_id,
        "complaint_id": row.id,
        "document_id": row.document_id,
        "date": row.created_at.date().isoformat(),
        "region": row.region,
        "text": row.text,
        "quote": row.text,
    }


def operations_dashboard(db: Session) -> dict:
    metrics = []
    for state, label in (
        ("at_risk", "At-risk installations"),
        ("open_incident", "Open operational incidents"),
        ("delayed", "Delayed installations"),
    ):
        rows = (
            db.query(Document)
            .filter(Document.source_type == "operations_ticket", Document.installation_state == state)
            .order_by(Document.created_at.desc())
            .all()
        )
        metrics.append({"key": state, "label": label, "value": len(rows), "records": [_doc_record(row) for row in rows]})

    counted = (
        db.query(Document.blocker, func.count(Document.id))
        .filter(Document.source_type == "operations_ticket", Document.blocker.isnot(None))
        .group_by(Document.blocker)
        .order_by(func.count(Document.id).desc(), Document.blocker.asc())
        .all()
    )
    blockers = []
    for name, count in counted:
        rows = (
            db.query(Document)
            .filter(Document.source_type == "operations_ticket", Document.blocker == name)
            .order_by(Document.created_at.desc())
            .all()
        )
        blockers.append(
            {
                "key": name,
                "label": BLOCKER_LABELS.get(name, name),
                "count": int(count),
                "records": [_doc_record(row) for row in rows],
            }
        )
    return {
        "persona": "operations_manager",
        "sample_question": SAMPLE_QUESTIONS["operations_manager"],
        "metrics": metrics,
        "blockers": blockers,
        "files": operations_files(),
    }


def engineering_dashboard(db: Session) -> dict:
    issues = (
        db.query(Issue)
        .filter(Issue.kind == "technical")
        .order_by(Issue.complaint_count.desc(), Issue.slug.asc())
        .all()
    )
    technical = []
    for issue in issues:
        complaints = (
            db.query(Complaint)
            .join(IssueComplaint, IssueComplaint.complaint_id == Complaint.id)
            .filter(IssueComplaint.issue_id == issue.id)
            .order_by(Complaint.created_at.desc())
            .all()
        )
        technical.append(
            {
                "key": issue.slug,
                "label": TECHNICAL_LABELS.get(issue.slug, issue.name),
                "complaint_count": issue.complaint_count,
                "records": [_complaint_record(row) for row in complaints],
            }
        )

    counted = (
        db.query(IncidentComplaint.incident_id, func.count(IncidentComplaint.complaint_id).label("n"))
        .group_by(IncidentComplaint.incident_id)
        .subquery()
    )
    ranked = (
        db.query(Incident, counted.c.n)
        .join(counted, counted.c.incident_id == Incident.id)
        .order_by(counted.c.n.desc(), Incident.id.asc())
        .limit(3)
        .all()
    )
    related = []
    for incident, count in ranked:
        complaints = (
            db.query(Complaint)
            .join(IncidentComplaint, IncidentComplaint.complaint_id == Complaint.id)
            .filter(IncidentComplaint.incident_id == incident.id)
            .all()
        )
        related.append(
            {
                "id": incident.id,
                "label": TECHNICAL_LABELS.get(incident.technical_issue or "", incident.technical_issue),
                "technical_issue": incident.technical_issue,
                "summary": incident.summary,
                "linked_conversations": int(count),
                "records": [_complaint_record(row) for row in complaints],
            }
        )
    return {
        "persona": "engineer",
        "sample_question": SAMPLE_QUESTIONS["engineer"],
        "technical_issues": technical,
        "related_incidents": related,
        "files": engineering_files(),
    }


def marketing_dashboard(db: Session) -> dict:
    total = db.query(func.count(Complaint.id)).scalar() or 0
    sentiment = []
    for key, label in (("positive", "Positive"), ("neutral", "Neutral"), ("negative", "Negative")):
        rows = (
            db.query(Complaint)
            .filter(Complaint.sentiment == key)
            .order_by(Complaint.created_at.desc())
            .all()
        )
        sentiment.append(
            {
                "key": key,
                "label": label,
                "count": len(rows),
                "share": (len(rows) / total) if total else 0,
                "records": [_complaint_record(row) for row in rows],
            }
        )
    counted = (
        db.query(Complaint.value_theme, func.count(Complaint.id))
        .filter(Complaint.value_theme.isnot(None))
        .group_by(Complaint.value_theme)
        .order_by(func.count(Complaint.id).desc(), Complaint.value_theme.asc())
        .all()
    )
    themes = []
    for key, count in counted:
        rows = (
            db.query(Complaint)
            .filter(Complaint.value_theme == key)
            .order_by(Complaint.created_at.desc())
            .all()
        )
        sentence = VALUE_SENTENCES[key]
        records = []
        for row in rows:
            quote = sentence if sentence in row.text else row.text
            records.append(
                {
                    "id": row.document_id,
                    "complaint_id": row.id,
                    "document_id": row.document_id,
                    "date": row.created_at.date().isoformat(),
                    "region": row.region,
                    "quote": quote,
                    "text": row.text,
                    "value_theme": key,
                }
            )
        themes.append(
            {
                "key": key,
                "label": VALUE_LABELS.get(key, key),
                "count": int(count),
                "records": records,
            }
        )
    return {
        "persona": "marketing",
        "sample_question": SAMPLE_QUESTIONS["marketing"],
        "sentiment": sentiment,
        "value_themes": themes,
        "files": marketing_files(),
    }


def ceo_dashboard(db: Session) -> dict:
    payload = theme_index(db)
    payload["persona"] = "ceo"
    payload["files"] = ceo_files()
    return payload


def theme_index(db: Session) -> dict:
    issues = (
        db.query(Issue)
        .filter(Issue.kind == "theme")
        .order_by(Issue.complaint_count.desc(), Issue.name.asc())
        .all()
    )
    return {
        "sample_question": SAMPLE_QUESTIONS["ceo"],
        "themes": [
            {
                "slug": issue.slug,
                "name": issue.name,
                "description": issue.description,
                "complaint_count": issue.complaint_count,
                "trend": issue.trend,
                "severity": issue.severity,
            }
            for issue in issues
        ],
    }


def investigation(db: Session, theme: str) -> dict | None:
    key = theme.strip()
    issue = (
        db.query(Issue)
        .filter((Issue.slug == key) | (func.lower(Issue.name) == key.lower()))
        .one_or_none()
    )
    if issue is None:
        return None
    complaints = (
        db.query(Complaint)
        .join(IssueComplaint, IssueComplaint.complaint_id == Complaint.id)
        .filter(IssueComplaint.issue_id == issue.id)
        .order_by(Complaint.created_at.desc())
        .all()
    )
    current = [row for row in complaints if period_of(row.created_at) == "current"]
    previous = [row for row in complaints if period_of(row.created_at) == "previous"]
    grouped: dict[str, list[Complaint]] = {}
    for row in complaints:
        grouped.setdefault(row.cause, []).append(row)
    total = len(complaints) or 1
    causes = []
    for cause, rows in sorted(grouped.items(), key=lambda item: (-len(item[1]), item[0])):
        causes.append(
            {
                "cause": cause,
                "label": CAUSE_LABELS.get(cause, cause),
                "count": len(rows),
                "share": len(rows) / total if complaints else 0,
            }
        )
    quotes = []
    for row in complaints[:4]:
        quotes.append(
            {
                "id": row.document_id,
                "complaint_id": row.id,
                "document_id": row.document_id,
                "quote": row.text,
                "region": row.region,
                "date": row.created_at.date().isoformat(),
            }
        )
    conversation_ids = [row.document_id for row in complaints]
    conversations = (
        db.query(Document)
        .filter(Document.id.in_(conversation_ids), Document.source_type == "conversation")
        .order_by(Document.created_at.desc())
        .all()
        if conversation_ids
        else []
    )
    themes = sorted({row.theme for row in complaints})
    operations = (
        db.query(Document)
        .filter(Document.source_type == "operations_ticket", Document.theme.in_(themes))
        .order_by(Document.created_at.desc())
        .all()
        if themes
        else []
    )
    complaint_ids = [row.id for row in complaints]
    incident_ids = [
        row[0]
        for row in db.query(IncidentComplaint.incident_id)
        .filter(IncidentComplaint.complaint_id.in_(complaint_ids))
        .distinct()
        .all()
    ] if complaint_ids else []
    incidents = db.query(Incident).filter(Incident.id.in_(incident_ids)).all() if incident_ids else []
    cause_order = {item["cause"]: index for index, item in enumerate(causes)}
    actions = (
        db.query(Document)
        .filter(
            Document.source_type == "internal",
            Document.theme == issue.slug,
            Document.recommended_action.isnot(None),
        )
        .all()
    )
    actions.sort(key=lambda row: cause_order.get(row.cause, 99))
    return {
        "slug": issue.slug,
        "name": issue.name,
        "description": issue.description,
        "complaint_count": issue.complaint_count,
        "current_period_count": len(current),
        "previous_period_count": len(previous),
        "trend_percent": issue.trend,
        "period": {
            "current_start": _iso(CURRENT_START),
            "previous_start": _iso(PREVIOUS_START),
            "as_of": _iso(AS_OF),
        },
        "causes": causes,
        "quotes": quotes,
        "evidence_counts": {
            "support_conversations": len(conversations),
            "operations_tickets": len(operations),
            "related_incidents": len(incidents),
        },
        "support_conversations": [_doc_record(row) for row in conversations],
        "operations_tickets": [_doc_record(row) for row in operations],
        "related_incidents": [
            {
                "id": row.id,
                "date": row.created_at.date().isoformat(),
                "region": None,
                "text": row.summary,
                "technical_issue": row.technical_issue,
            }
            for row in incidents
        ],
        "recommended_actions": [
            {"document_id": row.id, "cause": row.cause, "text": row.recommended_action}
            for row in actions
        ],
    }
