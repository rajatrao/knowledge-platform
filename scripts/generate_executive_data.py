#!/usr/bin/env python3
"""Generate a synthetic Lumenfield executive dataset.

Stdlib only. One run writes data/executive CSVs and markdown.
Snapshot date: 2026-09-27. random.seed(27).

Installation counts have one source of truth:
  deployment_metrics (daily, 2026-04-01 through 2026-09-27)
    -> market_performance (month)
    -> company_metrics (month, 2026-04 through 2026-09)

Daily history covers the full market_performance window so each
market-month equals the sum of its days. That is 180 days, which
includes the latest 90 days ending on the snapshot date.
"""

from __future__ import annotations

import csv
import random
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
ENG = DATA / "engineering"
OUT = ROOT / "data" / "executive"

SNAPSHOT = date(2026, 9, 27)
DAILY_START = date(2026, 4, 1)
SLOWDOWN_START = date(2026, 8, 24)
IMPROVE_START = date(2026, 7, 6)
PAUSE_START = date(2026, 8, 3)
STORM_DAY = date(2026, 9, 16)
FW_WEEK = date(2026, 9, 14)
FW_DECLINE_WEEK = date(2026, 9, 21)
WBR_END = date(2026, 9, 21)

CAPACITY_PER_CERT_TECH = 8

CITY_TO_MARKET = {
    "Austin": "MKT-001",
    "Lakeway": "MKT-001",
    "Manor": "MKT-002",
    "Round Rock": "MKT-003",
    "Hutto": "MKT-003",
    "Cedar Park": "MKT-004",
    "Leander": "MKT-004",
    "Georgetown": "MKT-005",
    "Buda": "MKT-006",
    "Pflugerville": "MKT-007",
}

MARKET_SPEC = [
    {
        "market_id": "MKT-001",
        "market_name": "Austin Metro",
        "status": "Active",
        "warehouse_id": "W001",
        "cities": ["Austin", "Lakeway"],
        "role": "bottleneck",
        "status_date": date(2024, 3, 1),
        "open_positions": 3,
        "service_note": (
            "Active market served by W001. Scheduled installation demand has "
            "risen faster than the certified crew. Open positions remain."
        ),
    },
    {
        "market_id": "MKT-002",
        "market_name": "North Austin",
        "status": "Active",
        "warehouse_id": "W001",
        "cities": ["Manor"],
        "role": "slowdown",
        "status_date": date(2025, 1, 15),
        "open_positions": 4,
        "service_note": (
            "Active market served by W001. Completed installations fell after "
            "2026-08-24 while scheduled work stayed up. Rework, parts waits, "
            "and customer delays rose in the same window."
        ),
    },
    {
        "market_id": "MKT-003",
        "market_name": "Round Rock",
        "status": "Active",
        "warehouse_id": "W002",
        "cities": ["Round Rock", "Hutto"],
        "role": "steady",
        "status_date": date(2024, 11, 1),
        "open_positions": 0,
        "service_note": "Active market served by W002. Volume and quality have been steady.",
    },
    {
        "market_id": "MKT-004",
        "market_name": "Cedar Park",
        "status": "Scaling",
        "warehouse_id": "W002",
        "cities": ["Cedar Park", "Leander"],
        "role": "scale",
        "status_date": date(2026, 6, 1),
        "open_positions": 1,
        "service_note": (
            "Scaling market served by W002. Demand is high, first-time completion "
            "is strong, field incidents are quiet, and the certified crew is covering the book."
        ),
    },
    {
        "market_id": "MKT-005",
        "market_name": "Georgetown",
        "status": "Active",
        "warehouse_id": "W003",
        "cities": ["Georgetown"],
        "role": "improvement",
        "status_date": date(2024, 8, 1),
        "open_positions": 0,
        "service_note": (
            "Active market served by W003. Cycle time, first-time completion, and "
            "rework improved after the 2026-07-06 cycle-time initiative."
        ),
    },
    {
        "market_id": "MKT-006",
        "market_name": "San Marcos",
        "status": "Launching",
        "warehouse_id": "W003",
        "cities": ["Buda"],
        "role": "blocked",
        "status_date": date(2026, 6, 15),
        "open_positions": 2,
        "service_note": (
            "Launching market. Launch roster is 5 technicians with 3 certified (60%). "
            "technicians.csv only lists the Buda subset; do not add the roster to that extract. "
            "San Marcos locations at W003 are not configured in the WMS, and launch inventory is incomplete."
        ),
    },
    {
        "market_id": "MKT-007",
        "market_name": "Pflugerville",
        "status": "Paused",
        "warehouse_id": "W002",
        "cities": ["Pflugerville"],
        "role": "paused",
        "status_date": date(2026, 8, 3),
        "open_positions": 0,
        "service_note": "Paused on 2026-08-03. Completed installations stopped after the pause date.",
    },
]

ROLE = {m["market_id"]: m["role"] for m in MARKET_SPEC}
NAME = {m["market_id"]: m["market_name"] for m in MARKET_SPEC}
WAREHOUSE_OF = {m["market_id"]: m["warehouse_id"] for m in MARKET_SPEC}

SCALE_PER_DAY = {4: 5, 5: 5, 6: 6, 7: 6, 8: 7, 9: 7}
BOTTLENECK_SCHEDULED = {4: 6, 5: 8, 6: 10, 7: 12, 8: 14, 9: 16}
BOTTLENECK_CAP = 9

DOC_TYPES = [
    "Strategy",
    "Operating Plan",
    "Market Review",
    "Weekly Business Review",
    "Product Review",
    "Engineering Review",
    "Operations Review",
    "Risk Review",
    "Launch Plan",
    "Executive Decision Memo",
]


