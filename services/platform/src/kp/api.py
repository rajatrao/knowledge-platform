"""FastAPI application."""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import asynccontextmanager

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from kp.auth import (
    clear_auth_cookie,
    create_knowledge_session,
    hash_token,
    latest_session,
    owned_session,
    set_auth_cookie,
    start_auth_session,
    user_from_request,
    verify_password,
)
from kp.config import get_settings
from kp.db import SessionLocal, ensure_schema, get_db
from kp.agent.sandbox import SandboxUnavailable
from kp.agent.skills import SkillSelectorRequired
from kp.flow import configure_flow_logging, event
from kp.knowledge.ask import handle_ask
from kp.knowledge.intent import JevUnavailable
from kp.models import Artifact, AuthSession, KnowledgeSession, Turn, User
from kp.read_models import (
    ceo_dashboard,
    engineering_dashboard,
    investigation,
    marketing_dashboard,
    operations_dashboard,
    theme_index,
)
from kp.seed import seed_users
from kp.storage import read_session_bytes, require_s3


class LoginBody(BaseModel):
    username: str
    password: str


class AskBody(BaseModel):
    query: str = Field(min_length=1)
    channel: str
    router: str
    provider: str | None = None
    model: str | None = None


_MODEL_ID = re.compile(r"[A-Za-z0-9._:-]{1,128}")


