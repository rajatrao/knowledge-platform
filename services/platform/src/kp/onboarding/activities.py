"""Directory side effects. No agent and no corpus search."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from temporalio import activity

from kp.db import SessionLocal
from kp.models import CustomerRecord, DirectoryRecord, ManagerNotification


def create_directory(db, details: dict, session_id: str) -> dict:
    row = DirectoryRecord(
        id=str(uuid.uuid4()),
        session_id=session_id,
        name=details["name"],
        email=details["email"],
        role=details["role"],
        persona_granted=False,
        manager_notified=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return {
        "id": row.id,
        "name": row.name,
        "email": row.email,
        "role": row.role,
        "session_id": session_id,
    }


def grant_persona_row(db, directory_id: str) -> None:
    row = db.get(DirectoryRecord, directory_id)
    if row is None:
        raise RuntimeError(f"directory record {directory_id} was not found")
    row.persona_granted = True


def notify_manager_row(db, directory_id: str) -> None:
    row = db.get(DirectoryRecord, directory_id)
    if row is None:
        raise RuntimeError(f"directory record {directory_id} was not found")
    row.manager_notified = True
    db.add(
        ManagerNotification(
            id=str(uuid.uuid4()),
            directory_id=row.id,
            message=f"New employee {row.name} ({row.email}) joined as {row.role}.",
            created_at=datetime.now(timezone.utc),
        )
    )


@activity.defn
def create_directory_record(details: dict) -> dict:
    db = SessionLocal()
    try:
        record = create_directory(db, details, details.get("session_id") or "")
        db.commit()
        return record
    finally:
        db.close()


@activity.defn
def grant_persona(directory_id: str) -> bool:
    db = SessionLocal()
    try:
        grant_persona_row(db, directory_id)
        db.commit()
        return True
    finally:
        db.close()


def create_customer(db, details: dict, session_id: str) -> dict:
    row = CustomerRecord(
        id=str(uuid.uuid4()),
        session_id=session_id,
        name=details["name"],
        email=details["email"],
        city=details["city"],
        system_type=details["system_type"],
        created_at=datetime.now(timezone.utc),
    )
    db.add(row)
    db.flush()
    return {
        "id": row.id,
        "name": row.name,
        "email": row.email,
        "city": row.city,
        "system_type": row.system_type,
        "session_id": session_id,
    }


@activity.defn
def create_customer_record(details: dict) -> dict:
    db = SessionLocal()
    try:
        record = create_customer(db, details, details.get("session_id") or "")
        db.commit()
        return record
    finally:
        db.close()


@activity.defn
def notify_manager(directory_id: str) -> bool:
    db = SessionLocal()
    try:
        notify_manager_row(db, directory_id)
        db.commit()
        return True
    finally:
        db.close()
