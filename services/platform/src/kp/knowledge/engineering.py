"""Engineering rows read from data/engineering at ask time.

Telemetry is not copied in full. A telemetry question gets the device summary
and a short window around the fault.
"""

from __future__ import annotations

import csv
import re
from datetime import datetime, timedelta
from pathlib import Path

from kp.config import get_settings
from kp.knowledge.retrieve import Bundle, _normalized_query, _outage_query

ENGINEERING_KIND = "engineering"

_INCIDENT_IDS: set[str] | None = None


def engineering_root() -> Path:
    return Path(get_settings().repo_root) / "data" / "engineering"


def engineering_query(query: str) -> bool:
    """Device, fault, firmware, and engineering-incident questions."""
    text = _normalized_query(query)
    if _blocks_engineering(text):
        return False
    if re.search(r"\bcomplaints?\b", text):
        return _specific_engineering_id(text)
    return _hard_engineering_signal(text)


def _specific_engineering_id(text: str) -> bool:
    if re.search(r"\bdev-\d{3}\b", text) or re.search(r"\bflt-\d+\b", text):
        return True
    if re.search(r"\b\d+\.\d+\.\d+\b", text):
        return True
    if re.search(r"\binc-\d{3}\b", text) and any(incident_id.casefold() in text for incident_id in _known_incidents()):
        return True
    return False


def include_engineering_records(bundle: Bundle, query: str) -> None:
    """Prepend matching engineering rows so synthesis quotes them."""
    text = _normalized_query(query)
    if not engineering_query(text):
        return
    selected = _select(text)
    if not selected:
        return
    _prepend(bundle, selected)


def records_for_ids(device_ids: list[str], incident_ids: list[str]) -> list[tuple[str, str, str]]:
    """Rows for a CEO drill-down that already names these ids."""
    hint = " ".join(device_ids + incident_ids)
    if not hint.strip():
        return []
    return _select(_normalized_query(hint))


def _blocks_engineering(text: str) -> bool:
    if _outage_query(text):
        return True
    if "revenue" in text or "forecast" in text:
        return True
    return False


def _hard_engineering_signal(text: str) -> bool:
    if re.search(r"\bdev-\d{3}\b", text):
        return True
    if re.search(r"\bflt-\d+\b", text):
        return True
    if re.search(r"\b\d+\.\d+\.\d+\b", text):
        return True
    if any(incident_id.casefold() in text for incident_id in _known_incidents()):
        if re.search(r"\binc-\d{3}\b", text):
            return True
    if re.search(
        r"\b(telemetry|anomal(?:y|ies)|firmware|device faults?|error codes?|engineering documents?)\b",
        text,
    ):
        return True
    if re.search(r"\b(offline|degraded|faulted)\b", text) and re.search(
        r"\b(device|battery|inverter|gateway|pack)\b", text
    ):
        return True
    return False


def _known_incidents() -> set[str]:
    global _INCIDENT_IDS
    if _INCIDENT_IDS is None:
        _INCIDENT_IDS = {row["incident_id"] for row in _rows("engineering_incidents.csv") if row.get("incident_id")}
    return _INCIDENT_IDS


def _prepend(bundle: Bundle, selected: list[tuple[str, str, str]]) -> None:
    existing = list(bundle.records.items())
    bundle.records.clear()
    for record_id, body, document_id in selected:
        bundle.add(ENGINEERING_KIND, record_id, body, document_id)
    for key, value in existing:
        bundle.records.setdefault(key, value)


def _rows(filename: str) -> list[dict[str, str]]:
    path = engineering_root() / filename
    if not path.is_file():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _indexed(filename: str, key: str) -> dict[str, dict[str, str]]:
    return {row[key]: row for row in _rows(filename) if row.get(key)}


def _unique(values: list[str]) -> list[str]:
    found: list[str] = []
    for value in values:
        token = value.upper()
        if token and token not in found:
            found.append(token)
    return found


