"""Temporal worker for onboarding and persona report workflows."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor

from temporalio.client import Client
from temporalio.worker import Worker

from kp.config import get_settings
from kp.db import ensure_schema
from kp.onboarding.activities import create_customer_record, create_directory_record, grant_persona, notify_manager
from kp.onboarding.fields import TASK_QUEUE
from kp.onboarding.workflow import OnboardCustomer, OnboardEmployee, OnboardSpecialist
from kp.reports.activities import REPORT_ACTIVITIES
from kp.reports.workflows import REPORT_WORKFLOWS

WORKFLOWS = [OnboardEmployee, OnboardCustomer, OnboardSpecialist, *REPORT_WORKFLOWS]
ACTIVITIES = [create_directory_record, grant_persona, notify_manager, create_customer_record, *REPORT_ACTIVITIES]


async def run_worker() -> None:
    ensure_schema()
    settings = get_settings()
    client = await Client.connect(settings.temporal_address, namespace=settings.temporal_namespace)
    worker = Worker(
        client,
        task_queue=TASK_QUEUE,
        workflows=WORKFLOWS,
        activities=ACTIVITIES,
        activity_executor=ThreadPoolExecutor(max_workers=8),
    )
    await worker.run()


def main() -> None:
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
