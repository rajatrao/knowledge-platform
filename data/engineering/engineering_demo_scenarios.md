# Engineering demo scenarios

Snapshot: 2026-09-27T16:00:00-05:00 America/Chicago. All identifiers are synthetic.

## 1. Thermal failure

Battery DEV-001 (Battery, Offline, firmware 4.2.1, HW-B) at SITE-001 went offline after a real temperature rise.

- Site: SITE-001 Copper Elm Node, Austin.
- Telemetry from 2026-09-26 08:00 through 14:40 shows pack temperature climbing from about 34 C to about 73 C while the pack was discharging. Earlier samples sit near 28 C.
- Warning fault THERM-110, then critical fault THERM-201 at 14:20 tied to cooling fan CMP-0003. The fan status is Failed. The pack stops reporting at 14:40 and device status is Offline.
- Anomaly ANO-001 overlaps that rise.
- Incident INC-001 is resolved. Confirmed root cause: cooling fan bearing seizure. The temperature threshold was not raised. Firmware is 4.2.1 and was ruled out.
- A field ticket remains open to install the replacement fan, so the pack is still offline in this snapshot.
- Follow DOC-001, not the conflicting threshold guide.

Supports: why this battery went offline; what the temperature did; which fault and component; the incident timeline.

## 2. Firmware regression

Several devices moved from 4.2.1 to 4.3.0 on 2026-09-15 02:00 and then raised COM-214. Signal strength stayed near -64 dBm while latency stepped from about 30 ms to about 340 ms.

- Rolled back to 4.2.1 on 2026-09-18: DEV-008 (Gateway, Online, firmware 4.2.1, HW-B) at SITE-002 and DEV-016 (Inverter, Online, firmware 4.2.1, HW-B) at SITE-005. Latency on the gateway recovered after the rollback.
- Patched to 4.3.1 on 2026-09-20: DEV-011 (Gateway, Online, firmware 4.3.1, HW-B) at SITE-003. Latency recovered after 4.3.1.
- Still on 4.3.0 with active COM-214: DEV-012 (Battery, Degraded, firmware 4.3.0, HW-B) at SITE-004 and DEV-098 (Gateway, Degraded, firmware 4.3.0, HW-B) at SITE-025.
- Incident INC-002. Firmware 4.3.0 release notes describe the heartbeat change from 4.2.1. 4.3.1 release notes describe the fix.
- Tests TEST-001 (4.3.0 Fail), TEST-002 (4.3.1 Pass), and TEST-003 (4.2.1 Pass) are the same heartbeat case.

Supports: did this start after the firmware update; what changed between 4.2.1 and 4.3.0; which devices rolled back.

## 3. Configuration mismatch

Inverter DEV-019 (Inverter, Online, firmware 4.2.1, HW-B) at SITE-006 at Limestone Yard.

- Historical configuration row: Inverter Power Limit parameter_value 75 kW, expected_value 90 kW, configuration_status Mismatch, last modified 2026-08-12.
- Corrected row: 90 kW equals expected 90 kW, last modified 2026-09-18 10:00.
- Before the correction, afternoon telemetry flatlines at 75 kW. After it, peaks reach the high 80s. Repeated INV-360 and CFG-101 faults are cleared at the correction time.
- Incident INC-003 is resolved.
- Live mismatches still open on other devices: SOC Maximum 75 versus expected 90 on DEV-006, Communication Timeout 8 s versus 30 s on DEV-014, Grid Voltage Limit 492 V versus 504 V on DEV-013.

Supports: a parameter outside the expected value, repeated inverter faults, and a correction that clears them.

## 4. Communication failure

Gateway DEV-025 (Gateway, Offline, firmware 4.2.1, HW-B) at SITE-007 at Owl Hollow Pad.

- From 2026-09-24 18:00 to 2026-09-25 02:00, latency climbs from about 48 ms toward 1750 ms and signal strength falls from about -68 dBm toward -107 dBm.
- COM-118, GW-090, then COM-101. The gateway goes offline and telemetry stops. Firmware stays 4.2.1. There is no 4.3.0 install.
- Incident INC-004. Anomaly ANO-005.
- This is a radio-path failure. The 4.3.0 regression moves latency only.

Supports: latency up, signal down, intermittent telemetry, then offline.

## 5. Repeated failure

BAT-204 on three HW-C batteries during discharge above 70 kW. One investigation.

- DEV-026 (Battery, Degraded, firmware 4.2.1, HW-C) at SITE-008
- DEV-031 (Battery, Degraded, firmware 4.2.1, HW-C) at SITE-009
- DEV-034 (Battery, Degraded, firmware 4.3.1, HW-C) at SITE-010
- Voltage on the first pack swings between about 705 V and 812 V before the fault. Normal baseline voltage is stable near 750 V.
- Incident INC-005. Confirmed cause: HW-C power-module busbar torque below spec. Firmware is not the common factor.
- Anomaly ANO-003.

