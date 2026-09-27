# Synthetic engineering dataset

Generated for the Knowledge Platform Engineer persona. Everything in this folder is fictional. There are no real customers, street addresses, product serials, credentials, or personal data.

Regenerate with:

```bash
python3 scripts/generate_engineering_data.py
```

The generator builds sites, devices, components, faults, telemetry, and incidents from one in-memory model, writes the CSVs, and exits with an error if a foreign key, count, or scripted pattern check fails.

Snapshot time: 2026-09-27T16:00:00-05:00 America/Chicago.

## What was generated

| File | Role |
| --- | --- |
| engineering_sites.csv | Fictional Texas-area sites |
| devices.csv | Batteries, inverters, gateways, energy controllers, sensors |
| device_components.csv | Parts on each device |
| error_codes.csv | Engineering error catalog |
| device_faults.csv | Faults, including recurring, pre-offline, and false alarms |
| device_telemetry.csv | 20-minute samples for the devices that matter to the scenarios |
| telemetry_anomalies.csv | Windows over those samples |
| firmware_versions.csv | Catalog, including 4.2.1, 4.3.0, and 4.3.1 |
| device_firmware_history.csv | Install, failure, rollback, and pending rows |
| device_configuration.csv | Setpoints, including mismatches and one corrected limit |
| engineering_incidents.csv | Investigations |
| incident_events.csv | Chronological engineering timeline |
| engineering_tickets.csv | Work items, some still open |
| engineering_documents.csv | Guides, specs, and release notes |
| failure_analysis.csv | Causes, including one left under investigation |
| engineering_changes.csv | Firmware, hardware, configuration, and process changes |
| engineering_test_results.csv | Includes the 4.3.0 heartbeat failure and the 4.3.1 pass |
| engineering_alerts.csv | Open and closed alerts at several severities |

Narrative indexes: `engineering_demo_scenarios.md`, `engineering_test_questions.md`, and `engineering_data_dictionary.md`.

## How the tables relate

A site has a customer key and a configuration. Its battery and inverter counts are the devices of those types at the site. Each device points at that site and carries components, a firmware history, and configuration rows. Faults point at a device and an error code. Telemetry and anomalies point at a device. An anomaly can point at the fault that marks the pattern. Incidents are the engineering investigations. Their events are the timeline. Tickets, alerts, and failure analyses point back at incidents when the work belongs to one. Documents and tests point at error codes and firmware versions.

## How an engineer uses this

Start from the symptom the operator reports.

- An offline battery: open the device, then its last telemetry, thermal faults, fan component, and incident INC-001.
- A complaint that started after an update: compare `device_firmware_history.installed_at` with the first COM-214, then read the 4.2.1 and 4.3.0 release notes and the heartbeat tests.
- Repeated inverter limits: read configuration history and the power trace before and after the correction.
- A gateway that vanished: plot latency and signal strength, then check whether firmware changed.
- The same code at several sites: group by hardware revision and discharge condition.
- A thermal warning that might be false: compare the drift pack with the Copper Elm shutdown. One snaps back and stays online. The other trips and goes offline.
- An SOC step that nobody can explain yet: INC-008 stays `Under Investigation`.
- Two old contactor incidents: same symptom, different confirmed parts.
- A watch list: the three online devices in INC-012.

## Example questions

- Why did battery DEV-001 go offline?
- Did the communication problem start after the firmware update?
- What changed between firmware 4.2.1 and 4.3.0?
- Are there conflicting engineering documents?
- Which systems should engineering investigate proactively?

The full list is in `engineering_test_questions.md`.

## Assumptions

- Smaller sites may have a battery and inverter without a separate gateway, because the requested site count and device count cannot both be met if every site also has a gateway and several sensors. Fully built scenario sites do have gateways. Six of them have two sensors.
- Battery + Solar + Inverter sites use an Energy Controller (`HelioNode-30`) as the PV interface. There is no separate solar-inverter device type.
- Battery + Grid Controller sites have a battery, an energy controller, and a gateway, and no inverter.
- Non-applicable telemetry and rating fields are blank, not zero.
- Configuration keeps the pre-correction mismatch row and a later corrected row for the Limestone inverter. Other mismatches are still the running value.
- Equipment installation dates are in 2025 so September 2026 faults have history. The operational story is September 2026.
- Shared version strings such as 4.2.1 have one catalog row per device type. Sensors and energy controllers were not built for 4.3.0.
- 4.4.0 exists only as a gateway beta. No device in the field is running it.
- Scenario 8 lists hypotheses and does not confirm one.

## Disclaimer

This dataset is synthetic. It was generated for a hackathon knowledge platform. It must not be treated as operating data from a real energy or battery company.