def _normalize_provider(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip().lower()
    if not cleaned:
        return None
    if cleaned in {"local", "ollama"}:
        return "ollama"
    if cleaned in {"cloud", "openai"}:
        return "openai"
    raise HTTPException(status_code=422, detail="provider must be ollama or openai")


def _normalize_model(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = value.strip()
    if not cleaned:
        return None
    if _MODEL_ID.fullmatch(cleaned) is None:
        raise HTTPException(status_code=422, detail="model is not a valid id")
    return cleaned


def _public_user(user: User, session: KnowledgeSession) -> dict:
    return {"username": user.username, "persona": user.persona, "session_id": session.id}


def _turn(row: Turn) -> dict:
    return {
        "id": row.id,
        "role": row.role,
        "content": row.content,
        "channel": row.channel,
        "citations": row.citations or [],
        "route": row.route,
        "artifacts": row.artifacts or [],
        "telemetry": row.telemetry,
        "report": row.report,
        "created_at": row.created_at.isoformat(),
    }


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings = get_settings()
    require_s3(settings)
    ensure_schema()
    db = SessionLocal()
    try:
        seed_users(db)
        db.commit()
    finally:
        db.close()
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    configure_flow_logging()
    app = FastAPI(title="Knowledge platform", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    def current_user(request: Request, db: Session = Depends(get_db)) -> User:
        return user_from_request(db, request)

    @app.get("/health")
    def health() -> dict:
        return {"status": "ok"}

    @app.post("/v1/auth/login")
    def login(body: LoginBody, response: Response, db: Session = Depends(get_db)) -> dict:
        user = db.query(User).filter(User.username == body.username).one_or_none()
        if user is None or not verify_password(body.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid username or password")
        token = start_auth_session(db, user)
        session = latest_session(db, user)
        db.commit()
        set_auth_cookie(response, token)
        return _public_user(user, session)

    @app.get("/v1/auth/me")
    def me(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
        session = latest_session(db, user)
        db.commit()
        return _public_user(user, session)

    @app.post("/v1/auth/logout")
    def logout(request: Request, response: Response, db: Session = Depends(get_db)) -> Response:
        token = request.cookies.get("kp_auth")
        if token:
            db.query(AuthSession).filter(AuthSession.token_hash == hash_token(token)).delete()
            db.commit()
        clear_auth_cookie(response)
        response.status_code = 204
        return response

    @app.get("/v1/llm/options")
    def llm_options(user: User = Depends(current_user)) -> dict:
        del user
        current = get_settings()
        return {
            "default": {"provider": "ollama", "model": current.ollama_model},
            "ollama": {"provider": "ollama", "model": current.ollama_model},
            "cloud": {
                "provider": "openai",
                "model": current.llm_model,
                "configured": bool(current.llm_api_key),
            },
        }

    @app.get("/v1/sessions")
    def list_sessions(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
        rows = (
            db.query(KnowledgeSession)
            .filter(KnowledgeSession.user_id == user.id)
            .order_by(KnowledgeSession.updated_at.desc())
            .all()
        )
        return {
            "sessions": [
                {
                    "id": row.id,
                    "title": row.title,
                    "persona": row.persona,
                    "updated_at": row.updated_at.isoformat(),
                }
                for row in rows
            ]
        }

    @app.post("/v1/sessions")
    def create_session(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
        session = create_knowledge_session(db, user)
        db.commit()
        event("session.created", session=session.id, persona=session.persona, user=user.username)
        return {"id": session.id, "title": session.title, "persona": session.persona}

    @app.delete("/v1/sessions/{session_id}", status_code=204)
    def delete_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> Response:
        session = owned_session(db, user, session_id)
        db.query(Artifact).filter(Artifact.session_id == session.id).delete()
        db.query(Turn).filter(Turn.session_id == session.id).delete()
        db.delete(session)
        db.commit()
        event("session.deleted", session=session_id, user=user.username)
        return Response(status_code=204)

    @app.get("/v1/sessions/{session_id}")
    def get_session(session_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
        session = owned_session(db, user, session_id)
        turns = db.query(Turn).filter(Turn.session_id == session.id).order_by(Turn.created_at.asc()).all()
        return {
            "id": session.id,
            "title": session.title,
            "persona": session.persona,
            "username": user.username,
            "turns": [_turn(row) for row in turns],
        }

    @app.post("/v1/sessions/{session_id}/ask")
    async def ask(session_id: str, body: AskBody, request: Request, user: User = Depends(current_user), db: Session = Depends(get_db)):
        if body.channel not in {"web", "slack", "api"}:
            raise HTTPException(status_code=422, detail="channel must be web, slack, or api")
        if body.router not in {"llm", "jev"}:
            raise HTTPException(status_code=422, detail="router must be llm or jev")
        provider = _normalize_provider(body.provider)
        model = _normalize_model(body.model)
        session = owned_session(db, user, session_id)
        event(
            "ask.received",
            session=session.id,
            persona=session.persona,
            channel=body.channel,
            router=body.router,
            provider=provider,
            model=model,
            query=body.query.strip(),
        )
        wants_progress = "application/x-ndjson" in request.headers.get("accept", "")

        async def run_ask(progress=None) -> dict:
            try:
                return await handle_ask(
                    db,
                    session,
                    body.query.strip(),
                    body.channel,
                    body.router,
                    provider,
                    model,
                    progress,
                )
            except SkillSelectorRequired as exc:
                event("ask.failed", session=session.id, status=400, error=exc)
                raise HTTPException(status_code=400, detail=str(exc)) from exc
            except SandboxUnavailable as exc:
                event("ask.failed", session=session.id, status=503, error=exc)
                raise HTTPException(status_code=503, detail=str(exc)) from exc
            except JevUnavailable as exc:
                event("ask.failed", session=session.id, status=502, error=exc)
                raise HTTPException(status_code=502, detail=str(exc)) from exc
            except httpx.HTTPError as exc:
                event("ask.failed", session=session.id, status=502, error="Router call failed")
                raise HTTPException(status_code=502, detail="Router call failed") from exc

        if not wants_progress:
            return await run_ask()

        queue: asyncio.Queue = asyncio.Queue()

        async def report(label: str) -> None:
            ack = asyncio.get_running_loop().create_future()
            await queue.put({"stage": label, "ack": ack})
            await ack

        async def run_progress() -> None:
            try:
                result = await run_ask(progress=report)
                await queue.put({"done": True, "result": result})
            except HTTPException as exc:
                detail = exc.detail if isinstance(exc.detail, str) else "Ask failed"
                await queue.put({"error": detail, "status": exc.status_code})
            except Exception as exc:
                event("ask.failed", session=session.id, status=500, error=type(exc).__name__)
                await queue.put({"error": "Ask failed", "status": 500})
            finally:
                await queue.put(None)

        async def generate():
            task = asyncio.create_task(run_progress())
            try:
                while True:
                    item = await queue.get()
                    if item is None:
                        break
                    ack = item.pop("ack", None)
                    yield json.dumps(item) + "\n"
                    if ack is not None and not ack.done():
                        ack.set_result(None)
            finally:
                if not task.done():
                    task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        return StreamingResponse(
            generate(),
            media_type="application/x-ndjson",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

    @app.get("/v1/sessions/{session_id}/artifacts/{artifact_id}")
    def get_artifact(session_id: str, artifact_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
        session = owned_session(db, user, session_id)
        wants_png = artifact_id.endswith(".png")
        key = artifact_id[:-4] if wants_png else artifact_id
        row = (
            db.query(Artifact)
            .filter(Artifact.session_id == session.id, Artifact.artifact_id == key)
            .one_or_none()
        )
        if row is None:
            raise HTTPException(status_code=404, detail="Artifact not found")
        if wants_png:
            data = read_session_bytes(session.id, f"workspace/artifacts/{key}.png")
            return Response(content=data, media_type="image/png")
        return {
            "id": row.artifact_id,
            "kind": row.kind,
            "chart_type": row.chart_type,
            "title": row.title,
            "spec": row.spec,
            "data_uri": f"/v1/sessions/{session.id}/artifacts/{row.artifact_id}",
            "image_uri": f"/v1/sessions/{session.id}/artifacts/{row.artifact_id}.png",
        }

    @app.get("/v1/dashboards/{persona}")
    def dashboard(persona: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
        builders = {
            "ceo": ceo_dashboard,
            "operations_manager": operations_dashboard,
            "engineer": engineering_dashboard,
            "marketing": marketing_dashboard,
        }
        if persona not in builders:
            raise HTTPException(status_code=404, detail="Dashboard not found")
        if user.persona != persona:
            raise HTTPException(status_code=403, detail="Dashboard is not available for this persona")
        return builders[persona](db)

    @app.get("/v1/themes")
    def themes(user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
        del user
        return theme_index(db)

    @app.get("/v1/investigations/{theme}")
    def investigate(theme: str, user: User = Depends(current_user), db: Session = Depends(get_db)) -> dict:
        del user
        payload = investigation(db, theme)
        if payload is None:
            raise HTTPException(status_code=404, detail="Investigation not found")
        return payload

    return app


app = create_app()