def _parse_ts(value: str) -> datetime | None:
    text = (value or "").strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _select(text: str) -> list[tuple[str, str, str]]:
    device_ids = _unique(re.findall(r"\bdev-\d{3}\b", text))
    versions = _unique(re.findall(r"\b\d+\.\d+\.\d+\b", text))
    incident_ids = [token for token in _unique(re.findall(r"\binc-\d{3}\b", text)) if token in _known_incidents()]
    analyses = _rows("failure_analysis.csv")
    if incident_ids and not device_ids:
        for row in analyses:
            if row.get("incident_id") in incident_ids and row.get("device_id"):
                device_ids.append(row["device_id"])
        device_ids = _unique(device_ids)
    if device_ids and not incident_ids:
        for row in analyses:
            if row.get("device_id") in device_ids and row.get("incident_id") in _known_incidents():
                incident_ids.append(row["incident_id"])
        incident_ids = _unique(incident_ids)
    if versions and not incident_ids:
        for row in _rows("engineering_incidents.csv"):
            if (row.get("related_firmware_version") or "") in versions:
                incident_ids.append(row["incident_id"])
        incident_ids = _unique(incident_ids)[:4]
        for row in analyses:
            if row.get("incident_id") in incident_ids and row.get("device_id"):
                device_ids.append(row["device_id"])
        device_ids = _unique(device_ids)

    if not device_ids and not versions and not incident_ids:
        return []

    devices = _indexed("devices.csv", "device_id")
    sites = _indexed("engineering_sites.csv", "site_id")
    records: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    def add(record_id: str, body: str, document_id: str) -> None:
        if not record_id or record_id in seen:
            return
        seen.add(record_id)
        records.append((record_id, _clip(body), document_id))

    if versions:
        for row in _rows("firmware_versions.csv"):
            if row.get("firmware_version") in versions:
                add(
                    f"{row['firmware_version']}-{row['device_type']}",
                    _firmware_text(row),
                    "firmware_versions.csv",
                )
        _add_version_devices(add, versions, devices, sites, device_ids)

    for device_id in device_ids[:8]:
        row = devices.get(device_id)
        if not row:
            continue
        site = sites.get(row.get("site_id") or "")
        add(device_id, _device_text(row, site), "devices.csv")
        if not versions and row.get("firmware_version"):
            for firmware in _rows("firmware_versions.csv"):
                if firmware.get("firmware_version") == row["firmware_version"] and firmware.get("device_type") == row.get("device_type"):
                    add(
                        f"{firmware['firmware_version']}-{firmware['device_type']}",
                        _firmware_text(firmware),
                        "firmware_versions.csv",
                    )

    fault_rows = [row for row in _rows("device_faults.csv") if row.get("device_id") in device_ids]
    components = _indexed("device_components.csv", "component_id")
    codes = _indexed("error_codes.csv", "error_code")
    for row in fault_rows[:8]:
        add(row["fault_id"], _fault_text(row), "device_faults.csv")
        component = components.get(row.get("component_id") or "")
        if component:
            add(component["component_id"], _component_text(component), "device_components.csv")
        code = codes.get(row.get("error_code") or "")
        if code:
            add(code["error_code"], _error_text(code), "error_codes.csv")

    for row in _rows("telemetry_anomalies.csv"):
        if row.get("device_id") in device_ids:
            add(row["anomaly_id"], _anomaly_text(row), "telemetry_anomalies.csv")
        if sum(1 for record_id, _, document_id in records if document_id == "telemetry_anomalies.csv") >= 3:
            break

    for row in analyses:
        if row.get("device_id") in device_ids or row.get("incident_id") in incident_ids:
            add(row["analysis_id"], _analysis_text(row), "failure_analysis.csv")

    incidents = _indexed("engineering_incidents.csv", "incident_id")
    for incident_id in incident_ids[:4]:
        row = incidents.get(incident_id)
        if row:
            add(incident_id, _incident_text(row), "engineering_incidents.csv")
    events = [row for row in _rows("incident_events.csv") if row.get("incident_id") in incident_ids]
    cause_events = [row for row in events if "root cause" in (row.get("event_type") or "").casefold()]
    other_events = [row for row in events if row not in cause_events]
    for row in (cause_events + other_events[-4:])[:8]:
        add(row["event_id"], _event_text(row), "incident_events.csv")

    ticket_count = 0
    for row in _rows("engineering_tickets.csv"):
        if row.get("affected_device_id") in device_ids or row.get("related_incident_id") in incident_ids:
            add(row["ticket_id"], _ticket_text(row), "engineering_tickets.csv")
            ticket_count += 1
        if ticket_count >= 4:
            break

    if versions or re.search(r"\b(documents?|doc-\d+)\b", text):
        doc_count = 0
        for row in _rows("engineering_documents.csv"):
            blob = " ".join(row.values()).casefold()
            if any(version.casefold() in blob for version in versions) or (row.get("document_id") or "").casefold() in text:
                add(row["document_id"], _document_text(row), "engineering_documents.csv")
                doc_count += 1
            if doc_count >= 3:
                break

    if versions:
        test_count = 0
        for row in _rows("engineering_test_results.csv"):
            if row.get("firmware_version") in versions:
                add(row["test_id"], _test_text(row), "engineering_test_results.csv")
                test_count += 1
            if test_count >= 4:
                break

    if _wants_telemetry(text):
        for device_id in device_ids[:2]:
            anchor = _fault_anchor(fault_rows, device_id)
            for row in _telemetry_window(device_id, anchor):
                add(row["telemetry_id"], _telemetry_text(row), "device_telemetry.csv")
    return records


