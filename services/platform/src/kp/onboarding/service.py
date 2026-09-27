"""Start or signal onboarding. Knowledge retrieval is not used here."""

from __future__ import annotations

import asyncio

from sqlalchemy.orm import Session

from kp.config import get_settings
from kp.models import KnowledgeSession
from kp.onboarding.activities import create_customer, create_directory, grant_persona_row, notify_manager_row
from kp.onboarding.fields import (
    FLOW_BY_KIND,
    extract_customer_params,
    extract_params,
    is_customer_onboarding_text,
    is_onboarding_text,
    merge_customer_details,
    merge_details,
    merge_specialist,
    missing_customer_fields,
    missing_fields,
    parse_specialist,
    success_sentence,
    workflow_id,
)

CUSTOMER_WORKFLOW = "onboard_customer"


def format_missing(missing: list[str]) -> str:
    return (
        f"Still need {', '.join(missing)}. "
        "Send the missing fields in this chat to continue onboarding."
    )


def format_summary(result: dict) -> str:
    return (
        f"Onboarded {result['name']} ({result['email']}) as {result['role']}. "
        f"Directory record {result['directory_id']} was created, the {result['role']} persona was granted, "
        "and the manager was notified."
    )


def format_customer_summary(result: dict) -> str:
    return (
        f"Onboarded {result['name']} ({result['email']}) in {result['city']} "
        f"with {result['system_type']}."
    )


class OnboardingService:
    async def handle(
        self,
        db: Session,
        session: KnowledgeSession,
        query: str,
        params: dict | None,
        workflow_name: str | None = None,
    ) -> dict:
        kind = self._kind(session, query, workflow_name)
        if kind == "customer":
            incoming = merge_customer_details(params, extract_customer_params(query))
        elif kind in FLOW_BY_KIND:
            incoming = parse_specialist(kind, query)
        else:
            incoming = merge_details(params, extract_params(query))
        if get_settings().onboarding_runner == "memory":
            return self._memory(db, session, incoming, kind)
        return await self._temporal(session, incoming, kind)

    def _kind(self, session: KnowledgeSession, query: str, workflow_name: str | None) -> str:
        pending = session.pending_workflow_id or ""
        if pending.startswith("onboard-specialist-"):
            stored = str((session.onboarding_draft or {}).get("kind") or "")
            if stored in FLOW_BY_KIND:
                return stored
            for kind in FLOW_BY_KIND:
                if f"-{kind}-" in pending:
                    return kind
        if pending.startswith("onboard-customer-"):
            return "customer"
        if pending.startswith("onboard-employee-"):
            return "employee"
        for kind, flow in FLOW_BY_KIND.items():
            if workflow_name == flow.workflow:
                return kind
        if workflow_name == CUSTOMER_WORKFLOW or (
            is_customer_onboarding_text(query) and not is_onboarding_text(query)
        ):
            return "customer"
        return "employee"

    def _memory(self, db: Session, session: KnowledgeSession, incoming: dict, kind: str) -> dict:
        if kind == "customer":
            return self._memory_customer(db, session, incoming)
        if kind in FLOW_BY_KIND:
            return self._memory_specialist(session, incoming, kind)
        draft = merge_details(session.onboarding_draft, incoming)
        session.pending_workflow_id = workflow_id(session.id)
        missing = missing_fields(draft)
        if missing:
            session.onboarding_draft = draft
            return {"answer": format_missing(missing), "completed": False}
        record = create_directory(db, draft, session.id)
        grant_persona_row(db, record["id"])
        notify_manager_row(db, record["id"])
        session.onboarding_draft = None
        session.pending_workflow_id = None
        return {"answer": format_summary({**draft, "directory_id": record["id"]}), "completed": True}

    def _memory_customer(self, db: Session, session: KnowledgeSession, incoming: dict) -> dict:
        draft = merge_customer_details(session.onboarding_draft, incoming)
        session.pending_workflow_id = workflow_id(session.id, "customer")
        missing = missing_customer_fields(draft)
        if missing:
            session.onboarding_draft = draft
            return {"answer": format_missing(missing), "completed": False}
        record = create_customer(db, draft, session.id)
        session.onboarding_draft = None
        session.pending_workflow_id = None
        return {"answer": format_customer_summary(draft | {"customer_id": record["id"]}), "completed": True}

    def _memory_specialist(self, session: KnowledgeSession, incoming: dict, kind: str) -> dict:
        draft = merge_specialist(kind, session.onboarding_draft, incoming)
        session.pending_workflow_id = workflow_id(session.id, kind)
        missing = missing_fields(draft)
        if missing:
            session.onboarding_draft = draft
            return {"answer": format_missing(missing), "completed": False}
        session.onboarding_draft = None
        session.pending_workflow_id = None
        return {"answer": success_sentence(draft), "completed": True}

    async def _temporal(self, session: KnowledgeSession, incoming: dict, kind: str) -> dict:
        from temporalio.client import Client, WorkflowExecutionStatus

        from kp.onboarding.fields import TASK_QUEUE
        from kp.onboarding.workflow import OnboardCustomer, OnboardEmployee, OnboardSpecialist

        if kind == "customer":
            workflow_cls = OnboardCustomer
            wf_id = workflow_id(session.id, "customer")
            summarize = format_customer_summary
            remember = merge_customer_details
        elif kind in FLOW_BY_KIND:
            workflow_cls = OnboardSpecialist
            wf_id = workflow_id(session.id, kind)
            summarize = success_sentence

            def remember(current, new, specialist_kind=kind):
                return merge_specialist(specialist_kind, current, new)
        else:
            workflow_cls = OnboardEmployee
            wf_id = workflow_id(session.id)
            summarize = format_summary
            remember = merge_details
        settings = get_settings()
        client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
        handle = client.get_workflow_handle(wf_id)
        running = False
        try:
            desc = await handle.describe()
            running = desc.status == WorkflowExecutionStatus.RUNNING
        except Exception:
            running = False
        if running:
            await handle.signal(workflow_cls.provide_details, incoming)
        else:
            handle = await client.start_workflow(
                workflow_cls.run,
                {**incoming, "session_id": session.id},
                id=wf_id,
                task_queue=TASK_QUEUE,
            )
        try:
            result = await asyncio.wait_for(handle.result(), timeout=8)
        except TimeoutError:
            missing = await handle.query(workflow_cls.missing_fields)
            session.pending_workflow_id = wf_id
            session.onboarding_draft = remember(session.onboarding_draft, incoming)
            return {"answer": format_missing(list(missing)), "completed": False}
        session.pending_workflow_id = None
        session.onboarding_draft = None
        return {"answer": summarize(result), "completed": True}
