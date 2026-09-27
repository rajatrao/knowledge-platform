"""Field-operations rows read from the synthetic CSVs at ask time.

Locations, statuses, and quantities come from those rows. Nothing is filled in
when a row is missing.
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from kp.config import get_settings
from kp.knowledge.retrieve import Bundle, _finance_query, _normalized_query, _outage_query

FIELD_OPS_KIND = "field_ops"

_OPEN_JOB = {"Scheduled", "Assigned", "En Route", "Onsite", "In Progress", "Waiting for Parts"}


def _corpus_inventory_question(text: str) -> bool:
    """Warehouse forecast questions stay on the company corpus, not the field CSVs."""
    return any(term in text for term in ("forecast", "days of cover", "on-hand", "on hand", "sku", "shortfall"))


def _wants_warehouse(text: str) -> bool:
    if _corpus_inventory_question(text):
        return False
    if re.search(r"\bw\d{3}\b", text):
        return True
    return bool(re.search(r"\bwarehouses?\b", text) or re.search(r"\bsupply\b", text))


def _wants_schedule(text: str) -> bool:
    return bool(re.search(r"\bschedul", text))


def _wants_ops_alert(text: str) -> bool:
    return bool(re.search(r"\boperational alerts?\b", text))


def field_ops_query(query: str) -> bool:
    """Technician, van, warehouse-supply, schedule, and who-is-available questions."""
    text = _normalized_query(query)
    if re.search(r"\b(technicians?|techs|vans?|crews?)\b", text):
        return True
    if re.search(r"\b[tvj]\d{3}\b", text):
        return True
    if _available_listing(text) is not None:
        return True
    return _wants_warehouse(text) or _wants_schedule(text) or _wants_ops_alert(text)


def include_field_ops_records(bundle: Bundle, query: str) -> None:
    """Prepend matching CSV rows so synthesis quotes them instead of complaints."""
    text = _normalized_query(query)
    if not field_ops_query(text) or _finance_query(text) or _outage_query(text):
        return
    selected = _select(text)
    if not selected:
        return
    existing = list(bundle.records.items())
    bundle.records.clear()
    for record_id, body, document_id in selected:
        bundle.add(FIELD_OPS_KIND, record_id, body, document_id)
    for key, value in existing:
        bundle.records.setdefault(key, value)


def prompt_records(bundle: Bundle, query: str) -> list[tuple[tuple[str, str], dict]]:
    """Dataset questions are answered from those rows, not complaint evidence.

    Revenue, forecast, and outage questions keep every retrieved record.
    """
    items = list(bundle.records.items())
    text = _normalized_query(query)
    if _finance_query(text) or _outage_query(text):
        return items
    from kp.knowledge.engineering import ENGINEERING_KIND, engineering_query
    from kp.knowledge.executive import EXECUTIVE_KIND, executive_query

    selected: list[tuple[tuple[str, str], dict]] = []
    engineering = engineering_query(text)
    executive = executive_query(text)
    if executive:
        selected.extend(item for item in items if item[0][0] == EXECUTIVE_KIND)
        if re.search(r"\b(why|cause|firmware|engineering|incidents?|devices?|jobs?)\b", text):
            selected.extend(item for item in items if item[0][0] == ENGINEERING_KIND)
            selected.extend(item for item in items if item[0][0] == FIELD_OPS_KIND)
    if engineering and not executive:
        selected.extend(item for item in items if item[0][0] == ENGINEERING_KIND)
    field = field_ops_query(text)
    named_field = bool(re.search(r"\b[tvjw]\d{3}\b", text))
    if field and not executive and (not engineering or named_field):
        selected.extend(item for item in items if item[0][0] == FIELD_OPS_KIND)
    if selected:
        return selected
    return items


def answer_uses_rows(answer: str, rows: list[dict]) -> bool:
    """True when the answer repeats an id, city, or technician name from the rows."""
    folded = (answer or "").casefold()
    if not folded:
        return False
    for row in rows:
        text = row.get("text") or ""
        for token in re.findall(r"\b(?:T|V|J|P|VI|JP)\d+\b", text, re.I):
            if token.casefold() in folded:
                return True
        city = re.search(
            r"\bcity ([A-Za-z][A-Za-z .'-]*?) (?:van|technician|lat|customer|priority|home_warehouse)\b",
            text,
        )
        if city and city.group(1).casefold() in folded:
            return True
        name = re.search(r"\bTechnician T\d{3} ([A-Za-z]+ [A-Za-z]+)\b", text)
        if name and name.group(1).casefold() in folded:
            return True
    return False


def _available_listing(text: str) -> str | None:
    if "available" not in text:
        return None
    if _ids(text, "v") or _ids(text, "t") or _ids(text, "j"):
        return None
    if re.search(r"\bwhere\b", text):
        return None
    vans = bool(re.search(r"\bvans?\b", text))
    people = bool(
        re.search(r"\b(technicians?|techs|crews?|who|people|person|persons|drivers?|staff)\b", text)
    )
    if vans and not people:
        return "vans"
    if people:
        return "technicians"
    return None


def _needs_job(text: str) -> bool:
    if re.search(r"\bj\d{3}\b", text) or re.search(r"\bjobs?\b", text):
        return True
    if re.search(r"\bwhere\b", text):
        return True
    return bool(re.search(r"\b(short|shortage|missing|everything|kitted|kit)\b", text))


def _needs_inventory(text: str) -> bool:
    return bool(
        re.search(
            r"\b(inventory|parts?|stock|short|shortage|missing|kitted|kit|carrying|everything)\b",
            text,
        )
    )


def _ids(text: str, prefix: str) -> list[str]:
    found: list[str] = []
    for match in re.findall(rf"\b{prefix}\d{{3}}\b", text):
        token = match.upper()
        if token not in found:
            found.append(token)
    return found


def _rows(filename: str) -> list[dict[str, str]]:
    path = Path(get_settings().repo_root) / "data" / filename
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _indexed(filename: str, key: str) -> dict[str, dict[str, str]]:
    return {row[key]: row for row in _rows(filename)}


def _select(text: str) -> list[tuple[str, str, str]]:
    techs = _indexed("technicians.csv", "technician_id")
    vans = _indexed("vans.csv", "van_id")
    jobs = (
        _indexed("jobs.csv", "job_id")
        if _needs_job(text) or _needs_inventory(text) or _wants_warehouse(text) or _wants_schedule(text)
        else {}
    )
    listing = _available_listing(text)
    van_ids = _ids(text, "v")
    tech_ids = _ids(text, "t")
    job_ids = _ids(text, "j")

    chosen_techs: dict[str, dict[str, str]] = {}
    chosen_vans: dict[str, dict[str, str]] = {}
    chosen_jobs: dict[str, dict[str, str]] = {}

    if listing == "technicians":
        for row in sorted(techs.values(), key=lambda item: item["technician_id"]):
            if row["status"] == "Available":
                chosen_techs[row["technician_id"]] = row
    elif listing == "vans":
        for row in sorted(vans.values(), key=lambda item: item["van_id"]):
            if row["status"] == "Available":
                chosen_vans[row["van_id"]] = row
    else:
        for van_id in van_ids:
            row = vans.get(van_id)
            if row:
                chosen_vans[van_id] = row
                _take_tech(chosen_techs, techs, row.get("assigned_technician_id") or "")
        for tech_id in tech_ids:
            _take_tech(chosen_techs, techs, tech_id)
            tech = techs.get(tech_id)
            if tech:
                _take_van(chosen_vans, vans, tech.get("assigned_van_id") or "")
        if not van_ids and not tech_ids and not job_ids:
            if re.search(r"\bvans?\b", text):
                chosen_vans = {row["van_id"]: row for row in sorted(vans.values(), key=lambda item: item["van_id"])}
            elif re.search(r"\btechnicians?\b", text):
                chosen_techs = {
                    row["technician_id"]: row
                    for row in sorted(techs.values(), key=lambda item: item["technician_id"])
                }
        if _needs_job(text):
            for job_id in job_ids:
                job = jobs.get(job_id)
                if job:
                    chosen_jobs[job_id] = job
            for tech in chosen_techs.values():
                job_id = tech.get("current_job_id") or ""
                job = jobs.get(job_id)
                if job:
                    chosen_jobs[job_id] = job
            for van in list(chosen_vans.values()):
                if any(job.get("van_id") == van["van_id"] for job in chosen_jobs.values()):
                    continue
                current = _open_job_for_van(jobs, van["van_id"])
                if current:
                    chosen_jobs[current["job_id"]] = current
            for job in chosen_jobs.values():
                _take_van(chosen_vans, vans, job.get("van_id") or "")
                _take_tech(chosen_techs, techs, job.get("technician_id") or "")

    records: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def add(record_id: str, body: str, document_id: str) -> None:
        if not record_id or record_id in seen:
            return
        seen.add(record_id)
        records.append((record_id, body, document_id))

    for row in chosen_vans.values():
        add(row["van_id"], _van_text(row), "vans.csv")
    for row in chosen_techs.values():
        add(row["technician_id"], _tech_text(row), "technicians.csv")
    for row in chosen_jobs.values():
        add(row["job_id"], _job_text(row), "jobs.csv")
    if _needs_inventory(text) and chosen_vans:
        _add_inventory(add, chosen_vans, chosen_jobs, jobs)
    if _wants_warehouse(text):
        _add_warehouse_supply(add, chosen_jobs, jobs)
    if _wants_schedule(text):
        _add_schedules(add, text, chosen_techs, chosen_jobs)
    if _wants_ops_alert(text):
        _add_operational_alerts(add, chosen_jobs, chosen_vans, chosen_techs)
    return records


def _take_tech(chosen: dict[str, dict[str, str]], techs: dict[str, dict[str, str]], tech_id: str) -> None:
    row = techs.get(tech_id)
    if row:
        chosen.setdefault(tech_id, row)


def _take_van(chosen: dict[str, dict[str, str]], vans: dict[str, dict[str, str]], van_id: str) -> None:
    row = vans.get(van_id)
    if row:
        chosen.setdefault(van_id, row)


def _open_job_for_van(jobs: dict[str, dict[str, str]], van_id: str) -> dict[str, str] | None:
    matches = [
        job
        for job in jobs.values()
        if job.get("van_id") == van_id and job.get("status") in _OPEN_JOB
    ]
    if not matches:
        return None
    matches.sort(key=lambda job: (job.get("scheduled_date") or "", job["job_id"]))
    today = [job for job in matches if job.get("scheduled_date") == "2026-09-27"]
    return today[-1] if today else matches[-1]


def _add_inventory(add, chosen_vans: dict[str, dict[str, str]], chosen_jobs: dict[str, dict[str, str]], jobs: dict[str, dict[str, str]]) -> None:
    by_van: dict[str, dict[str, int]] = {van_id: {} for van_id in chosen_vans}
    for row in _rows("van_inventory.csv"):
        van_id = row["van_id"]
        if van_id not in by_van:
            continue
        by_van[van_id][row["part_id"]] = int(row["quantity"])
        add(row["van_inventory_id"], _inventory_text(row), "van_inventory.csv")
    if not chosen_jobs:
        return
    wanted = set(chosen_jobs)
    for part in _rows("job_parts.csv"):
        if part["job_id"] not in wanted:
            continue
        job = jobs.get(part["job_id"]) or chosen_jobs[part["job_id"]]
        van_id = job.get("van_id") or ""
        quantities = by_van.get(van_id, {})
        add(part["job_part_id"], _job_part_text(part, van_id, quantities), "job_parts.csv")


def _van_text(row: dict[str, str]) -> str:
    technician = row["assigned_technician_id"] or "none"
    return (
        f"Van {row['van_id']} {row['vehicle_number']} status {row['status']} "
        f"technician {technician} city {row['current_city']} "
        f"lat {row['current_latitude']} lon {row['current_longitude']} "
        f"home_warehouse {row['home_warehouse_id']} last_check_in {row['last_check_in']}."
    )


def _tech_text(row: dict[str, str]) -> str:
    van = row["assigned_van_id"] or "none"
    job = row["current_job_id"] or "none"
    return (
        f"Technician {row['technician_id']} {row['name']} status {row['status']} "
        f"city {row['current_city']} van {van} current_job {job} "
        f"lat {row['current_latitude']} lon {row['current_longitude']} "
        f"as of {row['last_location_timestamp']}."
    )


def _job_text(row: dict[str, str]) -> str:
    technician = row["technician_id"] or "none"
    van = row["van_id"] or "none"
    return (
        f"Job {row['job_id']} status {row['status']} technician {technician} "
        f"van {van} customer {row['customer_id']} priority {row['priority']} "
        f"scheduled {row['scheduled_date']} type {row['job_type']}."
    )


def _inventory_text(row: dict[str, str]) -> str:
    return (
        f"Van inventory {row['van_inventory_id']} van {row['van_id']} "
        f"part {row['part_id']} quantity {row['quantity']} "
        f"last_inventory_check {row['last_inventory_check']}."
    )


def _add_warehouse_supply(add, chosen_jobs: dict[str, dict[str, str]], jobs: dict[str, dict[str, str]]) -> None:
    """Warehouse rows that can fill missing job parts. Zero on-hand stays a row."""
    if not chosen_jobs:
        alerts = _rows("operational_alerts.csv")
        for alert in alerts:
            job_id = alert.get("entity_id") or ""
            if alert.get("entity_type") != "Job" or job_id not in jobs:
                continue
            if "part" in (alert.get("alert_type") or "").casefold() or "stock" in (alert.get("description") or "").casefold():
                chosen_jobs[job_id] = jobs[job_id]
            if len(chosen_jobs) >= 3:
                break
    if not chosen_jobs:
        return
    parts = _indexed("parts.csv", "part_id")
    warehouses = _indexed("warehouses.csv", "warehouse_id")
    needed: set[str] = set()
    for part in _rows("job_parts.csv"):
        if part.get("job_id") not in chosen_jobs:
            continue
        status = part.get("status") or ""
        if status not in {"Missing", "Required"} and len(chosen_jobs) > 1:
            continue
        needed.add(part["part_id"])
        add(part["job_part_id"], _job_part_demand_text(part, parts), "job_parts.csv")
        if len(needed) >= 6:
            break
    if not needed:
        return
    seen_warehouses: set[str] = set()
    for row in _rows("warehouse_inventory.csv"):
        if row.get("part_id") not in needed:
            continue
        add(row["warehouse_inventory_id"], _warehouse_inventory_text(row, warehouses, parts), "warehouse_inventory.csv")
        seen_warehouses.add(row["warehouse_id"])
    for warehouse_id in sorted(seen_warehouses):
        row = warehouses.get(warehouse_id)
        if row:
            add(warehouse_id, _warehouse_text(row), "warehouses.csv")
    for alert in _rows("operational_alerts.csv"):
        entity = alert.get("entity_id") or ""
        if entity in chosen_jobs or entity in needed:
            add(alert["alert_id"], _alert_text(alert), "operational_alerts.csv")


def _add_schedules(add, text: str, chosen_techs: dict[str, dict[str, str]], chosen_jobs: dict[str, dict[str, str]]) -> None:
    tech_ids = set(chosen_techs)
    job_ids = set(chosen_jobs)
    if "tomorrow" in text:
        day = "2026-09-28"
    elif "today" in text:
        day = "2026-09-27"
    else:
        day = ""
    count = 0
    for row in _rows("schedules.csv"):
        matched = row.get("technician_id") in tech_ids or row.get("job_id") in job_ids
        if not matched and not tech_ids and not job_ids and day and row.get("date") == day:
            matched = True
        if not matched:
            continue
        add(row["schedule_id"], _schedule_text(row), "schedules.csv")
        count += 1
        if count >= 12:
            break


def _add_operational_alerts(add, chosen_jobs, chosen_vans, chosen_techs) -> None:
    entities = set(chosen_jobs) | set(chosen_vans) | set(chosen_techs)
    count = 0
    for row in _rows("operational_alerts.csv"):
        entity = row.get("entity_id") or ""
        if entities and entity not in entities:
            continue
        if (row.get("status") or "") not in {"Open", ""} and entities:
            continue
        add(row["alert_id"], _alert_text(row), "operational_alerts.csv")
        count += 1
        if count >= 8:
            break


def _warehouse_text(row: dict[str, str]) -> str:
    return (
        f"Warehouse {row['warehouse_id']} {row['warehouse_name']} city {row['city']} "
        f"status {row['status']} manager {row['manager_name']}."
    )


def _warehouse_inventory_text(row: dict[str, str], warehouses: dict[str, dict[str, str]], parts: dict[str, dict[str, str]]) -> str:
    warehouse = warehouses.get(row["warehouse_id"]) or {}
    part = parts.get(row["part_id"]) or {}
    name = warehouse.get("warehouse_name") or ""
    part_name = part.get("part_name") or ""
    return (
        f"Warehouse inventory {row['warehouse_inventory_id']} warehouse {row['warehouse_id']} {name} "
        f"part {row['part_id']} {part_name} on_hand {row['quantity_on_hand']} "
        f"reserved {row['quantity_reserved']} available {row['quantity_available']}."
    )


def _job_part_demand_text(part: dict[str, str], parts: dict[str, dict[str, str]]) -> str:
    named = parts.get(part["part_id"]) or {}
    part_name = named.get("part_name") or ""
    return (
        f"Job {part['job_id']} part {part['part_id']} {part_name} "
        f"required_quantity {part['required_quantity']} allocated_quantity {part['allocated_quantity']} "
        f"job_parts status {part['status']}."
    )


def _schedule_text(row: dict[str, str]) -> str:
    return (
        f"Schedule {row['schedule_id']} date {row['date']} technician {row['technician_id']} "
        f"job {row['job_id']} start {row['start_time']} end {row['end_time']} "
        f"city {row['location_city']} status {row['status']}."
    )


def _alert_text(row: dict[str, str]) -> str:
    return (
        f"Operational alert {row['alert_id']} type {row['alert_type']} severity {row['severity']} "
        f"status {row['status']} entity {row['entity_type']} {row['entity_id']} "
        f"{row['description']} recommended_action {row['recommended_action']}."
    )


def _job_part_text(part: dict[str, str], van_id: str, quantities: dict[str, int]) -> str:
    part_id = part["part_id"]
    required = int(part["required_quantity"])
    if part_id in quantities:
        have = quantities[part_id]
        source = f"van_inventory quantity {have}"
    else:
        have = 0
        source = "no van_inventory row, quantity 0"
    short = required - have
    if short < 0:
        short = 0
    return (
        f"Job {part['job_id']} part {part_id} required_quantity {required} "
        f"van {van_id or 'none'} {source} short {short} "
        f"job_parts status {part['status']}."
    )
