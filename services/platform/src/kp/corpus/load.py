"""Load the generated corpus into Postgres in one transaction."""

from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import delete
from sqlalchemy.orm import Session

from kp.corpus.generate import generate_corpus, parse_time
from kp.models import (
    Complaint,
    Document,
    Incident,
    IncidentComplaint,
    Issue,
    IssueComplaint,
    KnowledgeItem,
)


def write_corpus_files(corpus: dict, directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    files = {
        "conversations.json": corpus["conversations"],
        "operations_tickets.json": corpus["operations_tickets"],
        "incidents.json": corpus["incidents"],
        "documents.json": corpus["documents"],
        "performance.json": [row for row in corpus["all_documents"] if row["source_type"] == "company_performance"],
        "revenue.json": [row for row in corpus["all_documents"] if row["source_type"] == "revenue"],
        "ercot.json": [row for row in corpus["all_documents"] if row["source_type"] == "ercot"],
        "inventory.json": [row for row in corpus["all_documents"] if row["source_type"] == "warehouse_inventory"],
        "outages.json": [row for row in corpus["all_documents"] if row["source_type"] == "customer_outage"],
    }
    for name, payload in files.items():
        (directory / name).write_text(json.dumps(payload, indent=2))


def load_corpus(db: Session, corpus: dict | None = None) -> dict:
    corpus = corpus or generate_corpus()
    for model in (
        IncidentComplaint,
        IssueComplaint,
        KnowledgeItem,
        Incident,
        Issue,
        Complaint,
        Document,
    ):
        db.execute(delete(model))

    for row in corpus["all_documents"]:
        db.add(
            Document(
                id=row["id"],
                source_type=row["source_type"],
                title=row["title"],
                body=row["body"],
                region=row["region"],
                channel=row["channel"],
                theme=row["theme"],
                cause=row["cause"],
                recommended_action=row["recommended_action"],
                installation_state=row["installation_state"],
                blocker=row["blocker"],
                sentiment=row["sentiment"],
                value_theme=row["value_theme"],
                technical_issue=row["technical_issue"],
                created_at=parse_time(row["created_at"]),
            )
        )
    db.flush()
    for row in corpus["complaints"]:
        db.add(
            Complaint(
                id=row["id"],
                document_id=row["document_id"],
                text=row["text"],
                theme=row["theme"],
                cause=row["cause"],
                region=row["region"],
                sentiment=row["sentiment"],
                value_theme=row["value_theme"],
                technical_issue=row["technical_issue"],
                created_at=parse_time(row["created_at"]),
            )
        )
    db.flush()
    for row in corpus["issues"]:
        db.add(
            Issue(
                id=row["id"],
                slug=row["slug"],
                name=row["name"],
                description=row["description"],
                complaint_count=row["complaint_count"],
                trend=row["trend"],
                severity=row["severity"],
                first_seen=parse_time(row["first_seen"]),
                last_seen=parse_time(row["last_seen"]),
                kind=row["kind"],
            )
        )
    db.flush()
    for row in corpus["issue_complaints"]:
        db.add(IssueComplaint(issue_id=row["issue_id"], complaint_id=row["complaint_id"]))
    for row in corpus["incidents"]:
        db.add(
            Incident(
                id=row["id"],
                summary=row["summary"],
                technical_issue=row["technical_issue"],
                theme=row["theme"],
                cause=row["cause"],
                created_at=parse_time(row["created_at"]),
            )
        )
    db.flush()
    for row in corpus["incident_complaints"]:
        db.add(IncidentComplaint(incident_id=row["incident_id"], complaint_id=row["complaint_id"]))
    db.flush()
    for row in corpus["knowledge_items"]:
        db.add(
            KnowledgeItem(
                id=row["id"],
                document_id=row["document_id"],
                issue_id=row["issue_id"],
                title=row["title"],
                body=row["body"],
                kind=row["kind"],
            )
        )
    db.flush()
    return corpus
