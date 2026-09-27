"""Temporal onboarding workflows. This module does not import the deep agent."""

from __future__ import annotations

from datetime import timedelta

from temporalio import workflow

with workflow.unsafe.imports_passed_through():
    from kp.onboarding.activities import (
        create_customer_record,
        create_directory_record,
        grant_persona,
        notify_manager,
    )
    from kp.onboarding.fields import merge_customer_details, merge_details, merge_specialist
    from kp.onboarding.fields import missing_customer_fields as compute_customer_missing
    from kp.onboarding.fields import missing_fields as compute_missing


@workflow.defn
class OnboardEmployee:
    def __init__(self) -> None:
        self.details = {"name": None, "email": None, "role": None}
        self._updated = False

    @workflow.run
    async def run(self, initial: dict) -> dict:
        self.details = merge_details({}, initial or {})
        while compute_missing(self.details):
            await workflow.wait_condition(lambda: self._updated)
            self._updated = False
        directory = await workflow.execute_activity(
            create_directory_record,
            {**self.details, "session_id": workflow.info().workflow_id.removeprefix("onboard-employee-")},
            start_to_close_timeout=timedelta(seconds=20),
        )
        await workflow.execute_activity(
            grant_persona,
            directory["id"],
            start_to_close_timeout=timedelta(seconds=20),
        )
        await workflow.execute_activity(
            notify_manager,
            directory["id"],
            start_to_close_timeout=timedelta(seconds=20),
        )
        return {
            "name": self.details["name"],
            "email": self.details["email"],
            "role": self.details["role"],
            "directory_id": directory["id"],
            "persona_granted": True,
            "manager_notified": True,
        }

    @workflow.signal
    def provide_details(self, payload: dict) -> None:
        self.details = merge_details(self.details, payload or {})
        self._updated = True

    @workflow.query
    def missing_fields(self) -> list[str]:
        return compute_missing(self.details)


@workflow.defn
class OnboardCustomer:
    def __init__(self) -> None:
        self.details = {"name": None, "email": None, "city": None, "system_type": None}
        self._updated = False

    @workflow.run
    async def run(self, initial: dict) -> dict:
        self.details = merge_customer_details({}, initial or {})
        while compute_customer_missing(self.details):
            await workflow.wait_condition(lambda: self._updated)
            self._updated = False
        record = await workflow.execute_activity(
            create_customer_record,
            {**self.details, "session_id": workflow.info().workflow_id.removeprefix("onboard-customer-")},
            start_to_close_timeout=timedelta(seconds=20),
        )
        return {
            "name": self.details["name"],
            "email": self.details["email"],
            "city": self.details["city"],
            "system_type": self.details["system_type"],
            "customer_id": record["id"],
        }

    @workflow.signal
    def provide_details(self, payload: dict) -> None:
        self.details = merge_customer_details(self.details, payload or {})
        self._updated = True

    @workflow.query
    def missing_fields(self) -> list[str]:
        return compute_customer_missing(self.details)


@workflow.defn
class OnboardSpecialist:
    """One workflow for the six specialist flows. The payload kind selects the fields."""

    def __init__(self) -> None:
        self.kind = ""
        self.details: dict = {}
        self._updated = False

    @workflow.run
    async def run(self, initial: dict) -> dict:
        self.kind = str((initial or {}).get("kind") or "")
        self.details = merge_specialist(self.kind, {}, initial or {})
        while compute_missing(self.details):
            await workflow.wait_condition(lambda: self._updated)
            self._updated = False
        return dict(self.details)

    @workflow.signal
    def provide_details(self, payload: dict) -> None:
        self.details = merge_specialist(self.kind, self.details, payload or {})
        self._updated = True

    @workflow.query
    def missing_fields(self) -> list[str]:
        return compute_missing(self.details)
