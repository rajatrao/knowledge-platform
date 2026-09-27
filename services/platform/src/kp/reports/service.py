"""Start a persona report workflow. Knowledge retrieval is not used here."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from kp.config import get_settings
from kp.onboarding.fields import TASK_QUEUE
from kp.reports.intents import REPORT_WORKFLOW_NAMES
from kp.reports.present import format_report
from kp.reports.queries import READERS


class ReportService:
    async def handle(self, db: Session, name: str, params: dict | None) -> dict:
        if name not in REPORT_WORKFLOW_NAMES:
            raise RuntimeError(f"unknown report workflow {name}")
        # These reports do not collect fields. An empty payload still reads every row.
        incoming = params or {}
        if get_settings().onboarding_runner == "memory":
            report = READERS[name](db, incoming)
        else:
            report = await self._temporal(name, incoming)
        return {"answer": format_report(report), "report": report}

    async def _temporal(self, name: str, params: dict) -> dict:
        from temporalio.client import Client

        from kp.reports.workflows import WORKFLOW_BY_NAME

        settings = get_settings()
        client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
        handle = await client.start_workflow(
            WORKFLOW_BY_NAME[name].run,
            params,
            id=f"{name}-{uuid.uuid4()}",
            task_queue=TASK_QUEUE,
        )
        return await handle.result()
