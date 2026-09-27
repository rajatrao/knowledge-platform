# Engineering data dictionary

Synthetic tables for the Engineer persona. Primary keys are unique inside each file. Foreign keys are enforced by `scripts/generate_engineering_data.py`.

There is no customer dimension file. `customer_id` is a shared synthetic key (`CUST-###`) on sites and devices. The fictional customer names live in the generator and in this dictionary:

- CUST-001: Copper Elm Energy
- CUST-002: Glass Creek Storage
- CUST-003: Redbud Range Power
- CUST-004: Switchgrass Cooperative
- CUST-005: Cotton Flat Energy
- CUST-006: Limestone Hold Power
- CUST-007: Owl Hollow Storage
- CUST-008: Briar DC Energy
- CUST-009: Pebble Ford Power
- CUST-010: Yellow Dock Storage

Timestamps are America/Chicago with a numeric offset. The snapshot instant is 2026-09-27T16:00:00-05:00. Date-only fields are `YYYY-MM-DD`.

Blank telemetry cells mean the metric does not apply to that device type. Batteries do not report inverter AC power. Inverters do not report pack SOC. Gateways report latency, signal strength, and operating state.

`rated_capacity_kwh` is set on batteries. `rated_power_kw` is set on batteries, inverters, and energy controllers. Gateway and sensor ratings are blank.

A device may have more than one `device_configuration` row for the same parameter. The latest `last_modified` is the running value. Older rows are retained when a mismatch was corrected.

## engineering_sites.csv

- Primary key: `site_id`
- `customer_id`: synthetic customer key
- `site_name`, `city`, `latitude`, `longitude`: fictional site in one of Austin, Round Rock, Cedar Park, Georgetown, Pflugerville, Leander. No street address.
- `system_configuration`: one of Single Battery + Single Inverter, Dual Battery + Single Inverter, Dual Battery + Dual Inverter, Battery + Solar + Inverter, Battery + Grid Controller
- `battery_capacity_kwh`, `inverter_capacity_kw`: sums of the batteries and inverters at the site
- `number_of_batteries`, `number_of_inverters`: counts of those device types at the site
- `installation_date`, `commissioning_date`, `site_status`

## devices.csv

- Primary key: `device_id`
- Foreign key: `site_id` -> engineering_sites.site_id
- `customer_id` matches the site
- `device_serial`: `SYN-` prefix, not a real product serial
- `device_type`: Battery, Inverter, Gateway, Energy Controller, Sensor
- `manufacturer`, `model`: fictional Northline, MesaVolt, CinderPeak, RioCharge, LanternGrid
- `status`: Online, Offline, Degraded, Maintenance, Faulted
- `firmware_version`: must exist in firmware_versions.csv for the same device_type
- `hardware_revision`: HW-A, HW-B, HW-C, or HW-D
- `installation_date`, `commissioning_date`, `last_seen_at`
- `rated_capacity_kwh`, `rated_power_kw`

## device_components.csv

- Primary key: `component_id`
- Foreign key: `device_id` -> devices.device_id
- `component_type`: BMS, Inverter Controller, Power Module, Cooling Fan, Temperature Sensor, Voltage Sensor, Current Sensor, Communication Module, Gateway, Relay, Contactor
- `expected_lifespan_hours`, `hardware_revision`, `serial_number` (`SYN-CMP-`), `status` (In Service, Degraded, Failed, Replaced)

## error_codes.csv

- Primary key: `error_code`
- `severity`: Info, Warning, Error, Critical
- `subsystem`: Battery, BMS, Inverter, Communications, Thermal, Grid, Gateway, Firmware
- `title`, `description`, `likely_causes`, `recommended_diagnostic_steps`
- `escalation_required`: true or false
- `known_firmware_fix`: a firmware version, or blank
- `related_component_type`

## device_faults.csv

- Primary key: `fault_id`
- Foreign keys: `device_id` -> devices; `error_code` -> error_codes; `component_id` -> device_components when set
- `timestamp`, `severity`, `fault_status` (Active, Acknowledged, Cleared, Recurring, Escalated)
- `detected_by`, `technician_id` (ENG- or TECH-, may be blank), `job_id` (may be blank)
- `cleared_at` set only when status is Cleared, `resolution`, `notes`

## device_telemetry.csv

- Primary key: `telemetry_id`
- Foreign key: `device_id` -> devices
- `timestamp` is strictly increasing per device
- `battery_soc_percent`, `battery_voltage`, `battery_current`, `battery_temperature_c`
- `inverter_power_kw`, `grid_voltage`, `grid_frequency_hz`, `dc_bus_voltage`
- `charge_rate_kw`, `discharge_rate_kw`
- `communication_latency_ms`, `signal_strength_dbm`, `operating_state`
- Only a subset of devices has telemetry. Samples are every 20 minutes from 2026-09-13 00:00 through the snapshot, or until the device goes offline.

## telemetry_anomalies.csv

- Primary key: `anomaly_id`
- Foreign key: `device_id` -> devices
- `related_fault_id` -> device_faults when set
- `start_time`, `end_time` overlap telemetry that shows the pattern
- `anomaly_type`: Temperature Spike, Voltage Instability, Current Spike, Communication Degradation, Unexpected Shutdown, SOC Anomaly, Power Drop, Frequency Anomaly, Repeated Restart, Sensor Drift
- `metric`, `expected_range`, `observed_range`, `severity`, `detected`, `notes`

## firmware_versions.csv

