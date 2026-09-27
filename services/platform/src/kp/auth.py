"""Password checks and the kp_auth cookie."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import HTTPException, Request, Response
from sqlalchemy.orm import Session

from kp.config import get_settings
from kp.models import AuthSession, KnowledgeSession, User

COOKIE = "kp_auth"
AUTH_TTL = timedelta(days=14)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), password_hash.encode())
    except ValueError:
        return False


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def session_dir(session_id: str):
    settings = get_settings()
    path = settings.workspace_root / "tenants" / settings.tenant_id / "sessions" / session_id
    (path / "workspace" / "artifacts").mkdir(parents=True, exist_ok=True)
    return path


def create_knowledge_session(db: Session, user: User) -> KnowledgeSession:
    now = utcnow()
    row = KnowledgeSession(
        id=str(uuid.uuid4()),
        user_id=user.id,
        tenant_id=get_settings().tenant_id,
        persona=user.persona,
        title="New chat",
        pending_workflow_id=None,
        onboarding_draft=None,
        sandbox_namespace=None,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.flush()
    session_dir(row.id)
    return row


def latest_session(db: Session, user: User) -> KnowledgeSession:
    row = (
        db.query(KnowledgeSession)
        .filter(KnowledgeSession.user_id == user.id)
        .order_by(KnowledgeSession.updated_at.desc())
        .first()
    )
    if row is None:
        row = create_knowledge_session(db, user)
    return row


def owned_session(db: Session, user: User, session_id: str) -> KnowledgeSession:
    row = db.get(KnowledgeSession, session_id)
    if row is None or row.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found")
    return row


def user_from_request(db: Session, request: Request) -> User:
    token = request.cookies.get(COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Authentication required")
    auth = db.query(AuthSession).filter(AuthSession.token_hash == hash_token(token)).one_or_none()
    if auth is None or auth.expires_at <= utcnow():
        raise HTTPException(status_code=401, detail="Authentication required")
    user = db.get(User, auth.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required")
    return user


def start_auth_session(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    now = utcnow()
    db.add(
        AuthSession(
            id=str(uuid.uuid4()),
            user_id=user.id,
            token_hash=hash_token(token),
            expires_at=now + AUTH_TTL,
            created_at=now,
        )
    )
    db.flush()
    return token


def set_auth_cookie(response: Response, token: str) -> None:
    settings = get_settings()
    response.set_cookie(
        key=COOKIE,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        path="/",
        max_age=int(AUTH_TTL.total_seconds()),
    )


def clear_auth_cookie(response: Response) -> None:
    response.delete_cookie(COOKIE, path="/")
