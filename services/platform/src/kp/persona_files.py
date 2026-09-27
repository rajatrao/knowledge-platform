"""Persona dashboard figures read from the synthetic CSVs at request time.

Counts and lists come from those rows. Telemetry is not loaded. A blank cell
stays blank. Staffing and inventory can show up in the same window without
either one being treated as the proven primary cause.
"""

from __future__ import annotations

import csv
from pathlib import Path

from kp.config import get_settings

_SEVERITY = {"Critical": 0, "High": 1, "Medium": 2, "Low": 3}
_REVIEW_MARKETS = ("MKT-002", "MKT-006", "MKT-004")
_MARKET_ROLE = {
    "MKT-002": "Slowdown",
    "MKT-006": "Launch blocked",
    "MKT-004": "Healthy comparison",
}
_WOW_FIELDS = (
    ("installations_completed", "Installations completed"),
    ("average_csat", "Average CSAT"),
    ("critical_incidents", "Critical incidents"),
    ("stockout_events", "Stockout events"),
    ("workforce_utilization_percentage", "Workforce utilization"),
    ("firmware_related_incidents", "Firmware-related incidents"),
)
_PROACTIVE_DEVICES = ("DEV-054", "DEV-061", "DEV-062")
_ACTIVE_INCIDENT = {"Investigating": 0, "Mitigated": 1, "Monitoring": 2}
_NORTH_AUSTIN_EARLIER_WEEK = "2026-07-06"


def ceo_files() -> dict:
    root = _root()
    executive = root / "executive"
    company = sorted(_rows(executive, "company_metrics.csv"), key=lambda row: row.get("period") or "")
    latest = company[-1] if company else {}
    previous = company[-2] if len(company) > 1 else {}
    performance = _rows(executive, "market_performance.csv")
    markets = _indexed(executive, "markets.csv", "market_id")
    workforce = _rows(executive, "workforce_metrics.csv")
    inventory = _rows(executive, "inventory_risk.csv")
    health = sorted(_rows(executive, "engineering_health_metrics.csv"), key=lambda row: row.get("week_start") or "")
    reviews = sorted(_rows(executive, "weekly_business_review.csv"), key=lambda row: row.get("week_start") or "")
    warehouses = _rows(executive, "warehouse_metrics.csv")
    risks = [row for row in _rows(executive, "executive_risks.csv") if (row.get("status") or "").lower() == "open"]
    alerts = [row for row in _rows(executive, "executive_alerts.csv") if row.get("status") == "Open"]
    latest_period = latest.get("period") or ""
    previous_period = previous.get("period") or ""
    cycle = _weighted_cycle(performance, latest_period)
    certified = _certified_techs(workforce)
    critical_stock = [row for row in inventory if row.get("stockout_risk") == "Critical"]
    health_row = health[-1] if health else {}
    metrics = []
    if latest.get("installations_completed"):
        metrics.append(
            _metric(
                "installations_completed",
                "Installations completed",
                latest["installations_completed"],
                _versus(latest_period, latest.get("installations_completed"), previous_period, previous.get("installations_completed")),
                "company_metrics.csv",
            )
        )
    active_customers = _active_customers(root)
    if active_customers is not None:
        metrics.append(
            _metric(
                "active_customers",
                "Active customers",
                str(active_customers),
                "customer_id values whose customer_sites.csv site_status is Active.",
                "customer_sites.csv",
            )
        )
    if latest.get("first_time_completion_rate"):
        metrics.append(
            _metric(
                "first_time_completion_rate",
                "First-time completion",
                latest["first_time_completion_rate"],
                _versus(
                    latest_period,
                    latest.get("first_time_completion_rate"),
                    previous_period,
                    previous.get("first_time_completion_rate"),
                ),
                "company_metrics.csv",
            )
        )
    if cycle:
        metrics.append(
            _metric(
                "average_cycle_time_days",
                "Cycle days",
                cycle,
                f"Completion-weighted average_cycle_time_days for {latest_period}. Days with no completions are left out.",
                "market_performance.csv",
            )
        )
    if certified:
        metrics.append(
            _metric(
                "certified_technicians",
                "Certified techs",
                certified["count"],
                f"Sum of certified_technician_count for the week of {certified['week']}.",
                "workforce_metrics.csv",
            )
        )
    metrics.append(
        _metric(
            "critical_stockout_risks",
            "Critical stockout risks",
            str(len(critical_stock)),
            _critical_stock_detail(critical_stock),
            "inventory_risk.csv",
        )
    )
    if health_row.get("active_incidents"):
        metrics.append(
            _metric(
                "active_engineering_incidents",
                "Active engineering incidents",
                health_row["active_incidents"],
                (
                    f"active_incidents for the week of {health_row.get('week_start') or '—'}. "
                    "This is the executive rollup, not a count of engineering_incidents.csv rows."
                ),
                "engineering_health_metrics.csv",
            )
        )
    return {
        "persona": "ceo",
        "source_note": (
            "Figures are facts from the named files. "
            "A coincidence of staffing and inventory shortages does not prove which constraint was primary."
        ),
        "metrics": metrics,
        "week_over_week": _week_over_week(reviews),
        "risks": [_risk(row) for row in _by_severity(risks)[:12]],
        "open_risk_count": len(risks),
        "alerts": [_executive_alert(row) for row in _by_severity(alerts)[:12]],
        "open_alert_count": len(alerts),
        "markets": _review_markets(markets, performance, inventory, warehouses),
    }


