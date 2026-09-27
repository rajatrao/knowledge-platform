"""Ask dispatch. Onboarding never enters the knowledge path."""

from __future__ import annotations

import asyncio
import inspect
import time
import uuid
from collections.abc import Callable
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from kp.flow import event
from kp.knowledge.artifacts import build_artifacts, is_report
from kp.knowledge.context import prior_answer
from kp.knowledge.intent import CUSTOMER_WORKFLOW_NAME, WORKFLOW_NAME, router_for
from kp.onboarding.fields import SPECIALIST_WORKFLOW_NAMES
from kp.knowledge.field_ops import FIELD_OPS_KIND, include_field_ops_records
from kp.knowledge.engineering import ENGINEERING_KIND, include_engineering_records
from kp.knowledge.executive import EXECUTIVE_KIND, include_executive_records
from kp.knowledge.retrieve import include_company_records, retrieve
from kp.knowledge.synthesize import derive_suggested_questions, normalize_suggested_questions, synthesize
from kp.llm import reset_llm_choice, set_llm_choice
from kp.labels import PERSONA_SKILLS
from kp.models import KnowledgeSession, Turn
from kp.onboarding.service import OnboardingService
from kp.reports.intents import REPORT_WORKFLOW_NAMES
from kp.reports.service import ReportService


def _active_onboarding(session: KnowledgeSession, decision) -> str | None:
    pending = session.pending_workflow_id or ""
    names = {WORKFLOW_NAME, CUSTOMER_WORKFLOW_NAME, *SPECIALIST_WORKFLOW_NAMES}
    if pending.startswith("onboard-specialist-"):
        stored = str((session.onboarding_draft or {}).get("workflow") or "")
        if stored in SPECIALIST_WORKFLOW_NAMES:
            return stored
    if pending.startswith("onboard-customer-"):
        return CUSTOMER_WORKFLOW_NAME
    if pending.startswith("onboard-employee-"):
        return WORKFLOW_NAME
    if decision.kind == "workflow" and decision.name in names:
        return decision.name
    return None


def _stamp(session: KnowledgeSession) -> None:
    session.updated_at = datetime.now(timezone.utc)


async def _stage(progress: Callable[[str], object] | None, label: str) -> None:
    if progress is None:
        return
    reported = progress(label)
    if inspect.isawaitable(reported):
        await reported


async def handle_ask(
    db: Session,
    session: KnowledgeSession,
    query: str,
    channel: str,
    router_name: str,
    provider: str | None = None,
    model: str | None = None,
    progress: Callable[[str], object] | None = None,
) -> dict:
    token = set_llm_choice(provider, model)
    try:
        return await _handle_ask(db, session, query, channel, router_name, progress)
    finally:
        reset_llm_choice(token)


