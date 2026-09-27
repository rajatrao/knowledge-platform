"""Equal-length current and previous windows used by the seeded corpus."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

AS_OF = datetime(2026, 9, 26, tzinfo=timezone.utc)
PERIOD = timedelta(days=30)
CURRENT_START = AS_OF - PERIOD
PREVIOUS_START = AS_OF - (PERIOD * 2)


def aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def period_of(value: datetime) -> str:
    stamp = aware(value)
    if CURRENT_START <= stamp < AS_OF:
        return "current"
    if PREVIOUS_START <= stamp < CURRENT_START:
        return "previous"
    return "other"


def trend_percent(current: int, previous: int) -> float:
    if previous == 0:
        return 100.0 if current else 0.0
    return round((current - previous) / previous * 100, 1)