- Primary key: (`firmware_version`, `device_type`). The same dotted version is stored once per device type that can run it.
- `release_date`, `status` (Current, Deprecated, Beta, Rolled Back, Retired)
- `previous_version`, `release_notes`, `known_issues`, `resolved_issues`
- `required_hardware_revision`, `rollout_status`
- 4.2.1 is the previous stable image. 4.3.0 has the communications regression and is halted. 4.3.1 fixes it. 4.4.0 is a gateway beta with no field installs.

## device_firmware_history.csv

- Primary key: `deployment_id`
- Foreign keys: `device_id` -> devices; `firmware_version` must exist for that device type
- `installed_at` is chronological per device
- `installed_by`, `deployment_status` (Successful, Failed, Rolled Back, Pending)
- `previous_version` matches the prior row's `firmware_version`. The first row is blank.
- `rollback_reason` is set on rollbacks
- The device's current `firmware_version` is the latest Successful or Rolled Back row

## device_configuration.csv

- Primary key: `configuration_id`
- Foreign key: `device_id` -> devices
- `parameter_name`: Max Charge Current, Max Discharge Current, Temperature Threshold, Grid Voltage Limit, Grid Frequency Limit, SOC Minimum, SOC Maximum, Restart Delay, Communication Timeout, Inverter Power Limit
- `parameter_value`, `unit`, `expected_value`, `min_allowed`, `max_allowed`
- `last_modified`, `modified_by`, `configuration_status` (Nominal or Mismatch)
- Mismatch rows differ from the expected value. Nominal rows are equal.

## engineering_incidents.csv

- Primary key: `incident_id`
- `incident_title`, `severity`, `status` (Investigating, Mitigated, Resolved, Monitoring, Closed)
- `created_at`, `resolved_at`
- `affected_device_count`, `affected_site_count`, `primary_subsystem`
- `suspected_root_cause`, `confirmed_root_cause`, `impact`, `mitigation`, `permanent_fix`
- `firmware_related`, `related_firmware_version`

## incident_events.csv

- Primary key: `event_id`
- Foreign key: `incident_id` -> engineering_incidents
- `timestamp` is chronological per incident
- `event_type`: Alert, Investigation Started, Telemetry Reviewed, Fault Identified, Firmware Compared, Configuration Checked, Root Cause Suspected, Root Cause Confirmed, Fix Developed, Fix Deployed, Incident Resolved
- `engineer`, `description`, `evidence_reference`

## engineering_tickets.csv

- Primary key: `ticket_id`
- Foreign keys, when set: `affected_device_id` -> devices; `affected_site_id` -> engineering_sites; `related_error_code` -> error_codes; `related_incident_id` -> engineering_incidents
- `title`, `description`, `priority`, `status` (Open, Investigating, Blocked, Resolved, Closed)
- `created_at`, `assigned_engineer`, `subsystem`, `root_cause`, `resolution`, `linked_firmware_version`
- `related_incident_id` is blank only when the ticket is not tied to an incident

## engineering_documents.csv

- Primary key: `document_id`
- `title`, `document_type`, `subsystem`, `version`, `created_at`, `updated_at`, `author`, `status`, `summary`
- `applicable_device_types`, `related_error_codes`, `related_firmware_versions` are semicolon-separated. Codes and versions refer to the catalogs.
- Document types: Troubleshooting Guide, Engineering Spec, Failure Analysis, Runbook, Firmware Release Note, Architecture Document, Diagnostic Procedure, Installation Guide, Configuration Guide

## failure_analysis.csv

- Primary key: `analysis_id`
- Foreign keys: `incident_id` -> engineering_incidents; `device_id` -> devices
- `failure_mode`, `symptoms`, `contributing_factors`, `investigation_method`, `evidence`
- `root_cause`, `corrective_action`, `preventive_action`
- `confidence`: Low, Medium, High
- `analysis_date`
- For the unresolved SOC incident, `root_cause` is exactly `Under Investigation`

## engineering_changes.csv

- Primary key: `change_id`
- `title`, `change_type` (Firmware, Hardware, Configuration, Software, Manufacturing, Process)
- `subsystem`, `description`, `reason`, `created_at`, `approved_at`, `implementation_date`, `status`
- `affected_devices` semicolon-separated device ids
- `affected_firmware`, `risk_level`

## engineering_test_results.csv

- Primary key: `test_id`
- `test_name`, `device_type`, `firmware_version` (must exist for that device type)
- `test_date`, `test_environment`, `expected_result`, `actual_result`
- `result`: Pass, Fail, Blocked
- `engineer`, `related_issue`, `notes`

## engineering_alerts.csv

- Primary key: `alert_id`
- Foreign keys: `device_id` -> devices; `site_id` -> engineering_sites
- `related_error_code` -> error_codes when set; `related_incident_id` -> engineering_incidents when set
- `created_at`, `alert_type` (Thermal, Voltage, Communication, Firmware, Configuration, Repeated Fault, Device Offline, Performance Degradation)
- `severity`: Info, Warning, Error, Critical
- `metric`, `observed_value`, `threshold`, `description`, `status`, `recommended_action`

## Relationship summary

Sites own devices. Devices own components, firmware history, configuration, telemetry, and faults. Faults cite error codes. Anomalies cite devices and, when set, faults. Incidents are narrated by incident events and may be cited by tickets, alerts, and failure analyses. Documents cite error codes and firmware versions. Tests cite a firmware version for a device type. Changes cite devices and, when set, a firmware version.
