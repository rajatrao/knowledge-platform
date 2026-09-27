"""Fake customer outage records for April through September 2026.

Numbers are invented. Named events are included in that month's total.
"""

from __future__ import annotations

# month, label, customers, battery covered, lost power, median minutes, leading cause
MONTHS = (
    ("2026-04", "April 2026", 80, 72, 8, 41, "a utility grid outage"),
    ("2026-05", "May 2026", 146, 121, 25, 78, "a utility feeder outage during a thunderstorm"),
    ("2026-06", "June 2026", 94, 86, 8, 36, "planned utility maintenance"),
    ("2026-07", "July 2026", 121, 103, 18, 54, "a utility grid outage"),
    ("2026-08", "August 2026", 188, 149, 39, 96, "grid load shed during a heat wave"),
    ("2026-09", "September 2026", 67, 61, 6, 29, "a utility grid outage"),
)

# Included in the month totals above. Not additional outages.
EVENTS = (
    (
        "ki_outage_event_20260512",
        "2026-05-12",
        "Houston",
        "May 2026",
        61,
        146,
        48,
        13,
        110,
        "a thunderstorm opened a utility feeder",
    ),
    (
        "ki_outage_event_20260603",
        "2026-06-03",
        "Austin",
        "June 2026",
        14,
        94,
        14,
        0,
        22,
        "planned utility maintenance",
    ),
    (
        "ki_outage_event_20260814",
        "2026-08-14",
        "Houston and Dallas",
        "August 2026",
        97,
        188,
        71,
        26,
        140,
        "grid load shed during a heat wave, and 9 batteries did not start",
    ),
)


def six_month_totals() -> tuple[int, int, int]:
    customers = sum(row[2] for row in MONTHS)
    covered = sum(row[3] for row in MONTHS)
    uncovered = sum(row[4] for row in MONTHS)
    return customers, covered, uncovered


def outage_quotes() -> list[dict]:
    customers, covered, uncovered = six_month_totals()
    quotes = [
        _quote(
            "ki_outage_summary",
            "doc_outage_months",
            "Customer outages, April-September 2026",
            (
                f"From April 2026 through September 2026, fake sample data records {customers} customer outages. "
                f"Batteries covered {covered}. {uncovered} customers lost power. "
                "This is fake sample data, not a live outage feed."
            ),
        )
    ]
    for month, label, affected, battery, lost, minutes, cause in MONTHS:
        quotes.append(
            _quote(
                f"ki_outage_{month.replace('-', '_')}",
                "doc_outage_months",
                f"Customer outages, {label}",
                (
                    f"{label} customer outages: {affected} customers, battery covered {battery}, "
                    f"{lost} lost power, median duration {minutes} minutes. Leading cause was {cause}."
                ),
            )
        )
    for quote_id, day, where, month_label, affected, month_total, battery, lost, minutes, cause in EVENTS:
        quotes.append(
            _quote(
                quote_id,
                "doc_outage_events",
                f"Customer outage on {day}",
                (
                    f"On {day} in {where}, {affected} of {month_label}'s {month_total} customer outages occurred. "
                    f"Batteries covered {battery}. {lost} customers lost power for a median {minutes} minutes. "
                    f"Cause: {cause}."
                ),
            )
        )
    return quotes


def outage_documents() -> list[dict]:
    quotes = outage_quotes()
    by_doc: dict[str, list[str]] = {}
    for quote in quotes:
        by_doc.setdefault(quote["document_id"], []).append(quote["body"])
    titles = {
        "doc_outage_months": "Customer outages, April-September 2026",
        "doc_outage_events": "Customer outage events, April-September 2026",
    }
    return [
        _document(doc_id, titles[doc_id], "\n".join(lines))
        for doc_id, lines in by_doc.items()
    ]


def outage_knowledge_items() -> list[dict]:
    return [
        {
            "id": row["id"],
            "document_id": row["document_id"],
            "issue_id": None,
            "title": row["title"],
            "body": row["body"],
            "kind": "customer_outage",
        }
        for row in outage_quotes()
    ]


def _quote(quote_id: str, document_id: str, title: str, body: str) -> dict:
    return {
        "id": quote_id,
        "document_id": document_id,
        "title": title,
        "kind": "customer_outage",
        "body": body,
    }


def _document(doc_id: str, title: str, body: str) -> dict:
    return {
        "id": doc_id,
        "source_type": "customer_outage",
        "title": title,
        "body": body,
        "region": None,
        "channel": "internal",
        "theme": None,
        "cause": None,
        "recommended_action": None,
        "installation_state": None,
        "blocker": None,
        "sentiment": None,
        "value_theme": None,
        "technical_issue": None,
        "created_at": "2026-09-26T12:00:00Z",
    }