def _add_version_devices(add, versions: list[str], devices: dict[str, dict[str, str]], sites, already: list[str]) -> None:
    for version in versions:
        matched = [row for row in devices.values() if row.get("firmware_version") == version]
        matched.sort(key=lambda row: (0 if row.get("status") in {"Offline", "Degraded", "Faulted"} else 1, row["device_id"]))
        for row in matched[:4]:
            if row["device_id"] in already:
                continue
            site = sites.get(row.get("site_id") or "")
            add(row["device_id"], _device_text(row, site), "devices.csv")


def _wants_telemetry(text: str) -> bool:
    return bool(re.search(r"\b(telemetry|temperature|latency|soc|signal|voltage|current|trace)\b", text))


def _fault_anchor(fault_rows: list[dict[str, str]], device_id: str) -> datetime | None:
    stamps = [
        _parse_ts(row.get("timestamp") or "")
        for row in fault_rows
        if row.get("device_id") == device_id and _parse_ts(row.get("timestamp") or "")
    ]
    if not stamps:
        return None
    return max(stamps)


def _telemetry_window(device_id: str, anchor: datetime | None) -> list[dict[str, str]]:
    path = engineering_root() / "device_telemetry.csv"
    if not path.is_file():
        return []
    matched: list[dict[str, str]] = []
    with path.open(newline="", encoding="utf-8") as handle:
        for row in csv.DictReader(handle):
            if row.get("device_id") == device_id:
                matched.append(dict(row))
    if not matched:
        return []
    if anchor is None:
        return matched[-6:]
    start = anchor - timedelta(hours=6)
    end = anchor + timedelta(hours=1)
    window = []
    for row in matched:
        stamp = _parse_ts(row.get("timestamp") or "")
        if stamp is None or stamp < start or stamp > end:
            continue
        window.append((abs((stamp - anchor).total_seconds()), row))
    window.sort(key=lambda item: item[0])
    chosen = [row for _, row in window[:12]]
    chosen.sort(key=lambda row: row.get("timestamp") or "")
    return chosen


def _clip(body: str) -> str:
    text = " ".join(body.split())
    if len(text) > 900:
        return text[:897] + "..."
    return text


def _device_text(row: dict[str, str], site: dict[str, str] | None) -> str:
    site = site or {}
    return (
        f"Device {row['device_id']} type {row['device_type']} status {row['status']} "
        f"firmware {row['firmware_version']} hardware {row['hardware_revision']} "
        f"site {row['site_id']} {site.get('site_name', '')} city {site.get('city', '')} "
        f"last_seen {row['last_seen_at']}."
    )