async def _handle_ask(
    db: Session,
    session: KnowledgeSession,
    query: str,
    channel: str,
    router_name: str,
    progress: Callable[[str], object] | None = None,
) -> dict:
    started = time.perf_counter()
    history = (
        db.query(Turn)
        .filter(Turn.session_id == session.id)
        .order_by(Turn.created_at.asc())
        .all()
    )
    turns = [{"role": row.role, "content": row.content} for row in history][-6:]
    await _stage(progress, "routing ask")
    event("route.start", session=session.id, router=router_name, persona=session.persona)
    decision = router_for(router_name).route(session.persona, query, turns)
    event(
        "route.done",
        session=session.id,
        kind=decision.kind,
        target=decision.name,
        model=decision.telemetry.model,
        latency_ms=decision.telemetry.latency_ms,
        reason=decision.reason,
    )
    user_turn = Turn(
        id=str(uuid.uuid4()),
        session_id=session.id,
        role="user",
        content=query,
        channel=channel,
        citations=[],
        route=None,
        artifacts=[],
        telemetry=None,
        created_at=datetime.now(timezone.utc),
    )
    db.add(user_turn)
    if session.title == "New chat":
        session.title = query[:80]

    active = _active_onboarding(session, decision)
    report = None
    suggested_questions: list[str] = []
    if active:
        event("onboarding.start", session=session.id, workflow=active)
        outcome = await OnboardingService().handle(db, session, query, decision.params, workflow_name=active)
        event("onboarding.done", session=session.id, workflow=active)
        answer = outcome["answer"]
        citations: list[dict] = []
        artifacts: list[dict] = []
        route = {"kind": "workflow", "name": active}
    elif decision.kind == "workflow" and decision.name in REPORT_WORKFLOW_NAMES:
        event("report.start", session=session.id, workflow=decision.name)
        outcome = await ReportService().handle(db, decision.name, decision.params)
        event("report.done", session=session.id, workflow=decision.name)
        answer = outcome["answer"]
        report = outcome["report"]
        citations = []
        artifacts = []
        route = {"kind": "workflow", "name": decision.name}
    else:
        skill = decision.name if decision.kind == "skill" else PERSONA_SKILLS[session.persona]
        prior = prior_answer(turns, query)
        await _stage(progress, "retrieving data")
        event("retrieve.start", session=session.id, skill=skill)
        bundle = retrieve(db, session.persona, skill)
        record_query = f"{query}\n{prior}" if prior else query
        include_company_records(db, bundle, record_query)
        include_field_ops_records(bundle, record_query)
        include_engineering_records(bundle, record_query)
        include_executive_records(bundle, record_query)
        field_ids = [record_id for kind, record_id in bundle.records if kind == FIELD_OPS_KIND]
        engineering_ids = [record_id for kind, record_id in bundle.records if kind == ENGINEERING_KIND]
        executive_ids = [record_id for kind, record_id in bundle.records if kind == EXECUTIVE_KIND]
        event("retrieve.done", session=session.id, skill=skill, records=len(bundle.records))
        if field_ids:
            event("retrieve.field_ops", session=session.id, records=",".join(field_ids))
        if engineering_ids:
            event("retrieve.engineering", session=session.id, records=",".join(engineering_ids))
        if executive_ids:
            event("retrieve.executive", session=session.id, records=",".join(executive_ids))
        await _stage(progress, "agent synthesizing")
        answer, citations, charts = await synthesize(session.id, query, bundle, router_name, prior=prior)
        suggested_questions = normalize_suggested_questions(getattr(bundle, "suggested_questions", None))
        if not suggested_questions:
            suggested_questions = derive_suggested_questions(query, answer, charts)
        await _stage(progress, "building result")
        event("artifacts.start", session=session.id)
        artifacts = build_artifacts(db, session, query, answer, prior, charts if is_report(query) else [])
        event("artifacts.done", session=session.id, count=len(artifacts))
        folded = (query or "").casefold().replace("quater", "quarter")
        forecast = "forecast" in folded or any(year in folded for year in ("2027", "2028", "2029"))
        if forecast or (artifacts and not str(artifacts[0].get("title") or "").startswith("Quarterly")):
            citations = [item for item in citations if item.get("kind") != "knowledge_item"]
        route = {"kind": "skill", "name": skill}

    _stamp(session)
    assistant = Turn(
        id=str(uuid.uuid4()),
        session_id=session.id,
        role="assistant",
        content=answer,
        channel=channel,
        citations=citations,
        route=route,
        artifacts=artifacts,
        telemetry=decision.telemetry.as_dict(),
        report=report,
        created_at=datetime.now(timezone.utc),
    )
    db.add(assistant)
    db.commit()
    event(
        "ask.done",
        session=session.id,
        route=route["kind"],
        target=route["name"],
        citations=len(citations),
        artifacts=len(artifacts),
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )
    return {
        "session_id": session.id,
        "answer": answer,
        "citations": citations,
        "route": route,
        "artifacts": artifacts,
        "report": report,
        "telemetry": decision.telemetry.as_dict(),
        "suggested_questions": suggested_questions,
    }