def must(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def parse_day(value: str) -> date:
    return date.fromisoformat(value[:10])


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def daterange(start: date, end: date):
    day = start
    while day <= end:
        yield day
        day += timedelta(days=1)


def month_key(day: date) -> str:
    return f"{day.year:04d}-{day.month:02d}"


def write_csv(path: Path, rows: list[dict], fields: list[str], formats: dict | None = None) -> None:
    formats = formats or {}
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            out = {}
            for key in fields:
                value = row[key]
                if value is None:
                    out[key] = ""
                elif key in formats:
                    out[key] = formats[key](value)
                elif isinstance(value, date):
                    out[key] = value.isoformat()
                else:
                    out[key] = value
            writer.writerow(out)


def write_text(path: Path, text: str) -> None:
    path.write_text(text.rstrip() + "\n", encoding="utf-8")


def f1(value: float) -> str:
    return f"{value:.1f}"


def f3(value: float) -> str:
    return f"{value:.3f}"


def f4(value: float) -> str:
    return f"{value:.4f}"


def f2(value: float) -> str:
    return f"{value:.2f}"


def load_sources() -> dict:
    warehouses = load_csv(DATA / "warehouses.csv")
    techs = load_csv(DATA / "technicians.csv")
    parts = load_csv(DATA / "parts.csv")
    jobs = load_csv(DATA / "jobs.csv")
    customers = load_csv(DATA / "customer_sites.csv")
    inventory = load_csv(DATA / "warehouse_inventory.csv")
    devices = load_csv(ENG / "devices.csv")
    sites = load_csv(ENG / "engineering_sites.csv")
    incidents = load_csv(ENG / "engineering_incidents.csv")
    firmware = load_csv(ENG / "firmware_versions.csv")
    must(warehouses and techs and parts and jobs and customers, "missing field-ops source rows")
    must(devices and sites and incidents and firmware, "missing engineering source rows")
    return {
        "warehouses": warehouses,
        "techs": techs,
        "parts": parts,
        "jobs": jobs,
        "customers": customers,
        "inventory": inventory,
        "devices": devices,
        "sites": sites,
        "incidents": incidents,
        "firmware": firmware,
    }


def index_by(rows: list[dict], key: str) -> dict[str, dict]:
    return {row[key]: row for row in rows}


def build_markets(sources: dict) -> list[dict]:
    warehouse_ids = {row["warehouse_id"] for row in sources["warehouses"]}
    counts: dict[str, int] = {m["market_id"]: 0 for m in MARKET_SPEC}
    certified: dict[str, int] = {m["market_id"]: 0 for m in MARKET_SPEC}
    for tech in sources["techs"]:
        city = tech["current_city"]
        must(city in CITY_TO_MARKET, f"unmapped technician city {city}")
        market_id = CITY_TO_MARKET[city]
        counts[market_id] += 1
        if tech["certifications"].strip():
            certified[market_id] += 1
    must(sum(counts.values()) == len(sources["techs"]), "technician city rollup missed someone")
    rows = []
    for spec in MARKET_SPEC:
        market_id = spec["market_id"]
        must(spec["warehouse_id"] in warehouse_ids, f"unknown warehouse on {market_id}")
        extract_count = counts[market_id]
        extract_cert = certified[market_id]
        if market_id == "MKT-006":
            technician_count = 5
            certified_count = 3
        else:
            technician_count = extract_count
            certified_count = extract_cert
        must(certified_count <= technician_count, f"certified exceeds headcount for {market_id}")
        rows.append(
            {
                "market_id": market_id,
                "market_name": spec["market_name"],
                "company_name": "Lumenfield",
                "region": "Central Texas",
                "status": spec["status"],
                "warehouse_id": spec["warehouse_id"],
                "primary_cities": "; ".join(spec["cities"]),
                "technician_count": technician_count,
                "certified_technician_count": certified_count,
                "field_extract_technician_count": extract_count,
                "field_extract_certified_count": extract_cert,
                "open_positions": spec["open_positions"],
                "status_date": spec["status_date"],
                "service_note": spec["service_note"],
            }
        )
    san = next(row for row in rows if row["market_id"] == "MKT-006")
    must(san["certified_technician_count"] / san["technician_count"] == 0.6, "San Marcos cert ratio is not 60%")
    must(san["status"] == "Launching", "San Marcos must be Launching")
    statuses = {row["status"] for row in rows}
    must(statuses <= {"Planning", "Launching", "Active", "Scaling", "Paused"}, f"bad statuses {statuses}")
    must("Scaling" in statuses and "Launching" in statuses and "Paused" in statuses, "missing required statuses")
    return rows


def waiting_for(role: str, day: date) -> int:
    if role == "slowdown":
        return 8 if day >= SLOWDOWN_START else 1
    if role == "bottleneck":
        if day.month >= 9:
            return 5
        if day.month >= 7:
            return 3
        return 1
    if role == "scale":
        return 0
    if role == "steady":
        return 1
    if role == "improvement":
        return 1 if day >= IMPROVE_START else 3
    if role == "blocked":
        return 4
    if day >= PAUSE_START:
        return 0
    return 1


def cycle_for(role: str, day: date, completed: int):
    if completed <= 0:
        return None
    if role == "slowdown":
        return 18 if day >= SLOWDOWN_START else 9
    if role == "scale":
        return 6
    if role == "improvement":
        return 8 if day >= IMPROVE_START else 15
    if role == "bottleneck":
        return 12 if day.month >= 8 else 10
    if role == "blocked":
        return 20
    if role == "paused":
        return 11
    return 9


def quality_for(role: str, day: date, completed: int) -> tuple[int, int]:
    if completed <= 0:
        return 0, 0
    if role == "slowdown" and day >= SLOWDOWN_START:
        if day.weekday() in (0, 4):
            return 0, completed
        return completed, 0
    if role == "slowdown" and day.weekday() == 4:
        return completed - 1, 1
    if role == "scale" and day.day % 10 == 0:
        return completed - 1, 1
    if role == "improvement" and day < IMPROVE_START:
        return completed - 1, 1
    if role == "improvement" and day.weekday() == 4:
        return completed - 1, 1
    if role == "steady" and day.weekday() == 4:
        return completed - 1, 1
    if role == "bottleneck" and day.month >= 9 and day.weekday() == 4:
        return completed - 1, 1
    return completed, 0


def plan_day(role: str, day: date) -> tuple[int, int, int]:
    """Return scheduled, target, completed for a weekday. Weekends are handled by the caller."""
    month = day.month
    if role == "slowdown":
        scheduled = 4
        target = 4
        if day < SLOWDOWN_START:
            completed = 3
        else:
            completed = 1 if day.weekday() in (0, 2, 4) else 0
        return scheduled, target, completed
    if role == "scale":
        scheduled = SCALE_PER_DAY[month]
        return scheduled, scheduled, scheduled
    if role == "bottleneck":
        scheduled = BOTTLENECK_SCHEDULED[month]
        completed = min(scheduled, BOTTLENECK_CAP)
        return scheduled, scheduled, completed
    if role == "steady":
        completed = 4 if day.weekday() == 4 else 5
        return 5, 5, completed
    if role == "improvement":
        count = 4 if day >= IMPROVE_START else 3
        return count, count, count
    if role == "blocked":
        if day < date(2026, 6, 1) and day.weekday() == 2:
            return 1, 1, 1
        if day >= IMPROVE_START:
            return 0, 2, 0
        return 0, 0, 0
    if day < PAUSE_START and day.weekday() in (1, 3):
        return 1, 1, 1
    return 0, 0, 0


def build_daily(market_ids: list[str]) -> list[dict]:
    rows = []
    for day in daterange(DAILY_START, SNAPSHOT):
        weekend = day.weekday() >= 5
        for market_id in market_ids:
            role = ROLE[market_id]
            if weekend:
                scheduled = target = completed = 0
            else:
                scheduled, target, completed = plan_day(role, day)
                if role == "scale" and day == STORM_DAY:
                    completed = 2
                if role == "bottleneck" and day >= date(2026, 9, 22):
                    scheduled += 1
                    target += 1
            first_time, rework = quality_for(role, day, completed)
            must(first_time + rework == completed, f"quality split broke on {market_id} {day}")
            critical = 0
            stockout = 0
            if not weekend and role == "slowdown" and day >= SLOWDOWN_START and day.weekday() == 0:
                critical = 1
            if role == "bottleneck" and day == date(2026, 9, 15):
                critical = 1
            if not weekend and role == "slowdown" and day >= SLOWDOWN_START:
                stockout = 1
            if role == "bottleneck" and date(2026, 9, 14) <= day <= date(2026, 9, 18):
                stockout = 1
            if not weekend and role == "blocked" and day >= IMPROVE_START and day.weekday() == 0:
                stockout = 1
            delays = 0
            if not weekend:
                if role == "slowdown" and day >= SLOWDOWN_START:
                    delays = 2
                elif role == "bottleneck" and day.month >= 9:
                    delays = 1
                elif role == "improvement" and day < IMPROVE_START:
                    delays = 1
                elif role == "blocked" and day >= IMPROVE_START:
                    delays = 1
            rows.append(
                {
                    "deployment_date": day,
                    "market_id": market_id,
                    "installations_scheduled": scheduled,
                    "installations_completed": completed,
                    "installations_target": target,
                    "first_time_completion_count": first_time,
                    "rework_count": rework,
                    "average_cycle_time_days": cycle_for(role, day, completed),
                    "jobs_waiting_for_parts": waiting_for(role, day),
                    "customer_delay_count": delays,
                    "critical_incidents": critical,
                    "stockout_events": stockout,
                }
            )
    return rows


def aggregate_markets(daily: list[dict], market_ids: list[str]) -> list[dict]:
    buckets: dict[tuple[str, str], list[dict]] = {}
    for row in daily:
        buckets.setdefault((row["market_id"], month_key(row["deployment_date"])), []).append(row)
    periods = ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
    out = []
    for period in periods:
        for market_id in market_ids:
            chunk = buckets.get((market_id, period), [])
            must(chunk, f"no daily rows for {market_id} {period}")
            completed = sum(row["installations_completed"] for row in chunk)
            scheduled = sum(row["installations_scheduled"] for row in chunk)
            target = sum(row["installations_target"] for row in chunk)
            first_time = sum(row["first_time_completion_count"] for row in chunk)
            rework = sum(row["rework_count"] for row in chunk)
            delays = sum(row["customer_delay_count"] for row in chunk)
            critical = sum(row["critical_incidents"] for row in chunk)
            stockout = sum(row["stockout_events"] for row in chunk)
            last = max(chunk, key=lambda row: row["deployment_date"])
            weighted = 0
            for row in chunk:
                if row["installations_completed"] and row["average_cycle_time_days"] is not None:
                    weighted += row["average_cycle_time_days"] * row["installations_completed"]
            cycle = round(weighted / completed, 1) if completed else None
            attainment = round(100 * completed / target, 1) if target else None
            ftc_rate = round(first_time / completed, 3) if completed else None
            rework_rate = round(rework / completed, 3) if completed else None
            out.append(
                {
                    "period": period,
                    "market_id": market_id,
                    "installations_scheduled": scheduled,
                    "installations_completed": completed,
                    "installations_target": target,
                    "installation_attainment_percentage": attainment,
                    "first_time_completion_count": first_time,
                    "first_time_completion_rate": ftc_rate,
                    "rework_count": rework,
                    "rework_rate": rework_rate,
                    "average_cycle_time_days": cycle,
                    "jobs_waiting_for_parts": last["jobs_waiting_for_parts"],
                    "customer_delay_count": delays,
                    "critical_incidents": critical,
                    "stockout_events": stockout,
                }
            )
    return out


def weeks_covering() -> list[date]:
    start = week_start(DAILY_START)
    end = week_start(WBR_END)
    weeks = []
    cursor = start
    while cursor <= end:
        weeks.append(cursor)
        cursor += timedelta(days=7)
    return weeks


def rows_in_week(daily: list[dict], market_id: str, start: date) -> list[dict]:
    stop = start + timedelta(days=6)
    return [
        row
        for row in daily
        if row["market_id"] == market_id and start <= row["deployment_date"] <= stop
    ]


def build_funnel(daily: list[dict], market_ids: list[str], weeks: list[date]) -> list[dict]:
    rows = []
    for start in weeks:
        for market_id in market_ids:
            chunk = rows_in_week(daily, market_id, start)
            scheduled = sum(row["installations_scheduled"] for row in chunk)
            completed = sum(row["installations_completed"] for row in chunk)
            role = ROLE[market_id]
            if role == "scale":
                contracts = max(scheduled, completed)
                proposals = contracts + 2
                surveys = proposals + 3
                qualified = surveys + 4
                leads = qualified + 6
            elif role == "blocked":
                leads, qualified, surveys, proposals, contracts = 15, 10, 8, 4, 1
            elif role == "slowdown":
                leads, qualified, surveys, proposals, contracts = 16, 12, 10, 8, 6
            elif role == "paused" and start >= week_start(PAUSE_START):
                leads, qualified, surveys, proposals, contracts = 2, 1, 0, 0, 0
            elif role == "bottleneck":
                contracts = scheduled
                proposals = contracts + 3
                surveys = proposals + 4
                qualified = surveys + 5
                leads = qualified + 6
            else:
                leads, qualified, surveys, proposals = 18, 13, 10, 8
                contracts = min(8, max(completed, 4 if scheduled else 0))
            must(leads >= qualified >= surveys >= proposals >= contracts, f"funnel order {market_id} {start}")
            rows.append(
                {
                    "week_start": start,
                    "market_id": market_id,
                    "leads": leads,
                    "qualified_leads": qualified,
                    "site_surveys": surveys,
                    "proposals": proposals,
                    "contracts": contracts,
                    "installations_scheduled": scheduled,
                    "installations_completed": completed,
                }
            )
    return rows


def build_experience(market_ids: list[str], weeks: list[date]) -> list[dict]:
    decline_weeks = [start for start in weeks if start >= SLOWDOWN_START]
    steps = [
        (74, 11, 0.12, 3, 16),
        (69, 14, 0.16, 5, 14),
        (64, 17, 0.19, 6, 12),
        (60, 20, 0.22, 8, 10),
        (56, 23, 0.26, 9, 8),
    ]
    rows = []
    for start in weeks:
        for market_id in market_ids:
            role = ROLE[market_id]
            if role == "slowdown" and start in decline_weeks:
                csat, hours, repeat, complaints, surveys = steps[min(decline_weeks.index(start), len(steps) - 1)]
            elif role == "slowdown":
                csat, hours, repeat, complaints, surveys = 82, 7, 0.08, 1, 18
            elif role == "scale":
                csat, hours, repeat, complaints, surveys = 89, 5, 0.05, 1, 28
            elif role == "improvement" and start >= IMPROVE_START:
                csat, hours, repeat, complaints, surveys = 84, 6, 0.07, 1, 16
            elif role == "improvement":
                csat, hours, repeat, complaints, surveys = 73, 10, 0.14, 3, 14
            elif role == "blocked":
                csat, hours, repeat, complaints, surveys = 71, 16, 0.11, 1, 6
            elif role == "paused":
                csat, hours, repeat, complaints, surveys = 77, 8, 0.09, 1, 8
            elif role == "bottleneck" and start >= date(2026, 9, 1):
                csat, hours, repeat, complaints, surveys = 78, 9, 0.10, 2, 22
            else:
                csat, hours, repeat, complaints, surveys = 81, 7, 0.08, 1, 20
            nps = max(-100, min(100, int(round((csat - 75) * 2))))
            rows.append(
                {
                    "week_start": start,
                    "market_id": market_id,
                    "csat_score": csat,
                    "nps": nps,
                    "average_response_time_hours": hours,
                    "repeat_contact_rate": repeat,
                    "installation_complaint_count": complaints,
                    "survey_responses": surveys,
                }
            )
    return rows


def build_workforce(daily: list[dict], markets: list[dict], weeks: list[date]) -> list[dict]:
    by_id = {row["market_id"]: row for row in markets}
    rows = []
    for start in weeks:
        for market in markets:
            market_id = market["market_id"]
            chunk = rows_in_week(daily, market_id, start)
            scheduled = sum(row["installations_scheduled"] for row in chunk)
            completed = sum(row["installations_completed"] for row in chunk)
            certified = market["certified_technician_count"]
            technician_count = market["technician_count"]
            role = ROLE[market_id]
            if role == "blocked":
                utilization = 40
                overtime = 0
            else:
                capacity = certified * CAPACITY_PER_CERT_TECH
                utilization = round(100 * scheduled / capacity) if capacity else 0
                overtime = max(0, scheduled - capacity) * 2
            rows.append(
                {
                    "week_start": start,
                    "market_id": market_id,
                    "technician_count": technician_count,
                    "certified_technician_count": certified,
                    "open_positions": by_id[market_id]["open_positions"],
                    "scheduled_installations": scheduled,
                    "installations_completed": completed,
                    "utilization_percentage": utilization,
                    "overtime_hours": overtime,
                }
            )
    return rows


def build_warehouses(daily: list[dict], inventory: list[dict], weeks: list[date]) -> list[dict]:
    below = {"W001": 0, "W002": 0, "W003": 0}
    for row in inventory:
        available = int(row["quantity_available"])
        reorder = int(row["reorder_point"])
        if available < reorder:
            below[row["warehouse_id"]] = below.get(row["warehouse_id"], 0) + 1
    markets_for = {"W001": [], "W002": [], "W003": []}
    for market_id, warehouse_id in WAREHOUSE_OF.items():
        markets_for[warehouse_id].append(market_id)
    rows = []
    for start in weeks:
        stop = start + timedelta(days=6)
        for warehouse_id in ("W001", "W002", "W003"):
            chunk = [
                row
                for row in daily
                if row["market_id"] in markets_for[warehouse_id] and start <= row["deployment_date"] <= stop
            ]
            last_day = min(SNAPSHOT, stop)
            waiting = 0
            for market_id in markets_for[warehouse_id]:
                day_rows = [row for row in chunk if row["market_id"] == market_id and row["deployment_date"] == last_day]
                if not day_rows and chunk:
                    day_rows = [max((row for row in chunk if row["market_id"] == market_id), key=lambda row: row["deployment_date"])]
                if day_rows:
                    waiting += day_rows[0]["jobs_waiting_for_parts"]
            if warehouse_id == "W001" and start >= SLOWDOWN_START:
                fill = 86
                note = "P006 HaloWave quantity_available at W001 is 0 on the 2026-09-27 inventory snapshot."
            elif warehouse_id == "W001":
                fill = 97
                note = "No W001 stockout days in this week."
            elif warehouse_id == "W002":
                fill = 98
                note = "W002 continues to fill Cedar Park, Round Rock, and Pflugerville."
            else:
                fill = 93
                note = "Georgetown shipping is live. San Marcos launch locations at W003 are not configured in the WMS."
            rows.append(
                {
                    "week_start": start,
                    "warehouse_id": warehouse_id,
                    "stockout_events": sum(row["stockout_events"] for row in chunk),
                    "jobs_waiting_for_parts": waiting,
                    "fill_rate_percentage": fill,
                    "inventory_accuracy_percentage": 99 if warehouse_id == "W002" else 98,
                    "cycle_counts_completed": 8 if warehouse_id == "W003" else 12,
                    "lines_below_reorder": below.get(warehouse_id, 0),
                    "wms_core_status": "Operational",
                    "launch_location_configured": "no" if warehouse_id == "W003" else "yes",
                    "notes": note,
                }
            )
    return rows


def build_inventory_risk(sources: dict, markets: list[dict]) -> list[dict]:
    parts = index_by(sources["parts"], "part_id")
    markets_for: dict[str, list[str]] = {}
    for market in markets:
        markets_for.setdefault(market["warehouse_id"], []).append(market["market_id"])
    problem = []
    healthy = []
    for row in sources["inventory"]:
        available = int(row["quantity_available"])
        reorder = int(row["reorder_point"])
        item = {
            "part_id": row["part_id"],
            "warehouse_id": row["warehouse_id"],
            "available": available,
            "reorder": reorder,
        }
        if available < reorder:
            problem.append(item)
        else:
            healthy.append(item)
    must(any(item["part_id"] == "P006" and item["warehouse_id"] == "W001" and item["available"] == 0 for item in problem), "expected P006 to be out at W001")
    problem.sort(key=lambda item: (0 if item["part_id"] == "P006" and item["warehouse_id"] == "W001" else 1, item["part_id"], item["warehouse_id"]))
    healthy.sort(key=lambda item: (-item["available"], item["part_id"], item["warehouse_id"]))
    chosen = problem + healthy
    # Keep about 20: all current problem lines, then healthy lines.
    if len(problem) >= 20:
        chosen = problem[:20]
    else:
        chosen = problem + healthy[: 20 - len(problem)]
    must(len(chosen) == 20, f"expected 20 inventory risks, got {len(chosen)}")
    job_ids = {row["job_id"] for row in sources["jobs"]}
    must("J001" in job_ids and "J007" in job_ids, "expected J001 and J007")
    rows = []
    for index, item in enumerate(chosen, start=1):
        part = parts[item["part_id"]]
        available = item["available"]
        if item["part_id"] == "P006" and item["warehouse_id"] == "W001":
            consumption = 4
            level = "Critical"
            blocked = 0
            note = (
                "W001 quantity_available for P006 HaloWave 7.6 Hybrid Inverter is 0. "
                "No Waiting for Parts job in jobs.csv has a customer in a W001 market. "
                "J007 is an inverter repair waiting on parts for a Cedar Park customer served by W002, where P006 is still available. "
                "Weekly consumption is a planning rate, not a purchase order."
            )
        elif item["part_id"] == "P018" and item["warehouse_id"] in ("W002", "W003"):
            consumption = 2
            level = "High"
            blocked = 1 if item["warehouse_id"] == "W002" else 0
            note = (
                f"P018 200A Class T Fuse is below reorder at {item['warehouse_id']} "
                f"(quantity_available {available}). J001 is Waiting for Parts with an open Class T fuse symptom. "
                "W001 still shows a higher P018 balance, so this is not the same position as the W001 P006 stockout."
            )
        elif available == 0:
            consumption = 1
            level = "High"
            blocked = 0
            note = f"{part['part_name']} quantity_available is 0 at {item['warehouse_id']}."
        elif available < item["reorder"]:
            consumption = 1
            level = "Medium"
            blocked = 0
            note = f"{part['part_name']} is below its warehouse reorder point at {item['warehouse_id']}."
        else:
            consumption = 1
            level = "Low"
            blocked = 0
            note = f"{part['part_name']} quantity_available at {item['warehouse_id']} covers multiple weeks at the planning rate."
        weeks = round(available / consumption, 1)
        rows.append(
            {
                "risk_id": f"IR-{index:03d}",
                "as_of_date": SNAPSHOT,
                "part_id": item["part_id"],
                "warehouse_id": item["warehouse_id"],
                "part_name": part["part_name"],
                "part_criticality": part["criticality"],
                "current_available_quantity": available,
                "weekly_consumption": consumption,
                "weeks_of_supply": weeks,
                "stockout_risk": level,
                "jobs_blocked": blocked,
                "affected_market_ids": ";".join(markets_for.get(item["warehouse_id"], [])),
                "note": note,
            }
        )
    return rows


def build_engineering(sources: dict, weeks: list[date]) -> list[dict]:
    incidents = index_by(sources["incidents"], "incident_id")
    must("INC-002" in incidents, "INC-002 missing")
    inc = incidents["INC-002"]
    must(inc["created_at"].startswith("2026-09-15"), "INC-002 is not dated 2026-09-15")
    must(inc["firmware_related"] == "true", "INC-002 is not firmware related")
    must(inc["related_firmware_version"] == "4.3.0", "INC-002 is not firmware 4.3.0")
    affected = int(inc["affected_device_count"])
    on_430 = [row["device_id"] for row in sources["devices"] if row["firmware_version"] == "4.3.0"]
    must(on_430, "no devices left on 4.3.0")
    fw_spike = affected + 2
    fw_decline = max(1, fw_spike // 2)
    must(fw_spike > fw_decline > 0, "firmware spike did not decline")
    active = 4
    rows = []
    for start in weeks:
        if start == FW_WEEK:
            new = fw_spike + 2
            resolved = 1
            firmware_count = fw_spike
            devices_on = affected
            primary = "INC-002"
            note = (
                f"Week of 2026-09-15 (week starting {FW_WEEK.isoformat()}). "
                f"INC-002 affected_device_count is {affected}. Firmware 4.3.0 rollout spike."
            )
        elif start == FW_DECLINE_WEEK:
            new = fw_decline
            active_target = 4 + fw_decline + 1
            resolved = active + new - active_target
            firmware_count = fw_decline
            devices_on = len(on_430)
            primary = "INC-002"
            note = (
                "Partial decline after the 4.3.0 halt and rollback. INC-002 is still the primary incident. "
                f"devices.csv currently shows {len(on_430)} devices on 4.3.0 ({', '.join(on_430)})."
            )
        elif start == date(2026, 8, 31):
            new, resolved, firmware_count = 3, 3, 1
            devices_on = 0
            primary = "INC-022"
            note = "INC-022 is firmware_related on 4.3.1. It is not the 4.3.0 regression."
        else:
            new, resolved, firmware_count = 2, 2, 0
            devices_on = 0
            primary = ""
            note = ""
        must(resolved >= 0, f"negative resolves on {start}")
        active = active + new - resolved
        must(active >= 0, f"negative active incidents on {start}")
        rows.append(
            {
                "week_start": start,
                "firmware_related_incidents": firmware_count,
                "active_incidents": active,
                "new_incidents": new,
                "resolved_incidents": resolved,
                "devices_on_firmware_430": devices_on,
                "rollout_affected_device_count": affected if start == FW_WEEK else (len(on_430) if start == FW_DECLINE_WEEK else 0),
                "primary_incident_id": primary,
                "notes": note,
            }
        )
    return rows


def build_reliability(sources: dict) -> list[dict]:
    incidents = index_by(sources["incidents"], "incident_id")
    must("INC-005" in incidents, "INC-005 missing")
    counts: dict[tuple[str, str], int] = {}
    degraded: dict[tuple[str, str], list[str]] = {}
    for device in sources["devices"]:
        key = (device["device_type"], device["hardware_revision"])
        counts[key] = counts.get(key, 0) + 1
        if device["status"] == "Degraded":
            degraded.setdefault(key, []).append(device["device_id"])
    periods = ["2026-04", "2026-05", "2026-06", "2026-07", "2026-08", "2026-09"]
    rows = []
    for period in periods:
        for (device_type, revision) in sorted(counts):
            base = counts[(device_type, revision)]
            if revision == "HW-C":
                failure_count = max(1, int(round(base * 0.25)))
                if device_type == "Battery" and period == "2026-09":
                    failure_count += 1
            else:
                failure_count = 1 if base >= 20 else 0
            failure_count = min(base, failure_count)
            rate = round(failure_count / base, 4)
            related = ""
            device_ids = ""
            note = "installed_base is the 2026-09-27 device census, repeated across months."
            if revision == "HW-C" and device_type == "Battery":
                related = "INC-005"
                ids = degraded.get((device_type, revision), [])
                device_ids = ";".join(ids)
                note = (
                    "INC-005 describes HW-C cell imbalance from a busbar torque issue. "
                    f"Degraded HW-C batteries in devices.csv: {device_ids or 'none'}."
                )
            elif revision == "HW-C":
                note = (
                    "HW-C failure_rate is elevated versus other revisions of this device type. "
                    "INC-005 confirms a battery mechanism; do not treat that root cause as proven for this device type."
                )
            rows.append(
                {
                    "period": period,
                    "device_type": device_type,
                    "hardware_revision": revision,
                    "installed_base": base,
                    "failure_count": failure_count,
                    "failure_rate": rate,
                    "related_incident_id": related,
                    "related_device_ids": device_ids,
                    "notes": note,
                }
            )
    return rows


def build_company(monthly: list[dict], experience: list[dict], workforce: list[dict], open_critical: int) -> list[dict]:
    periods = []
    year, month = 2025, 10
    for _ in range(12):
        periods.append(f"{year:04d}-{month:02d}")
        month += 1
        if month == 13:
            month = 1
            year += 1
    early = {
        "2025-10": (248, 260, 240, 2, 1, 79.0, 71.0, 1, 0.860),
        "2025-11": (261, 275, 250, 1, 0, 80.0, 74.0, 1, 0.870),
        "2025-12": (214, 240, 250, 3, 2, 76.0, 68.0, 2, 0.810),
        "2026-01": (198, 220, 230, 2, 1, 75.0, 64.0, 1, 0.800),
        "2026-02": (226, 250, 240, 4, 3, 77.0, 70.0, 2, 0.830),
        "2026-03": (255, 270, 245, 1, 1, 81.0, 73.0, 1, 0.880),
    }
    by_period: dict[str, list[dict]] = {}
    for row in monthly:
        by_period.setdefault(row["period"], []).append(row)
    rows = []
    for period in periods:
        if period in early:
            scheduled, completed, target, critical, stockout, csat, util, risks, ftc = early[period]
            rows.append(
                {
                    "period": period,
                    "installations_scheduled": scheduled,
                    "installations_completed": completed,
                    "installations_target": target,
                    "installation_attainment_percentage": round(100 * completed / target, 1),
                    "first_time_completion_rate": ftc,
                    "critical_incidents": critical,
                    "stockout_events": stockout,
                    "average_csat": csat,
                    "workforce_utilization_percentage": util,
                    "open_critical_risks": risks,
                    "drilldown_available": "no",
                    "notes": "No market_performance rows exist before 2026-04. Do not allocate this month across markets.",
                }
            )
            continue
        chunk = by_period[period]
        completed = sum(row["installations_completed"] for row in chunk)
        scheduled = sum(row["installations_scheduled"] for row in chunk)
        target = sum(row["installations_target"] for row in chunk)
        critical = sum(row["critical_incidents"] for row in chunk)
        stockout = sum(row["stockout_events"] for row in chunk)
        first_time = sum(row["first_time_completion_count"] for row in chunk)
        year_n, month_n = int(period[:4]), int(period[5:])
        csat_vals = [
            row["csat_score"]
            for row in experience
            if row["week_start"].year == year_n and row["week_start"].month == month_n
        ]
        util_vals = [
            row["utilization_percentage"]
            for row in workforce
            if row["week_start"].year == year_n and row["week_start"].month == month_n
        ]
        must(csat_vals and util_vals, f"missing weekly inputs for {period}")
        rows.append(
            {
                "period": period,
                "installations_scheduled": scheduled,
                "installations_completed": completed,
                "installations_target": target,
                "installation_attainment_percentage": round(100 * completed / target, 1) if target else None,
                "first_time_completion_rate": round(first_time / completed, 3) if completed else None,
                "critical_incidents": critical,
                "stockout_events": stockout,
                "average_csat": round(sum(csat_vals) / len(csat_vals), 1),
                "workforce_utilization_percentage": round(sum(util_vals) / len(util_vals), 1),
                "open_critical_risks": open_critical if period == "2026-09" else 2,
                "drilldown_available": "yes",
                "notes": (
                    "installations_completed, critical_incidents, and stockout_events equal the sum of "
                    "market_performance for this month. Those market totals equal deployment_metrics."
                ),
            }
        )
    return rows


def build_risks(highlights: dict) -> list[dict]:
    specs = [
        ("RSK-01", date(2026, 8, 26), "Critical", "open", "MKT-002", "W001", "", "", "INIT-02", "SCN-01", "installations_completed", highlights["m002_sep_completed"], "North Austin installations down", "Completed installations in MKT-002 fell after 2026-08-24 while the monthly target did not."),
        ("RSK-02", date(2026, 8, 26), "Critical", "open", "MKT-002", "W001", "P006", "", "INIT-03", "SCN-04", "weeks_of_supply", highlights["p006_wos"], "P006 stockout at W001", "HaloWave 7.6 Hybrid Inverter weeks_of_supply at W001 is 0.0 on the inventory snapshot."),
        ("RSK-03", date(2026, 9, 15), "High", "open", "", "", "", "INC-002", "INIT-05", "SCN-05", "firmware_related_incidents", highlights["fw_spike"], "Firmware 4.3.0 regression", "INC-002 is the heartbeat regression. The week of 2026-09-15 spiked, then the next week declined only part way."),
        ("RSK-04", date(2026, 7, 8), "High", "open", "MKT-006", "W003", "", "", "INIT-04", "SCN-03", "certified_technician_count", 3, "San Marcos launch blocked", "Launch roster certification is 3 of 5. WMS locations for San Marcos at W003 are unfinished."),
        ("RSK-05", date(2026, 9, 16), "High", "open", "", "", "", "INC-005", "INIT-06", "SCN-08", "failure_rate", highlights["hwc_rate"], "HW-C battery failure rate", "Battery HW-C failure_rate is above Battery HW-B. INC-005 is the investigated mechanism."),
        ("RSK-06", date(2026, 6, 15), "High", "open", "MKT-001", "", "", "", "INIT-08", "SCN-07", "utilization_percentage", highlights["austin_util_latest"], "Austin Metro crew over book", "Scheduled installs in MKT-001 rose faster than certified headcount. Utilization is above 100 and open_positions is 3."),
        ("RSK-07", date(2026, 9, 2), "High", "open", "MKT-002", "", "", "", "", "SCN-06", "csat_score", highlights["m002_csat_latest"], "North Austin CSAT decline", "CSAT, response time, repeat contacts, and installation complaints moved together in MKT-002."),
        ("RSK-08", date(2026, 8, 26), "Medium", "open", "MKT-002", "W001", "P006", "", "INIT-03", "SCN-04", "jobs_waiting_for_parts", highlights["m002_sep_waiting"], "Jobs waiting for parts", "MKT-002 month-end jobs_waiting_for_parts is elevated versus June."),
        ("RSK-09", date(2026, 8, 26), "Medium", "mitigating", "", "W001", "P006", "", "INIT-03", "SCN-04", "stockout_events", highlights["m002_sep_stockouts"], "W001 stockout days", "Market-days with a stockout flag rose for the W001 markets after 2026-08-24."),
        ("RSK-10", date(2026, 8, 26), "Medium", "open", "MKT-002", "", "", "", "INIT-02", "SCN-01", "average_cycle_time_days", highlights["m002_sep_cycle"], "North Austin cycle time", "September cycle time in MKT-002 is longer than July."),
        ("RSK-11", date(2026, 7, 6), "Medium", "monitoring", "MKT-005", "", "", "", "INIT-01", "SCN-09", "average_cycle_time_days", highlights["geo_sep_cycle"], "Georgetown cycle time watch", "Cycle time fell after INIT-01. Keep watching so the gain holds."),
        ("RSK-12", date(2026, 5, 4), "Low", "monitoring", "MKT-003", "W002", "", "", "", "SCN-10", "overtime_hours", 0, "Round Rock overtime watch", "Round Rock overtime is not the current constraint. Status is monitoring, severity Low."),
        ("RSK-13", date(2026, 4, 9), "Low", "closed", "MKT-003", "", "", "", "", "", "installation_complaint_count", 1, "Closed spring complaint cluster", "An April complaint cluster in Round Rock was closed. It is not an open executive issue."),
        ("RSK-14", date(2026, 9, 10), "Critical", "mitigating", "MKT-003", "W002", "P018", "", "INIT-03", "SCN-04", "weeks_of_supply", highlights["p018_wos"], "P018 low at W002", "Class T fuse weeks of supply at W002 are low. This is a different part and warehouse from the P006 stockout."),
        ("RSK-15", date(2026, 1, 12), "Critical", "closed", "", "W002", "", "", "", "", "stockout_events", 0, "Closed winter stockout", "A January W002 stockout was closed. September company history is a different event."),
        ("RSK-16", date(2026, 8, 3), "High", "mitigating", "MKT-002", "", "", "", "INIT-02", "SCN-07", "open_positions", 4, "North Austin open positions", "MKT-002 open_positions is 4 against a two-person field extract."),
        ("RSK-17", date(2026, 8, 26), "High", "monitoring", "MKT-002", "", "", "", "INIT-02", "SCN-01", "rework_rate", highlights["m002_sep_rework"], "North Austin rework", "Rework rate in MKT-002 rose after 2026-08-24."),
        ("RSK-18", date(2026, 6, 1), "Medium", "closed", "MKT-005", "", "", "", "INIT-01", "SCN-09", "first_time_completion_rate", highlights["geo_sep_ftc"], "Georgetown quality gap closed", "The pre-July quality gap in Georgetown is closed. INIT-01 stays on the books as completed work."),
        ("RSK-19", date(2026, 9, 1), "Low", "open", "", "W002", "", "", "", "SCN-10", "inventory_accuracy_percentage", 99, "W002 accuracy watch", "W002 inventory accuracy is healthy. Severity is Low and status is open as a watch item."),
        ("RSK-20", date(2026, 7, 20), "Medium", "open", "MKT-006", "W003", "P003", "", "INIT-04", "SCN-03", "launch_location_configured", "no", "San Marcos inventory and WMS", "W003 launch_location_configured is no. P003 quantity_available at W003 is 0, and P006 is not a stocked launch position there."),
    ]
    must(len(specs) == 20, "expected 20 risks")
    rows = []
    for spec in specs:
        rows.append(
            {
                "risk_id": spec[0],
                "opened_date": spec[1],
                "severity": spec[2],
                "status": spec[3],
                "market_id": spec[4],
                "warehouse_id": spec[5],
                "part_id": spec[6],
                "related_incident_id": spec[7],
                "related_initiative_id": spec[8],
                "scenario_id": spec[9],
                "affected_metric": spec[10],
                "observed_value": spec[11],
                "title": spec[12],
                "summary": spec[13],
            }
        )
    return rows


def build_initiatives() -> list[dict]:
    return [
        {
            "initiative_id": "INIT-01",
            "initiative_name": "Georgetown cycle-time reduction",
            "status": "Active",
            "start_date": IMPROVE_START,
            "target_end_date": date(2026, 10, 31),
            "owner_role": "VP Operations",
            "market_id": "MKT-005",
            "related_risk_id": "RSK-11",
            "related_incident_id": "",
            "scenario_id": "SCN-09",
            "expected_effect": "Lower cycle time, higher first-time completion, lower rework in Georgetown.",
            "status_note": "Started 2026-07-06. September quality is better than June. Headcount did not change.",
        },
        {
            "initiative_id": "INIT-02",
            "initiative_name": "North Austin installation recovery",
            "status": "Active",
            "start_date": date(2026, 9, 1),
            "target_end_date": date(2026, 11, 15),
            "owner_role": "VP Operations",
            "market_id": "MKT-002",
            "related_risk_id": "RSK-01",
            "related_incident_id": "",
            "scenario_id": "SCN-01",
            "expected_effect": "Restore completed installations in North Austin.",
            "status_note": "Crew recovery is open. September completions are still down, so the initiative has not shown up in the totals yet.",
        },
        {
            "initiative_id": "INIT-03",
            "initiative_name": "P006 HaloWave replenishment",
            "status": "Active",
            "start_date": date(2026, 9, 8),
            "target_end_date": date(2026, 10, 12),
            "owner_role": "VP Operations",
            "market_id": "MKT-001",
            "related_risk_id": "RSK-02",
            "related_incident_id": "",
            "scenario_id": "SCN-04",
            "expected_effect": "Restore P006 quantity_available at W001 above reorder.",
            "status_note": "Snapshot still shows 0 available at W001. P018 at W002 is a separate buy.",
        },
        {
            "initiative_id": "INIT-04",
            "initiative_name": "San Marcos WMS launch configuration",
            "status": "On Hold",
            "start_date": date(2026, 8, 3),
            "target_end_date": date(2026, 10, 30),
            "owner_role": "VP Operations",
            "market_id": "MKT-006",
            "related_risk_id": "RSK-04",
            "related_incident_id": "",
            "scenario_id": "SCN-03",
            "expected_effect": "Finish WMS locations and minimum launch inventory at W003 before first-wave installs.",
            "status_note": "Blocked. launch_location_configured is no. Certified coverage on the launch roster is 60%.",
        },
        {
            "initiative_id": "INIT-05",
            "initiative_name": "Firmware 4.3.1 completion",
            "status": "Active",
            "start_date": date(2026, 9, 15),
            "target_end_date": date(2026, 10, 6),
            "owner_role": "VP Engineering",
            "market_id": "",
            "related_risk_id": "RSK-03",
            "related_incident_id": "INC-002",
            "scenario_id": "SCN-05",
            "expected_effect": "Move remaining 4.3.0 devices to 4.3.1 and keep firmware-related incidents down.",
            "status_note": "INC-002 is mitigated, not closed. The week after 2026-09-15 declined only part way.",
        },
        {
            "initiative_id": "INIT-06",
            "initiative_name": "HW-C busbar torque campaign",
            "status": "Active",
            "start_date": date(2026, 9, 16),
            "target_end_date": date(2026, 11, 30),
            "owner_role": "VP Engineering",
            "market_id": "",
            "related_risk_id": "RSK-05",
            "related_incident_id": "INC-005",
            "scenario_id": "SCN-08",
            "expected_effect": "Cut Battery HW-C failure_rate after busbar re-torque.",
            "status_note": "Tied to INC-005. September Battery HW-C failure_rate is still the high revision.",
        },
        {
            "initiative_id": "INIT-07",
            "initiative_name": "Cedar Park scale playbook",
            "status": "Active",
            "start_date": date(2026, 6, 1),
            "target_end_date": date(2026, 12, 15),
            "owner_role": "VP Operations",
            "market_id": "MKT-004",
            "related_risk_id": "",
            "related_incident_id": "",
            "scenario_id": "SCN-02",
            "expected_effect": "Hold first-time completion and cycle time while Cedar Park volume stays high.",
            "status_note": "Metrics support more volume. This row is not a rank and does not label the market best.",
        },
        {
            "initiative_id": "INIT-08",
            "initiative_name": "Austin Metro certified capacity",
            "status": "Active",
            "start_date": date(2026, 5, 4),
            "target_end_date": date(2026, 12, 1),
            "owner_role": "VP Operations",
            "market_id": "MKT-001",
            "related_risk_id": "RSK-06",
            "related_incident_id": "",
            "scenario_id": "SCN-07",
            "expected_effect": "Add certified capacity so scheduled demand stops outrunning the crew.",
            "status_note": "Certified headcount is flat. September utilization is above 100 and open_positions is 3.",
        },
    ]


def build_wbr(daily: list[dict], experience: list[dict], workforce: list[dict], engineering: list[dict]) -> list[dict]:
    weeks = []
    cursor = WBR_END - timedelta(weeks=15)
    while cursor <= WBR_END:
        weeks.append(cursor)
        cursor += timedelta(days=7)
    must(len(weeks) == 16, "WBR week count is not 16")
    must(weeks[-1] == WBR_END, "WBR does not end on 2026-09-21")
    eng = {row["week_start"]: row for row in engineering}
    rows = []
    for start in weeks:
        stop = start + timedelta(days=6)
        chunk = [row for row in daily if start <= row["deployment_date"] <= stop]
        completed = sum(row["installations_completed"] for row in chunk)
        target = sum(row["installations_target"] for row in chunk)
        critical = sum(row["critical_incidents"] for row in chunk)
        stockout = sum(row["stockout_events"] for row in chunk)
        csat_vals = [row["csat_score"] for row in experience if row["week_start"] == start]
        util_vals = [row["utilization_percentage"] for row in workforce if row["week_start"] == start]
        must(len(csat_vals) == 7 and len(util_vals) == 7, f"WBR inputs missing for {start}")
        risks = []
        attention = []
        if start >= SLOWDOWN_START:
            risks.append("SCN-01 MKT-002 installation slowdown")
            risks.append("SCN-04 P006 weeks_of_supply at W001")
            attention.append("SCN-06 CSAT decline in North Austin")
        if start >= FW_WEEK:
            risks.append("SCN-05 INC-002 firmware 4.3.0")
        if start >= IMPROVE_START:
            attention.append("SCN-09 Georgetown INIT-01")
        attention.append("SCN-02 Cedar Park volume watch")
        attention.append("SCN-03 San Marcos launch still blocked")
        if start >= date(2026, 6, 8):
            risks.append("SCN-07 MKT-001 demand versus certified crew")
        if start == WBR_END:
            attention.append(
                "SCN-11 versus week of 2026-09-14: company installs rose because 2026-09-16 was a short Cedar Park day; MKT-002 did not recover"
            )
        if not risks:
            risks.append("SCN-10 open risks remain mixed severity")
        rows.append(
            {
                "week_start": start,
                "installations_completed": completed,
                "installations_target": target,
                "installation_attainment_percentage": round(100 * completed / target, 1) if target else None,
                "average_csat": round(sum(csat_vals) / len(csat_vals), 1),
                "critical_incidents": critical,
                "stockout_events": stockout,
                "workforce_utilization_percentage": round(sum(util_vals) / len(util_vals), 1),
                "firmware_related_incidents": eng[start]["firmware_related_incidents"],
                "major_risks": "; ".join(risks),
                "executive_attention_items": "; ".join(attention),
            }
        )
    return rows


def build_alerts() -> list[dict]:
    specs = [
        ("ALT-001", date(2026, 9, 22), "Critical", "Open", "MKT-002", "SCN-04", "RSK-02", "", "P006 available is 0 at W001", "HaloWave weeks of supply is 0.0. North Austin and Austin Metro both draw from W001."),
        ("ALT-002", date(2026, 9, 21), "High", "Open", "MKT-002", "SCN-01", "RSK-01", "", "North Austin installations still down", "Completed installs remain well below the pre-August run rate. Rework is up."),
        ("ALT-003", date(2026, 9, 15), "High", "Open", "", "SCN-05", "RSK-03", "INC-002", "Firmware 4.3.0 heartbeat regression", "INC-002 opened 2026-09-15. Firmware-related incidents spiked that week and only partly declined the next week."),
        ("ALT-004", date(2026, 8, 20), "High", "Open", "MKT-006", "SCN-03", "RSK-04", "", "San Marcos WMS configuration unfinished", "Launch locations at W003 are not configured. Certified coverage on the launch roster is 3 of 5."),
        ("ALT-005", date(2026, 9, 23), "Medium", "Open", "MKT-002", "SCN-06", "RSK-07", "", "North Austin CSAT fell again", "Latest week CSAT is 56, with slower response, more repeat contacts, and more installation complaints."),
        ("ALT-006", date(2026, 9, 17), "High", "Open", "", "SCN-08", "RSK-05", "INC-005", "HW-C battery failure rate elevated", "Battery HW-C failure_rate is above other revisions. INC-005 is the linked investigation."),
        ("ALT-007", date(2026, 9, 18), "Medium", "Open", "MKT-001", "SCN-07", "RSK-06", "", "Austin Metro utilization above capacity", "Scheduled work is above certified weekly capacity and overtime is up. Open positions are 3."),
        ("ALT-008", date(2026, 9, 19), "Low", "Open", "MKT-003", "SCN-04", "RSK-14", "", "P018 weeks of supply are thin at W002", "Class T fuse coverage at W002 is low. This is not the W001 P006 stockout."),
        ("ALT-009", date(2026, 7, 20), "Medium", "Acknowledged", "MKT-005", "SCN-09", "RSK-11", "", "Georgetown cycle time is improving", "INIT-01 started 2026-07-06. September cycle time and rework are better than June."),
        ("ALT-010", date(2026, 8, 3), "Low", "Acknowledged", "MKT-007", "", "", "", "Pflugerville expansion paused", "Completed installations in MKT-007 are zero after 2026-08-03."),
        ("ALT-011", date(2026, 6, 12), "High", "Resolved", "MKT-003", "", "", "", "Round Rock permit delay cleared", "A June permit hold was resolved. It is not the current North Austin slowdown."),
        ("ALT-012", date(2026, 5, 2), "Medium", "Resolved", "MKT-004", "SCN-02", "", "", "Cedar Park truck gap closed", "A May vehicle gap was resolved before the scale playbook."),
        ("ALT-013", date(2026, 9, 16), "Critical", "Acknowledged", "MKT-001", "SCN-04", "RSK-02", "", "W001 stockout days still hitting Austin Metro", "The week of 2026-09-14 includes extra W001 stockout flags on Austin Metro as well as North Austin."),
        ("ALT-014", date(2026, 4, 15), "Low", "Resolved", "MKT-003", "", "", "", "Round Rock spring training closed", "Training follow-up from April is closed."),
        ("ALT-015", date(2026, 9, 25), "Medium", "Open", "", "SCN-11", "", "", "Week-over-week review is mixed", "Installs, CSAT, incidents, stockouts, and utilization all moved between the weeks of 2026-09-14 and 2026-09-21. The install increase is not a North Austin recovery."),
    ]
    must(len(specs) == 15, "expected 15 alerts")
    rows = []
    for spec in specs:
        rows.append(
            {
                "alert_id": spec[0],
                "created_at": spec[1],
                "severity": spec[2],
                "status": spec[3],
                "market_id": spec[4],
                "scenario_id": spec[5],
                "related_risk_id": spec[6],
                "related_incident_id": spec[7],
                "title": spec[8],
                "summary": spec[9],
            }
        )
    return rows


def build_issues(sources: dict, markets: list[dict]) -> list[dict]:
    customers_by_market: dict[str, list[dict]] = {m["market_id"]: [] for m in markets}
    for customer in sources["customers"]:
        city = customer["city"]
        must(city in CITY_TO_MARKET, f"unmapped customer city {city}")
        customers_by_market[CITY_TO_MARKET[city]].append(customer)
    for market_id, people in customers_by_market.items():
        must(people, f"no customers for {market_id}")
    jobs_by_customer: dict[str, list[str]] = {}
    for job in sources["jobs"]:
        jobs_by_customer.setdefault(job["customer_id"], []).append(job["job_id"])
    sites = index_by(sources["sites"], "site_id")
    devices = sources["devices"]
    firmware_devices = [row for row in devices if row["firmware_version"] == "4.3.0"]
    hwc = [
        row
        for row in devices
        if row["hardware_revision"] == "HW-C" and row["device_type"] == "Battery" and row["status"] == "Degraded"
    ]
    must(len(firmware_devices) >= 2, "expected devices still on 4.3.0")
    must(len(hwc) >= 3, "expected degraded HW-C batteries")
    other_devices = [row for row in devices if row not in firmware_devices and row not in hwc][:5]
    pinned_devices = firmware_devices[:2] + hwc[:3] + other_devices
    must(len(pinned_devices) == 10, "expected 10 device-linked issues")
    rows = []

    def add(opened: date, market_id: str, customer_id: str, site_id: str, job_id: str, device_id: str, category: str, severity: str, status: str, summary: str) -> None:
        rows.append(
            {
                "issue_id": f"ISS-{len(rows) + 1:03d}",
                "opened_date": opened,
                "market_id": market_id,
                "customer_id": customer_id,
                "site_id": site_id,
                "related_job_id": job_id,
                "related_device_id": device_id,
                "category": category,
                "severity": severity,
                "status": status,
                "summary": summary,
            }
        )

    for device in pinned_devices:
        site = sites[device["site_id"]]
        must(site["city"] in CITY_TO_MARKET, f"unmapped engineering city {site['city']}")
        market_id = CITY_TO_MARKET[site["city"]]
        customer = random.choice(customers_by_market[market_id])
        if device["firmware_version"] == "4.3.0":
            category = "Firmware"
            summary = (
                f"Engineering device {device['device_id']} at {device['site_id']} is still on firmware 4.3.0 "
                f"after INC-002. Field customer {customer['customer_id']} is a {NAME[market_id]} customer from "
                "customer_sites, which uses a different id list than engineering CUST ids."
            )
        elif device["hardware_revision"] == "HW-C" and device["device_type"] == "Battery" and device["status"] == "Degraded":
            category = "Hardware Reliability"
            summary = (
                f"Degraded HW-C battery {device['device_id']} at {device['site_id']} matches the hardware revision in INC-005. "
                f"Field customer {customer['customer_id']} is linked by market geography only."
            )
        else:
            category = "Hardware Reliability"
            summary = (
                f"Device {device['device_id']} ({device['device_type']} {device['hardware_revision']}) is an engineering id. "
                f"Field customer {customer['customer_id']} is not an engineering CUST id."
            )
        add(date(2026, 9, 18), market_id, customer["customer_id"], device["site_id"], "", device["device_id"], category, "High", "Open", summary)

    quotas = {
        "MKT-002": 22,
        "MKT-001": 12,
        "MKT-003": 8,
        "MKT-004": 8,
        "MKT-005": 8,
        "MKT-006": 6,
        "MKT-007": 6,
    }
    customers_by_id = index_by(sources["customers"], "customer_id")
    jobs = sources["jobs"]
    j007 = next(job for job in jobs if job["job_id"] == "J007")
    j001 = next(job for job in jobs if job["job_id"] == "J001")
    pinned_jobs = {
        CITY_TO_MARKET[customers_by_id[j007["customer_id"]]["city"]]: ("J007", "Parts Wait", "J007 is Waiting for Parts on an inverter repair. The customer is in Cedar Park, served by W002, where P006 still has available quantity. This wait is not the W001 P006 stockout."),
        CITY_TO_MARKET[customers_by_id[j001["customer_id"]]["city"]]: ("J001", "Parts Wait", "J001 is Waiting for Parts with an open Class T fuse symptom. The customer is in Round Rock, served by W002, where P018 is below reorder. W001 still has P018 available."),
    }
    for market_id, quota in quotas.items():
        people = customers_by_market[market_id]
        for index in range(quota):
            customer = people[index % len(people)]
            job_id = ""
            category = "Installation Delay"
            severity = "Medium"
            status = "Open" if market_id == "MKT-002" else "Closed"
            if index == 0 and market_id in pinned_jobs:
                job_id, category, summary = pinned_jobs[market_id]
                customer_id = j007["customer_id"] if job_id == "J007" else j001["customer_id"]
                summary = f"{summary} Customer {customer_id} is the job's customer in {NAME[market_id]}."
                opened = date(2026, 9, 20)
                severity = "High"
                status = "Open"
            else:
                customer_id = customer["customer_id"]
                if random.random() < 0.45 and jobs_by_customer.get(customer_id):
                    job_id = random.choice(jobs_by_customer[customer_id])
                if market_id == "MKT-002":
                    opened = SLOWDOWN_START + timedelta(days=(index * 3) % 34)
                    category = "Installation Delay" if index % 2 == 0 else "Installation Quality"
                    severity = "High" if index % 3 == 0 else "Medium"
                    summary = (
                        f"Synthetic installation complaint in North Austin for customer {customer_id}. "
                        "Completed installs are down, rework is up, and response time has lengthened."
                    )
                elif market_id == "MKT-006":
                    opened = date(2026, 7, 15) + timedelta(days=index)
                    category = "Launch"
                    severity = "Medium"
                    summary = "San Marcos launch issue: WMS location configuration at W003 is unfinished and install completions are not running."
                elif market_id == "MKT-004":
                    opened = date(2026, 8, 4) + timedelta(days=index * 2)
                    category = "Scheduling"
                    severity = "Low"
                    status = "Closed"
                    summary = f"Low-severity scheduling note for Cedar Park customer {customer_id}. Completion quality on the market remains strong."
                else:
                    opened = date(2026, 5, 4) + timedelta(days=index * 5)
                    if opened > SNAPSHOT:
                        opened = SNAPSHOT
                    category = "Communication"
                    severity = "Low"
                    summary = f"Synthetic service note for {NAME[market_id]} customer {customer_id}."
            add(opened, market_id, customer_id, "", job_id, "", category, severity, status, summary)
    must(len(rows) == 80, f"expected 80 issues, got {len(rows)}")
    return rows


def build_documents(highlights: dict) -> list[dict]:
    crafted = [
        ("Launch Plan", "San Marcos launch plan", "MKT-006", "RSK-04", "INIT-04", "", "COO", date(2026, 8, 18),
         "The San Marcos launch plan says WMS location configuration at W003 is unfinished. The launch roster is 5 technicians with 3 certified, about 60 percent, and that roster is not the same count as the Buda rows in technicians.csv. Inventory for the launch is incomplete, including a zero balance on P003 at W003. No first-wave installation completions are in the September deployment file."),
        ("Engineering Review", "Firmware 4.3.0 review", "", "RSK-03", "INIT-05", "INC-002", "VP Engineering", date(2026, 9, 16),
         f"Engineering review of the 2026-09-15 firmware 4.3.0 window. INC-002 affected {highlights['inc002_affected']} devices and is the heartbeat regression. Firmware-related incidents were {highlights['fw_spike']} in the week starting 2026-09-14 and {highlights['fw_decline']} the following week. devices.csv still shows {highlights['devices_on_430']} devices on 4.3.0."),
        ("Risk Review", "Open high and critical risks", "", "RSK-01", "", "", "CEO", date(2026, 9, 24),
         "Risk review of the open book. RSK-01 and RSK-02 are open Critical items on North Austin installations and P006 weeks of supply. Open High items include INC-002, the San Marcos launch, HW-C failure rate, Austin Metro utilization, and North Austin CSAT. Not every risk is Critical, and several items are mitigating, monitoring, or closed."),
        ("Market Review", "North Austin installation slowdown", "MKT-002", "RSK-01", "INIT-02", "", "VP Operations", date(2026, 9, 22),
         f"North Austin completed {highlights['m002_sep_completed']} installations in 2026-09 versus {highlights['m002_jul_completed']} in 2026-07. Rework rate moved from {highlights['m002_jul_rework']} to {highlights['m002_sep_rework']}. The same weeks show a two-person crew, open positions, and a P006 stockout at W001. Those facts co-occur; this memo does not decide which constraint was primary."),
        ("Operations Review", "W001 P006 replenishment", "MKT-001", "RSK-02", "INIT-03", "", "VP Operations", date(2026, 9, 18),
         "Operations review of P006 at W001. quantity_available is 0 and weeks_of_supply is 0.0 at a planning consumption of 4 per week. The open Waiting for Parts jobs J001 and J007 belong to W002 markets, so they are not the W001 balance. P018 low weeks of supply at W002 is a separate line."),
        ("Weekly Business Review", "Week of 2026-09-21 business review", "", "", "", "", "CEO", date(2026, 9, 25),
         f"Company installations were {highlights['wbr_latest_installs']} in the week of 2026-09-21 and {highlights['wbr_prior_installs']} in the week of 2026-09-14. CSAT, incidents, stockouts, and utilization also moved. The install increase is the absence of the 2026-09-16 short day in Cedar Park, not a recovery in North Austin."),
        ("Product Review", "HW-C reliability", "", "RSK-05", "INIT-06", "INC-005", "VP Engineering", date(2026, 9, 18),
         f"Product review of hardware revision HW-C. Battery HW-C failure_rate in 2026-09 is {highlights['hwc_rate']} on an installed base of {highlights['hwc_base']}, versus {highlights['hwb_rate']} for Battery HW-B. INC-005 and the degraded HW-C battery ids are the engineering link. Small bases make some HW-C rates noisy."),
        ("Executive Decision Memo", "Where to put the next crew week", "MKT-004", "RSK-01", "INIT-07", "", "CEO", date(2026, 9, 26),
         "Decision memo comparing Cedar Park operating metrics with North Austin and Austin Metro. Cedar Park shows high completions, high first-time completion, no stockout days, and overtime at zero. North Austin completions are down. Austin Metro scheduled demand is above certified capacity. The memo does not rank markets with a score column."),
        ("Operating Plan", "September operating plan gap", "", "RSK-06", "INIT-08", "", "COO", date(2026, 9, 2),
         "The September operating plan assumed Austin Metro could keep up with a higher scheduled book. Certified headcount stayed flat, utilization moved above 100, and completed installs hit the daily cap. San Marcos remains in the plan as a launch that has not started completions."),
        ("Strategy", "Central Texas footprint", "", "", "INIT-07", "", "CEO", date(2026, 4, 6),
         "Strategy note for the seven-market footprint. Austin Metro, North Austin, Round Rock, Cedar Park, Georgetown, San Marcos, and Pflugerville share three warehouses. The note is a planning frame. It is not a forecast of every metric rising."),
        ("Engineering Review", "INC-005 HW-C cell imbalance", "", "RSK-05", "INIT-06", "INC-005", "VP Engineering", date(2026, 9, 17),
         "INC-005 covers HW-C cell imbalance tied to busbar torque, with three affected devices in the engineering incident row. Degraded HW-C batteries in the device file are listed on the September Battery HW-C reliability row. Firmware 4.3.0 is a different incident, INC-002."),
        ("Market Review", "Georgetown after the July initiative", "MKT-005", "RSK-18", "INIT-01", "", "VP Operations", date(2026, 9, 10),
         f"Georgetown average cycle time was {highlights['geo_jun_cycle']} days in 2026-06 and {highlights['geo_sep_cycle']} days in 2026-09. First-time completion rose and rework fell. INIT-01 started 2026-07-06. Technician count did not change between those months."),
    ]
    must(len(crafted) == 12, "expected 12 crafted documents")
    rows = []
    for index, spec in enumerate(crafted, start=1):
        rows.append(
            {
                "document_id": f"DOC-{index:03d}",
                "document_type": spec[0],
                "title": spec[1],
                "document_date": spec[7],
                "author_role": spec[6],
                "market_id": spec[2],
                "related_risk_id": spec[3],
                "related_initiative_id": spec[4],
                "related_incident_id": spec[5],
                "summary": spec[8],
            }
        )
    closers = [
        "Use the metric tables for the figures rather than this summary.",
        "This note is synthetic planning context for the executive pack.",
        "Scenario ids in related files are pointers into the metric tables.",
        "A coincidence of two bad metrics is not a root-cause finding.",
    ]
    market_cycle = [m["market_id"] for m in MARKET_SPEC]
    for index in range(13, 51):
        doc_type = DOC_TYPES[(index - 1) % len(DOC_TYPES)]
        market_id = market_cycle[(index - 1) % len(market_cycle)]
        doc_date = date(2026, 4, 2) + timedelta(days=(index - 13) * 4)
        if doc_date > SNAPSHOT:
            doc_date = SNAPSHOT - timedelta(days=(index % 5))
        closer = random.choice(closers)
        summary = (
            f"{doc_type} {index:03d} dated {doc_date.isoformat()} is a synthetic Lumenfield note about "
            f"{NAME[market_id]} ({market_id}) and warehouse {WAREHOUSE_OF[market_id]}. "
            f"It records a discussion item for the executive pack and does not change the metric tables. {closer}"
        )
        rows.append(
            {
                "document_id": f"DOC-{index:03d}",
                "document_type": doc_type,
                "title": f"{doc_type}: {NAME[market_id]}",
                "document_date": doc_date,
                "author_role": ("CEO", "COO", "VP Operations", "VP Engineering", "VP Customer")[index % 5],
                "market_id": market_id,
                "related_risk_id": "",
                "related_initiative_id": "",
                "related_incident_id": "",
                "summary": summary,
            }
        )
    must(len(rows) == 50, "expected 50 documents")
    must(set(DOC_TYPES) <= {row["document_type"] for row in rows}, "missing a document type")
    return rows


def period_rows(rows: list[dict], market_id: str, period: str) -> dict:
    return next(row for row in rows if row["market_id"] == market_id and row["period"] == period)


def build_highlights(monthly, experience, workforce, inventory, engineering, reliability, wbr, sources) -> dict:
    m002_sep = period_rows(monthly, "MKT-002", "2026-09")
    m002_jul = period_rows(monthly, "MKT-002", "2026-07")
    m004_sep = period_rows(monthly, "MKT-004", "2026-09")
    m005_sep = period_rows(monthly, "MKT-005", "2026-09")
    m005_jun = period_rows(monthly, "MKT-005", "2026-06")
    p006 = next(row for row in inventory if row["part_id"] == "P006" and row["warehouse_id"] == "W001")
    p018 = next(row for row in inventory if row["part_id"] == "P018" and row["warehouse_id"] == "W002")
    latest_cx = next(row for row in experience if row["market_id"] == "MKT-002" and row["week_start"] == WBR_END)
    july_cx = next(row for row in experience if row["market_id"] == "MKT-002" and row["week_start"] == date(2026, 7, 6))
    austin_latest = next(row for row in workforce if row["market_id"] == "MKT-001" and row["week_start"] == WBR_END)
    austin_april = next(row for row in workforce if row["market_id"] == "MKT-001" and row["week_start"] == date(2026, 4, 6))
    spike = next(row for row in engineering if row["week_start"] == FW_WEEK)
    decline = next(row for row in engineering if row["week_start"] == FW_DECLINE_WEEK)
    hwc = next(row for row in reliability if row["period"] == "2026-09" and row["device_type"] == "Battery" and row["hardware_revision"] == "HW-C")
    hwb = next(row for row in reliability if row["period"] == "2026-09" and row["device_type"] == "Battery" and row["hardware_revision"] == "HW-B")
    inc002 = next(row for row in sources["incidents"] if row["incident_id"] == "INC-002")
    return {
        "m002_sep_completed": m002_sep["installations_completed"],
        "m002_jul_completed": m002_jul["installations_completed"],
        "m002_sep_rework": m002_sep["rework_rate"],
        "m002_jul_rework": m002_jul["rework_rate"],
        "m002_sep_waiting": m002_sep["jobs_waiting_for_parts"],
        "m002_sep_stockouts": m002_sep["stockout_events"],
        "m002_sep_cycle": m002_sep["average_cycle_time_days"],
        "m002_sep_delays": m002_sep["customer_delay_count"],
        "m004_sep_completed": m004_sep["installations_completed"],
        "m004_sep_ftc": m004_sep["first_time_completion_rate"],
        "geo_sep_cycle": m005_sep["average_cycle_time_days"],
        "geo_jun_cycle": m005_jun["average_cycle_time_days"],
        "geo_sep_ftc": m005_sep["first_time_completion_rate"],
        "geo_jun_ftc": m005_jun["first_time_completion_rate"],
        "p006_wos": p006["weeks_of_supply"],
        "p006_available": p006["current_available_quantity"],
        "p006_consumption": p006["weekly_consumption"],
        "p018_wos": p018["weeks_of_supply"],
        "p018_available": p018["current_available_quantity"],
        "m002_csat_latest": latest_cx["csat_score"],
        "m002_csat_july": july_cx["csat_score"],
        "m002_hours_latest": latest_cx["average_response_time_hours"],
        "m002_repeat_latest": latest_cx["repeat_contact_rate"],
        "m002_complaints_latest": latest_cx["installation_complaint_count"],
        "austin_util_latest": austin_latest["utilization_percentage"],
        "austin_sched_latest": austin_latest["scheduled_installations"],
        "austin_sched_april": austin_april["scheduled_installations"],
        "austin_ot_latest": austin_latest["overtime_hours"],
        "fw_spike": spike["firmware_related_incidents"],
        "fw_decline": decline["firmware_related_incidents"],
        "active_spike": spike["active_incidents"],
        "active_decline": decline["active_incidents"],
        "hwc_rate": hwc["failure_rate"],
        "hwb_rate": hwb["failure_rate"],
        "hwc_base": hwc["installed_base"],
        "hwc_failures": hwc["failure_count"],
        "hwc_devices": hwc["related_device_ids"],
        "inc002_affected": int(inc002["affected_device_count"]),
        "devices_on_430": decline["devices_on_firmware_430"],
        "wbr_latest_installs": wbr[-1]["installations_completed"],
        "wbr_prior_installs": wbr[-2]["installations_completed"],
        "wbr_latest_csat": wbr[-1]["average_csat"],
        "wbr_prior_csat": wbr[-2]["average_csat"],
        "wbr_latest_incidents": wbr[-1]["critical_incidents"],
        "wbr_prior_incidents": wbr[-2]["critical_incidents"],
        "wbr_latest_stockouts": wbr[-1]["stockout_events"],
        "wbr_prior_stockouts": wbr[-2]["stockout_events"],
        "wbr_latest_util": wbr[-1]["workforce_utilization_percentage"],
        "wbr_prior_util": wbr[-2]["workforce_utilization_percentage"],
        "wbr_latest_fw": wbr[-1]["firmware_related_incidents"],
        "wbr_prior_fw": wbr[-2]["firmware_related_incidents"],
        "company_sep_completed": None,
    }


def scenario_asserts(highlights: dict, monthly, markets, workforce, inventory, engineering) -> None:
    must(highlights["m002_sep_completed"] < highlights["m002_jul_completed"] * 0.5, "North Austin did not slow down")
    must(highlights["m002_sep_rework"] > 0.5 and highlights["m002_jul_rework"] < 0.25, "North Austin rework story failed")
    must(highlights["m002_sep_waiting"] >= 6 and highlights["m002_sep_stockouts"] >= 10, "North Austin parts story failed")
    cedar = period_rows(monthly, "MKT-004", "2026-09")
    must(cedar["first_time_completion_rate"] >= 0.9, "Cedar Park first-time completion is weak")
    must(cedar["stockout_events"] == 0 and cedar["jobs_waiting_for_parts"] == 0 and cedar["critical_incidents"] == 0, "Cedar Park is not quiet")
    must(cedar["installations_completed"] > highlights["m002_sep_completed"], "Cedar Park is not ahead of North Austin")
    cedar_ot = [row for row in workforce if row["market_id"] == "MKT-004" and row["week_start"].month == 9]
    must(all(row["overtime_hours"] == 0 for row in cedar_ot), "Cedar Park September overtime is not zero")
    san = next(row for row in markets if row["market_id"] == "MKT-006")
    must(san["status"] == "Launching", "San Marcos status")
    must(period_rows(monthly, "MKT-006", "2026-09")["installations_completed"] == 0, "San Marcos still installing in September")
    paused = period_rows(monthly, "MKT-007", "2026-09")
    must(paused["installations_completed"] == 0, "Pflugerville did not pause")
    must(highlights["p006_available"] == 0 and highlights["p006_wos"] == 0, "P006 shortage missing")
    must(highlights["fw_spike"] > highlights["fw_decline"] > 0, "firmware spike shape failed")
    must(highlights["active_spike"] > highlights["active_decline"] > 4, "active incident spike shape failed")
    must(highlights["m002_csat_latest"] <= highlights["m002_csat_july"] - 15, "CSAT did not decline")
    must(highlights["austin_sched_latest"] > highlights["austin_sched_april"], "Austin demand did not rise")
    must(highlights["austin_util_latest"] > 100 and highlights["austin_ot_latest"] > 0, "Austin utilization story failed")
    must(highlights["geo_sep_cycle"] < highlights["geo_jun_cycle"], "Georgetown cycle time did not fall")
    must(highlights["geo_sep_ftc"] > highlights["geo_jun_ftc"], "Georgetown first-time completion did not rise")
    must(highlights["hwc_rate"] > highlights["hwb_rate"], "HW-C rate is not higher")
    totals = []
    for market in markets:
        totals.append(sum(row["installations_completed"] for row in monthly if row["market_id"] == market["market_id"]))
    must(len(set(totals)) == len(totals), f"installation totals are not all different: {totals}")
    must(highlights["wbr_latest_installs"] != highlights["wbr_prior_installs"], "WBR installs did not change")
    must(highlights["wbr_latest_csat"] != highlights["wbr_prior_csat"], "WBR CSAT did not change")
    must(highlights["wbr_latest_incidents"] != highlights["wbr_prior_incidents"], "WBR incidents did not change")
    must(highlights["wbr_latest_stockouts"] != highlights["wbr_prior_stockouts"], "WBR stockouts did not change")
    must(highlights["wbr_latest_util"] != highlights["wbr_prior_util"], "WBR utilization did not change")
    levels = {row["stockout_risk"] for row in inventory}
    must("Critical" in levels and "Low" in levels, f"stockout risk levels missing Critical/Low: {levels}")
    aug = next(row for row in engineering if row["week_start"] == date(2026, 8, 3))
    must(highlights["fw_spike"] > aug["firmware_related_incidents"], "spike is not above a quiet August week")


def questions() -> dict[str, list[str]]:
    return {
        "COMPANY": [
            "What is company installations_completed for 2026-09, and which file is the source of truth behind it?",
            "Do 2026-09 company installations equal the sum of market_performance for MKT-001 through MKT-007?",
            "Which months from 2025-10 through 2026-09 missed the company installation target?",
            "How do company stockout_events in 2026-09 compare with 2026-07?",
            "How do company critical_incidents in 2026-09 compare with 2026-08?",
            "Why can a CEO not drill company_metrics before 2026-04 into a market?",
            "What is installation attainment for the latest company month?",
            "Did installations_completed rise in every month from 2025-10 through 2026-09?",
            "How should company_metrics.installations_completed be reconciled to deployment_metrics?",
            "What is the snapshot date of this executive pack, and which markets are in it?",
        ],
        "MARKETS": [
            "Why are installations down in North Austin (MKT-002)?",
            "Which market is Scaling, and do demand, first-time completion, incidents, certified techs, and inventory support more volume there?",
            "Why is San Marcos (MKT-006) still Launching?",
            "What is the status of Austin Metro (MKT-001), and which warehouse serves it?",
            "Which markets share W001 Mesa Volt Depot?",
            "Compare 2026-09 installations_completed for Cedar Park (MKT-004) and North Austin (MKT-002).",
            "What changed in Georgetown (MKT-005) cycle time and first-time completion after 2026-07-06?",
            "Why is Pflugerville (MKT-007) Paused, and what were its September installations?",
            "Do all seven markets have the same installation total?",
            "How does Round Rock (MKT-003) September volume compare with the North Austin slowdown?",
            "Which Active market, other than a launch or a pause, shows the installation slowdown?",
            "Map MKT-001 through MKT-007 to warehouse ids and statuses.",
        ],
        "CUSTOMERS": [
            "How did North Austin CSAT move from the week of 2026-07-06 to the week of 2026-09-21?",
            "Did response time, repeat contacts, and installation complaints rise in the same market where CSAT fell?",
            "Where did installation complaints concentrate in the latest week?",
            "How does Cedar Park CSAT in the latest week compare with North Austin?",
            "How many customer_issues are tagged to MKT-002, and what categories dominate?",
            "Which customer_issues reference J001 or J007, and what is each job's status in jobs.csv?",
            "customer_sites.csv has no site_id. When is customer_issues.site_id populated, and where must that id exist?",
            "What does the San Marcos funnel show for site surveys versus installations_completed?",
            "Are Cedar Park contracts being followed by completed installs?",
            "In North Austin, did contracts disappear, or did completed installs fall while scheduled work stayed up?",
        ],
        "OPERATIONS": [
            "For MKT-002 in 2026-09, show that market monthly installations equal the daily deployment sum.",
            "What happened to jobs_waiting_for_parts in North Austin between June and September 2026?",
            "How did rework_rate in MKT-002 change after 2026-08-24?",
            "What is first_time_completion_rate for Cedar Park in 2026-09?",
            "What is average cycle time in Georgetown for 2026-06 versus 2026-09?",
            "Which warehouse weekly rows show the W001 stockout pattern after 2026-08-24?",
            "How is installation_attainment_percentage calculated on the weekly business review?",
            "What happened on 2026-09-16 in Cedar Park, and how did that change the company week?",
            "What date range does deployment_metrics cover, and why is it longer than the latest 90 days?",
            "Drill from company 2026-09 installations to MKT-002, then to one September day in deployment_metrics.",
        ],
        "WORKFORCE": [
            "How many technicians.csv rows roll up to North Austin, and what is certified_technician_count?",
            "Where is scheduled installation demand rising faster than certified technician capacity?",
            "What is open_positions for Austin Metro versus Cedar Park?",
            "Is certified_technician_count ever greater than technician_count?",
            "Why is San Marcos certified coverage 3 of 5, and how many of those people are in technicians.csv?",
            "What do utilization and overtime look like for MKT-001 in the week of 2026-09-21?",
            "Did Georgetown's improvement come from hiring, or from INIT-01 with flat headcount?",
            "Which market is understaffed in the same window that installations fell?",
            "What does utilization_percentage above 100 mean in this pack?",
        ],
        "INVENTORY": [
            "What is weeks_of_supply for P006 at W001, and what is quantity_available in warehouse_inventory.csv?",
            "Which inventory_risk rows are Critical, and which are Low?",
            "How does P018 at W002 compare with P018 at W001?",
            "Which markets are exposed to the W001 P006 stockout?",
            "Show that weeks_of_supply equals available quantity divided by weekly consumption for P006.",
            "Which warehouses serve the customers on J001 and J007, and which short parts are actually in those warehouses?",
            "Is W003 inventory and WMS setup complete enough for the San Marcos launch?",
            "What is the reorder situation for P018, the 200A Class T Fuse?",
            "Does a Critical stockout_risk on P006 by itself prove that parts, rather than staffing, caused the North Austin miss?",
        ],
        "ENGINEERING": [
            "What happened to firmware_related_incidents and active_incidents in the week of 2026-09-15?",
            "Did those incident counts fully recover in the week of 2026-09-21?",
            "Which incident is the firmware 4.3.0 regression, and how many devices did it affect?",
            "Which devices are still on firmware 4.3.0 in devices.csv?",
            "Which hardware revision has the higher failure_rate, and what is failure_count divided by installed_base?",
            "Which incident describes the HW-C battery issue, and which degraded HW-C battery ids are in devices.csv?",
            "How is engineering_health_metrics related to company_metrics.critical_incidents?",
            "Compare Battery HW-C and Battery HW-B failure rates in 2026-09.",
            "Why is INC-022 not the 4.3.0 spike?",
        ],
        "RISK": [
            "Which open Critical risks have an affected_metric that can be checked in another table?",
            "Are all executive risks Critical?",
            "What is the status mix of executive_risks across open, mitigating, monitoring, and closed?",
            "Which risk says the San Marcos WMS configuration is unfinished?",
            "Which risk tracks HW-C failure_rate, and what observed value does it carry?",
            "Which risks are closed, and should they drive this week's review?",
            "What is the difference between stockout_risk on inventory_risk and a row in executive_risks?",
            "Which open High risks mention utilization, CSAT, or firmware?",
        ],
        "EXECUTIVE": [
            "What changed week over week in the 2026-09-21 business review versus 2026-09-14 for installs, CSAT, incidents, stockouts, and utilization?",
            "Which initiatives are active, and which one started on 2026-07-06?",
            "What should the CEO weigh before adding volume in Cedar Park while North Austin is missing plan?",
            "Which executive alerts are still Open, and which Open alerts are Critical?",
            "Which launch-plan document says the W003 WMS configuration is unfinished?",
            "What does this pack warn against concluding when North Austin staffing and P006 are both short?",
            "Which documents should be read before a review of INC-002?",
            "What are SCN-01 through SCN-12, and which ids would you open for a Monday staff meeting?",
            "Does the latest weekly business review install increase mean North Austin recovered?",
            "Walk the drill-down from company_metrics to market_performance to deployment_metrics to a job, a part, a technician city, and an engineering incident.",
        ],
    }


def render_questions() -> str:
    grouped = questions()
    lines = [
        "# Executive test questions",
        "",
        "Synthetic questions for the Lumenfield CEO pack. Snapshot 2026-09-27.",
        "Answer from `data/executive` and the field-ops and engineering CSVs. Do not treat a coincidence of two bad metrics as proof of a single cause.",
        "",
    ]
    total = 0
    for group, items in grouped.items():
        lines.append(f"## {group}")
        lines.append("")
        for item in items:
            total += 1
            lines.append(f"{total}. {item}")
        lines.append("")
    must(total >= 75, f"only {total} questions")
    return "\n".join(lines)


def render_readme() -> str:
    return """
# Lumenfield executive dataset

Synthetic operating pack for a CEO and the executive team of Lumenfield, a fictional Central Texas energy-storage company. It is shaped like a multi-market installer and service business. It is not Base Power, and it does not contain real financials, customers, employees, addresses, or credentials.

Snapshot date: 2026-09-27. Persona: CEO, COO, and functional VPs preparing a weekly business review.

## Purpose

Give an executive agent one consistent book of markets, installations, customers, workforce, inventory, engineering health, risks, and decisions. The figures are generated. The relationships are deliberate.

## Sources

This pack reuses ids from:

- `data/warehouses.csv` (W001, W002, W003)
- `data/technicians.csv` (city rollup into markets)
- `data/parts.csv` and `data/warehouse_inventory.csv` (part balances, including P006 at W001 and P018)
- `data/jobs.csv` and `data/customer_sites.csv` (field customer and job ids)
- `data/engineering/devices.csv`, `engineering_sites.csv`, `engineering_incidents.csv`, `firmware_versions.csv`

Field customer ids (`C001`) and engineering customer ids (`CUST-001`) are different lists. `customer_sites.csv` has no `site_id`. When `customer_issues.site_id` is filled, it is an engineering site id.

## Relationships

- `markets.warehouse_id` points at `warehouses.csv`. Several markets share one warehouse.
- `deployment_metrics` is the daily source of truth for installations, targets, critical incidents, and stockout events from 2026-04-01 through 2026-09-27.
- `market_performance` for a market-month is the sum of those days (month-end snapshot for jobs waiting; completion-weighted cycle time).
- `company_metrics` for 2026-04 through 2026-09 sums the seven markets. Months from 2025-10 through 2026-03 have no market drill-down.
- `customer_funnel` and `workforce_metrics` installation and schedule counts for a week match the daily file.
- `warehouse_metrics.stockout_events` for a week is the sum of daily stockout flags for the markets on that warehouse.
- `inventory_risk.current_available_quantity` is `warehouse_inventory.quantity_available` for that part and warehouse on the snapshot. `weeks_of_supply` divides that balance by a planning consumption rate.
- `engineering_health_metrics` for the week of 2026-09-15 is tied to INC-002 (firmware 4.3.0).
- `reliability_metrics.failure_rate` is `failure_count / installed_base`. Battery HW-C points at INC-005.
- Risks, alerts, initiatives, and documents point at scenario ids SCN-01 through SCN-12. They are labels, not a market ranking.

## Assumptions

- A week starts on Monday. The week of 2026-09-15 is the week starting 2026-09-14.
- Daily history runs from 2026-04-01 so April through September monthly totals equal the daily file. The latest 90 days are inside that range.
- Technician cities map once: Austin and Lakeway to Austin Metro; Manor to North Austin; Round Rock and Hutto to Round Rock; Cedar Park and Leander to Cedar Park; Georgetown to Georgetown; Buda to San Marcos; Pflugerville to Pflugerville.
- For every market except San Marcos, `technician_count` matches that city rollup. A technician with a non-empty certifications field counts as certified.
- San Marcos `technician_count` 5 and `certified_technician_count` 3 are the launch roster (60 percent). `field_extract_technician_count` is the Buda subset actually present in `technicians.csv`. Do not add those two counts together.
- Utilization uses scheduled installations divided by certified technicians times 8 installs per week. Above 100 means the book is larger than that capacity. San Marcos utilization is a training load, not install throughput.
- `installed_base` on reliability rows is the 2026-09-27 device census repeated for each month.
- `lines_below_reorder` on warehouse rows is the snapshot count, repeated each week. The time pattern is `stockout_events`.
- No revenue, margin, or headcount-cost dollars are included.

## How to regenerate

```bash
/Users/rajat/Downloads/hackathon/base/knowledge-proj/.venv/bin/python scripts/generate_executive_data.py
```

The script uses only the Python standard library (`csv`, `random`, `datetime`, `pathlib`) and `random.seed(27)`. It exits with an error if validation fails.

## Synthetic disclaimer

All names, customers, balances, and metrics are fictional. Warehouse and technician ids are carried forward from the other synthetic datasets in this repo so the executive pack can join to them. Do not describe these figures as real operating results.
""".strip()


def render_dictionary() -> str:
    sections = [
        ("markets.csv", [
            ("market_id", "Market key MKT-001 through MKT-007."),
            ("market_name", "Austin Metro, North Austin, Round Rock, Cedar Park, Georgetown, San Marcos, or Pflugerville."),
            ("company_name", "Always Lumenfield, the fictional company."),
            ("region", "Always Central Texas."),
            ("status", "Planning, Launching, Active, Scaling, or Paused."),
            ("warehouse_id", "Serving warehouse. Must exist in data/warehouses.csv."),
            ("primary_cities", "Technician and customer cities rolled into this market."),
            ("technician_count", "Roster used for capacity. Matches technicians.csv except the San Marcos launch roster."),
            ("certified_technician_count", "Certified roster. Must be less than or equal to technician_count."),
            ("field_extract_technician_count", "Count of technicians.csv rows in primary_cities."),
            ("field_extract_certified_count", "Those rows whose certifications field is non-empty."),
            ("open_positions", "Unfilled requisitions. Not included in technician_count."),
            ("status_date", "Date the current status took effect."),
            ("service_note", "Short operating note. Not a rank."),
        ]),
        ("market_performance.csv", [
            ("period", "Month YYYY-MM from 2026-04 through 2026-09."),
            ("market_id", "Market key."),
            ("installations_scheduled", "Sum of daily scheduled installs."),
            ("installations_completed", "Sum of daily completed installs. Source of truth for the month."),
            ("installations_target", "Sum of daily targets."),
            ("installation_attainment_percentage", "100 times completed divided by target. Blank when target is 0."),
            ("first_time_completion_count", "Sum of daily first-time completions."),
            ("first_time_completion_rate", "first_time_completion_count divided by installations_completed."),
            ("rework_count", "Sum of daily rework. With first-time completions, equals installations_completed."),
            ("rework_rate", "rework_count divided by installations_completed."),
            ("average_cycle_time_days", "Completion-weighted average of daily cycle time."),
            ("jobs_waiting_for_parts", "Snapshot on the last day of the month in the daily file, not a sum."),
            ("customer_delay_count", "Sum of daily customer delays."),
            ("critical_incidents", "Sum of daily critical incident flags."),
            ("stockout_events", "Sum of daily stockout flags. A flag is a market-day, so two markets can both count the same warehouse day."),
        ]),
        ("deployment_metrics.csv", [
            ("deployment_date", "Calendar day from 2026-04-01 through 2026-09-27."),
            ("market_id", "Market key."),
            ("installations_scheduled", "Installations booked that day."),
            ("installations_completed", "Installations finished that day."),
            ("installations_target", "Operating-plan target that day."),
            ("first_time_completion_count", "Completions that did not need rework."),
            ("rework_count", "Completions that were rework. Adds with first-time completions to installations_completed."),
            ("average_cycle_time_days", "Cycle time for completions that day. Blank when completed is 0."),
            ("jobs_waiting_for_parts", "End-of-day queue snapshot."),
            ("customer_delay_count", "Customers delayed that day."),
            ("critical_incidents", "Critical incident flags that day."),
            ("stockout_events", "1 when that market-day was hit by a stockout, else 0."),
        ]),
        ("customer_funnel.csv", [
            ("week_start", "Monday of the week."),
            ("market_id", "Market key."),
            ("leads", "New leads."),
            ("qualified_leads", "Leads that qualified. Less than or equal to leads."),
            ("site_surveys", "Surveys. Less than or equal to qualified leads."),
            ("proposals", "Proposals. Less than or equal to surveys."),
            ("contracts", "Contracts. Less than or equal to proposals."),
            ("installations_scheduled", "Sum of daily scheduled installs that week."),
            ("installations_completed", "Sum of daily completed installs that week."),
        ]),
        ("customer_experience_metrics.csv", [
            ("week_start", "Monday of the week."),
            ("market_id", "Market key."),
            ("csat_score", "Customer satisfaction on a 0-100 scale."),
            ("nps", "Synthetic net promoter score derived from CSAT, from -100 to 100."),
            ("average_response_time_hours", "Average first-response time in hours."),
            ("repeat_contact_rate", "Share of contacts that were repeats, from 0 to 1."),
            ("installation_complaint_count", "Installation complaints opened that week."),
            ("survey_responses", "Survey responses that week."),
        ]),
        ("customer_issues.csv", [
            ("issue_id", "ISS-001 through ISS-080."),
            ("opened_date", "Date the issue was opened."),
            ("market_id", "Market key."),
            ("customer_id", "Field customer id from customer_sites.csv. Blank only if unset."),
            ("site_id", "Engineering site id when the issue references a device. Blank for field-only issues. customer_sites.csv has no site id."),
            ("related_job_id", "jobs.csv job id, or blank."),
            ("related_device_id", "devices.csv device id, or blank."),
            ("category", "Installation Delay, Installation Quality, Parts Wait, Firmware, Hardware Reliability, Scheduling, Communication, or Launch."),
            ("severity", "Critical, High, Medium, or Low."),
            ("status", "Open or Closed."),
            ("summary", "Two or three synthetic sentences."),
        ]),
        ("workforce_metrics.csv", [
            ("week_start", "Monday of the week."),
            ("market_id", "Market key."),
            ("technician_count", "Roster that week. Flat in this pack."),
            ("certified_technician_count", "Certified roster. Less than or equal to technician_count."),
            ("open_positions", "Unfilled requisitions."),
            ("scheduled_installations", "Sum of daily scheduled installs that week."),
            ("installations_completed", "Sum of daily completed installs that week."),
            ("utilization_percentage", "100 times scheduled divided by certified times 8, except San Marcos, which uses a training load of 40."),
            ("overtime_hours", "Two hours for each scheduled install above certified weekly capacity. Zero when the book fits."),
        ]),
        ("warehouse_metrics.csv", [
            ("week_start", "Monday of the week."),
            ("warehouse_id", "W001, W002, or W003."),
            ("stockout_events", "Sum of daily stockout flags for markets served by this warehouse."),
            ("jobs_waiting_for_parts", "Sum of market waiting snapshots on the last day of the week that exists in the daily file."),
            ("fill_rate_percentage", "Modeled fill rate. W001 steps down after 2026-08-24."),
            ("inventory_accuracy_percentage", "Modeled cycle-count accuracy."),
            ("cycle_counts_completed", "Cycle counts finished that week."),
            ("lines_below_reorder", "Snapshot count of warehouse_inventory lines under reorder. Repeated every week."),
            ("wms_core_status", "Operational for all three warehouses."),
            ("launch_location_configured", "yes, except W003, where San Marcos launch locations are not configured."),
            ("notes", "Short warehouse note for the week."),
        ]),
        ("inventory_risk.csv", [
            ("risk_id", "IR-001 through IR-020."),
            ("as_of_date", "2026-09-27."),
            ("part_id", "Part id from parts.csv."),
            ("warehouse_id", "Warehouse id."),
            ("part_name", "Name from parts.csv."),
            ("part_criticality", "Criticality from parts.csv."),
            ("current_available_quantity", "quantity_available from warehouse_inventory.csv for this part and warehouse."),
            ("weekly_consumption", "Planning consumption per week. Not a purchase-order quantity."),
            ("weeks_of_supply", "current_available_quantity divided by weekly_consumption, rounded to 1 decimal."),
            ("stockout_risk", "Critical, High, Medium, or Low."),
            ("jobs_blocked", "Count of linked waiting jobs called out in the note."),
            ("affected_market_ids", "Markets whose warehouse_id matches this row."),
            ("note", "Why the line is on the register."),
        ]),
        ("engineering_health_metrics.csv", [
            ("week_start", "Monday of the week."),
            ("firmware_related_incidents", "Firmware-related incidents opened or active in the executive rollup that week."),
            ("active_incidents", "Week-end open engineering incidents in this rollup."),
            ("new_incidents", "Incidents opened that week."),
            ("resolved_incidents", "Incidents resolved that week. active moves by new minus resolved."),
            ("devices_on_firmware_430", "Devices treated as on 4.3.0 that week. Latest week matches the devices.csv census."),
            ("rollout_affected_device_count", "INC-002 affected_device_count on the spike week; census count on the decline week."),
            ("primary_incident_id", "INC-002, INC-022, or blank."),
            ("notes", "Tie to the engineering incident file."),
        ]),
        ("reliability_metrics.csv", [
            ("period", "Month YYYY-MM."),
            ("device_type", "Device type present in devices.csv."),
            ("hardware_revision", "Hardware revision present for that device type."),
            ("installed_base", "Device census count for that type and revision."),
            ("failure_count", "Failures in the month. failure_rate times installed_base."),
            ("failure_rate", "failure_count divided by installed_base."),
            ("related_incident_id", "INC-005 on Battery HW-C rows, else blank."),
            ("related_device_ids", "Degraded HW-C battery ids on Battery HW-C rows."),
            ("notes", "Limitation of the census and of the HW-C mechanism."),
        ]),
        ("company_metrics.csv", [
            ("period", "Month from 2025-10 through 2026-09."),
            ("installations_scheduled", "Sum of markets from 2026-04. Earlier months are company-only history."),
            ("installations_completed", "Sum of markets from 2026-04."),
            ("installations_target", "Sum of market targets from 2026-04."),
            ("installation_attainment_percentage", "100 times completed divided by target."),
            ("first_time_completion_rate", "Company first-time completions divided by completed installs, from 2026-04."),
            ("critical_incidents", "Sum of market critical incidents from 2026-04."),
            ("stockout_events", "Sum of market stockout events from 2026-04."),
            ("average_csat", "Unweighted mean of market-week CSAT scores whose week_start falls in the month."),
            ("workforce_utilization_percentage", "Unweighted mean of market-week utilization whose week_start falls in the month."),
            ("open_critical_risks", "2026-09 matches open Critical rows in executive_risks. Earlier months are a synthetic history of the count."),
            ("drilldown_available", "yes from 2026-04, no before that."),
            ("notes", "How the month relates to market_performance."),
        ]),
        ("executive_risks.csv", [
            ("risk_id", "RSK-01 through RSK-20."),
            ("opened_date", "Date opened."),
            ("severity", "Critical, High, Medium, or Low."),
            ("status", "open, mitigating, monitoring, or closed."),
            ("market_id", "Market key or blank."),
            ("warehouse_id", "Warehouse id or blank."),
            ("part_id", "Part id or blank."),
            ("related_incident_id", "Engineering incident id or blank."),
            ("related_initiative_id", "Initiative id or blank."),
            ("scenario_id", "SCN id or blank."),
            ("affected_metric", "Metric name that exists in another table."),
            ("observed_value", "Value of that metric taken from the generated tables."),
            ("title", "Short title."),
            ("summary", "What the risk claims, in a sentence or two."),
        ]),
        ("executive_initiatives.csv", [
            ("initiative_id", "INIT-01 through INIT-08."),
            ("initiative_name", "Name of the initiative."),
            ("status", "Active or On Hold."),
            ("start_date", "Start date. Georgetown's initiative starts 2026-07-06."),
            ("target_end_date", "Target end date."),
            ("owner_role", "Role only. No employee name."),
            ("market_id", "Market key or blank."),
            ("related_risk_id", "Risk id or blank."),
            ("related_incident_id", "Incident id or blank."),
            ("scenario_id", "SCN id."),
            ("expected_effect", "What the initiative is supposed to change."),
            ("status_note", "Whether the metric tables already show the effect."),
        ]),
        ("weekly_business_review.csv", [
            ("week_start", "Monday. Sixteen weeks ending 2026-09-21."),
            ("installations_completed", "Company sum of daily completions that week."),
            ("installations_target", "Company sum of daily targets that week."),
            ("installation_attainment_percentage", "100 times completed divided by target."),
            ("average_csat", "Unweighted mean of the seven market CSAT scores that week."),
            ("critical_incidents", "Sum of daily critical flags that week."),
            ("stockout_events", "Sum of daily stockout flags that week."),
            ("workforce_utilization_percentage", "Unweighted mean of the seven market utilization figures."),
            ("firmware_related_incidents", "From engineering_health_metrics for the same week."),
            ("major_risks", "Short text pointing at scenario ids."),
            ("executive_attention_items", "Short text pointing at scenario ids."),
        ]),
        ("executive_alerts.csv", [
            ("alert_id", "ALT-001 through ALT-015."),
            ("created_at", "Date raised."),
            ("severity", "Critical, High, Medium, or Low."),
            ("status", "Open, Acknowledged, or Resolved."),
            ("market_id", "Market key or blank."),
            ("scenario_id", "SCN id or blank."),
            ("related_risk_id", "Risk id or blank."),
            ("related_incident_id", "Incident id or blank."),
            ("title", "Short title."),
            ("summary", "What the alert says."),
        ]),
        ("executive_documents.csv", [
            ("document_id", "DOC-001 through DOC-050."),
            ("document_type", "Strategy, Operating Plan, Market Review, Weekly Business Review, Product Review, Engineering Review, Operations Review, Risk Review, Launch Plan, or Executive Decision Memo."),
            ("title", "Document title."),
            ("document_date", "Document date."),
            ("author_role", "Role only. No employee name."),
            ("market_id", "Market key or blank."),
            ("related_risk_id", "Risk id or blank."),
            ("related_initiative_id", "Initiative id or blank."),
            ("related_incident_id", "Incident id or blank."),
            ("summary", "A few synthetic sentences."),
        ]),
    ]
    lines = ["# Data dictionary", "", "Column definitions for `data/executive`. All figures are synthetic.", ""]
    for filename, fields in sections:
        lines.append(f"## {filename}")
        lines.append("")
        for name, desc in fields:
            lines.append(f"- `{name}`: {desc}")
        lines.append("")
    return "\n".join(lines)


def render_metrics(highlights: dict, company: list[dict]) -> str:
    company_sep = next(row for row in company if row["period"] == "2026-09")
    causation = (
        "A coincidence of staffing and inventory shortages does not prove which constraint was primary. "
        "In North Austin (MKT-002), certified headcount is tight and P006 at W001 is out of stock in the same weeks. "
        "The tables show that those conditions occurred together. They do not identify which one caused the installation decline."
    )
    metrics = [
        ("installations_completed", "Installations finished.", "Sum of deployment_metrics.installations_completed.", "deployment_metrics.csv, rolled to market_performance.csv and company_metrics.csv", "Day, month, and company month.", f"MKT-002 completed {highlights['m002_sep_completed']} installations in 2026-09. Company installations_completed for 2026-09 is {company_sep['installations_completed']}, the sum of the seven markets.", "Market-days are the source of truth only from 2026-04-01. Earlier company months have no market split. " + causation),
        ("installations_scheduled", "Installations booked.", "Sum of daily installations_scheduled.", "deployment_metrics.csv", "Day and week.", f"Austin Metro scheduled {highlights['austin_sched_latest']} installations in the week of 2026-09-21, up from {highlights['austin_sched_april']} in the week of 2026-04-06.", "Scheduled work is demand. It is not completions, and it is not proof that a crew or a part was available."),
        ("installations_target", "Operating-plan completions.", "Sum of daily installations_target.", "deployment_metrics.csv", "Day, week, and month.", f"Company target for 2026-09 is {company_sep['installations_target']}.", "The San Marcos target stays on the books after completions stop. A target is a plan, not a forecast that was achieved."),
        ("installation_attainment_percentage", "Plan attainment.", "100 * installations_completed / installations_target.", "weekly_business_review.csv and market_performance.csv", "Week or month.", f"The week of 2026-09-21 completed {highlights['wbr_latest_installs']} against its target. Attainment is blank when the target is 0.", "Attainment can rise because the prior week had a one-day shortfall. Check the market split before calling it a recovery."),
        ("first_time_completion_rate", "Share of completions that were clean the first time.", "first_time_completion_count / installations_completed.", "market_performance.csv", "Month.", f"Cedar Park 2026-09 first_time_completion_rate is {highlights['m004_sep_ftc']}. Georgetown moved from {highlights['geo_jun_ftc']} in 2026-06 to {highlights['geo_sep_ftc']} in 2026-09.", "Blank when completions are 0, as in San Marcos in September. A high rate on a tiny base is not the same as a high rate on a full book."),
        ("rework_rate", "Share of completions that were rework.", "rework_count / installations_completed.", "market_performance.csv", "Month.", f"North Austin rework_rate was {highlights['m002_jul_rework']} in 2026-07 and {highlights['m002_sep_rework']} in 2026-09.", "First-time and rework counts add to completions, so the two rates add to 1 when both are present. Rework rising with a stockout still does not name the cause."),
        ("average_cycle_time_days", "Completion-weighted cycle time.", "Sum of daily cycle time times completions, divided by completions.", "market_performance.csv", "Month.", f"Georgetown cycle time was {highlights['geo_jun_cycle']} days in 2026-06 and {highlights['geo_sep_cycle']} days in 2026-09. North Austin September cycle time is {highlights['m002_sep_cycle']} days.", "Days with zero completions are left out of the weight. The average does not say why the cycle moved."),
        ("jobs_waiting_for_parts", "Queue snapshot.", "Last daily snapshot in the period, not a sum.", "deployment_metrics.csv and market_performance.csv", "Day or month-end.", f"North Austin jobs_waiting_for_parts at September month-end is {highlights['m002_sep_waiting']}.", causation),
        ("customer_delay_count", "Customers delayed.", "Sum of daily customer_delay_count.", "deployment_metrics.csv", "Day and month.", f"North Austin customer_delay_count for 2026-09 is {highlights['m002_sep_delays']}.", "A delay count does not say whether the customer was waiting on a crew, a part, or a schedule change."),
        ("critical_incidents", "Field critical-incident flags.", "Sum of daily critical_incidents.", "deployment_metrics.csv, summed to market and company.", "Day and month.", f"Company critical_incidents for 2026-09 is {company_sep['critical_incidents']}.", "This is not the engineering incident register. Firmware volume lives in engineering_health_metrics."),
        ("stockout_events", "Market-days flagged for a stockout.", "Sum of daily stockout_events.", "deployment_metrics.csv", "Day, week, and month.", f"North Austin stockout_events in 2026-09 are {highlights['m002_sep_stockouts']}. The week of 2026-09-14 company stockout_events were {highlights['wbr_prior_stockouts']}, then {highlights['wbr_latest_stockouts']} the next week.", "Two markets on the same warehouse can each flag the same calendar day. Summing markets is not a count of unique parts."),
        ("csat_score", "Customer satisfaction.", "0-100 score on the weekly experience row.", "customer_experience_metrics.csv", "Week.", f"North Austin CSAT was {highlights['m002_csat_july']} in the week of 2026-07-06 and {highlights['m002_csat_latest']} in the week of 2026-09-21.", "Company average CSAT is an unweighted mean of market-weeks. It is not weighted by survey responses."),
        ("nps", "Net promoter score.", "Clipped (csat_score - 75) * 2.", "customer_experience_metrics.csv", "Week.", f"North Austin's latest CSAT of {highlights['m002_csat_latest']} produces a negative NPS.", "NPS here is derived from CSAT. It is not a separate survey."),
        ("average_response_time_hours", "First response time.", "Weekly average hours.", "customer_experience_metrics.csv", "Week.", f"North Austin response time in the latest week is {highlights['m002_hours_latest']} hours.", "Response time moving with CSAT shows co-movement, not the cause of the installation miss."),
        ("repeat_contact_rate", "Repeat contact share.", "Repeats divided by contacts, stored from 0 to 1.", "customer_experience_metrics.csv", "Week.", f"North Austin repeat_contact_rate in the latest week is {highlights['m002_repeat_latest']}.", "The rate is not a ticket-system extract."),
        ("installation_complaint_count", "Installation complaints.", "Count of complaints that week.", "customer_experience_metrics.csv", "Week.", f"North Austin installation complaints in the latest week are {highlights['m002_complaints_latest']}.", "Complaint counts are not the same object as customer_issues rows, though both concentrate on North Austin."),
        ("technician_count", "Roster headcount.", "City rollup from technicians.csv, except the San Marcos launch roster of 5.", "workforce_metrics.csv", "Week.", "North Austin technician_count is the Manor rollup. San Marcos technician_count is 5 while field_extract_technician_count is the Buda subset.", "Do not add the San Marcos roster to the field extract."),
        ("certified_technician_count", "Certified headcount.", "Non-empty certifications in the extract, except San Marcos where the launch roster certified count is 3.", "workforce_metrics.csv", "Week.", "San Marcos certified_technician_count 3 divided by technician_count 5 is 0.6.", "Certification here is not a specific license level except where the service note says otherwise."),
        ("open_positions", "Unfilled roles.", "Constant requisition count by market.", "workforce_metrics.csv", "Week.", "Austin Metro open_positions is 3. North Austin open_positions is 4.", "Open positions are not included in technician_count."),
        ("utilization_percentage", "Booked load versus certified capacity.", "100 * scheduled_installations / (certified_technician_count * 8). San Marcos is fixed at 40.", "workforce_metrics.csv", "Week.", f"Austin Metro utilization in the week of 2026-09-21 is {highlights['austin_util_latest']}.", "Above 100 means scheduled work exceeds the capacity rule. It does not, by itself, prove overtime was worked or that parts were available. " + causation),
        ("overtime_hours", "Hours above the capacity rule.", "2 * max(0, scheduled_installations - certified_technician_count * 8).", "workforce_metrics.csv", "Week.", f"Austin Metro overtime in the week of 2026-09-21 is {highlights['austin_ot_latest']} hours. Cedar Park September overtime is 0.", "The formula is a planning conversion, not a payroll extract."),
        ("weeks_of_supply", "Coverage of the on-hand available balance.", "current_available_quantity / weekly_consumption, rounded to 1 decimal.", "inventory_risk.csv", "Snapshot 2026-09-27.", f"P006 at W001 has available {highlights['p006_available']}, weekly consumption {highlights['p006_consumption']}, and weeks_of_supply {highlights['p006_wos']}.", "Consumption is a planning rate. A value of 0.0 means the available balance is 0, not that demand was measured that week. " + causation),
        ("stockout_risk", "Register severity for a part-warehouse line.", "Set from the balance versus consumption, with P006 at W001 forced to Critical.", "inventory_risk.csv", "Snapshot.", "P006 at W001 is Critical. At least one other line is Low.", "stockout_risk is not the same column as executive_risks.severity."),
        ("current_available_quantity", "Available on-hand balance.", "warehouse_inventory.quantity_available for the part and warehouse.", "inventory_risk.csv", "Snapshot 2026-09-27.", f"P006 at W001 current_available_quantity is {highlights['p006_available']}. P018 at W002 is {highlights['p018_available']}.", "Van inventory is not included. A warehouse can show stock while a job still waits on a van."),
        ("firmware_related_incidents", "Firmware-related incident count in the executive rollup.", "Set so the week of 2026-09-15 spikes and the next week declines part way, using INC-002's affected device count.", "engineering_health_metrics.csv", "Week.", f"Week starting 2026-09-14 has {highlights['fw_spike']} firmware_related_incidents. Week starting 2026-09-21 has {highlights['fw_decline']}. INC-002 affected_device_count is {highlights['inc002_affected']}.", "This rollup is not a raw count of every engineering_incidents.csv row. INC-022 is a different firmware note on 4.3.1."),
        ("active_incidents", "Week-end open incidents in the executive engineering rollup.", "Prior active + new_incidents - resolved_incidents.", "engineering_health_metrics.csv", "Week.", f"Active incidents were {highlights['active_spike']} in the spike week and {highlights['active_decline']} the next week.", "A partial decline is not a close. INC-002 remains the primary incident."),
        ("failure_rate", "Share of the installed base that failed in the month.", "failure_count / installed_base.", "reliability_metrics.csv", "Month, by device type and hardware revision.", f"Battery HW-C in 2026-09 failed {highlights['hwc_failures']} times on a base of {highlights['hwc_base']}, rate {highlights['hwc_rate']}. Battery HW-B rate is {highlights['hwb_rate']}.", "installed_base is the 2026-09-27 census for every month. Small bases make rates jump. INC-005 supports a battery mechanism, not every HW-C device type."),
        ("failure_count", "Failures in the month.", "Numerator of failure_rate.", "reliability_metrics.csv", "Month.", f"Battery HW-C failure_count in 2026-09 is {highlights['hwc_failures']}.", "Counts are synthetic monthly totals consistent with the rate. They are not a dump of device_faults.csv."),
        ("installed_base", "Devices of that type and revision.", "Count of devices.csv rows.", "reliability_metrics.csv", "Census repeated each month.", f"Battery HW-C installed_base is {highlights['hwc_base']}.", "The census does not reconstruct how many units were installed in April versus September."),
        ("leads", "Top of the weekly funnel.", "Generated weekly stage above qualified leads.", "customer_funnel.csv", "Week.", "San Marcos keeps leads and surveys while installations_completed stays at 0 in September.", "Funnel stages are not the same object as customer_issues."),
    ]
    lines = [
        "# Metric definitions",
        "",
        "Each definition is how this pack computed the figure. Examples use the generated files.",
        "",
        causation,
        "",
    ]
    for name, definition, formula, source, period, example, limitation in metrics:
        lines.extend(
            [
                f"## {name}",
                "",
                f"- Name: `{name}`",
                f"- Definition: {definition}",
                f"- Formula: {formula}",
                f"- Source file: {source}",
                f"- Time period: {period}",
                f"- Example: {example}",
                f"- Limitation: {limitation}",
                "",
            ]
        )
    return "\n".join(lines)


def render_scenarios(highlights: dict, markets: list[dict]) -> str:
    by_id = {row["market_id"]: row for row in markets}
    blocks = [
        ("SCN-01", "Installation slowdown", "Why are installations down?",
         f"Market North Austin ({by_id['MKT-002']['market_name']} is MKT-002), warehouse W001, part P006.",
         f"2026-09 installations_completed for MKT-002 are {highlights['m002_sep_completed']}, versus {highlights['m002_jul_completed']} in 2026-07. The break starts 2026-08-24. Rework rate is {highlights['m002_sep_rework']} in September versus {highlights['m002_jul_rework']} in July. Cycle time is {highlights['m002_sep_cycle']} days. Jobs waiting are {highlights['m002_sep_waiting']}. The field extract for Manor is the North Austin roster, and open_positions is 4. P006 at W001 has weeks_of_supply {highlights['p006_wos']}.",
         "Staffing and inventory are both bad in this window. That co-occurrence does not prove which constraint was primary."),
        ("SCN-02", "Market ready to scale", "Which market can take more volume?",
         "Cedar Park is MKT-004, warehouse W002. There is no best-market column.",
         f"September installations_completed are {highlights['m004_sep_completed']} with first_time_completion_rate {highlights['m004_sep_ftc']}. Stockout events and jobs waiting are 0. Critical incidents are 0. September overtime hours are 0. Certified headcount equals the Cedar Park and Leander extract. W002 is not the P006 stockout warehouse.",
         "High volume alone is not the signal. Austin Metro has high volume and is over capacity."),
        ("SCN-03", "Launch blocked", "Why has San Marcos not launched?",
         "San Marcos is MKT-006, status Launching, warehouse W003.",
         "Certified technicians are 3 of 5 on the launch roster (60 percent). field_extract_technician_count is only the Buda rows in technicians.csv. September installations_completed are 0. warehouse_metrics.launch_location_configured is no for W003. DOC-001 and RSK-04 say the WMS configuration is unfinished. P003 at W003 is on the inventory register with available 0.",
         "Georgetown also uses W003 and is installing. The WMS gap is the San Marcos launch locations, not a dead warehouse."),
        ("SCN-04", "Inventory-driven delays", "Which part is short, and who is waiting?",
         "Part P006 at W001 is the Critical line. Part P018 at W002 is a separate High line. J001 (Round Rock, W002) is the Class T fuse wait and lines up with low P018 at W002. J007 (Cedar Park, W002) is an inverter repair waiting on parts; W002 still has P006 available, so J007 does not explain the W001 stockout.",
         f"P006 available is {highlights['p006_available']}, weekly consumption is {highlights['p006_consumption']}, weeks_of_supply is {highlights['p006_wos']}. North Austin stockout_events in September are {highlights['m002_sep_stockouts']} and customer_delay_count is {highlights['m002_sep_delays']}. P018 at W002 has weeks_of_supply {highlights['p018_wos']} and available {highlights['p018_available']}.",
         "A part at zero weeks of supply is a fact about the balance. It is not, by itself, the proven cause of every missed install."),
        ("SCN-05", "Firmware spike after 4.3.0", "What happened the week of 2026-09-15?",
         "Incident INC-002. Firmware 4.3.0. Week starting 2026-09-14, then the week starting 2026-09-21.",
         f"INC-002 affected_device_count is {highlights['inc002_affected']}. firmware_related_incidents went to {highlights['fw_spike']} and active_incidents to {highlights['active_spike']}, then the next week they were {highlights['fw_decline']} and {highlights['active_decline']}. devices.csv still has {highlights['devices_on_430']} devices on 4.3.0. ALT-003, RSK-03, INIT-05, and DOC-002 point here.",
         "The following week is a partial decline, not a return to the earlier baseline, and not a closed incident."),
        ("SCN-06", "Customer satisfaction decline", "How did customers in the slowdown market react?",
         "North Austin, MKT-002.",
         f"CSAT moved from {highlights['m002_csat_july']} in the week of 2026-07-06 to {highlights['m002_csat_latest']} in the week of 2026-09-21. Latest response time is {highlights['m002_hours_latest']} hours, repeat contact rate is {highlights['m002_repeat_latest']}, and installation complaints are {highlights['m002_complaints_latest']}.",
         "Cedar Park CSAT stays high in the same weeks. The decline is not company-wide in every market."),
        ("SCN-07", "Workforce bottleneck", "Where is demand outrunning certified techs?",
         "Austin Metro, MKT-001. North Austin is the smaller absolute crew in SCN-01.",
         f"Austin Metro scheduled installations rose from {highlights['austin_sched_april']} in the week of 2026-04-06 to {highlights['austin_sched_latest']} in the week of 2026-09-21. Certified headcount is flat. Utilization is {highlights['austin_util_latest']} and overtime is {highlights['austin_ot_latest']} hours. open_positions is 3.",
         "Utilization above 100 is the capacity rule in this pack. It is not a timecard feed."),
        ("SCN-08", "Hardware revision reliability", "Which revision fails more often?",
         f"Hardware revision HW-C, incident INC-005, degraded batteries {highlights['hwc_devices'] or 'listed on the reliability row'}.",
         f"Battery HW-C failure_rate in 2026-09 is {highlights['hwc_rate']} ({highlights['hwc_failures']} / {highlights['hwc_base']}). Battery HW-B is {highlights['hwb_rate']}. Other HW-C device types are also higher than their peers; INC-005 only confirms the battery mechanism.",
         "installed_base is today's census, so the rate is not a historical survival curve. Small bases move the rate a lot."),
        ("SCN-09", "Operational improvement", "Which market got better, and after which start date?",
         "Georgetown, MKT-005. Initiative INIT-01 started 2026-07-06.",
         f"Cycle time went from {highlights['geo_jun_cycle']} days in 2026-06 to {highlights['geo_sep_cycle']} days in 2026-09. First-time completion went from {highlights['geo_jun_ftc']} to {highlights['geo_sep_ftc']}. Rework fell because first-time and rework add to one. Technician count did not change.",
         "This is a different market from the North Austin slowdown."),
        ("SCN-10", "Open risks with metric backing", "Which open risks are more than a label?",
         "RSK-01 Critical open, installations_completed, MKT-002. RSK-02 Critical open, weeks_of_supply, P006. RSK-03 High open, firmware_related_incidents, INC-002. RSK-04 High open, certified_technician_count, MKT-006. RSK-05 High open, failure_rate, INC-005. RSK-06 High open, utilization_percentage, MKT-001. RSK-07 High open, csat_score, MKT-002.",
         "Each observed_value is copied from the metric table named in affected_metric. Statuses also include mitigating, monitoring, and closed. Severities include Medium and Low.",
         "A closed Critical risk, such as RSK-15, is not a current fire."),
        ("SCN-11", "Week-over-week change", "What moved in the latest business review?",
         "weekly_business_review weeks of 2026-09-21 and 2026-09-14.",
         f"Installs {highlights['wbr_prior_installs']} then {highlights['wbr_latest_installs']}. CSAT {highlights['wbr_prior_csat']} then {highlights['wbr_latest_csat']}. Critical incidents {highlights['wbr_prior_incidents']} then {highlights['wbr_latest_incidents']}. Stockouts {highlights['wbr_prior_stockouts']} then {highlights['wbr_latest_stockouts']}. Utilization {highlights['wbr_prior_util']} then {highlights['wbr_latest_util']}. Firmware-related incidents {highlights['wbr_prior_fw']} then {highlights['wbr_latest_fw']}.",
         "The install increase is the 2026-09-16 short completion day in Cedar Park falling out of the later week. North Austin completions did not recover."),
        ("SCN-12", "Drill-down path", "How do I go from the company number to a job, a part, and an incident?",
         "company_metrics -> market_performance -> deployment_metrics -> jobs.csv, technicians.csv, warehouse_inventory.csv, engineering incidents and devices.",
         f"Start at company_metrics 2026-09 installations_completed. Split it by market_performance. Open MKT-002 and confirm the month equals the sum of deployment_metrics days. P006 at W001 and P018 at W002 are inventory_risk rows whose quantities match warehouse_inventory.csv. J001 is the Round Rock fuse job next to low P018 at W002. J007 is a Cedar Park inverter job and is not a W001 customer. Technician cities for MKT-002 are Manor in technicians.csv. For the firmware week, open INC-002 and the devices still on 4.3.0. For the hardware revision, open INC-005 and Battery HW-C in reliability_metrics.",
         "Field customer ids and engineering customer ids do not join. Site ids on customer issues, when present, are engineering site ids."),
    ]
    lines = [
        "# Executive scenarios",
        "",
        "Twelve situations encoded in the metric tables. Scenario ids are pointers. They are not a ranking.",
        "",
        "A coincidence of staffing and inventory shortages does not prove which constraint was primary.",
        "",
    ]
    for sid, title, question, ids, evidence, limit in blocks:
        lines.extend(
            [
                f"## {sid} {title}",
                "",
                f"Question: {question}",
                "",
                f"Ids: {ids}",
                "",
                f"What the numbers show: {evidence}",
                "",
                f"Do not conclude: {limit}",
                "",
            ]
        )
    return "\n".join(lines)


def validate_disk(sources: dict) -> dict[str, int]:
    def read(name: str) -> list[dict[str, str]]:
        return load_csv(OUT / name)

    markets = read("markets.csv")
    monthly = read("market_performance.csv")
    daily = read("deployment_metrics.csv")
    funnel = read("customer_funnel.csv")
    experience = read("customer_experience_metrics.csv")
    issues = read("customer_issues.csv")
    workforce = read("workforce_metrics.csv")
    warehouses = read("warehouse_metrics.csv")
    inventory = read("inventory_risk.csv")
    engineering = read("engineering_health_metrics.csv")
    reliability = read("reliability_metrics.csv")
    company = read("company_metrics.csv")
    risks = read("executive_risks.csv")
    initiatives = read("executive_initiatives.csv")
    wbr = read("weekly_business_review.csv")
    alerts = read("executive_alerts.csv")
    documents = read("executive_documents.csv")

    market_ids = {row["market_id"] for row in markets}
    warehouse_ids = {row["warehouse_id"] for row in sources["warehouses"]}
    part_ids = {row["part_id"] for row in sources["parts"]}
    customer_ids = {row["customer_id"] for row in sources["customers"]}
    job_ids = {row["job_id"] for row in sources["jobs"]}
    device_ids = {row["device_id"] for row in sources["devices"]}
    site_ids = {row["site_id"] for row in sources["sites"]}
    incident_ids = {row["incident_id"] for row in sources["incidents"]}

    def check_market(rows: list[dict], label: str) -> None:
        for row in rows:
            if row.get("market_id"):
                must(row["market_id"] in market_ids, f"{label} bad market {row['market_id']}")

    for label, rows in (
        ("market_performance", monthly),
        ("deployment", daily),
        ("funnel", funnel),
        ("experience", experience),
        ("issues", issues),
        ("workforce", workforce),
        ("risks", risks),
        ("initiatives", initiatives),
        ("alerts", alerts),
        ("documents", documents),
    ):
        check_market(rows, label)

    for row in markets + warehouses + inventory + risks:
        if row.get("warehouse_id"):
            must(row["warehouse_id"] in warehouse_ids, f"bad warehouse {row['warehouse_id']}")
    for row in inventory + risks:
        if row.get("part_id"):
            must(row["part_id"] in part_ids, f"bad part {row['part_id']}")
    for row in issues:
        if row["customer_id"]:
            must(row["customer_id"] in customer_ids, f"bad customer {row['customer_id']}")
        if row["site_id"]:
            must(row["site_id"] in site_ids, f"bad site {row['site_id']}")
        if row["related_job_id"]:
            must(row["related_job_id"] in job_ids, f"bad job {row['related_job_id']}")
        if row["related_device_id"]:
            must(row["related_device_id"] in device_ids, f"bad device {row['related_device_id']}")
    for row in list(engineering) + list(reliability) + list(risks) + list(alerts) + list(documents) + list(initiatives):
        if row.get("related_incident_id"):
            must(row["related_incident_id"] in incident_ids, f"bad incident {row['related_incident_id']}")
        if row.get("primary_incident_id"):
            must(row["primary_incident_id"] in incident_ids, f"bad primary incident {row['primary_incident_id']}")

    for row in workforce:
        must(int(row["certified_technician_count"]) <= int(row["technician_count"]), "certified exceeds technician_count")

    for row in inventory:
        available = int(row["current_available_quantity"])
        consumption = float(row["weekly_consumption"])
        must(consumption > 0, "consumption must be positive")
        weeks = float(row["weeks_of_supply"])
        must(abs(weeks - round(available / consumption, 1)) < 1e-9, f"weeks_of_supply rounding {row['risk_id']}")
        must(abs(weeks - (available / consumption)) <= 0.051, f"weeks_of_supply drift {row['risk_id']}")

    for row in reliability:
        base = int(row["installed_base"])
        failures = int(row["failure_count"])
        rate = float(row["failure_rate"])
        must(base > 0, "installed base is 0")
        must(abs(rate - (failures / base)) < 0.001, f"failure_rate drift {row['device_type']} {row['hardware_revision']} {row['period']}")

    daily_sum: dict[tuple[str, str], int] = {}
    daily_crit: dict[tuple[str, str], int] = {}
    daily_stock: dict[tuple[str, str], int] = {}
    for row in daily:
        key = (row["market_id"], row["deployment_date"][:7])
        daily_sum[key] = daily_sum.get(key, 0) + int(row["installations_completed"])
        daily_crit[key] = daily_crit.get(key, 0) + int(row["critical_incidents"])
        daily_stock[key] = daily_stock.get(key, 0) + int(row["stockout_events"])
    market_month_completed: dict[str, int] = {}
    market_month_crit: dict[str, int] = {}
    market_month_stock: dict[str, int] = {}
    totals_by_market: dict[str, int] = {}
    for row in monthly:
        key = (row["market_id"], row["period"])
        completed = int(row["installations_completed"])
        must(completed == daily_sum.get(key, -1), f"monthly installs != daily for {key}")
        must(int(row["critical_incidents"]) == daily_crit.get(key, -1), f"monthly critical != daily for {key}")
        must(int(row["stockout_events"]) == daily_stock.get(key, -1), f"monthly stockout != daily for {key}")
        market_month_completed[row["period"]] = market_month_completed.get(row["period"], 0) + completed
        market_month_crit[row["period"]] = market_month_crit.get(row["period"], 0) + int(row["critical_incidents"])
        market_month_stock[row["period"]] = market_month_stock.get(row["period"], 0) + int(row["stockout_events"])
        totals_by_market[row["market_id"]] = totals_by_market.get(row["market_id"], 0) + completed
        if row["installations_target"] not in ("", "0"):
            target = int(row["installations_target"])
            if target:
                attainment = float(row["installation_attainment_percentage"])
                must(abs(attainment - (100 * completed / target)) <= 0.051, f"attainment drift {key}")
    must(len(set(totals_by_market.values())) == len(totals_by_market), "market installation totals match")

    for row in company:
        if row["drilldown_available"] != "yes":
            continue
        period = row["period"]
        must(int(row["installations_completed"]) == market_month_completed[period], f"company installs != markets {period}")
        must(int(row["critical_incidents"]) == market_month_crit[period], f"company critical != markets {period}")
        must(int(row["stockout_events"]) == market_month_stock[period], f"company stockouts != markets {period}")

    must(not all(row["severity"] == "Critical" for row in risks), "every risk is Critical")
    open_high = [row for row in risks if row["status"] == "open" and row["severity"] in ("High", "Critical")]
    must(len(open_high) >= 3, "not enough open high/critical risks")
    levels = {row["stockout_risk"] for row in inventory}
    must("Critical" in levels and "Low" in levels, "missing Critical or Low stockout risk")
    must(wbr[-1]["week_start"] == "2026-09-21", "WBR end week")
    must(int(wbr[-1]["installations_completed"]) != int(wbr[-2]["installations_completed"]), "latest week installs match prior week")
    for row in wbr:
        completed = int(row["installations_completed"])
        target = int(row["installations_target"])
        must(target > 0, "WBR target is 0")
        must(abs(float(row["installation_attainment_percentage"]) - (100 * completed / target)) <= 0.051, "WBR attainment drift")

    counts = {
        "markets": len(markets),
        "market_performance": len(monthly),
        "deployment_metrics": len(daily),
        "customer_funnel": len(funnel),
        "customer_experience_metrics": len(experience),
        "customer_issues": len(issues),
        "workforce_metrics": len(workforce),
        "warehouse_metrics": len(warehouses),
        "inventory_risk": len(inventory),
        "engineering_health_metrics": len(engineering),
        "reliability_metrics": len(reliability),
        "company_metrics": len(company),
        "executive_risks": len(risks),
        "executive_initiatives": len(initiatives),
        "weekly_business_review": len(wbr),
        "executive_alerts": len(alerts),
        "executive_documents": len(documents),
    }
    return counts


def main() -> None:
    random.seed(27)
    sources = load_sources()
    markets = build_markets(sources)
    market_ids = [row["market_id"] for row in markets]
    daily = build_daily(market_ids)
    monthly = aggregate_markets(daily, market_ids)
    weeks = weeks_covering()
    must(len(weeks) == 26, f"expected 26 weeks, got {len(weeks)}")
    funnel = build_funnel(daily, market_ids, weeks)
    experience = build_experience(market_ids, weeks)
    workforce = build_workforce(daily, markets, weeks)
    warehouse_rows = build_warehouses(daily, sources["inventory"], weeks)
    inventory = build_inventory_risk(sources, markets)
    engineering = build_engineering(sources, weeks)
    reliability = build_reliability(sources)
    wbr = build_wbr(daily, experience, workforce, engineering)
    highlights = build_highlights(monthly, experience, workforce, inventory, engineering, reliability, wbr, sources)
    scenario_asserts(highlights, monthly, markets, workforce, inventory, engineering)
    risks = build_risks(highlights)
    open_critical = sum(1 for row in risks if row["severity"] == "Critical" and row["status"] == "open")
    must(open_critical >= 2, "expected at least two open critical risks")
    company = build_company(monthly, experience, workforce, open_critical)
    highlights["company_sep_completed"] = next(row["installations_completed"] for row in company if row["period"] == "2026-09")
    initiatives = build_initiatives()
    alerts = build_alerts()
    issues = build_issues(sources, markets)
    documents = build_documents(highlights)
    question_text = render_questions()
    must(question_text.count("\n") > 75, "question file looks short")
    must(sum(len(items) for items in questions().values()) >= 75, "fewer than 75 questions")

    OUT.mkdir(parents=True, exist_ok=True)
    one_decimal = {"installation_attainment_percentage": f1, "average_cycle_time_days": f1, "weeks_of_supply": f1, "average_csat": f1, "workforce_utilization_percentage": f1}
    three_decimal = {"first_time_completion_rate": f3, "rework_rate": f3}
    rate_formats = {**one_decimal, **three_decimal}

    write_csv(
        OUT / "markets.csv",
        markets,
        ["market_id", "market_name", "company_name", "region", "status", "warehouse_id", "primary_cities", "technician_count", "certified_technician_count", "field_extract_technician_count", "field_extract_certified_count", "open_positions", "status_date", "service_note"],
    )
    write_csv(
        OUT / "market_performance.csv",
        monthly,
        ["period", "market_id", "installations_scheduled", "installations_completed", "installations_target", "installation_attainment_percentage", "first_time_completion_count", "first_time_completion_rate", "rework_count", "rework_rate", "average_cycle_time_days", "jobs_waiting_for_parts", "customer_delay_count", "critical_incidents", "stockout_events"],
        rate_formats,
    )
    write_csv(
        OUT / "deployment_metrics.csv",
        daily,
        ["deployment_date", "market_id", "installations_scheduled", "installations_completed", "installations_target", "first_time_completion_count", "rework_count", "average_cycle_time_days", "jobs_waiting_for_parts", "customer_delay_count", "critical_incidents", "stockout_events"],
    )
    write_csv(
        OUT / "customer_funnel.csv",
        funnel,
        ["week_start", "market_id", "leads", "qualified_leads", "site_surveys", "proposals", "contracts", "installations_scheduled", "installations_completed"],
    )
    write_csv(
        OUT / "customer_experience_metrics.csv",
        experience,
        ["week_start", "market_id", "csat_score", "nps", "average_response_time_hours", "repeat_contact_rate", "installation_complaint_count", "survey_responses"],
        {"repeat_contact_rate": f2},
    )
    write_csv(
        OUT / "customer_issues.csv",
        issues,
        ["issue_id", "opened_date", "market_id", "customer_id", "site_id", "related_job_id", "related_device_id", "category", "severity", "status", "summary"],
    )
    write_csv(
        OUT / "workforce_metrics.csv",
        workforce,
        ["week_start", "market_id", "technician_count", "certified_technician_count", "open_positions", "scheduled_installations", "installations_completed", "utilization_percentage", "overtime_hours"],
    )
    write_csv(
        OUT / "warehouse_metrics.csv",
        warehouse_rows,
        ["week_start", "warehouse_id", "stockout_events", "jobs_waiting_for_parts", "fill_rate_percentage", "inventory_accuracy_percentage", "cycle_counts_completed", "lines_below_reorder", "wms_core_status", "launch_location_configured", "notes"],
    )
    write_csv(
        OUT / "inventory_risk.csv",
        inventory,
        ["risk_id", "as_of_date", "part_id", "warehouse_id", "part_name", "part_criticality", "current_available_quantity", "weekly_consumption", "weeks_of_supply", "stockout_risk", "jobs_blocked", "affected_market_ids", "note"],
        {"weeks_of_supply": f1},
    )
    write_csv(
        OUT / "engineering_health_metrics.csv",
        engineering,
        ["week_start", "firmware_related_incidents", "active_incidents", "new_incidents", "resolved_incidents", "devices_on_firmware_430", "rollout_affected_device_count", "primary_incident_id", "notes"],
    )
    write_csv(
        OUT / "reliability_metrics.csv",
        reliability,
        ["period", "device_type", "hardware_revision", "installed_base", "failure_count", "failure_rate", "related_incident_id", "related_device_ids", "notes"],
        {"failure_rate": f4},
    )
    write_csv(
        OUT / "company_metrics.csv",
        company,
        ["period", "installations_scheduled", "installations_completed", "installations_target", "installation_attainment_percentage", "first_time_completion_rate", "critical_incidents", "stockout_events", "average_csat", "workforce_utilization_percentage", "open_critical_risks", "drilldown_available", "notes"],
        {"installation_attainment_percentage": f1, "first_time_completion_rate": f3, "average_csat": f1, "workforce_utilization_percentage": f1},
    )
    write_csv(
        OUT / "executive_risks.csv",
        risks,
        ["risk_id", "opened_date", "severity", "status", "market_id", "warehouse_id", "part_id", "related_incident_id", "related_initiative_id", "scenario_id", "affected_metric", "observed_value", "title", "summary"],
    )
    write_csv(
        OUT / "executive_initiatives.csv",
        initiatives,
        ["initiative_id", "initiative_name", "status", "start_date", "target_end_date", "owner_role", "market_id", "related_risk_id", "related_incident_id", "scenario_id", "expected_effect", "status_note"],
    )
    write_csv(
        OUT / "weekly_business_review.csv",
        wbr,
        ["week_start", "installations_completed", "installations_target", "installation_attainment_percentage", "average_csat", "critical_incidents", "stockout_events", "workforce_utilization_percentage", "firmware_related_incidents", "major_risks", "executive_attention_items"],
        {"installation_attainment_percentage": f1, "average_csat": f1, "workforce_utilization_percentage": f1},
    )
    write_csv(
        OUT / "executive_alerts.csv",
        alerts,
        ["alert_id", "created_at", "severity", "status", "market_id", "scenario_id", "related_risk_id", "related_incident_id", "title", "summary"],
    )
    write_csv(
        OUT / "executive_documents.csv",
        documents,
        ["document_id", "document_type", "title", "document_date", "author_role", "market_id", "related_risk_id", "related_initiative_id", "related_incident_id", "summary"],
    )
    write_text(OUT / "README.md", render_readme())
    write_text(OUT / "data_dictionary.md", render_dictionary())
    write_text(OUT / "metric_definitions.md", render_metrics(highlights, company))
    write_text(OUT / "executive_scenarios.md", render_scenarios(highlights, markets))
    write_text(OUT / "executive_test_questions.md", question_text)

    counts = validate_disk(sources)
    print("VALIDATION PASSED")
    for name, count in counts.items():
        print(f"{name} {count}")
    print("SCN-01 MKT-002 North Austin W001 P006")
    print("SCN-02 MKT-004 Cedar Park W002")
    print("SCN-03 MKT-006 San Marcos W003")
    print("SCN-04 P006 W001; P018 W002 J001; J007 is W002 and not the P006 stockout")
    print("SCN-05 INC-002 firmware 4.3.0")
    print("SCN-06 MKT-002")
    print("SCN-07 MKT-001")
    print(f"SCN-08 HW-C INC-005 devices {highlights['hwc_devices']}")
    print("SCN-09 MKT-005 INIT-01 2026-07-06")
    print("SCN-10 RSK-01 RSK-02 RSK-03 RSK-04 RSK-05 RSK-06 RSK-07")
    print("SCN-11 weeks 2026-09-14 and 2026-09-21")
    print("SCN-12 company_metrics -> market_performance -> deployment_metrics")


if __name__ == "__main__":
    main()