def _firmware_text(row: dict[str, str]) -> str:
    return (
        f"Firmware {row['firmware_version']} device_type {row['device_type']} status {row['status']} "
        f"previous_version {row.get('previous_version', '')} rollout_status {row.get('rollout_status', '')}. "
        f"release_notes {row.get('release_notes', '')} known_issues {row.get('known_issues', '')} "
        f"resolved_issues {row.get('resolved_issues', '')}."
    )


def _fault_text(row: dict[str, str]) -> str:
    return (
        f"Fault {row['fault_id']} device {row['device_id']} at {row['timestamp']} "
        f"error_code {row['error_code']} severity {row['severity']} status {row['fault_status']} "
        f"component {row.get('component_id', '')} resolution {row.get('resolution', '')} "
        f"notes {row.get('notes', '')}."
    )


def _component_text(row: dict[str, str]) -> str:
    return (
        f"Component {row['component_id']} device {row['device_id']} type {row['component_type']} "
        f"status {row['status']}."
    )


def _error_text(row: dict[str, str]) -> str:
    return (
        f"Error code {row['error_code']} {row.get('title', '')} severity {row.get('severity', '')} "
        f"subsystem {row.get('subsystem', '')}. Catalog text is not a confirmed root cause."
    )


def _anomaly_text(row: dict[str, str]) -> str:
    return (
        f"Anomaly {row['anomaly_id']} device {row['device_id']} type {row['anomaly_type']} "
        f"metric {row['metric']} from {row['start_time']} to {row['end_time']} "
        f"observed {row.get('observed_range', '')} expected {row.get('expected_range', '')} "
        f"notes {row.get('notes', '')}."
    )


def _analysis_text(row: dict[str, str]) -> str:
    return (
        f"Failure analysis {row['analysis_id']} incident {row['incident_id']} device {row['device_id']} "
        f"root_cause {row.get('root_cause', '')}. symptoms {row.get('symptoms', '')} "
        f"contributing_factors {row.get('contributing_factors', '')}."
    )


def _incident_text(row: dict[str, str]) -> str:
    return (
        f"Incident {row['incident_id']} status {row['status']} "
        f"confirmed_root_cause {row.get('confirmed_root_cause', '')}. "
        f"suspected_root_cause {row.get('suspected_root_cause', '')}. "
        f"title {row.get('incident_title', '')}. impact {row.get('impact', '')}. "
        f"firmware_related {row.get('firmware_related', '')} "
        f"related_firmware_version {row.get('related_firmware_version', '')}."
    )


def _event_text(row: dict[str, str]) -> str:
    return (
        f"Incident event {row['event_id']} incident {row['incident_id']} at {row['timestamp']} "
        f"type {row['event_type']}. {row.get('description', '')}."
    )


def _ticket_text(row: dict[str, str]) -> str:
    return (
        f"Ticket {row['ticket_id']} status {row['status']} device {row.get('affected_device_id', '')} "
        f"incident {row.get('related_incident_id', '')} root_cause {row.get('root_cause', '')}. "
        f"{row.get('title', '')}. {row.get('description', '')}."
    )


def _document_text(row: dict[str, str]) -> str:
    return (
        f"Engineering document {row['document_id']} {row.get('title', '')} "
        f"type {row.get('document_type', '')} status {row.get('status', '')}. "
        f"{row.get('summary', '')}."
    )


def _test_text(row: dict[str, str]) -> str:
    return (
        f"Test {row['test_id']} {row.get('test_name', '')} firmware {row.get('firmware_version', '')} "
        f"result {row.get('result', '')}. expected {row.get('expected_result', '')} "
        f"actual {row.get('actual_result', '')}."
    )


def _telemetry_text(row: dict[str, str]) -> str:
    bits = [f"Telemetry {row['telemetry_id']} device {row['device_id']} at {row['timestamp']}"]
    for key in (
        "battery_soc_percent",
        "battery_temperature_c",
        "battery_voltage",
        "battery_current",
        "inverter_power_kw",
        "communication_latency_ms",
        "signal_strength_dbm",
        "operating_state",
        "discharge_rate_kw",
        "charge_rate_kw",
    ):
        if row.get(key):
            bits.append(f"{key} {row[key]}")
    return " ".join(bits) + "."
