"""Postgres tables for auth, sessions, and the evidence model."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    persona: Mapped[str] = mapped_column(String(32))
    skill_ids: Mapped[list] = mapped_column(JSONB, nullable=False, default=list, server_default=text("'[]'::jsonb"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class AuthSession(Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class KnowledgeSession(Base):
    __tablename__ = "knowledge_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), index=True)
    tenant_id: Mapped[str] = mapped_column(String(32), default="base")
    persona: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    pending_workflow_id: Mapped[str | None] = mapped_column(String(80), nullable=True)
    onboarding_draft: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    sandbox_namespace: Mapped[str | None] = mapped_column(String(63), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Turn(Base):
    __tablename__ = "turns"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))
    content: Mapped[str] = mapped_column(Text)
    channel: Mapped[str | None] = mapped_column(String(16), nullable=True)
    citations: Mapped[list] = mapped_column(JSONB, default=list)
    route: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    artifacts: Mapped[list] = mapped_column(JSONB, default=list)
    telemetry: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    report: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(32), nullable=True)
    theme: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    cause: Mapped[str | None] = mapped_column(String(64), nullable=True)
    recommended_action: Mapped[str | None] = mapped_column(Text, nullable=True)
    installation_state: Mapped[str | None] = mapped_column(String(32), nullable=True, index=True)
    blocker: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    sentiment: Mapped[str | None] = mapped_column(String(16), nullable=True)
    value_theme: Mapped[str | None] = mapped_column(String(64), nullable=True)
    technical_issue: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Complaint(Base):
    __tablename__ = "complaints"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text)
    theme: Mapped[str] = mapped_column(String(64), index=True)
    cause: Mapped[str] = mapped_column(String(64))
    region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sentiment: Mapped[str | None] = mapped_column(String(16), nullable=True, index=True)
    value_theme: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    technical_issue: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)


class Issue(Base):
    """Aggregated problem. complaint_count is checked against issue_complaints."""

    __tablename__ = "issues"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    slug: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[str] = mapped_column(Text)
    complaint_count: Mapped[int] = mapped_column(Integer)
    trend: Mapped[float] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(16))
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    kind: Mapped[str] = mapped_column(String(16))


class IssueComplaint(Base):
    __tablename__ = "issue_complaints"

    issue_id: Mapped[str] = mapped_column(ForeignKey("issues.id"), primary_key=True)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), primary_key=True)


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String(32), primary_key=True)
    summary: Mapped[str] = mapped_column(Text)
    technical_issue: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    theme: Mapped[str | None] = mapped_column(String(64), nullable=True)
    cause: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class IncidentComplaint(Base):
    __tablename__ = "incident_complaints"

    incident_id: Mapped[str] = mapped_column(ForeignKey("incidents.id"), primary_key=True)
    complaint_id: Mapped[str] = mapped_column(ForeignKey("complaints.id"), primary_key=True)


class KnowledgeItem(Base):
    __tablename__ = "knowledge_items"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    document_id: Mapped[str] = mapped_column(ForeignKey("documents.id"), nullable=False, index=True)
    issue_id: Mapped[str | None] = mapped_column(ForeignKey("issues.id"), nullable=True, index=True)
    title: Mapped[str] = mapped_column(String(300))
    body: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(32))


class CustomerRecord(Base):
    """External company or household customer. This is not an employee directory row."""

    __tablename__ = "customer_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200))
    city: Mapped[str] = mapped_column(String(120))
    system_type: Mapped[str] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class DirectoryRecord(Base):
    __tablename__ = "directory_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True)
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str] = mapped_column(String(200))
    role: Mapped[str] = mapped_column(String(32))
    persona_granted: Mapped[bool] = mapped_column(default=False)
    manager_notified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ManagerNotification(Base):
    __tablename__ = "manager_notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    directory_id: Mapped[str] = mapped_column(ForeignKey("directory_records.id"))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Artifact(Base):
    __tablename__ = "artifacts"
    __table_args__ = (UniqueConstraint("session_id", "artifact_id", name="uq_artifact"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    session_id: Mapped[str] = mapped_column(ForeignKey("knowledge_sessions.id"), index=True)
    artifact_id: Mapped[str] = mapped_column(String(64))
    kind: Mapped[str] = mapped_column(String(16))
    chart_type: Mapped[str] = mapped_column(String(16))
    title: Mapped[str] = mapped_column(String(300))
    spec: Mapped[dict] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