def operations_files() -> dict:
    root = _root()
    jobs = _rows(root, "jobs.csv")
    alerts = [row for row in _rows(root, "operational_alerts.csv") if row.get("status") == "Open"]
    techs = _indexed(root, "technicians.csv", "technician_id")
    vans = _indexed(root, "vans.csv", "van_id")
    parts = _indexed(root, "parts.csv", "part_id")
    sites = _indexed(root, "customer_sites.csv", "customer_id")
    waiting = [row for row in jobs if row.get("status") == "Waiting for Parts"]
    available_techs = sorted(row["technician_id"] for row in techs.values() if row.get("status") == "Available")
    available_vans = sorted(row["van_id"] for row in vans.values() if row.get("status") == "Available")
    part_names = {key: row.get("part_name") or "" for key, row in parts.items()}
    gaps = _kit_gaps(waiting, _rows(root, "job_parts.csv"), _van_quantities(root), part_names, vans)
    hints = _supply_hints(waiting, _rows(root, "job_parts.csv"), _rows(root, "warehouse_inventory.csv"), part_names)
    return {
        "persona": "operations_manager",
        "source_note": "Figures are facts from the field files.",
        "metrics": [
            _metric(
                "open_alerts",
                "Open operational alerts",
                str(len(alerts)),
                "status Open.",
                "operational_alerts.csv",
            ),
            _metric(
                "jobs_waiting_for_parts",
                "Jobs waiting for parts",
                str(len(waiting)),
                ", ".join(row["job_id"] for row in waiting) or "None",
                "jobs.csv",
            ),
            _metric(
                "vans_available",
                "Vans available",
                str(len(available_vans)),
                ", ".join(available_vans) or "None",
                "vans.csv",
            ),
            _metric(
                "techs_available",
                "Technicians available",
                str(len(available_techs)),
                ", ".join(available_techs) or "None",
                "technicians.csv",
            ),
        ],
        "alerts": [_ops_alert(row) for row in _by_severity(alerts)[:12]],
        "open_alert_count": len(alerts),
        "waiting_jobs": [_waiting_job(row, sites) for row in waiting],
        "kit_gaps": gaps,
        "supply_hints": hints,
    }