Supports: same error code, same hardware revision, similar conditions, one investigation.

## 6. Sensor drift

Battery DEV-037 (Battery, Online, firmware 4.2.1, HW-B) at SITE-011 stayed online.

- From 2026-09-20 to the replacement at 2026-09-24 09:00, reported temperature climbs smoothly by more than 15 C while voltage stays inside the normal band.
- At the replacement, temperature snaps back to about 28 C in one sample. A real pack would not do that.
- False THERM-110 warnings and THERM-155. Sensor CMP-0210 is Replaced. New sensor CMP-0216 is In Service.
- Incident INC-006 is resolved. This is not INC-001.

Supports: telling a false thermal alert from the real Copper Elm shutdown.

## 7. Inverter power drop

Inverter DEV-043 (Inverter, Faulted, firmware 4.2.1, HW-B) at SITE-012.

- The sample before 2026-09-23 17:40 is about 78 kW. The next sample is about 6.5 kW, and power stays down. Grid frequency stays near 60 Hz. The DC bus sags.
- Fault INV-402. Incident INC-007. Ticket ET-032 is Blocked on the replacement power module.
- The power limit on this inverter already matched 90 kW, so this is not scenario 3.

Supports: normal power, then a sudden reduction, with a fault and a ticket.

## 8. Unknown root cause

Battery DEV-045 (Battery, Degraded, firmware 4.2.1, HW-B) at SITE-013. Incident INC-008.

- At 2026-09-21 03:20, SOC falls by about 50 points while current and charge/discharge power at that sample are near zero.
- Fault BAT-330 is Active. Confirmed root cause is exactly "Under Investigation".
- Unconfirmed hypotheses only: SOC estimator bias, current-sensor offset, standby parasitic load.
- Tickets ET-033 and ET-034 are open. There is no Root Cause Confirmed event and no permanent fix.
- Firmware is 4.2.1, the same as healthy peers. Do not treat a hypothesis as the cause.

Supports: a clear symptom with more than one possible cause, still unresolved.

## 9. Similar history, different causes

Both incidents are titled "Contactor opened during discharge". The symptom text matches: the main contactor opened during a routine discharge, with no thermal alarm and no firmware change in the prior 7 days.

- INC-009 on DEV-048 (Battery, Online, firmware 4.3.1, HW-D) at SITE-014. Confirmed cause: contactor coil driver failed (REL-204, coil current zero).
- INC-010 on DEV-051 (Battery, Online, firmware 4.2.1, HW-B) at SITE-015. Confirmed cause: precharge resistor open (REL-210, coil current present, DC bus did not rise).

Supports: similar incidents with different confirmed root causes.

## 10. Proactive investigation

None of these devices has failed. Status is Online. Incident INC-012 is Monitoring.

- DEV-054 (Battery, Online, firmware 4.2.1, HW-B) at SITE-016: temperature sits near 40 C, below the 60 C trip. Warning only.
- DEV-061 (Gateway, Online, firmware 4.2.1, HW-B) at SITE-017: latency climbs from about 42 ms toward about 140 ms. RSSI stays stable. Firmware is not 4.3.0.
- DEV-062 (Battery, Online, firmware 4.3.1, HW-B) at SITE-018: four isolated BMS-218 watchdog restarts, then the pack returns.

Supports: which systems engineering should investigate before they fail.

## 11. Grid frequency excursion

Inverter DEV-066 (Inverter, Faulted, firmware 4.2.1, HW-B) at SITE-019. Incident INC-011.

Frequency reaches 61.28 Hz at 2026-09-25 13:40, power goes to zero, frequency returns, and the INV-201 latch holds power at zero. This is not the power-module collapse in scenario 7.

## 12. Conflicting documents

DOC-001 THERM-201 Protective Shutdown Runbook says to replace the cooling fan and not to raise the temperature threshold.

DOC-002 Field Configuration Guide: Thermal Thresholds says to raise the threshold by 10 C and treats fan replacement as optional.

Both are Published. They disagree on THERM-201.

## 13. Shared failure mode

Two later incidents, separate from the scenarios above, share the confirmed root cause "DC bus capacitor ESR rise on the inverter power module" and error INV-305. They are a different shared mode from the HW-C BAT-204 cluster.

## Question map

| Scenario | Questions |
| --- | --- |
| 1 Thermal | 1-6, 29, 30, 34, 42, 50 |
| 2 Firmware | 7-11, 31, 32, 36, 37, 43, 49 |
| 3 Configuration | 12-14, 44 |
| 4 Communication | 15-16 |
| 5 Repeated HW-C | 17-18, 39, 47 |
| 6 Sensor drift | 19-20, 45 |
| 7 Power drop | 21-22 |
| 8 Unknown | 23-24, 46 |
| 9 Similar history | 25 |
| 10 Proactive | 26-27, 33 |
| Documents | 28-29 |
| Extra frequency and shared capacitor mode | 40-41, 48 |
