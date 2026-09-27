"""Postgres tools exposed to the deep agent through MCP."""

from __future__ import annotations

from kp.db import SessionLocal
from kp.models import Complaint, Document, Incident, Issue, KnowledgeItem


def _rows(query, limit: int) -> list:
    return query.limit(max(1, min(limit, 50))).all()


def search_complaints(theme: str | None = None, region: str | None = None, text: str | None = None, limit: int = 20) -> list[dict]:
    db = SessionLocal()
    try:
        query = db.query(Complaint)
        if theme:
            query = query.filter(Complaint.theme == theme)
        if region:
            query = query.filter(Complaint.region == region)
        if text:
            query = query.filter(Complaint.text.ilike(f"%{text}%"))
        return [
            {
                "id": row.id,
                "document_id": row.document_id,
                "theme": row.theme,
                "cause": row.cause,
                "region": row.region,
                "text": row.text,
                "created_at": row.created_at.isoformat(),
            }
            for row in _rows(query, limit)
        ]
    finally:
        db.close()


def search_documents(source_type: str | None = None, theme: str | None = None, text: str | None = None, limit: int = 20) -> list[dict]:
    db = SessionLocal()
    try:
        query = db.query(Document)
        if source_type:
            query = query.filter(Document.source_type == source_type)
        if theme:
            query = query.filter(Document.theme == theme)
        if text:
            query = query.filter(Document.body.ilike(f"%{text}%"))
        return [
            {
                "id": row.id,
                "source_type": row.source_type,
                "title": row.title,
                "body": row.body,
                "theme": row.theme,
                "cause": row.cause,
            }
            for row in _rows(query, limit)
        ]
    finally:
        db.close()


def search_issues(name: str | None = None, limit: int = 20) -> list[dict]:
    db = SessionLocal()
    try:
        query = db.query(Issue)
        if name:
            query = query.filter(Issue.name.ilike(f"%{name}%"))
        return [
            {
                "id": row.id,
                "slug": row.slug,
                "name": row.name,
                "description": row.description,
                "complaint_count": row.complaint_count,
                "trend": row.trend,
                "severity": row.severity,
            }
            for row in _rows(query.order_by(Issue.complaint_count.desc()), limit)
        ]
    finally:
        db.close()


def search_incidents(technical_issue: str | None = None, limit: int = 20) -> list[dict]:
    db = SessionLocal()
    try:
        query = db.query(Incident)
        if technical_issue:
            query = query.filter(Incident.technical_issue == technical_issue)
        return [
            {"id": row.id, "summary": row.summary, "technical_issue": row.technical_issue, "theme": row.theme}
            for row in _rows(query, limit)
        ]
    finally:
        db.close()


def search_knowledge(theme: str | None = None, text: str | None = None, limit: int = 20) -> list[dict]:
    db = SessionLocal()
    try:
        query = db.query(KnowledgeItem, Document).join(Document, KnowledgeItem.document_id == Document.id)
        if theme:
            query = query.filter(Document.theme == theme)
        if text:
            query = query.filter(KnowledgeItem.body.ilike(f"%{text}%"))
        rows = query.limit(max(1, min(limit, 50))).all()
        return [
            {
                "id": item.id,
                "document_id": item.document_id,
                "issue_id": item.issue_id,
                "title": item.title,
                "body": item.body,
                "theme": document.theme,
            }
            for item, document in rows
        ]
    finally:
        db.close()


def read_resource(uri: str) -> dict:
    """Open one record by URI, for example kp://complaints/cmp_001."""
    if not uri.startswith("kp://"):
        raise ValueError("URI must start with kp://")
    kind, _, record_id = uri.removeprefix("kp://").partition("/")
    db = SessionLocal()
    try:
        table = {
            "documents": Document,
            "complaints": Complaint,
            "issues": Issue,
            "incidents": Incident,
            "knowledge_items": KnowledgeItem,
        }.get(kind)
        if table is None or not record_id:
            raise ValueError(f"unknown resource {uri}")
        row = db.get(table, record_id)
        if row is None:
            raise ValueError(f"resource {uri} was not found")
        data = {column.name: getattr(row, column.name) for column in table.__table__.columns}
        for key, value in list(data.items()):
            if hasattr(value, "isoformat"):
                data[key] = value.isoformat()
        data["uri"] = uri
        return data
    finally:
        db.close()


def build_server():
    from fastmcp import FastMCP

    mcp = FastMCP("knowledge")
    mcp.tool()(search_complaints)
    mcp.tool()(search_documents)
    mcp.tool()(search_issues)
    mcp.tool()(search_incidents)
    mcp.tool()(search_knowledge)
    mcp.tool()(read_resource)
    return mcp