def engineering_files() -> dict:
    root = _root() / "engineering"
    devices = _rows(root, "devices.csv")
    incidents = _rows(root, "engineering_incidents.csv")
    offline = [_device(row) for row in devices if row.get("status") == "Offline"]
    faulted = [_device(row) for row in devices if row.get("status") == "Faulted"]
    firmware = [_device(row) for row in devices if row.get("firmware_version") == "4.3.0"]
    active = [row for row in incidents if row.get("status") not in {"Closed", "Resolved"}]
    active.sort(key=lambda row: (_ACTIVE_INCIDENT.get(row.get("status") or "", 9), row.get("incident_id") or ""))
    unresolved = [row for row in incidents if row.get("confirmed_root_cause") == "Under Investigation"]
    unresolved.sort(key=lambda row: (row.get("incident_id") != "INC-008", row.get("incident_id") or ""))
    by_id = {row["device_id"]: row for row in devices if row.get("device_id")}
    firmware_incident = next((row for row in incidents if row.get("incident_id") == "INC-002"), None)
    watch_incident = next((row for row in incidents if row.get("incident_id") == "INC-012"), None)
    return {
        "persona": "engineer",
        "source_note": (
            "Device and incident figures are facts from the engineering files. "
            "Telemetry rows are not included. A confirmed_root_cause of Under Investigation is the file value."
        ),
        "metrics": [
            _metric(
                "devices_offline",
                "Devices offline",
                str(len(offline)),
                ", ".join(row["device_id"] for row in offline) or "None",
                "devices.csv",
            ),
            _metric(
                "devices_faulted",
                "Devices faulted",
                str(len(faulted)),
                ", ".join(row["device_id"] for row in faulted) or "None",
                "devices.csv",
            ),
            _metric(
                "active_incidents",
                "Active incidents",
                str(len(active)),
                "engineering_incidents.csv rows whose status is not Closed or Resolved.",
                "engineering_incidents.csv",
            ),
            _metric(
                "firmware_430",
                "Firmware 4.3.0 still installed",
                str(len(firmware)),
                _firmware_detail(firmware, firmware_incident),
                "devices.csv, engineering_incidents.csv" if firmware_incident else "devices.csv",
            ),
        ],
        "offline": offline,
        "faulted": faulted,
        "active_incidents": [_incident_brief(row) for row in active[:8]],
        "active_incident_count": len(active),
        "under_investigation": [_unresolved(row) for row in unresolved],
        "proactive_watch": [_device(by_id[device_id]) for device_id in _PROACTIVE_DEVICES if device_id in by_id],
        "proactive_incident": _incident_brief(watch_incident) if watch_incident else None,
    }


def marketing_files() -> dict:
    executive = _root() / "executive"
    experience = _rows(executive, "customer_experience_metrics.csv")
    issues = _rows(executive, "customer_issues.csv")
    markets = _indexed(executive, "markets.csv", "market_id")
    latest_week = max((row.get("week_start") or "" for row in experience), default="")
    latest_rows = [row for row in experience if row.get("week_start") == latest_week]
    latest_rows.sort(key=lambda row: row.get("market_id") or "")
    north_latest = next((row for row in latest_rows if row.get("market_id") == "MKT-002"), None)
    north_earlier = next(
        (
            row
            for row in experience
            if row.get("market_id") == "MKT-002" and row.get("week_start") == _NORTH_AUSTIN_EARLIER_WEEK
        ),
        None,
    )
    cedar = next((row for row in latest_rows if row.get("market_id") == "MKT-004"), None)
    return {
        "persona": "marketing",
        "source_note": "Satisfaction and issue categories are facts from the customer files. Markets are listed in market id order.",
        "north_austin": _north_austin(markets, north_earlier, north_latest, cedar),
        "satisfaction": [_satisfaction(row, markets) for row in latest_rows],
        "satisfaction_week": latest_week,
        "categories": _issue_categories(issues),
    }


def _root() -> Path:
    return Path(get_settings().repo_root) / "data"


def _rows(directory: Path, filename: str) -> list[dict[str, str]]:
    path = directory / filename
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _indexed(directory: Path, filename: str, key: str) -> dict[str, dict[str, str]]:
    return {row[key]: row for row in _rows(directory, filename) if row.get(key)}


def _metric(key: str, label: str, value: str, detail: str, source: str) -> dict:
    return {"key": key, "label": label, "value": value, "detail": detail, "source": source}


def _versus(latest_period: str, latest_value: str | None, previous_period: str, previous_value: str | None) -> str:
    text = f"{latest_period} in the file."
    if previous_period and previous_value:
        text = f"{latest_period} versus {previous_value} in {previous_period}."
    return text


def _active_customers(root: Path) -> int | None:
    sites = _rows(root, "customer_sites.csv")
    if not sites or "site_status" not in sites[0]:
        return None
    return len({row["customer_id"] for row in sites if row.get("site_status") == "Active" and row.get("customer_id")})


def _weighted_cycle(rows: list[dict[str, str]], period: str) -> str:
    weighted = 0.0
    completions = 0.0
    for row in rows:
        if row.get("period") != period:
            continue
        done = row.get("installations_completed") or ""
        cycle = row.get("average_cycle_time_days") or ""
        if not done or not cycle:
            continue
        weight = float(done)
        if weight <= 0:
            continue
        weighted += float(cycle) * weight
        completions += weight
    if completions <= 0:
        return ""
    return f"{weighted / completions:.1f}"


def _certified_techs(rows: list[dict[str, str]]) -> dict[str, str] | None:
    if not rows:
        return None
    week = max(row.get("week_start") or "" for row in rows)
    total = sum(int(row["certified_technician_count"] or 0) for row in rows if row.get("week_start") == week)
    return {"week": week, "count": str(total)}


def _critical_stock_detail(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "No inventory_risk.csv row has stockout_risk Critical."
    parts = [
        f"{row.get('part_id') or 'part'} at {row.get('warehouse_id') or 'warehouse'} weeks_of_supply {row.get('weeks_of_supply') or '—'}"
        for row in rows
    ]
    return "stockout_risk Critical: " + "; ".join(parts) + "."


def _week_over_week(rows: list[dict[str, str]]) -> dict | None:
    if len(rows) < 2:
        return None
    previous, latest = rows[-2], rows[-1]
    return {
        "previous_week": previous.get("week_start") or "",
        "latest_week": latest.get("week_start") or "",
        "source": "weekly_business_review.csv",
        "rows": [
            {
                "key": key,
                "label": label,
                "previous": previous.get(key) or "",
                "latest": latest.get(key) or "",
            }
            for key, label in _WOW_FIELDS
        ],
        "note": _wow_note(previous, latest),
    }


def _wow_note(previous: dict[str, str], latest: dict[str, str]) -> str:
    note = (
        f"Week of {previous.get('week_start') or '—'} compared with week of {latest.get('week_start') or '—'} "
        "in weekly_business_review.csv."
    )
    attention = (latest.get("executive_attention_items") or "").strip()
    if attention:
        note = f"{note} {attention}"
    return note


def _by_severity(rows: list[dict[str, str]]) -> list[dict[str, str]]:
    return sorted(rows, key=lambda row: (_SEVERITY.get(row.get("severity") or "", 9), row.get("risk_id") or row.get("alert_id") or ""))


def _risk(row: dict[str, str]) -> dict:
    return {
        "risk_id": row.get("risk_id") or "",
        "severity": row.get("severity") or "",
        "status": row.get("status") or "",
        "market_id": row.get("market_id") or "",
        "title": row.get("title") or "",
        "affected_metric": row.get("affected_metric") or "",
        "observed_value": row.get("observed_value") or "",
    }


def _executive_alert(row: dict[str, str]) -> dict:
    return {
        "alert_id": row.get("alert_id") or "",
        "severity": row.get("severity") or "",
        "status": row.get("status") or "",
        "market_id": row.get("market_id") or "",
        "title": row.get("title") or "",
        "summary": row.get("summary") or "",
    }


def _review_markets(
    markets: dict[str, dict[str, str]],
    performance: list[dict[str, str]],
    inventory: list[dict[str, str]],
    warehouses: list[dict[str, str]],
) -> list[dict]:
    cards = []
    for market_id in _REVIEW_MARKETS:
        market = markets.get(market_id) or {"market_id": market_id, "market_name": market_id}
        cards.append(
            {
                "market_id": market_id,
                "name": market.get("market_name") or market_id,
                "role": _MARKET_ROLE.get(market_id, ""),
                "status": market.get("status") or "",
                "lines": _market_lines(market, performance, inventory, warehouses),
            }
        )
    return cards


def _market_lines(
    market: dict[str, str],
    performance: list[dict[str, str]],
    inventory: list[dict[str, str]],
    warehouses: list[dict[str, str]],
) -> list[str]:
    market_id = market.get("market_id") or ""
    september = _performance_row(performance, "2026-09", market_id)
    july = _performance_row(performance, "2026-07", market_id)
    lines: list[str] = []
    if market.get("status"):
        lines.append(f"Status {market['status']} in markets.csv.")
    if september:
        lines.append(
            "2026-09 installations_completed "
            f"{september.get('installations_completed') or '0'} in market_performance.csv."
        )
        if july and july.get("installations_completed"):
            lines.append(f"2026-07 installations_completed were {july['installations_completed']}.")
        detail = _performance_detail(september)
        if detail:
            lines.append(detail)
    if market_id == "MKT-002":
        lines.append(_north_austin_caveat(market, inventory))
    if market_id == "MKT-006":
        lines.append(
            f"Launch roster certified_technician_count {market.get('certified_technician_count') or '—'} "
            f"of technician_count {market.get('technician_count') or '—'}."
        )
        launch = _launch_flag(warehouses, market.get("warehouse_id") or "")
        if launch:
            lines.append(launch)
    return [line for line in lines if line]


def _performance_row(rows: list[dict[str, str]], period: str, market_id: str) -> dict[str, str] | None:
    for row in rows:
        if row.get("period") == period and row.get("market_id") == market_id:
            return row
    return None


def _performance_detail(row: dict[str, str]) -> str:
    parts = []
    if row.get("first_time_completion_rate"):
        parts.append(f"first_time_completion_rate {row['first_time_completion_rate']}")
    if row.get("average_cycle_time_days"):
        parts.append(f"average_cycle_time_days {row['average_cycle_time_days']}")
    if row.get("jobs_waiting_for_parts"):
        parts.append(f"jobs_waiting_for_parts {row['jobs_waiting_for_parts']}")
    if row.get("rework_rate"):
        parts.append(f"rework_rate {row['rework_rate']}")
    if row.get("stockout_events") != "":
        parts.append(f"stockout_events {row.get('stockout_events') or '0'}")
    if row.get("critical_incidents") != "":
        parts.append(f"critical_incidents {row.get('critical_incidents') or '0'}")
    return ". ".join(parts) + "." if parts else ""


def _north_austin_caveat(market: dict[str, str], inventory: list[dict[str, str]]) -> str:
    certified = market.get("certified_technician_count") or "—"
    stock = next((row for row in inventory if row.get("part_id") == "P006" and row.get("warehouse_id") == "W001"), None)
    weeks = stock.get("weeks_of_supply") if stock else "—"
    return (
        f"Certified headcount is {certified} and P006 at W001 weeks_of_supply is {weeks}. "
        "Both are in the files. They do not identify which constraint was primary."
    )


def _launch_flag(rows: list[dict[str, str]], warehouse_id: str) -> str:
    matched = [row for row in rows if row.get("warehouse_id") == warehouse_id]
    if not matched:
        return ""
    latest = max(matched, key=lambda row: row.get("week_start") or "")
    flag = latest.get("launch_location_configured") or ""
    if not flag:
        return ""
    return (
        f"{warehouse_id} launch_location_configured is {flag} "
        f"for the week of {latest.get('week_start') or '—'} in warehouse_metrics.csv."
    )


def _van_quantities(root: Path) -> dict[tuple[str, str], int]:
    quantities: dict[tuple[str, str], int] = {}
    for row in _rows(root, "van_inventory.csv"):
        van_id = row.get("van_id") or ""
        part_id = row.get("part_id") or ""
        if van_id and part_id:
            quantities[(van_id, part_id)] = int(row.get("quantity") or 0)
    return quantities


def _kit_gaps(
    jobs: list[dict[str, str]],
    job_parts: list[dict[str, str]],
    quantities: dict[tuple[str, str], int],
    part_names: dict[str, str],
    vans: dict[str, dict[str, str]],
) -> list[dict]:
    gaps = []
    for job in jobs:
        van_id = job.get("van_id") or ""
        for part in job_parts:
            if part.get("job_id") != job.get("job_id") or part.get("status") != "Missing":
                continue
            part_id = part.get("part_id") or ""
            required = int(part.get("required_quantity") or 0)
            if (van_id, part_id) in quantities:
                have = quantities[(van_id, part_id)]
                inventory_note = f"van_inventory quantity {have}"
            else:
                have = 0
                inventory_note = "no van_inventory row, quantity 0"
            short = required - have
            if short < 0:
                short = 0
            if short <= 0:
                continue
            van = vans.get(van_id) or {}
            gaps.append(
                {
                    "job_id": job.get("job_id") or "",
                    "van_id": van_id,
                    "technician_id": job.get("technician_id") or "",
                    "city": van.get("current_city") or "",
                    "part_id": part_id,
                    "part_name": part_names.get(part_id) or "",
                    "required_quantity": str(required),
                    "van_quantity": str(have),
                    "short": str(short),
                    "inventory_note": inventory_note,
                    "job_parts_status": part.get("status") or "",
                }
            )
    return gaps


def _supply_hints(
    jobs: list[dict[str, str]],
    job_parts: list[dict[str, str]],
    inventory: list[dict[str, str]],
    part_names: dict[str, str],
) -> list[dict]:
    hints = []
    for job in jobs:
        for part in job_parts:
            if part.get("job_id") != job.get("job_id") or part.get("status") != "Missing":
                continue
            part_id = part.get("part_id") or ""
            warehouses = [
                {
                    "warehouse_id": row.get("warehouse_id") or "",
                    "quantity_available": row.get("quantity_available") or "0",
                }
                for row in inventory
                if row.get("part_id") == part_id
            ]
            warehouses.sort(key=lambda row: row["warehouse_id"])
            if not warehouses:
                continue
            hints.append(
                {
                    "job_id": job.get("job_id") or "",
                    "job_status": job.get("status") or "",
                    "part_id": part_id,
                    "part_name": part_names.get(part_id) or "",
                    "warehouses": warehouses,
                }
            )
    return hints


def _waiting_job(row: dict[str, str], sites: dict[str, dict[str, str]]) -> dict:
    site = sites.get(row.get("customer_id") or "") or {}
    return {
        "job_id": row.get("job_id") or "",
        "status": row.get("status") or "",
        "priority": row.get("priority") or "",
        "technician_id": row.get("technician_id") or "",
        "van_id": row.get("van_id") or "",
        "customer_id": row.get("customer_id") or "",
        "city": site.get("city") or "",
        "job_type": row.get("job_type") or "",
    }


def _ops_alert(row: dict[str, str]) -> dict:
    return {
        "alert_id": row.get("alert_id") or "",
        "severity": row.get("severity") or "",
        "alert_type": row.get("alert_type") or "",
        "entity_type": row.get("entity_type") or "",
        "entity_id": row.get("entity_id") or "",
        "description": row.get("description") or "",
        "recommended_action": row.get("recommended_action") or "",
    }


def _device(row: dict[str, str]) -> dict:
    return {
        "device_id": row.get("device_id") or "",
        "device_type": row.get("device_type") or "",
        "status": row.get("status") or "",
        "firmware_version": row.get("firmware_version") or "",
        "site_id": row.get("site_id") or "",
    }


def _incident_brief(row: dict[str, str] | None) -> dict:
    if not row:
        return {}
    return {
        "incident_id": row.get("incident_id") or "",
        "title": row.get("incident_title") or "",
        "status": row.get("status") or "",
        "severity": row.get("severity") or "",
    }


def _unresolved(row: dict[str, str]) -> dict:
    brief = _incident_brief(row)
    brief["confirmed_root_cause"] = row.get("confirmed_root_cause") or ""
    return brief


def _firmware_detail(devices: list[dict], incident: dict[str, str] | None) -> str:
    names = ", ".join(row["device_id"] for row in devices) or "None"
    if not incident:
        return names
    return f"{names}. {incident.get('incident_id') or 'INC-002'} status is {incident.get('status') or '—'}."


def _satisfaction(row: dict[str, str], markets: dict[str, dict[str, str]]) -> dict:
    market = markets.get(row.get("market_id") or "") or {}
    return {
        "market_id": row.get("market_id") or "",
        "name": market.get("market_name") or row.get("market_id") or "",
        "week_start": row.get("week_start") or "",
        "csat_score": row.get("csat_score") or "",
        "nps": row.get("nps") or "",
        "installation_complaint_count": row.get("installation_complaint_count") or "",
    }


def _north_austin(
    markets: dict[str, dict[str, str]],
    earlier: dict[str, str] | None,
    latest: dict[str, str] | None,
    cedar: dict[str, str] | None,
) -> dict | None:
    if earlier is None and latest is None:
        return None
    market = markets.get("MKT-002") or {}
    payload = {
        "market_id": "MKT-002",
        "name": market.get("market_name") or "North Austin",
        "source": "customer_experience_metrics.csv",
    }
    if earlier:
        payload["from_week"] = earlier.get("week_start") or ""
        payload["from_csat"] = earlier.get("csat_score") or ""
    if latest:
        payload["to_week"] = latest.get("week_start") or ""
        payload["to_csat"] = latest.get("csat_score") or ""
        payload["to_nps"] = latest.get("nps") or ""
        payload["to_response_hours"] = latest.get("average_response_time_hours") or ""
        payload["to_repeat_contact_rate"] = latest.get("repeat_contact_rate") or ""
        payload["to_installation_complaints"] = latest.get("installation_complaint_count") or ""
    if cedar:
        payload["comparison_market_id"] = "MKT-004"
        payload["comparison_name"] = (markets.get("MKT-004") or {}).get("market_name") or "Cedar Park"
        payload["comparison_week"] = cedar.get("week_start") or ""
        payload["comparison_csat"] = cedar.get("csat_score") or ""
    return payload


def _issue_categories(rows: list[dict[str, str]]) -> list[dict]:
    grouped: dict[str, dict[str, int]] = {}
    for row in rows:
        category = row.get("category") or "Uncategorized"
        bucket = grouped.setdefault(category, {"count": 0, "open": 0, "north_austin_open": 0})
        bucket["count"] += 1
        if row.get("status") == "Open":
            bucket["open"] += 1
            if row.get("market_id") == "MKT-002":
                bucket["north_austin_open"] += 1
    categories = [
        {
            "category": name,
            "count": counts["count"],
            "open": counts["open"],
            "north_austin_open": counts["north_austin_open"],
        }
        for name, counts in grouped.items()
    ]
    categories.sort(key=lambda row: (-row["count"], row["category"]))
    return categories
