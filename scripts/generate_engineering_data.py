#!/usr/bin/env python3
"""Generate a synthetic, internally consistent engineering dataset.

All rows are fictional. Snapshot time is 2026-09-27 16:00 America/Chicago.
Run: python3 scripts/generate_engineering_data.py
"""

from __future__ import annotations

import csv
import math
import statistics
import sys
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

try:
    from zoneinfo import ZoneInfo

    TZ = ZoneInfo("America/Chicago")
except Exception:  # pragma: no cover
    TZ = timezone(timedelta(hours=-5))

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "engineering"

NOW = datetime(2026, 9, 27, 16, 0, tzinfo=TZ)
TEL_START = datetime(2026, 9, 13, 0, 0, tzinfo=TZ)
STEP = timedelta(minutes=20)

FW_UPGRADE = datetime(2026, 9, 15, 2, 0, tzinfo=TZ)
FW_ROLLBACK = datetime(2026, 9, 18, 11, 0, tzinfo=TZ)
FW_PATCH = datetime(2026, 9, 20, 6, 0, tzinfo=TZ)
CONFIG_BAD = datetime(2026, 8, 12, 9, 30, tzinfo=TZ)
CONFIG_FIX = datetime(2026, 9, 18, 10, 0, tzinfo=TZ)

THERMAL_RAMP_START = datetime(2026, 9, 26, 8, 0, tzinfo=TZ)
THERMAL_WARN = datetime(2026, 9, 26, 11, 0, tzinfo=TZ)
THERMAL_FAULT = datetime(2026, 9, 26, 14, 20, tzinfo=TZ)
THERMAL_OFFLINE = datetime(2026, 9, 26, 14, 40, tzinfo=TZ)

VOLT_WINDOWS = [
    (datetime(2026, 9, 16, 10, 0, tzinfo=TZ), datetime(2026, 9, 16, 14, 0, tzinfo=TZ)),
    (datetime(2026, 9, 19, 10, 0, tzinfo=TZ), datetime(2026, 9, 19, 14, 0, tzinfo=TZ)),
    (datetime(2026, 9, 22, 9, 0, tzinfo=TZ), datetime(2026, 9, 22, 13, 20, tzinfo=TZ)),
]
VOLT_FAULTS = [
    datetime(2026, 9, 16, 13, 40, tzinfo=TZ),
    datetime(2026, 9, 19, 13, 40, tzinfo=TZ),
    datetime(2026, 9, 22, 13, 0, tzinfo=TZ),
]

COMM_START = datetime(2026, 9, 24, 18, 0, tzinfo=TZ)
COMM_WARN = datetime(2026, 9, 24, 23, 0, tzinfo=TZ)
COMM_FAULT = datetime(2026, 9, 25, 1, 40, tzinfo=TZ)
COMM_OFFLINE = datetime(2026, 9, 25, 2, 0, tzinfo=TZ)

SOC_STEP = datetime(2026, 9, 21, 3, 20, tzinfo=TZ)
POWER_DROP = datetime(2026, 9, 23, 17, 40, tzinfo=TZ)
FREQ_START = datetime(2026, 9, 25, 13, 20, tzinfo=TZ)
FREQ_PEAK = datetime(2026, 9, 25, 13, 40, tzinfo=TZ)
FREQ_RECOVER = datetime(2026, 9, 25, 14, 20, tzinfo=TZ)

DRIFT_START = datetime(2026, 9, 20, 0, 0, tzinfo=TZ)
DRIFT_REPLACE = datetime(2026, 9, 24, 9, 0, tzinfo=TZ)
DRIFT_FAULTS = [
    datetime(2026, 9, 21, 16, 0, tzinfo=TZ),
    datetime(2026, 9, 22, 11, 20, tzinfo=TZ),
    datetime(2026, 9, 23, 18, 40, tzinfo=TZ),
]

PRO_TEMP_START = datetime(2026, 9, 22, 0, 0, tzinfo=TZ)
PRO_LAT_START = datetime(2026, 9, 20, 0, 0, tzinfo=TZ)
CURRENT_SPIKE = datetime(2026, 9, 15, 4, 20, tzinfo=TZ)

UNDER = "Under Investigation"

CITIES = {
    "Austin": (30.2672, -97.7431),
    "Round Rock": (30.5083, -97.6789),
    "Cedar Park": (30.5052, -97.8203),
    "Georgetown": (30.6333, -97.6770),
    "Pflugerville": (30.4394, -97.6200),
    "Leander": (30.5788, -97.8531),
}

CUSTOMERS = [
    ("CUST-001", "Copper Elm Energy"),
    ("CUST-002", "Glass Creek Storage"),
    ("CUST-003", "Redbud Range Power"),
    ("CUST-004", "Switchgrass Cooperative"),
    ("CUST-005", "Cotton Flat Energy"),
    ("CUST-006", "Limestone Hold Power"),
    ("CUST-007", "Owl Hollow Storage"),
    ("CUST-008", "Briar DC Energy"),
    ("CUST-009", "Pebble Ford Power"),
    ("CUST-010", "Yellow Dock Storage"),
]

SITE_NAMES = [
    "Copper Elm Node",
    "Glass Creek Yard",
    "Redbud Range Pad",
    "Switchgrass Hold",
    "Cotton Flat Node",
    "Limestone Yard",
    "Owl Hollow Pad",
    "Briar DC Node",
    "Pebble Ford Yard",
    "Yellow Dock Hold",
    "Blue Sage Node",
    "Warm Spring Yard",
    "High Lamp Pad",
    "Little Brake Node",
    "Open Cinder Yard",
    "Stonewater Hold",
    "Clear Fork Node",
    "North Mesa Yard",
    "Lantern Field Pad",
    "Cinder Flat Node",
    "Dry Sage Yard",
    "Bright Lug Hold",
    "West Arroyo Node",
    "East Arroyo Yard",
    "Helio Bench Pad",
    "South Helio Node",
    "North Helio Yard",
    "Helio Spur Hold",
    "BusTie North Node",
    "BusTie South Yard",
    "BusTie East Pad",
    "BusTie West Hold",
    "Compact Elm One",
    "Compact Elm Two",
    "Compact Creek Three",
    "Compact Creek Four",
    "Compact Range Five",
    "Compact Range Six",
    "Compact Hold Seven",
    "Compact Hold Eight",
    "Compact Flat Nine",
    "Compact Flat Ten",
    "Compact Sage Eleven",
    "Compact Sage Twelve",
]

CONFIG_SHAPE = {
    "Single Battery + Single Inverter": (1, 1, 0),
    "Dual Battery + Single Inverter": (2, 1, 0),
    "Dual Battery + Dual Inverter": (2, 2, 0),
    "Battery + Solar + Inverter": (1, 1, 1),
    "Battery + Grid Controller": (1, 0, 1),
}

HW_RANK = {"HW-A": 1, "HW-B": 2, "HW-C": 3, "HW-D": 4}

# Component kits by device type. (type, lifespan hours)
KITS = {
    "Battery": [
        ("BMS", 87600),
        ("Power Module", 60000),
        ("Cooling Fan", 35000),
        ("Temperature Sensor", 50000),
        ("Voltage Sensor", 50000),
        ("Current Sensor", 50000),
        ("Communication Module", 70000),
        ("Relay", 40000),
        ("Contactor", 40000),
    ],
    "Inverter": [
        ("Inverter Controller", 70000),
        ("Power Module", 60000),
        ("Cooling Fan", 35000),
        ("Temperature Sensor", 50000),
        ("Voltage Sensor", 50000),
        ("Current Sensor", 50000),
        ("Communication Module", 70000),
        ("Relay", 40000),
    ],
    "Gateway": [
        ("Gateway", 80000),
        ("Communication Module", 70000),
        ("Temperature Sensor", 50000),
    ],
    "Energy Controller": [
        ("Inverter Controller", 70000),
        ("Communication Module", 70000),
        ("Voltage Sensor", 50000),
        ("Relay", 40000),
    ],
    "Sensor": [
        ("Temperature Sensor", 50000),
    ],
}

BATTERY_PARAMS = [
    ("Max Charge Current", "120", "A", "0", "150"),
    ("Max Discharge Current", "120", "A", "0", "150"),
    ("Temperature Threshold", "60", "C", "45", "70"),
    ("SOC Minimum", "10", "%", "5", "20"),
    ("SOC Maximum", "95", "%", "80", "100"),
    ("Restart Delay", "30", "s", "5", "300"),
    ("Communication Timeout", "30", "s", "5", "120"),
]
INVERTER_PARAMS = [
    ("Grid Voltage Limit", "504", "V", "450", "530"),
    ("Grid Frequency Limit", "0.5", "Hz", "0.2", "1.0"),
    ("Inverter Power Limit", "90", "kW", "10", "90"),
    ("Restart Delay", "60", "s", "5", "300"),
    ("Communication Timeout", "30", "s", "5", "120"),
    ("Temperature Threshold", "70", "C", "50", "85"),
]
GATEWAY_PARAMS = [
    ("Communication Timeout", "30", "s", "5", "120"),
    ("Restart Delay", "15", "s", "5", "300"),
]
EC_PARAMS = [
    ("Grid Voltage Limit", "504", "V", "450", "530"),
    ("Grid Frequency Limit", "0.5", "Hz", "0.2", "1.0"),
    ("Communication Timeout", "30", "s", "5", "120"),
]
SENSOR_PARAMS = [
    ("Temperature Threshold", "60", "C", "45", "70"),
]
PARAMS_BY_TYPE = {
    "Battery": BATTERY_PARAMS,
    "Inverter": INVERTER_PARAMS,
    "Gateway": GATEWAY_PARAMS,
    "Energy Controller": EC_PARAMS,
    "Sensor": SENSOR_PARAMS,
}


def at(y, m, d, hh=0, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=TZ)


def fmt(ts):
    if ts is None:
        return ""
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=TZ)
    local = ts.astimezone(TZ)
    return local.strftime("%Y-%m-%dT%H:%M:%S") + local.strftime("%z")[:3] + ":" + local.strftime("%z")[3:]


def parse(value):
    if not value:
        return None
    raw = value.replace("Z", "+00:00")
    return datetime.fromisoformat(raw)


def day_str(ts):
    return ts.astimezone(TZ).strftime("%Y-%m-%d")


def clamp(value, lo, hi):
    return max(lo, min(hi, value))


def unit_noise(i, salt):
    x = math.sin(i * 12.9898 + salt * 78.233) * 43758.5453
    return x - math.floor(x)


def noise(i, salt, scale):
    return (unit_noise(i, salt) - 0.5) * 2 * scale


def lerp(ts, t0, t1, v0, v1):
    if ts <= t0:
        return v0
    if ts >= t1:
        return v1
    span = (t1 - t0).total_seconds()
    return v0 + (ts - t0).total_seconds() / span * (v1 - v0)


def num(value):
    return "" if value is None or value == "" else f"{value:.2f}"


def num3(value):
    return "" if value is None or value == "" else f"{value:.3f}"


def timestamps(start, end):
    out = []
    cursor = start
    while cursor <= end:
        out.append(cursor)
        cursor += STEP
    return out


class World:
    def __init__(self):
        self.sites = []
        self.devices = []
        self.components = []
        self.errors = []
        self.faults = []
        self.telemetry = []
        self.anomalies = []
        self.firmware = []
        self.fw_history = []
        self.configs = []
        self.incidents = []
        self.events = []
        self.tickets = []
        self.documents = []
        self.analyses = []
        self.changes = []
        self.tests = []
        self.alerts = []
        self.device_meta = {}
        self.site_meta = {}
        self.named = {}
        self.components_by_device = defaultdict(list)

    def add_device_alias(self, key, device):
        self.named[key] = device["device_id"]
        self.device_meta[device["device_id"]]["alias"] = key


def fail(message):
    raise SystemExit(f"VALIDATION FAILED: {message}")


def check(condition, message):
    if not condition:
        fail(message)


# ---------------------------------------------------------------------------
# Catalogs
# ---------------------------------------------------------------------------

def error_catalog():
    rows = [
        ("BAT-101", "Warning", "Battery", "Cell delta elevated during charge",
         "One cell group is more than 30 mV from the pack median while charging.",
         "Uneven cell aging; balancer duty cycle too low; loose sense lead",
         "1) Compare group voltages in the BMS snapshot. 2) Confirm the balancer is running. 3) Reseat the sense harness if the delta is on one channel only.",
         "false", "", "Voltage Sensor"),
        ("BAT-102", "Info", "Battery", "Charge complete",
         "The pack reached the configured SOC maximum and charge current tapered to standby.",
         "Normal end of charge",
         "1) Confirm SOC matches the coulomb count. 2) No field action if the taper was controlled.",
         "false", "", "BMS"),
        ("BAT-118", "Warning", "Battery", "SOC residual above estimate band",
         "The SOC estimator and the coulomb counter differ by more than 8 points.",
         "Current sensor offset; estimator bias after a partial cycle; stale voltage reference",
         "1) Rest the pack for 20 minutes and compare open-circuit voltage to SOC. 2) Check current-sensor zero. 3) Do not recalibrate until the residual repeats.",
         "false", "", "Current Sensor"),
        ("BAT-141", "Warning", "Battery", "Charge rate limited by temperature",
         "The BMS reduced charge current because pack temperature entered the derate band.",
         "High ambient; cooling airflow low; sustained charge",
         "1) Read pack temperature and the cooling command. 2) Confirm inlet air path. 3) Compare with the site sensor.",
         "false", "", "Cooling Fan"),
        ("BAT-204", "Error", "Battery", "Cell group voltage imbalance",
         "A cell group diverged by more than 80 mV under discharge above 70 kW.",
         "HW-C power-module busbar torque below spec; cell group connection resistance; voltage sense drift",
         "1) Capture group voltages at the next discharge above 70 kW. 2) Compare hardware revision. 3) Torque-check the HW-C busbar before replacing cells.",
         "true", "", "Power Module"),
        ("BAT-217", "Warning", "Battery", "Charge current above setpoint",
         "Charge current exceeded the configured max for one sample and then returned.",
         "Transient setpoint overshoot; current sensor spike; charger handshake glitch",
         "1) Check whether the spike lasted more than one sample. 2) Compare current sensor to the inverter DC reading. 3) Clear if it does not repeat.",
         "false", "", "Current Sensor"),
        ("BAT-330", "Error", "Battery", "Unexpected SOC step",
         "Reported SOC changed by more than 25 points without a matching charge or discharge energy.",
         "Unconfirmed: SOC estimator bias; current-sensor offset; unmetered standby load",
         "1) Compare SOC to integrated current across the step. 2) Check firmware against peers. 3) Do not declare a cause until a second instrument agrees.",
         "true", "", "BMS"),
        ("BAT-340", "Critical", "Battery", "Contactor opened under load",
         "The main contactor opened while discharge current was above 20 A.",
         "Contactor coil driver fault; precharge circuit open; protection latch",
         "1) Read the contactor coil current at the trip. 2) Check precharge voltage rise time. 3) Leave the pack open until the driver or precharge part is identified.",
         "true", "", "Contactor"),
        ("BMS-104", "Info", "BMS", "Cell balancing active",
         "The BMS enabled passive balancing on one or more cell groups.",
         "Normal balancing after a charge",
         "1) Confirm balance current is inside the BMS spec. 2) No action if group delta is falling.",
         "false", "", "BMS"),
        ("BMS-210", "Warning", "BMS", "BMS temperature channels disagree",
         "Two BMS temperature channels differ by more than 6 C while current is below 10 A.",
         "Sensor drift; harness resistance; real local hotspot",
         "1) Compare both channels to the pack current. 2) A drift case stays high at zero current. 3) A hotspot rises with current.",
         "false", "", "Temperature Sensor"),
        ("BMS-218", "Warning", "BMS", "BMS watchdog restart",
         "The BMS watchdog reset the controller and the pack returned to the previous state within one minute.",
         "Supply dip; firmware task overrun; noise on the reset line",
         "1) Count restarts in 24 hours. 2) Check the 12 V rail. 3) Escalate if more than three restarts occur in a day.",
         "false", "", "BMS"),
        ("BMS-301", "Error", "BMS", "Cell voltage sense channel stale",
         "A voltage sense channel missed three updates.",
         "Sense harness; BMS analog front end; connector fretting",
         "1) Identify the stale channel. 2) Swap the sense lead to a known-good port if the procedure allows. 3) Replace the harness before the BMS board.",
         "true", "", "Voltage Sensor"),
        ("BMS-330", "Critical", "BMS", "BMS safety latch",
         "The BMS latched a safety output and opened the contactors.",
         "Real protection event; failed safety input; firmware latch bug",
         "1) Read the latch source bit. 2) Do not clear the latch until telemetry around the bit is saved.",
         "true", "", "BMS"),
        ("INV-109", "Info", "Inverter", "Inverter online",
         "The inverter completed precharge and closed its AC contactor.",
         "Normal start",
         "1) Confirm grid voltage and frequency are inside limits. 2) No action.",
         "false", "", "Inverter Controller"),
        ("INV-201", "Error", "Inverter", "Inverter protection latch",
         "The inverter latched offline after a protection comparison failed.",
         "Grid excursion; hardware trip; nuisance comparison after a firmware change",
         "1) Read the latch reason. 2) Compare grid frequency and voltage in the minute before the latch. 3) Leave the latch set if the grid trace is still outside limits.",
         "true", "", "Inverter Controller"),
        ("INV-214", "Warning", "Inverter", "Inverter thermal derate",
         "AC output was reduced because the inverter heat sink crossed the derate threshold.",
         "Blocked airflow; high ambient; fan wear",
         "1) Compare heat-sink temperature to power. 2) Inspect the inverter fan. 3) Derate is expected only above the configured temperature threshold.",
         "false", "", "Cooling Fan"),
        ("INV-250", "Warning", "Inverter", "Restart delay active",
         "The inverter is waiting out the configured restart delay before reconnecting.",
         "Recent trip; configured delay; operator command",
         "1) Read the delay timer. 2) Confirm the delay matches the approved configuration.",
         "false", "", "Inverter Controller"),
        ("INV-305", "Error", "Inverter", "DC bus ripple above spec",
         "DC bus ripple exceeded 25 V peak to peak at power above 40 kW.",
         "DC bus capacitor ESR rise; loose DC link; current sensor noise",
         "1) Capture ripple at a known power. 2) Compare with a sister inverter on the same bus. 3) Plan a power-module swap if ESR is high on HW-B modules.",
         "true", "", "Power Module"),
        ("INV-318", "Warning", "Inverter", "AC overvoltage ride-through",
         "Grid voltage entered the ride-through band and the inverter stayed online.",
         "Utility switching; tap changer; local capacitor switching",
         "1) Record the voltage peak and duration. 2) No inverter repair if the event stayed inside the ride-through curve.",
         "false", "", "Inverter Controller"),
        ("INV-360", "Error", "Inverter", "Output capped below commanded power",
         "Commanded discharge was above the measured AC power by more than 10 kW for at least 15 minutes.",
         "Inverter power limit set below the engineered value; thermal derate; current limit",
         "1) Read Inverter Power Limit and compare it to the expected value. 2) Check configuration_status. 3) Confirm temperature is not in derate.",
         "true", "", "Inverter Controller"),
        ("INV-402", "Error", "Inverter", "Inverter output collapsed",
         "AC power fell by more than 50 kW in one sample while the grid was inside normal limits.",
         "Phase module fault; gate-driver undervoltage; DC input sag",
         "1) Compare grid voltage and DC bus at the drop. 2) If the grid is normal and the bus sags, inspect the power module. 3) Open a hardware ticket if the output stays down.",
         "true", "", "Power Module"),
        ("INV-415", "Critical", "Inverter", "Inverter hardware trip",
         "A hardware comparator tripped the inverter faster than the software loop.",
         "Desaturation; overcurrent; failed gate driver",
         "1) Do not restart more than once. 2) Capture the hardware trip code. 3) Replace the power module if desaturation is set.",
         "true", "", "Power Module"),
        ("COM-090", "Info", "Communications", "Link quality nominal",
         "Heartbeat latency and signal strength are inside the nominal band.",
         "Normal operation",
         "1) No action.",
         "false", "", "Communication Module"),
        ("COM-101", "Error", "Communications", "Gateway link loss",
         "The gateway stopped acknowledging heartbeats after signal strength fell and latency rose.",
         "Antenna or cable; interference; failed gateway radio",
         "1) Compare latency and signal strength. 2) A radio fault moves both. 3) A firmware heartbeat fault moves latency only. 4) Inspect the antenna if signal strength fell by more than 15 dBm.",
         "true", "", "Gateway"),
        ("COM-118", "Warning", "Communications", "Intermittent telemetry gap",
         "More than two expected telemetry frames were missing in 30 minutes.",
         "Latency rise; retransmission; gateway buffer",
         "1) Check communication latency and signal strength. 2) Count gaps before escalating.",
         "false", "", "Communication Module"),
        ("COM-214", "Error", "Communications", "Heartbeat session dropped",
         "The session layer dropped a healthy link when one-way latency exceeded 120 ms. Signal strength stays nominal.",
         "Firmware 4.3.0 heartbeat state machine regression",
         "1) Confirm signal strength is unchanged. 2) Confirm the device is on 4.3.0. 3) Roll back to 4.2.1 or upgrade to 4.3.1. 4) Do not replace the radio if signal strength is nominal.",
         "true", "4.3.1", "Communication Module"),
        ("COM-240", "Info", "Communications", "Compressed telemetry frames enabled",
         "The gateway is sending the compressed frame format introduced in 4.3.0.",
         "Firmware feature",
         "1) Confirm the collector accepts compressed frames. 2) No fault action.",
         "false", "", "Communication Module"),
        ("THERM-110", "Warning", "Thermal", "Pack temperature above warning threshold",
         "Pack temperature crossed 48 C. This is a warning, not a shutdown.",
         "Real heat rise; sensor drift; high ambient",
         "1) Compare the rate of rise. 2) A real rise tracks current and does not snap back. 3) A drifting sensor rises at low current and snaps back after replacement.",
         "false", "", "Temperature Sensor"),
        ("THERM-155", "Warning", "Thermal", "Temperature rate of change implausible",
         "Reported temperature changed faster than the pack thermal mass allows.",
         "Temperature sensor drift or a loose sensor lead",
         "1) Compare the step to pack current. 2) Check the redundant channel. 3) Replace the sensor if the channels disagree at low current.",
         "false", "", "Temperature Sensor"),
        ("THERM-201", "Critical", "Thermal", "Pack thermal protective shutdown",
         "The BMS opened the contactors because pack temperature crossed the protective threshold.",
         "Cooling fan stopped; blocked airflow; sustained discharge",
         "1) Read temperature for the two hours before the trip. 2) Confirm the cooling fan tach. 3) Do not raise the temperature threshold to clear this fault. 4) Replace the fan if tach is zero while temperature is rising.",
         "true", "", "Cooling Fan"),
        ("GRID-118", "Warning", "Grid", "Grid voltage outside preferred band",
         "Grid voltage left the preferred band but stayed inside the trip limits.",
         "Utility regulation; local switching",
         "1) Record duration. 2) Compare with the neighboring site. 3) No inverter repair for a shared grid dip.",
         "false", "", "Voltage Sensor"),
        ("GRID-201", "Info", "Grid", "Grid nominal",
         "Grid voltage and frequency returned to the nominal band.",
         "Normal recovery",
         "1) No action.",
         "false", "", "Inverter Controller"),
        ("GRID-302", "Error", "Grid", "Grid frequency excursion",
         "Grid frequency left the 59.5 to 60.5 Hz operating band.",
         "Utility disturbance; islanding; measurement error",
         "1) Confirm the excursion on the inverter and the gateway. 2) If both agree, treat it as a grid event. 3) The inverter may latch even after frequency returns.",
         "true", "", "Inverter Controller"),
        ("GRID-310", "Critical", "Grid", "Grid disconnect",
         "The inverter opened the AC contactor because the grid stayed outside limits past the ride-through timer.",
         "Sustained grid disturbance; failed grid relay",
         "1) Save the pre-trip waveform. 2) Reclose only after the grid is inside limits for the restart delay.",
         "true", "", "Relay"),
        ("GW-090", "Warning", "Gateway", "Signal strength declining",
         "RSSI fell more than 8 dBm from the site baseline and is still falling.",
         "Antenna alignment; foliage; interference; failing radio",
         "1) Compare RSSI to latency. 2) Inspect the antenna if latency is still low. 3) Escalate if RSSI crosses -95 dBm.",
         "false", "", "Gateway"),
        ("GW-101", "Warning", "Gateway", "Gateway CPU elevated",
         "Gateway CPU stayed above 80 percent for 10 minutes.",
         "Firmware 4.4.0 lab build; log flood; retry storm",
         "1) Check the firmware version. 2) Confirm this is not a 4.3.0 heartbeat storm. 3) Capture a CPU profile before replacing hardware.",
         "false", "", "Gateway"),
        ("GW-140", "Error", "Gateway", "Gateway restart loop",
         "The gateway rebooted more than three times in an hour.",
         "Power supply; firmware crash; watchdog",
         "1) Read the reboot reason. 2) Check the supply rail. 3) Hold the device out of the firmware rollout if the reboot reason is a panic.",
         "true", "", "Gateway"),
        ("FW-104", "Info", "Firmware", "Firmware bank verified",
         "The inactive firmware bank signature matched the release manifest.",
         "Normal update pre-check",
         "1) No action.",
         "false", "", "Communication Module"),
        ("FW-210", "Error", "Firmware", "Heartbeat regression signature",
         "The device logged the 4.3.0 heartbeat state-machine signature while the radio link was healthy.",
         "Firmware 4.3.0 communications regression",
         "1) Confirm version 4.3.0. 2) Upgrade to 4.3.1 or roll back to 4.2.1. 3) Use COM-214 as the customer-facing fault code.",
         "true", "4.3.1", "Communication Module"),
        ("CFG-090", "Warning", "Inverter", "Power limit below rated power",
         "Inverter Power Limit is more than 10 kW below the nameplate rating.",
         "Configuration mismatch; intentional derate",
         "1) Compare parameter_value to expected_value. 2) If they differ, the row is a mismatch, not a hardware fault.",
         "false", "", "Inverter Controller"),
        ("CFG-101", "Error", "Inverter", "Configuration outside approved envelope",
         "A running parameter does not match the approved expected value for the site.",
         "Field edit without an engineering change; stale template",
         "1) Open device_configuration for the device. 2) Restore the expected value through a change record. 3) Confirm faults stop after the new last_modified time.",
         "true", "", "Inverter Controller"),
        ("REL-204", "Error", "Battery", "Contactor coil driver fault",
         "The contactor was commanded closed and the coil current stayed at zero.",
         "Failed coil driver; open coil; harness",
         "1) Measure coil current. 2) If the command is present and current is zero, replace the driver. 3) Do not confuse this with a precharge-resistor failure.",
         "true", "", "Contactor"),
        ("REL-210", "Error", "Battery", "Precharge resistor open",
         "DC bus voltage did not rise during the precharge window, so the main contactor stayed open.",
         "Open precharge resistor; welded precharge relay; blown fuse",
         "1) Check precharge voltage slope. 2) A coil-driver fault still shows coil current at zero. 3) This fault shows coil current present and no voltage rise.",
         "true", "", "Relay"),
        ("SEN-112", "Warning", "Thermal", "Redundant temperature channels diverged",
         "The primary pack temperature and the redundant channel differ by more than 8 C.",
         "Primary sensor drift; redundant sensor drift; real gradient",
         "1) Trust the channel that agrees with current and with the site probe. 2) Replace the divergent sensor. 3) Do not shut the pack down on one divergent channel if current is low.",
         "false", "", "Temperature Sensor"),
    ]
    catalog = []
    for row in rows:
        catalog.append({
            "error_code": row[0],
            "severity": row[1],
            "subsystem": row[2],
            "title": row[3],
            "description": row[4],
            "likely_causes": row[5],
            "recommended_diagnostic_steps": row[6],
            "escalation_required": row[7],
            "known_firmware_fix": row[8],
            "related_component_type": row[9],
        })
    return catalog


def firmware_catalog():
    notes_421 = (
        "Previous stable release. Fixed 200 ms heartbeat, uncompressed telemetry frames, "
        "and communication timeout handled in the gateway task. No communications regression."
    )
    notes_430 = (
        "Replaced the 4.2.1 fixed heartbeat with an adaptive heartbeat and added compressed "
        "telemetry frames. Communication timeout handling moved from the gateway task into "
        "the shared session layer. Introduces a communications regression."
    )
    issues_430 = (
        "COM-214 communications regression: the heartbeat state machine drops the session "
        "when one-way latency exceeds 120 ms. Signal strength is unaffected. FW-210 is the "
        "matching firmware signature."
    )
    notes_431 = (
        "Restores the 4.2.1 heartbeat state machine and keeps compressed telemetry frames. "
        "Communication timeout handling stays in the session layer with the 4.2.1 timing thresholds."
    )
    resolved_431 = "COM-214 heartbeat session drop introduced in 4.3.0. FW-210 signature no longer raised."
    rows = []

    def add(version, device_type, release, status, previous, notes, known, resolved, hw, rollout):
        rows.append({
            "firmware_version": version,
            "device_type": device_type,
            "release_date": release,
            "status": status,
            "previous_version": previous,
            "release_notes": notes,
            "known_issues": known,
            "resolved_issues": resolved,
            "required_hardware_revision": hw,
            "rollout_status": rollout,
        })

    for device_type in ("Battery", "Inverter", "Gateway"):
        if device_type != "Inverter":
            add("4.1.4", device_type, "2025-11-15", "Deprecated", "4.0.9" if device_type == "Battery" else "4.1.0",
                "Maintenance branch. Fixed heartbeat. Still found on HW-A hardware that cannot take 4.3.x.",
                "No adaptive diagnostics.", "Earlier watchdog nuisance on 4.0.9.", "HW-A", "Limited to HW-A field units")
        else:
            add("4.1.4", device_type, "2025-11-15", "Deprecated", "4.1.0",
                "Maintenance branch for HW-A inverters. Fixed heartbeat.",
                "No compressed telemetry.", "DC precharge timing from 4.1.0.", "HW-A", "Limited to HW-A field units")
        add("4.2.1", device_type, "2026-04-02", "Deprecated", "4.1.4",
            notes_421, "None critical. Superseded by 4.3.1 for HW-B and later.",
            "Watchdog nuisance seen on 4.1.4 under noisy DC supplies.", "HW-A",
            "General availability, superseded")
        add("4.3.0", device_type, "2026-09-08", "Rolled Back", "4.2.1",
            notes_430, issues_430, "None. This build is the source of COM-214.", "HW-B",
            "Halted")
        add("4.3.1", device_type, "2026-09-19", "Current", "4.3.0",
            notes_431, "None critical in the communications suite.", resolved_431, "HW-B",
            "Limited production")

    add("4.0.9", "Battery", "2025-06-01", "Retired", "",
        "Initial Arroyo-200 field image. Retired before the September 2026 snapshot.",
        "Watchdog nuisance and coarse SOC tracking.", "", "HW-A", "Withdrawn")
    add("4.4.0", "Gateway", "2026-09-22", "Beta", "4.3.1",
        "Lab image with extra CPU tracing. Not approved for field rollout.",
        "Raises gateway CPU. Not related to the 4.3.0 heartbeat regression.",
        "", "HW-C", "No field installs")
    add("4.2.1", "Energy Controller", "2026-04-02", "Deprecated", "4.1.4",
        "Previous stable controller image. Same heartbeat behavior as device firmware 4.2.1.",
        "None critical.", "Grid ride-through timer fix from the 4.1 branch.", "HW-A",
        "General availability, superseded")
    add("4.3.1", "Energy Controller", "2026-09-19", "Current", "4.2.1",
        "Current controller image. Heartbeat timing matches the fixed 4.3.1 session layer. Energy controllers skipped 4.3.0.",
        "None critical.", "Does not contain the 4.3.0 regression because 4.3.0 was not built for this type.",
        "HW-B", "Limited production")
    add("4.1.4", "Sensor", "2025-11-15", "Deprecated", "4.0.9",
        "Probe firmware with basic calibration.", "No drift detection.", "", "HW-A", "HW-A probes only")
    add("4.2.1", "Sensor", "2026-04-02", "Current", "4.1.4",
        "Current probe image. Reports redundant temperature channels. Sensors are not part of the 4.3.0 heartbeat rollout.",
        "None critical.", "Calibration drift check from 4.1.4.", "HW-A", "General availability")
    return rows


# ---------------------------------------------------------------------------
# Fleet
# ---------------------------------------------------------------------------

def site_specs():
    specs = []

    def add(name, city, config, gateway=True, sensors=0, battery_role=None, inverter_role=None, gateway_role=None):
        specs.append({
            "name": name,
            "city": city,
            "config": config,
            "gateway": gateway,
            "sensors": sensors,
            "battery_role": battery_role,
            "inverter_role": inverter_role,
            "gateway_role": gateway_role,
        })

    add("Copper Elm Node", "Austin", "Single Battery + Single Inverter", True, 2, battery_role="thermal")
    add("Glass Creek Yard", "Round Rock", "Single Battery + Single Inverter", True, 0, gateway_role="fw_rollback_gw")
    add("Redbud Range Pad", "Cedar Park", "Single Battery + Single Inverter", True, 0, gateway_role="fw_fixed_gw")
    add("Switchgrass Hold", "Georgetown", "Single Battery + Single Inverter", True, 0, battery_role="fw_stuck_bat")
    add("Cotton Flat Node", "Pflugerville", "Single Battery + Single Inverter", True, 0, inverter_role="fw_rollback_inv")
    add("Limestone Yard", "Leander", "Single Battery + Single Inverter", True, 2, inverter_role="config_inv")
    add("Owl Hollow Pad", "Austin", "Single Battery + Single Inverter", True, 0, gateway_role="comm_gw")
    add("Briar DC Node", "Round Rock", "Single Battery + Single Inverter", True, 2, battery_role="repeat_a")
    add("Pebble Ford Yard", "Cedar Park", "Single Battery + Single Inverter", True, 0, battery_role="repeat_b")
    add("Yellow Dock Hold", "Georgetown", "Single Battery + Single Inverter", True, 0, battery_role="repeat_c")
    add("Blue Sage Node", "Pflugerville", "Single Battery + Single Inverter", True, 2, battery_role="drift_bat")
    add("Warm Spring Yard", "Leander", "Single Battery + Single Inverter", True, 0, inverter_role="power_inv")
    add("High Lamp Pad", "Austin", "Single Battery + Single Inverter", True, 0, battery_role="soc_bat")
    add("Little Brake Node", "Round Rock", "Single Battery + Single Inverter", True, 0, battery_role="hist_a")
    add("Open Cinder Yard", "Cedar Park", "Single Battery + Single Inverter", True, 0, battery_role="hist_b")
    add("Stonewater Hold", "Georgetown", "Single Battery + Single Inverter", True, 2, battery_role="pro_temp")
    add("Clear Fork Node", "Pflugerville", "Single Battery + Single Inverter", True, 0, gateway_role="pro_gw")
    add("North Mesa Yard", "Leander", "Single Battery + Single Inverter", True, 0, battery_role="pro_minor")
    add("Lantern Field Pad", "Austin", "Single Battery + Single Inverter", True, 2, inverter_role="freq_inv")

    dual_cities = ["Round Rock", "Cedar Park", "Georgetown"]
    for i, city in enumerate(dual_cities):
        add(["Cinder Flat Node", "Dry Sage Yard", "Bright Lug Hold"][i], city, "Dual Battery + Single Inverter", True, 1)
    add("West Arroyo Node", "Austin", "Dual Battery + Dual Inverter", True, 0)
    add("East Arroyo Yard", "Leander", "Dual Battery + Dual Inverter", True, 0)
    add("Helio Bench Pad", "Pflugerville", "Battery + Solar + Inverter", True, 0, gateway_role="fw_stuck_gw")
    add("South Helio Node", "Austin", "Battery + Solar + Inverter", True, 0)
    add("North Helio Yard", "Round Rock", "Battery + Solar + Inverter", True, 0)
    add("Helio Spur Hold", "Cedar Park", "Battery + Solar + Inverter", True, 0)
    add("BusTie North Node", "Georgetown", "Battery + Grid Controller", True, 0)
    add("BusTie South Yard", "Leander", "Battery + Grid Controller", True, 0)
    add("BusTie East Pad", "Austin", "Battery + Grid Controller", True, 0)
    add("BusTie West Hold", "Pflugerville", "Battery + Grid Controller", True, 0)
    compact = [
        ("Compact Elm One", "Austin"),
        ("Compact Elm Two", "Round Rock"),
        ("Compact Creek Three", "Cedar Park"),
        ("Compact Creek Four", "Georgetown"),
        ("Compact Range Five", "Pflugerville"),
        ("Compact Range Six", "Leander"),
        ("Compact Hold Seven", "Austin"),
        ("Compact Hold Eight", "Round Rock"),
        ("Compact Flat Nine", "Cedar Park"),
        ("Compact Flat Ten", "Georgetown"),
        ("Compact Sage Eleven", "Pflugerville"),
        ("Compact Sage Twelve", "Leander"),
    ]
    for name, city in compact:
        add(name, city, "Single Battery + Single Inverter", gateway=False, sensors=0)
    return specs


STATUS_BY_ROLE = {
    "thermal": "Offline",
    "comm_gw": "Offline",
    "power_inv": "Faulted",
    "freq_inv": "Faulted",
    "fw_stuck_bat": "Degraded",
    "fw_stuck_gw": "Degraded",
    "repeat_a": "Degraded",
    "repeat_b": "Degraded",
    "repeat_c": "Degraded",
    "soc_bat": "Degraded",
}

FORCED_HW = {
    "repeat_a": "HW-C",
    "repeat_b": "HW-C",
    "repeat_c": "HW-C",
    "thermal": "HW-B",
    "drift_bat": "HW-B",
    "soc_bat": "HW-B",
    "pro_temp": "HW-B",
    "pro_minor": "HW-B",
    "pro_gw": "HW-B",
    "fw_rollback_gw": "HW-B",
    "fw_fixed_gw": "HW-B",
    "fw_stuck_bat": "HW-B",
    "fw_stuck_gw": "HW-B",
    "fw_rollback_inv": "HW-B",
    "config_inv": "HW-B",
    "power_inv": "HW-B",
    "freq_inv": "HW-B",
    "comm_gw": "HW-B",
    "hist_a": "HW-D",
    "hist_b": "HW-B",
}

TELEMETRY_ROLES = {
    "thermal",
    "fw_rollback_gw",
    "fw_fixed_gw",
    "fw_stuck_bat",
    "fw_stuck_gw",
    "config_inv",
    "comm_gw",
    "repeat_a",
    "repeat_b",
    "drift_bat",
    "power_inv",
    "soc_bat",
    "pro_temp",
    "pro_gw",
    "pro_minor",
    "freq_inv",
}


def serial_for(device_type, number):
    prefix = {
        "Battery": "BAT",
        "Inverter": "INV",
        "Gateway": "GW",
        "Energy Controller": "EC",
        "Sensor": "SEN",
    }[device_type]
    return f"SYN-{prefix}-{number:05d}"


def model_for(device_type, index):
    if device_type == "Battery":
        if index % 2 == 0:
            return "Northline", "Arroyo-200", "200", "100"
        return "MesaVolt", "Ledge-200", "200", "100"
    if device_type == "Inverter":
        return "CinderPeak", "Sill-90", "", "90"
    if device_type == "Gateway":
        return "RioCharge", "Link-4", "", ""
    if device_type == "Energy Controller":
        return "LanternGrid", "BusTie-50", "", "50"
    return "Northline", "Sense-T" if index % 2 == 0 else "Sense-V", "", ""


def build_fleet(world):
    specs = site_specs()
    check(len(specs) == len(SITE_NAMES) or True, "site spec mismatch")
    for index, spec in enumerate(specs):
        site_number = index + 1
        site_id = f"SITE-{site_number:03d}"
        customer_id, _customer_name = CUSTOMERS[index % len(CUSTOMERS)]
        lat, lon = CITIES[spec["city"]]
        lat += ((index % 7) - 3) * 0.018
        lon += ((index % 5) - 2) * 0.021
        install = at(2025, 6, 2) + timedelta(days=(index * 11) % 200)
        commission = install + timedelta(days=12)
        site = {
            "site_id": site_id,
            "customer_id": customer_id,
            "site_name": spec["name"],
            "city": spec["city"],
            "latitude": f"{lat:.6f}",
            "longitude": f"{lon:.6f}",
            "system_configuration": spec["config"],
            "battery_capacity_kwh": "0",
            "inverter_capacity_kw": "0",
            "number_of_batteries": "0",
            "number_of_inverters": "0",
            "installation_date": install.strftime("%Y-%m-%d"),
            "commissioning_date": commission.strftime("%Y-%m-%d"),
            "site_status": "Active",
        }
        world.sites.append(site)
        world.site_meta[site_id] = {"install": install, "commission": commission, "spec": spec}
        if spec["name"] == "Copper Elm Node":
            world.named["site_thermal"] = site_id

        n_bat, n_inv, n_ec = CONFIG_SHAPE[spec["config"]]
        plan = (
            [("Battery", spec["battery_role"] if i == 0 else None) for i in range(n_bat)]
            + [("Inverter", spec["inverter_role"] if i == 0 else None) for i in range(n_inv)]
            + [("Energy Controller", None) for _ in range(n_ec)]
        )
        if spec["gateway"]:
            plan.append(("Gateway", spec["gateway_role"]))
        for s_index in range(spec["sensors"]):
            plan.append(("Sensor", None))

        for device_type, role in plan:
            number = len(world.devices) + 1
            device_id = f"DEV-{number:03d}"
            manufacturer, model, capacity, power = model_for(device_type, number)
            if device_type == "Energy Controller" and spec["config"] == "Battery + Solar + Inverter":
                manufacturer, model, power = "LanternGrid", "HelioNode-30", "30"
            hw_cycle = ["HW-B", "HW-B", "HW-B", "HW-C", "HW-A", "HW-B", "HW-D"]
            hw = FORCED_HW.get(role, hw_cycle[number % 7])
            status = STATUS_BY_ROLE.get(role, "Online")
            device = {
                "device_id": device_id,
                "device_serial": serial_for(device_type, number),
                "customer_id": customer_id,
                "site_id": site_id,
                "device_type": device_type,
                "manufacturer": manufacturer,
                "model": model,
                "installation_date": install.strftime("%Y-%m-%d"),
                "status": status,
                "firmware_version": "",
                "hardware_revision": hw,
                "commissioning_date": commission.strftime("%Y-%m-%d"),
                "last_seen_at": fmt(NOW),
                "rated_capacity_kwh": capacity,
                "rated_power_kw": power,
            }
            world.devices.append(device)
            world.device_meta[device_id] = {
                "role": role,
                "alias": role,
                "status": status,
                "hw": hw,
                "telemetry": role in TELEMETRY_ROLES,
                "salt": number * 17 + 3,
                "history_kind": "default",
                "install": install,
                "commission": commission,
            }
            if role:
                world.named[role] = device_id
                if role == "thermal":
                    world.named["site_thermal"] = site_id

    # One device held for maintenance, and pin the live 75-vs-90 mismatch battery.
    maintenance_set = False
    mismatch_set = False
    for device in world.devices:
        meta = world.device_meta[device["device_id"]]
        if meta["role"]:
            continue
        if not maintenance_set and device["device_type"] == "Battery" and device["site_id"] >= "SITE-033":
            meta["role"] = "maintenance"
            meta["alias"] = "maintenance"
            device["status"] = "Maintenance"
            meta["status"] = "Maintenance"
            world.named["maintenance"] = device["device_id"]
            maintenance_set = True
            continue
        if not mismatch_set and device["device_type"] == "Battery" and device["status"] == "Online":
            meta["role"] = "mismatch_soc"
            meta["alias"] = "mismatch_soc"
            world.named["mismatch_soc"] = device["device_id"]
            mismatch_set = True
        if maintenance_set and mismatch_set:
            break

    healthy_need = {"Battery": 2, "Inverter": 1, "Gateway": 1}
    healthy_ids = []
    for device in world.devices:
        meta = world.device_meta[device["device_id"]]
        if meta["role"] or device["status"] != "Online":
            continue
        kind = device["device_type"]
        if healthy_need.get(kind, 0) > 0:
            meta["role"] = "healthy"
            meta["alias"] = f"healthy_{kind}_{healthy_need[kind]}"
            meta["telemetry"] = True
            world.named[meta["alias"]] = device["device_id"]
            healthy_ids.append(device["device_id"])
            healthy_need[kind] -= 1
    world.named["healthy_ids"] = healthy_ids

    failed_set = False
    pending_set = False
    timeout_mismatch_set = False
    voltage_mismatch_set = False
    for device in world.devices:
        meta = world.device_meta[device["device_id"]]
        if meta["role"]:
            continue
        if device["device_type"] == "Inverter" and device["hardware_revision"] != "HW-A":
            if not failed_set:
                meta["history_kind"] = "failed"
                meta["role"] = "failed_fw"
                world.named["failed_fw"] = device["device_id"]
                failed_set = True
                continue
            if not pending_set:
                meta["history_kind"] = "pending"
                meta["role"] = "pending_fw"
                world.named["pending_fw"] = device["device_id"]
                pending_set = True
                continue
            if not voltage_mismatch_set:
                meta["role"] = "mismatch_voltage"
                world.named["mismatch_voltage"] = device["device_id"]
                voltage_mismatch_set = True
                continue
        if device["device_type"] == "Gateway" and not timeout_mismatch_set:
            meta["role"] = "mismatch_timeout"
            world.named["mismatch_timeout"] = device["device_id"]
            timeout_mismatch_set = True
    check(maintenance_set and mismatch_set and failed_set and pending_set, "missing reserved filler devices")
    check(timeout_mismatch_set and voltage_mismatch_set, "missing live mismatch devices")
    check("thermal" in world.named and world.named["thermal"] == "DEV-001", "DEV-001 must be the thermal battery")


def finalize_sites(world):
    by_site = defaultdict(list)
    for device in world.devices:
        by_site[device["site_id"]].append(device)
    for site in world.sites:
        devs = by_site[site["site_id"]]
        bats = [d for d in devs if d["device_type"] == "Battery"]
        invs = [d for d in devs if d["device_type"] == "Inverter"]
        site["number_of_batteries"] = str(len(bats))
        site["number_of_inverters"] = str(len(invs))
        site["battery_capacity_kwh"] = str(sum(int(d["rated_capacity_kwh"] or 0) for d in bats))
        site["inverter_capacity_kw"] = str(sum(int(d["rated_power_kw"] or 0) for d in invs))
        if any(world.device_meta[d["device_id"]]["role"] == "maintenance" for d in devs):
            site["site_status"] = "Maintenance"


def build_components(world):
    for device in world.devices:
        meta = world.device_meta[device["device_id"]]
        role = meta["role"]
        for comp_type, lifespan in KITS[device["device_type"]]:
            if device["device_type"] == "Sensor" and device["model"] == "Sense-V":
                comp_type = "Voltage Sensor"
            number = len(world.components) + 1
            status = "In Service"
            hw = device["hardware_revision"]
            if role == "thermal" and comp_type == "Cooling Fan":
                status = "Failed"
            elif role == "drift_bat" and comp_type == "Temperature Sensor":
                status = "Replaced"
            elif role in ("repeat_a", "repeat_b", "repeat_c") and comp_type == "Power Module":
                status = "Degraded"
                hw = "HW-C"
            elif role == "comm_gw" and comp_type == "Communication Module":
                status = "Failed"
            elif role == "comm_gw" and comp_type == "Gateway":
                status = "Degraded"
            elif role == "power_inv" and comp_type == "Power Module":
                status = "Failed"
            elif role in ("fw_stuck_bat", "fw_stuck_gw", "fw_rollback_gw", "fw_fixed_gw", "fw_rollback_inv") and comp_type == "Communication Module":
                status = "Degraded" if role in ("fw_stuck_bat", "fw_stuck_gw") else "In Service"
            row = {
                "component_id": f"CMP-{number:04d}",
                "device_id": device["device_id"],
                "component_type": comp_type,
                "expected_lifespan_hours": str(lifespan),
                "hardware_revision": hw,
                "serial_number": f"SYN-CMP-{number:06d}",
                "status": status,
            }
            world.components.append(row)
            world.components_by_device[device["device_id"]].append(row)
            if role == "thermal" and comp_type == "Cooling Fan":
                world.named["thermal_fan"] = row["component_id"]
            if role == "drift_bat" and comp_type == "Temperature Sensor" and status == "Replaced":
                world.named["drift_sensor"] = row["component_id"]
            if role == "repeat_a" and comp_type == "Power Module":
                world.named["repeat_module"] = row["component_id"]
            if role == "comm_gw" and comp_type == "Gateway":
                world.named["comm_radio"] = row["component_id"]
            if role == "power_inv" and comp_type == "Power Module":
                world.named["power_module"] = row["component_id"]
        if role == "drift_bat":
            number = len(world.components) + 1
            row = {
                "component_id": f"CMP-{number:04d}",
                "device_id": device["device_id"],
                "component_type": "Temperature Sensor",
                "expected_lifespan_hours": "50000",
                "hardware_revision": "HW-D",
                "serial_number": f"SYN-CMP-{number:06d}",
                "status": "In Service",
            }
            world.components.append(row)
            world.components_by_device[device["device_id"]].append(row)
            world.named["drift_sensor_new"] = row["component_id"]


def component_of(world, device_id, comp_type):
    for row in world.components_by_device[device_id]:
        if row["component_type"] == comp_type:
            return row["component_id"]
    return ""


def build_firmware_history(world):
    allowed = defaultdict(set)
    for row in world.firmware:
        allowed[row["device_type"]].add(row["firmware_version"])

    def append_row(device, version, when, status, previous, reason=""):
        world.fw_history.append({
            "deployment_id": f"DEP-{len(world.fw_history)+1:04d}",
            "device_id": device["device_id"],
            "firmware_version": version,
            "installed_at": fmt(when),
            "installed_by": "ENG-110" if status != "Failed" else "ENG-118",
            "deployment_status": status,
            "previous_version": previous,
            "rollback_reason": reason,
        })

    for device in world.devices:
        meta = world.device_meta[device["device_id"]]
        role = meta["role"]
        commission = meta["commission"] + timedelta(hours=15)
        kind = meta["history_kind"]
        device_type = device["device_type"]

        if role in ("fw_rollback_gw", "fw_rollback_inv"):
            append_row(device, "4.2.1", commission, "Successful", "")
            append_row(device, "4.3.0", FW_UPGRADE, "Successful", "4.2.1")
            append_row(device, "4.2.1", FW_ROLLBACK, "Rolled Back", "4.3.0",
                       "COM-214 heartbeat regression on 4.3.0")
        elif role == "fw_fixed_gw":
            append_row(device, "4.2.1", commission, "Successful", "")
            append_row(device, "4.3.0", FW_UPGRADE, "Successful", "4.2.1")
            append_row(device, "4.3.1", FW_PATCH, "Successful", "4.3.0")
        elif role in ("fw_stuck_bat", "fw_stuck_gw"):
            append_row(device, "4.2.1", commission, "Successful", "")
            append_row(device, "4.3.0", FW_UPGRADE, "Successful", "4.2.1")
        elif kind == "failed":
            append_row(device, "4.2.1", commission, "Successful", "")
            append_row(device, "4.3.1", at(2026, 9, 21, 2, 0), "Failed", "4.2.1")
        elif kind == "pending":
            append_row(device, "4.2.1", commission, "Successful", "")
            append_row(device, "4.3.1", at(2026, 9, 26, 22, 0), "Pending", "4.2.1")
        else:
            hw = device["hardware_revision"]
            if device_type == "Sensor":
                version = "4.1.4" if hw == "HW-A" and meta["salt"] % 2 == 0 else "4.2.1"
            elif device_type == "Energy Controller":
                version = "4.3.1" if hw != "HW-A" and meta["salt"] % 5 == 0 else "4.2.1"
            elif hw == "HW-A":
                version = "4.1.4" if meta["salt"] % 2 == 0 else "4.2.1"
            elif meta["salt"] % 7 == 0 and "4.3.1" in allowed[device_type]:
                version = "4.3.1"
            else:
                version = "4.2.1"
            if version == "4.3.1":
                append_row(device, "4.2.1", commission, "Successful", "")
                append_row(device, "4.3.1", at(2026, 9, 21, 9, 0), "Successful", "4.2.1")
            else:
                append_row(device, version, commission, "Successful", "")

        history = [row for row in world.fw_history if row["device_id"] == device["device_id"]]
        current = None
        for row in history:
            if row["deployment_status"] in ("Successful", "Rolled Back"):
                current = row["firmware_version"]
        check(current in allowed[device_type], f"{device['device_id']} firmware {current} missing for {device_type}")
        device["firmware_version"] = current


def build_configuration(world):
    for device in world.devices:
        meta = world.device_meta[device["device_id"]]
        role = meta["role"]
        for name, expected, unit, lo, hi in PARAMS_BY_TYPE[device["device_type"]]:
            rows_to_write = [(expected, expected, "Nominal", meta["commission"] + timedelta(hours=16), "ENG-104")]
            if role == "config_inv" and name == "Inverter Power Limit":
                rows_to_write = [
                    ("75", "90", "Mismatch", CONFIG_BAD, "TECH-214"),
                    ("90", "90", "Nominal", CONFIG_FIX, "ENG-110"),
                ]
            elif role == "mismatch_soc" and name == "SOC Maximum":
                rows_to_write = [("75", "90", "Mismatch", at(2026, 9, 9, 13, 0), "TECH-221")]
            elif role == "mismatch_timeout" and name == "Communication Timeout":
                rows_to_write = [("8", "30", "Mismatch", at(2026, 9, 11, 8, 40), "TECH-214")]
            elif role == "mismatch_voltage" and name == "Grid Voltage Limit":
                rows_to_write = [("492", "504", "Mismatch", at(2026, 9, 12, 15, 10), "TECH-210")]
            for value, expect, status, modified, who in rows_to_write:
                world.configs.append({
                    "configuration_id": f"CFG-{len(world.configs)+1:05d}",
                    "device_id": device["device_id"],
                    "parameter_name": name,
                    "parameter_value": value,
                    "unit": unit,
                    "expected_value": expect,
                    "min_allowed": lo,
                    "max_allowed": hi,
                    "last_modified": fmt(modified),
                    "modified_by": who,
                    "configuration_status": status,
                })


# ---------------------------------------------------------------------------
# Telemetry
# ---------------------------------------------------------------------------

def hour_frac(ts):
    local = ts.astimezone(TZ)
    return local.hour + local.minute / 60.0


def discharge_shape(ts):
    hour = hour_frac(ts)
    if 16.0 <= hour <= 21.0:
        x = (hour - 16.0) / 5.0
        return 90.0 * math.sin(x * math.pi)
    return 0.0


def charge_shape(ts):
    hour = hour_frac(ts)
    if 0.0 <= hour <= 6.0:
        x = hour / 6.0
        return 40.0 * math.sin(x * math.pi)
    return 0.0


def in_window(ts, start, end):
    return start <= ts <= end


def battery_metrics(ts, i, salt, role):
    hour = hour_frac(ts)
    soc = 58 + 22 * math.sin((hour - 7) / 24 * 2 * math.pi)
    soc = clamp(soc + noise(i, salt, 1.2), 28, 88)
    temp = 28 + 2.2 * math.sin((hour - 15) / 24 * 2 * math.pi) + noise(i, salt + 1, 0.6)
    discharge = discharge_shape(ts)
    charge = charge_shape(ts) if discharge < 1 else 0.0
    if discharge > 1:
        current = discharge * 1000 / 750
        state = "Discharging"
    elif charge > 1:
        current = -charge * 1000 / 750
        state = "Charging"
    else:
        current = noise(i, salt + 2, 1.5)
        state = "Idle"
    voltage = 752 + (soc - 50) * 0.18 + noise(i, salt + 3, 1.4)
    latency = 32 + noise(i, salt + 4, 6)
    signal = -64 + noise(i, salt + 5, 3)
    metrics = {
        "battery_soc_percent": soc,
        "battery_voltage": voltage,
        "battery_current": current,
        "battery_temperature_c": temp,
        "inverter_power_kw": None,
        "grid_voltage": None,
        "grid_frequency_hz": None,
        "dc_bus_voltage": voltage + 8,
        "charge_rate_kw": charge,
        "discharge_rate_kw": discharge,
        "communication_latency_ms": latency,
        "signal_strength_dbm": signal,
        "operating_state": state,
    }
    apply_battery_overlay(metrics, ts, i, salt, role)
    return metrics


def apply_battery_overlay(metrics, ts, i, salt, role):
    if role == "thermal":
        if ts >= THERMAL_RAMP_START and ts <= THERMAL_OFFLINE:
            metrics["battery_temperature_c"] = lerp(ts, THERMAL_RAMP_START, THERMAL_OFFLINE, 34, 73)
            metrics["discharge_rate_kw"] = 62
            metrics["charge_rate_kw"] = 0
            metrics["battery_current"] = 82
            metrics["operating_state"] = "Discharging"
            metrics["battery_voltage"] = 748 - lerp(ts, THERMAL_RAMP_START, THERMAL_OFFLINE, 0, 8)
            if ts >= THERMAL_FAULT:
                metrics["operating_state"] = "Fault"
        if ts == CURRENT_SPIKE:
            metrics["battery_current"] = 184
            metrics["charge_rate_kw"] = 138
            metrics["operating_state"] = "Charging"
    elif role == "fw_stuck_bat":
        if ts >= FW_UPGRADE:
            metrics["communication_latency_ms"] = 340 + noise(i, salt, 25)
            metrics["signal_strength_dbm"] = -64 + noise(i, salt + 5, 2)
            metrics["operating_state"] = "Degraded"
    elif role in ("repeat_a", "repeat_b"):
        windows = VOLT_WINDOWS if role == "repeat_a" else VOLT_WINDOWS[1:]
        for start, end in windows:
            if in_window(ts, start, end):
                swing = 705 if (i % 2 == 0) else 812
                metrics["battery_voltage"] = swing + noise(i, salt, 3)
                metrics["dc_bus_voltage"] = metrics["battery_voltage"] + 6
                metrics["operating_state"] = "Discharging"
                metrics["discharge_rate_kw"] = 78
                metrics["battery_current"] = 104
    elif role == "drift_bat":
        if DRIFT_START <= ts < DRIFT_REPLACE:
            hours = (ts - DRIFT_START).total_seconds() / 3600
            metrics["battery_temperature_c"] = 28 + hours * 0.22
        elif ts >= DRIFT_REPLACE:
            metrics["battery_temperature_c"] = 28.4 + noise(i, salt, 0.4)
        # Voltage and current stay on the base profile so the rise is not a real thermal load.
    elif role == "soc_bat":
        if ts >= SOC_STEP:
            metrics["battery_soc_percent"] = clamp(metrics["battery_soc_percent"] - 48, 8, 40)
            # Keep current and power on the normal schedule so the SOC step has no energy match
            # at the step itself. The base profile may still charge or discharge later.
            if ts == SOC_STEP:
                metrics["battery_current"] = 0.4
                metrics["charge_rate_kw"] = 0
                metrics["discharge_rate_kw"] = 0
                metrics["operating_state"] = "Idle"
            else:
                metrics["operating_state"] = "Degraded"
    elif role == "pro_temp":
        if ts >= PRO_TEMP_START:
            metrics["battery_temperature_c"] = 39.5 + noise(i, salt, 1.4)
            metrics["operating_state"] = metrics["operating_state"]
    elif role == "pro_minor":
        # Four isolated watchdog samples. Latency returns on the next sample.
        if ts in (
            at(2026, 9, 18, 2, 20),
            at(2026, 9, 20, 7, 40),
            at(2026, 9, 23, 1, 0),
            at(2026, 9, 26, 4, 40),
        ):
            metrics["operating_state"] = "Restart"
            metrics["communication_latency_ms"] = 110
    elif role == "healthy":
        pass


def inverter_metrics(ts, i, salt, role):
    discharge = discharge_shape(ts)
    power = discharge if discharge > 1 else (6 + noise(i, salt, 1.5))
    if power < 0:
        power = 0
    freq = 60.0 + noise(i, salt + 2, 0.012)
    voltage = 480 + noise(i, salt + 3, 1.6)
    latency = 30 + noise(i, salt + 4, 5)
    state = "Discharging" if discharge > 10 else "Idle"
    metrics = {
        "battery_soc_percent": None,
        "battery_voltage": None,
        "battery_current": None,
        "battery_temperature_c": None,
        "inverter_power_kw": power,
        "grid_voltage": voltage,
        "grid_frequency_hz": freq,
        "dc_bus_voltage": 760 + noise(i, salt + 6, 2),
        "charge_rate_kw": None,
        "discharge_rate_kw": None,
        "communication_latency_ms": latency,
        "signal_strength_dbm": -63 + noise(i, salt + 5, 2),
        "operating_state": state,
    }
    if role == "config_inv":
        if ts < CONFIG_FIX and metrics["inverter_power_kw"] > 75:
            metrics["inverter_power_kw"] = 75.0
            metrics["operating_state"] = "Throttled"
    elif role == "power_inv":
        if ts >= POWER_DROP:
            metrics["inverter_power_kw"] = 6.5
            metrics["dc_bus_voltage"] = 690
            metrics["operating_state"] = "Fault"
            metrics["grid_frequency_hz"] = 60.0 + noise(i, salt, 0.01)
            metrics["grid_voltage"] = 480 + noise(i, salt, 1)
        elif ts == POWER_DROP - STEP:
            metrics["inverter_power_kw"] = 78
            metrics["operating_state"] = "Discharging"
    elif role == "freq_inv":
        if ts == FREQ_START:
            metrics["grid_frequency_hz"] = 60.84
            metrics["inverter_power_kw"] = 22
            metrics["operating_state"] = "Discharging"
        elif ts == FREQ_PEAK:
            metrics["grid_frequency_hz"] = 61.28
            metrics["inverter_power_kw"] = 0
            metrics["operating_state"] = "Fault"
        elif ts > FREQ_PEAK:
            metrics["grid_frequency_hz"] = 60.01 + noise(i, salt, 0.008)
            metrics["inverter_power_kw"] = 0
            metrics["operating_state"] = "Fault"
    elif role == "fw_rollback_inv":
        if FW_UPGRADE <= ts < FW_ROLLBACK:
            metrics["communication_latency_ms"] = 360 + noise(i, salt, 20)
            metrics["signal_strength_dbm"] = -64 + noise(i, salt, 1.5)
    return metrics


def gateway_metrics(ts, i, salt, role):
    metrics = {
        "battery_soc_percent": None,
        "battery_voltage": None,
        "battery_current": None,
        "battery_temperature_c": None,
        "inverter_power_kw": None,
        "grid_voltage": None,
        "grid_frequency_hz": None,
        "dc_bus_voltage": None,
        "charge_rate_kw": None,
        "discharge_rate_kw": None,
        "communication_latency_ms": 28 + noise(i, salt, 5),
        "signal_strength_dbm": -65 + noise(i, salt + 1, 2.5),
        "operating_state": "Online",
    }
    if role in ("fw_rollback_gw", "fw_fixed_gw", "fw_stuck_gw"):
        bad_end = {
            "fw_rollback_gw": FW_ROLLBACK,
            "fw_fixed_gw": FW_PATCH,
            "fw_stuck_gw": NOW + STEP,
        }[role]
        if FW_UPGRADE <= ts < bad_end:
            metrics["communication_latency_ms"] = 320 + noise(i, salt, 30)
            metrics["signal_strength_dbm"] = -64 + noise(i, salt + 1, 2)
            metrics["operating_state"] = "Degraded"
    elif role == "comm_gw":
        if in_window(ts, COMM_START, COMM_OFFLINE):
            metrics["communication_latency_ms"] = lerp(ts, COMM_START, COMM_OFFLINE, 48, 1750)
            metrics["signal_strength_dbm"] = lerp(ts, COMM_START, COMM_OFFLINE, -68, -107)
            metrics["operating_state"] = "Degraded"
            if ts >= COMM_OFFLINE:
                metrics["operating_state"] = "Offline"
    elif role == "pro_gw":
        if ts >= PRO_LAT_START:
            hours = (ts - PRO_LAT_START).total_seconds() / 3600
            metrics["communication_latency_ms"] = 42 + hours * 0.55
            metrics["signal_strength_dbm"] = -66 + noise(i, salt, 1.5)
            metrics["operating_state"] = "Online"
    return metrics


def telemetry_end(role):
    if role == "thermal":
        return THERMAL_OFFLINE
    if role == "comm_gw":
        return COMM_OFFLINE
    return NOW


def metric_row(device_id, ts, metrics, tel_id):
    return {
        "telemetry_id": tel_id,
        "device_id": device_id,
        "timestamp": fmt(ts),
        "battery_soc_percent": num(metrics["battery_soc_percent"]),
        "battery_voltage": num(metrics["battery_voltage"]),
        "battery_current": num(metrics["battery_current"]),
        "battery_temperature_c": num(metrics["battery_temperature_c"]),
        "inverter_power_kw": num(metrics["inverter_power_kw"]),
        "grid_voltage": num(metrics["grid_voltage"]),
        "grid_frequency_hz": num3(metrics["grid_frequency_hz"]),
        "dc_bus_voltage": num(metrics["dc_bus_voltage"]),
        "charge_rate_kw": num(metrics["charge_rate_kw"]),
        "discharge_rate_kw": num(metrics["discharge_rate_kw"]),
        "communication_latency_ms": num(metrics["communication_latency_ms"]),
        "signal_strength_dbm": num(metrics["signal_strength_dbm"]),
        "operating_state": metrics["operating_state"],
    }


def build_telemetry(world):
    for device in world.devices:
        meta = world.device_meta[device["device_id"]]
        if not meta["telemetry"]:
            continue
        role = meta["role"]
        salt = meta["salt"]
        end = telemetry_end(role)
        for i, ts in enumerate(timestamps(TEL_START, end)):
            if device["device_type"] == "Battery":
                metrics = battery_metrics(ts, i, salt, role)
            elif device["device_type"] == "Inverter":
                metrics = inverter_metrics(ts, i, salt, role)
            elif device["device_type"] == "Gateway":
                metrics = gateway_metrics(ts, i, salt, role)
            else:
                continue
            tel_id = f"TEL-{len(world.telemetry)+1:07d}"
            world.telemetry.append(metric_row(device["device_id"], ts, metrics, tel_id))
        last = [row for row in world.telemetry if row["device_id"] == device["device_id"]][-1]
        device["last_seen_at"] = last["timestamp"]


def series(world, device_id):
    rows = [row for row in world.telemetry if row["device_id"] == device_id]
    rows.sort(key=lambda row: row["timestamp"])
    return rows


def observed(rows, field):
    values = []
    for row in rows:
        if row[field] != "":
            values.append(float(row[field]))
    return values


def add_anomaly(world, device_id, start, end, anomaly_type, metric, expected, severity, fault_id, notes):
    rows = [
        row for row in series(world, device_id)
        if start <= parse(row["timestamp"]) <= end and row[metric] != ""
    ]
    check(len(rows) >= 2, f"anomaly window empty for {device_id} {anomaly_type}")
    values = [float(row[metric]) for row in rows]
    observed_range = f"{min(values):.2f} to {max(values):.2f}"
    world.anomalies.append({
        "anomaly_id": f"ANO-{len(world.anomalies)+1:03d}",
        "device_id": device_id,
        "start_time": fmt(start),
        "end_time": fmt(end),
        "anomaly_type": anomaly_type,
        "metric": metric,
        "expected_range": expected,
        "observed_range": observed_range,
        "severity": severity,
        "detected": "true",
        "related_fault_id": fault_id,
        "notes": notes,
    })
    return world.anomalies[-1]["anomaly_id"]


# ---------------------------------------------------------------------------
# Faults, incidents, and the rest of the graph
# ---------------------------------------------------------------------------

def add_fault(world, device_id, ts, code, status, detected_by, component_id="", technician="", job="",
              cleared_at=None, resolution="", notes=""):
    error = next(row for row in world.errors if row["error_code"] == code)
    fault = {
        "fault_id": f"FLT-{len(world.faults)+1:04d}",
        "device_id": device_id,
        "timestamp": fmt(ts),
        "error_code": code,
        "severity": error["severity"],
        "fault_status": status,
        "detected_by": detected_by,
        "component_id": component_id,
        "technician_id": technician,
        "job_id": job,
        "cleared_at": fmt(cleared_at) if cleared_at else "",
        "resolution": resolution,
        "notes": notes,
    }
    world.faults.append(fault)
    return fault["fault_id"]


def build_faults(world):
    thermal = world.named["thermal"]
    world.named["flt_thermal_warn"] = add_fault(
        world, thermal, THERMAL_WARN, "THERM-110", "Cleared", "BMS",
        component_of(world, thermal, "Temperature Sensor"), "ENG-104", "JOB-6101",
        THERMAL_FAULT, "Superseded by THERM-201 protective shutdown",
        "Warning during the temperature rise. The rise continued.",
    )
    world.named["flt_thermal"] = add_fault(
        world, thermal, THERMAL_FAULT, "THERM-201", "Escalated", "BMS",
        world.named["thermal_fan"], "ENG-104", "JOB-6102",
        notes="Cooling fan tach was zero while pack temperature was still rising. Pack went offline at 14:40.",
    )
    world.named["flt_spike"] = add_fault(
        world, thermal, CURRENT_SPIKE, "BAT-217", "Cleared", "BMS",
        component_of(world, thermal, "Current Sensor"), "ENG-118", "",
        CURRENT_SPIKE + timedelta(minutes=20), "Transient false alarm",
        "Single-sample charge current spike on 15 Sep. Unrelated to the 26 Sep thermal shutdown.",
    )

    for role, label in (("fw_rollback_gw", "rollback gateway"), ("fw_fixed_gw", "patched gateway"),
                        ("fw_stuck_bat", "battery still on 4.3.0"), ("fw_stuck_gw", "gateway still on 4.3.0"),
                        ("fw_rollback_inv", "rolled-back inverter")):
        device_id = world.named[role]
        cleared = None
        resolution = ""
        status = "Active"
        if role in ("fw_rollback_gw", "fw_rollback_inv"):
            cleared = FW_ROLLBACK
            resolution = "Rolled back to 4.2.1"
            status = "Cleared"
        elif role == "fw_fixed_gw":
            cleared = FW_PATCH
            resolution = "Upgraded to 4.3.1"
            status = "Cleared"
        else:
            status = "Recurring"
        fault_id = add_fault(
            world, device_id, FW_UPGRADE + timedelta(hours=4, minutes=20), "COM-214", status,
            "Firmware Monitor", component_of(world, device_id, "Communication Module"),
            "ENG-110", "JOB-6201", cleared, resolution,
            f"COM-214 started after the 4.3.0 install on this {label}. Signal strength stayed nominal.",
        )
        world.named[f"flt_{role}"] = fault_id
        if role == "fw_stuck_bat":
            add_fault(
                world, device_id, FW_UPGRADE + timedelta(hours=6), "FW-210", "Active",
                "Firmware Monitor", component_of(world, device_id, "Communication Module"),
                notes="FW-210 signature confirms the 4.3.0 heartbeat regression. Not a radio fault.",
            )

    config = world.named["config_inv"]
    for stamp in (at(2026, 9, 14, 18, 0), at(2026, 9, 15, 18, 20), at(2026, 9, 16, 17, 40), at(2026, 9, 17, 18, 40)):
        add_fault(
            world, config, stamp, "INV-360", "Cleared", "Inverter Controller",
            component_of(world, config, "Inverter Controller"), "ENG-125", "JOB-6301",
            CONFIG_FIX, "Inverter Power Limit restored from 75 kW to 90 kW",
            "Afternoon discharge flatlined at 75 kW while the engineered limit was 90 kW.",
        )
    world.named["flt_config"] = add_fault(
        world, config, at(2026, 9, 17, 18, 0), "CFG-101", "Cleared", "NOC",
        component_of(world, config, "Inverter Controller"), "ENG-110", "JOB-6302",
        CONFIG_FIX, "Configuration restored to the expected 90 kW limit",
        "parameter_value 75 kW did not match expected_value 90 kW.",
    )

    comm = world.named["comm_gw"]
    add_fault(
        world, comm, COMM_WARN, "COM-118", "Cleared", "Gateway",
        world.named["comm_radio"], "", "", COMM_FAULT, "Progressed to link loss",
        "Telemetry gaps while latency was rising and signal strength was falling.",
    )
    world.named["flt_comm"] = add_fault(
        world, comm, COMM_FAULT, "COM-101", "Escalated", "Gateway",
        world.named["comm_radio"], "ENG-104", "JOB-6401",
        notes="Latency and signal strength both degraded before the gateway stopped reporting. Firmware stayed 4.2.1.",
    )
    add_fault(
        world, comm, COMM_START + timedelta(hours=2), "GW-090", "Acknowledged", "Gateway",
        world.named["comm_radio"], "TECH-210", "",
        notes="RSSI decline preceded the link loss.",
    )

    for role, ordinal in (("repeat_a", 0), ("repeat_b", 1), ("repeat_c", 2)):
        device_id = world.named[role]
        stamps = VOLT_FAULTS if role == "repeat_a" else VOLT_FAULTS[1:]
        if role == "repeat_c":
            stamps = [at(2026, 9, 18, 17, 20), at(2026, 9, 21, 17, 0), at(2026, 9, 24, 16, 40)]
        for idx, stamp in enumerate(stamps):
            status = "Escalated" if role == "repeat_a" and idx == len(stamps) - 1 else "Recurring"
            fault_id = add_fault(
                world, device_id, stamp, "BAT-204", status, "BMS",
                component_of(world, device_id, "Power Module"), "ENG-125", "JOB-6501",
                notes="HW-C pack, cell-group imbalance during discharge above 70 kW. Same signature as the other HW-C sites.",
            )
            if role == "repeat_a" and idx == len(stamps) - 1:
                world.named["flt_repeat"] = fault_id

    drift = world.named["drift_bat"]
    world.named["flt_drift"] = add_fault(
        world, drift, DRIFT_FAULTS[-1], "THERM-155", "Cleared", "BMS",
        world.named["drift_sensor"], "ENG-118", "JOB-6601",
        DRIFT_REPLACE, "Replaced drifting temperature sensor",
        "Temperature rose for days at low current and snapped back when the sensor was replaced. Not a cooling failure.",
    )
    for stamp in DRIFT_FAULTS[:2]:
        add_fault(
            world, drift, stamp, "THERM-110", "Cleared", "BMS",
            world.named["drift_sensor"], "ENG-118", "JOB-6602",
            DRIFT_REPLACE, "False thermal warning from a drifting sensor",
            "Pack current and voltage stayed normal. Warning cleared after the sensor swap.",
        )

    power = world.named["power_inv"]
    world.named["flt_power"] = add_fault(
        world, power, POWER_DROP, "INV-402", "Active", "Inverter Controller",
        world.named["power_module"], "ENG-125", "JOB-6701",
        notes="AC power fell from about 78 kW to 6.5 kW in one sample. Grid frequency and voltage stayed nominal. DC bus sagged.",
    )

    soc = world.named["soc_bat"]
    world.named["flt_soc"] = add_fault(
        world, soc, SOC_STEP, "BAT-330", "Active", "BMS",
        component_of(world, soc, "BMS"), "ENG-101", "JOB-6801",
        notes="SOC stepped without a matching current. Cause is not confirmed.",
    )

    world.named["flt_hist_a"] = add_fault(
        world, world.named["hist_a"], at(2026, 9, 8, 19, 10), "REL-204", "Cleared", "BMS",
        component_of(world, world.named["hist_a"], "Contactor"), "ENG-104", "JOB-6901",
        at(2026, 9, 10, 11, 0), "Replaced contactor coil driver",
        "Contactor opened under load. Coil current was zero while the close command was present.",
    )
    world.named["flt_hist_b"] = add_fault(
        world, world.named["hist_b"], at(2026, 9, 11, 18, 30), "REL-210", "Cleared", "BMS",
        component_of(world, world.named["hist_b"], "Relay"), "ENG-104", "JOB-6902",
        at(2026, 9, 14, 9, 20), "Replaced open precharge resistor",
        "Contactor stayed open because DC bus voltage did not rise. Coil current was present. Different cause from the coil-driver case.",
    )

    freq = world.named["freq_inv"]
    world.named["flt_freq"] = add_fault(
        world, freq, FREQ_PEAK, "GRID-302", "Acknowledged", "Inverter Controller",
        component_of(world, freq, "Inverter Controller"), "ENG-110", "JOB-7001",
        notes="Grid frequency reached 61.28 Hz. The inverter latched at zero power after frequency returned.",
    )
    add_fault(
        world, freq, FREQ_PEAK + timedelta(minutes=20), "INV-201", "Acknowledged", "Inverter Controller",
        component_of(world, freq, "Inverter Controller"), "ENG-110", "JOB-7001",
        notes="Protection latch after the frequency excursion. Grid was back inside band and the latch stayed set.",
    )

    pro_temp = world.named["pro_temp"]
    world.named["flt_pro_temp"] = add_fault(
        world, pro_temp, at(2026, 9, 25, 15, 0), "BAT-141", "Acknowledged", "BMS",
        component_of(world, pro_temp, "Cooling Fan"), "", "",
        notes="Early warning only. Temperature is elevated and flat, below the THERM-201 threshold. Pack is still online.",
    )
    for stamp in (at(2026, 9, 18, 2, 20), at(2026, 9, 20, 7, 40), at(2026, 9, 23, 1, 0), at(2026, 9, 26, 4, 40)):
        fault_id = add_fault(
            world, world.named["pro_minor"], stamp, "BMS-218", "Recurring", "BMS",
            component_of(world, world.named["pro_minor"], "BMS"), "", "",
            notes="Short watchdog restart. The pack returned and stayed online. Early warning, not a failed system.",
        )
        world.named["flt_pro_minor"] = fault_id

    # Transient false alarms on healthy devices. Telemetry stays inside normal bands.
    for alias, code in (
        ("healthy_Battery_2", "BAT-101"),
        ("healthy_Inverter_1", "INV-318"),
        ("healthy_Gateway_1", "COM-118"),
    ):
        device_id = world.named[alias]
        stamp = at(2026, 9, 17, 9, 20)
        add_fault(
            world, device_id, stamp, code, "Cleared", "NOC",
            "", "TECH-221", "", stamp + timedelta(minutes=20), "Transient false alarm",
            "Single poll outside the threshold. Following samples stayed inside normal limits.",
        )

    # A few additional cleared nuisance faults so the fault table is not only the scripted set.
    extras = [
        ("hist_a", "BMS-104", at(2026, 9, 5, 8, 0)),
        ("hist_b", "BAT-102", at(2026, 9, 6, 5, 40)),
        ("pro_temp", "BMS-104", at(2026, 9, 14, 6, 20)),
    ]
    for role, code, stamp in extras:
        add_fault(
            world, world.named[role], stamp, code, "Cleared", "BMS",
            "", "", "", stamp + timedelta(minutes=40), "Informational, no fault found",
            "Expected operating message, closed by the NOC.",
        )


def add_incident(world, title, severity, status, created, resolved, device_ids, subsystem,
                 suspected, confirmed, impact, mitigation, permanent, fw_related, fw_version):
    sites = sorted({next(d["site_id"] for d in world.devices if d["device_id"] == device_id) for device_id in device_ids})
    row = {
        "incident_id": f"INC-{len(world.incidents)+1:03d}",
        "incident_title": title,
        "severity": severity,
        "status": status,
        "created_at": fmt(created),
        "resolved_at": fmt(resolved) if resolved else "",
        "affected_device_count": str(len(device_ids)),
        "affected_site_count": str(len(sites)),
        "primary_subsystem": subsystem,
        "suspected_root_cause": suspected,
        "confirmed_root_cause": confirmed,
        "impact": impact,
        "mitigation": mitigation,
        "permanent_fix": permanent,
        "firmware_related": "true" if fw_related else "false",
        "related_firmware_version": fw_version,
    }
    world.incidents.append(row)
    return row["incident_id"]


def add_event(world, incident_id, ts, event_type, engineer, description, evidence):
    world.events.append({
        "event_id": f"IEV-{len(world.events)+1:04d}",
        "incident_id": incident_id,
        "timestamp": fmt(ts),
        "event_type": event_type,
        "engineer": engineer,
        "description": description,
        "evidence_reference": evidence,
    })


def build_scripted_incidents(world):
    thermal = world.named["thermal"]
    inc = add_incident(
        world,
        "Pack thermal shutdown on Copper Elm Node",
        "Critical", "Resolved", THERMAL_WARN, at(2026, 9, 27, 15, 10),
        [thermal], "Thermal",
        "Cooling fan stopped during a sustained discharge.",
        "Cooling fan bearing seizure caused a real pack temperature rise and a THERM-201 protective shutdown.",
        f"{thermal} went offline after pack temperature climbed from about 34 C to about 73 C.",
        "Pack left offline. Temperature threshold was not raised.",
        f"Replace cooling fan {world.named['thermal_fan']} and recommission {thermal}.",
        False, "",
    )
    world.named["inc_thermal"] = inc
    check(inc == "INC-001", "thermal incident must be INC-001")
    timeline = [
        (THERMAL_WARN, "Alert", "ENG-104", "THERM-110 warning while pack temperature was rising.", world.named["flt_thermal_warn"]),
        (at(2026, 9, 26, 14, 55), "Investigation Started", "ENG-104", "Engineer opened the thermal shutdown investigation.", thermal),
        (at(2026, 9, 26, 15, 20), "Telemetry Reviewed", "ENG-104", "Temperature rose for hours under discharge before the trip. It did not snap back.", "DEV-001 telemetry 2026-09-26T08:00 to 2026-09-26T14:40"),
        (at(2026, 9, 26, 15, 40), "Fault Identified", "ENG-104", "THERM-201 opened the contactors. Cooling fan tach was zero.", world.named["flt_thermal"]),
        (at(2026, 9, 26, 16, 10), "Firmware Compared", "ENG-104", "Device is on 4.2.1, the previous stable image. No 4.3.0 heartbeat signature.", "firmware 4.2.1"),
        (at(2026, 9, 26, 16, 30), "Configuration Checked", "ENG-104", "Temperature threshold matches the expected 60 C. This is not a configuration mismatch.", "Temperature Threshold"),
        (at(2026, 9, 26, 17, 10), "Root Cause Suspected", "ENG-104", "Suspected cooling fan seizure because temperature rose with current and fan tach was zero.", world.named["thermal_fan"]),
        (at(2026, 9, 26, 18, 40), "Root Cause Confirmed", "ENG-104", "Confirmed cooling fan bearing seizure. The temperature sensor agreed with the rise, so this is not sensor drift.", world.named["thermal_fan"]),
        (at(2026, 9, 27, 9, 0), "Fix Developed", "ENG-125", "Fan replacement and recommission procedure issued. Threshold change rejected.", "DOC thermal runbook"),
        (at(2026, 9, 27, 13, 30), "Fix Deployed", "TECH-210", "Replacement fan kit issued to the site. The pack stays offline until the fan is installed.", "JOB-6102"),
        (at(2026, 9, 27, 15, 10), "Incident Resolved", "ENG-104", "Investigation closed. The pack is still offline pending the physical fan replacement.", inc),
    ]
    for item in timeline:
        add_event(world, inc, *item)

    fw_devices = [world.named[role] for role in ("fw_rollback_gw", "fw_fixed_gw", "fw_stuck_bat", "fw_stuck_gw", "fw_rollback_inv")]
    inc = add_incident(
        world,
        "Heartbeat session drops after 4.3.0",
        "High", "Mitigated", FW_UPGRADE + timedelta(hours=5), None,
        fw_devices, "Communications",
        "4.3.0 heartbeat state machine.",
        "Firmware 4.3.0 drops healthy sessions when one-way latency exceeds 120 ms. 4.3.1 restores the 4.2.1 heartbeat timing.",
        "Five devices raised COM-214 after the 15 Sep 4.3.0 window. Signal strength did not fall.",
        "4.3.0 rollout halted. Two devices rolled back to 4.2.1. One gateway upgraded to 4.3.1.",
        "Move remaining 4.3.0 devices to 4.3.1. Do not deploy 4.3.0.",
        True, "4.3.0",
    )
    world.named["inc_firmware"] = inc
    add_event(world, inc, FW_UPGRADE + timedelta(hours=5), "Alert", "ENG-110", "COM-214 raised on devices that had just taken 4.3.0.", world.named["flt_fw_stuck_bat"])
    add_event(world, inc, at(2026, 9, 15, 9, 0), "Investigation Started", "ENG-110", "Compared install time to the first COM-214 on each device.", "device_firmware_history")
    add_event(world, inc, at(2026, 9, 15, 11, 30), "Telemetry Reviewed", "ENG-110", "Latency stepped up at the 4.3.0 install. Signal strength stayed near -64 dBm.", "gateway telemetry")
    add_event(world, inc, at(2026, 9, 15, 13, 0), "Fault Identified", "ENG-110", "COM-214 and FW-210 share the 4.3.0 heartbeat signature.", "COM-214")
    add_event(world, inc, at(2026, 9, 15, 15, 0), "Firmware Compared", "ENG-110", "4.2.1 uses a fixed heartbeat. 4.3.0 moved timeout handling into the session layer and drops sessions above 120 ms.", "4.2.1 vs 4.3.0")
    add_event(world, inc, at(2026, 9, 16, 10, 0), "Configuration Checked", "ENG-110", "Communication timeout values match the approved 30 s setting on the affected devices.", "Communication Timeout")
    add_event(world, inc, at(2026, 9, 16, 14, 0), "Root Cause Suspected", "ENG-110", "Suspected the 4.3.0 heartbeat change because peers on 4.2.1 did not drop.", "firmware_versions 4.3.0")
    add_event(world, inc, at(2026, 9, 17, 16, 0), "Root Cause Confirmed", "ENG-110", "Lab test of 4.3.0 reproduced COM-214 at 180 ms induced latency. 4.2.1 did not.", "TEST heartbeat")
    add_event(world, inc, at(2026, 9, 19, 18, 0), "Fix Developed", "ENG-125", "4.3.1 restores 4.2.1 heartbeat timing and keeps compressed frames.", "4.3.1")
    add_event(world, inc, FW_PATCH, "Fix Deployed", "ENG-110", "4.3.1 installed on the Cedar Park gateway. Rollback remains in place on the other recovered devices.", world.named["fw_fixed_gw"])
    add_event(world, inc, at(2026, 9, 21, 9, 0), "Incident Resolved", "ENG-110", "Mitigation is in place. Two devices are still on 4.3.0 and the incident stays in monitoring until they move.", inc)
    # Status stays Mitigated because two devices remain on 4.3.0. The event records the engineering conclusion.
    world.incidents[-1]["status"] = "Mitigated"
    world.incidents[-1]["resolved_at"] = ""

    config = world.named["config_inv"]
    inc = add_incident(
        world,
        "Inverter power capped by a mismatched limit",
        "High", "Resolved", at(2026, 9, 14, 18, 20), CONFIG_FIX + timedelta(hours=2),
        [config], "Inverter",
        "Inverter Power Limit left at 75 kW against the expected 90 kW.",
        "A field edit set Inverter Power Limit to 75 kW. The approved expected value is 90 kW. Restoring 90 kW cleared the repeated INV-360 faults.",
        "Afternoon discharge on the Limestone Yard inverter flatlined near 75 kW from 14 Sep through 17 Sep.",
        "Power limit restored to 90 kW on 18 Sep.",
        "Require an engineering change before a field edit to Inverter Power Limit.",
        False, "",
    )
    world.named["inc_config"] = inc
    add_event(world, inc, at(2026, 9, 14, 18, 20), "Alert", "ENG-125", "INV-360 repeated during the evening discharge.", config)
    add_event(world, inc, at(2026, 9, 15, 9, 0), "Investigation Started", "ENG-125", "Opened after the second capped discharge.", "INV-360")
    add_event(world, inc, at(2026, 9, 16, 11, 0), "Telemetry Reviewed", "ENG-125", "Unconstrained shape would have reached the high 80s. Measured power stopped at 75 kW.", "inverter telemetry")
    add_event(world, inc, at(2026, 9, 17, 18, 10), "Fault Identified", "ENG-125", "CFG-101 matched the cap.", world.named["flt_config"])
    add_event(world, inc, at(2026, 9, 18, 8, 0), "Firmware Compared", "ENG-125", "Inverter firmware was not changed during the fault window.", "4.2.1")
    add_event(world, inc, at(2026, 9, 18, 8, 40), "Configuration Checked", "ENG-125", "Found Inverter Power Limit parameter_value 75 kW, expected_value 90 kW, status Mismatch.", "CFG Inverter Power Limit")
    add_event(world, inc, at(2026, 9, 18, 9, 10), "Root Cause Suspected", "ENG-125", "The 75 kW value explains the flat afternoon peak.", "configuration")
    add_event(world, inc, CONFIG_FIX, "Root Cause Confirmed", "ENG-110", "After the value returned to 90 kW the next discharge was no longer capped.", "CONFIG_FIX")
    add_event(world, inc, CONFIG_FIX + timedelta(minutes=30), "Fix Developed", "ENG-110", "Restore the approved limit and keep the old row for audit.", "ECR config")
    add_event(world, inc, CONFIG_FIX + timedelta(hours=1), "Fix Deployed", "ENG-110", "Running configuration set to 90 kW.", config)
    add_event(world, inc, CONFIG_FIX + timedelta(hours=2), "Incident Resolved", "ENG-110", "Faults stopped after the configuration correction.", inc)

    comm = world.named["comm_gw"]
    inc = add_incident(
        world,
        "Gateway link loss after signal collapse",
        "High", "Resolved", COMM_WARN, at(2026, 9, 26, 16, 0),
        [comm], "Communications",
        "Radio path or antenna failure.",
        "Gateway radio path failed. Latency rose and signal strength fell together, then the gateway went offline. Firmware remained 4.2.1.",
        f"{comm} stopped reporting at 2026-09-25 02:00 after RSSI fell past -100 dBm.",
        "Site dispatched for antenna and radio replacement. Neighboring gateways on 4.3.0 were not part of this path failure.",
        "Replace the gateway radio module and re-aim the antenna.",
        False, "",
    )
    world.named["inc_comm"] = inc
    add_event(world, inc, COMM_WARN, "Alert", "ENG-104", "COM-118 gaps started as RSSI fell.", "COM-118")
    add_event(world, inc, at(2026, 9, 25, 8, 0), "Investigation Started", "ENG-104", "Gateway was offline at the morning check.", comm)
    add_event(world, inc, at(2026, 9, 25, 9, 30), "Telemetry Reviewed", "ENG-104", "From 18:00 on 24 Sep, latency climbed and signal strength fell. Both moved, which is not the 4.3.0 pattern.", "gateway telemetry")
    add_event(world, inc, at(2026, 9, 25, 10, 0), "Fault Identified", "ENG-104", "COM-101 link loss.", world.named["flt_comm"])
    add_event(world, inc, at(2026, 9, 25, 11, 0), "Firmware Compared", "ENG-104", "Gateway is on 4.2.1 with no 4.3.0 install. COM-214 was not raised.", "firmware 4.2.1")
    add_event(world, inc, at(2026, 9, 25, 11, 30), "Configuration Checked", "ENG-104", "Communication timeout is the expected 30 s.", "Communication Timeout")
    add_event(world, inc, at(2026, 9, 25, 13, 0), "Root Cause Suspected", "ENG-104", "Suspected the radio path because signal strength collapsed with latency.", world.named["comm_radio"])
    add_event(world, inc, at(2026, 9, 25, 16, 0), "Root Cause Confirmed", "ENG-104", "Confirmed a failed gateway radio path. Distinct from the firmware heartbeat regression.", world.named["flt_comm"])
    add_event(world, inc, at(2026, 9, 26, 9, 0), "Fix Developed", "ENG-125", "Radio module replacement procedure.", "COM-101")
    add_event(world, inc, at(2026, 9, 26, 14, 0), "Fix Deployed", "TECH-210", "Replacement radio staged. Gateway has not returned to service in this snapshot.", comm)
    add_event(world, inc, at(2026, 9, 26, 16, 0), "Incident Resolved", "ENG-104", "Cause closed as a radio path failure. Device remains offline until the swap.", inc)

    repeats = [world.named[role] for role in ("repeat_a", "repeat_b", "repeat_c")]
    inc = add_incident(
        world,
        "HW-C cell imbalance at three sites",
        "High", "Mitigated", at(2026, 9, 16, 14, 0), None,
        repeats, "Battery",
        "Shared HW-C power-module busbar torque issue.",
        "HW-C power-module busbar torque below spec causes cell-group voltage imbalance under discharge above 70 kW.",
        "BAT-204 recurred at three sites on HW-C packs during similar late-day discharge.",
        "Discharge on the three packs capped at 60 kW until the busbars are re-torqued.",
        "Re-torque the HW-C busbar and add the torque check to the HW-C installation guide.",
        False, "",
    )
    world.named["inc_repeat"] = inc
    add_event(world, inc, at(2026, 9, 16, 14, 0), "Alert", "ENG-125", "First BAT-204 on an HW-C pack.", world.named["repeat_a"])
    add_event(world, inc, at(2026, 9, 19, 15, 0), "Investigation Started", "ENG-125", "Second site repeated the same code.", world.named["repeat_b"])
    add_event(world, inc, at(2026, 9, 22, 14, 0), "Telemetry Reviewed", "ENG-125", "Pack voltage swung between about 705 V and 812 V before the fault. Peers on other revisions did not.", "voltage telemetry")
    add_event(world, inc, at(2026, 9, 22, 15, 0), "Fault Identified", "ENG-125", "BAT-204 on all three HW-C batteries.", world.named["flt_repeat"])
    add_event(world, inc, at(2026, 9, 23, 10, 0), "Firmware Compared", "ENG-125", "The three packs are not on a shared new firmware image. Hardware revision is the common field.", "HW-C")
    add_event(world, inc, at(2026, 9, 23, 11, 0), "Configuration Checked", "ENG-125", "Current limits match the expected 120 A. Not a configuration mismatch.", "Max Discharge Current")
    add_event(world, inc, at(2026, 9, 24, 9, 0), "Root Cause Suspected", "ENG-125", "Suspected HW-C busbar torque after the common revision and discharge condition lined up.", world.named["repeat_module"])
    add_event(world, inc, at(2026, 9, 25, 16, 0), "Root Cause Confirmed", "ENG-125", "Confirmed low busbar torque on the HW-C power module.", "HW-C")
    add_event(world, inc, at(2026, 9, 26, 11, 0), "Fix Developed", "ENG-125", "Torque campaign and a temporary 60 kW discharge cap.", "ECR torque")
    add_event(world, inc, at(2026, 9, 27, 9, 0), "Fix Deployed", "TECH-214", "Discharge cap applied. Physical re-torque is not finished.", repeats[0])

    drift = world.named["drift_bat"]
    inc = add_incident(
        world,
        "False thermal warnings from a drifting pack sensor",
        "Medium", "Resolved", DRIFT_FAULTS[0], DRIFT_REPLACE + timedelta(hours=3),
        [drift], "Thermal",
        "Temperature sensor drift rather than a real pack heat rise.",
        "The pack temperature sensor drifted high over four days and snapped back to about 28 C when it was replaced. Cooling and current were normal.",
        "False THERM-110 warnings. The pack stayed online. This is not the Copper Elm thermal shutdown.",
        "Ignored the high channel after the redundant channel stayed normal, then replaced the sensor.",
        f"Replaced {world.named['drift_sensor']} with {world.named['drift_sensor_new']}.",
        False, "",
    )
    world.named["inc_drift"] = inc
    add_event(world, inc, DRIFT_FAULTS[0], "Alert", "ENG-118", "THERM-110 on a pack whose current was not high.", drift)
    add_event(world, inc, at(2026, 9, 22, 9, 0), "Investigation Started", "ENG-118", "Warnings repeated without a shutdown.", "THERM-110")
    add_event(world, inc, at(2026, 9, 23, 10, 0), "Telemetry Reviewed", "ENG-118", "Temperature climbed smoothly for days and voltage stayed steady. A real thermal mass would not snap back in one sample.", "drift telemetry")
    add_event(world, inc, DRIFT_FAULTS[-1], "Fault Identified", "ENG-118", "THERM-155 rate-of-change fault.", world.named["flt_drift"])
    add_event(world, inc, at(2026, 9, 23, 19, 0), "Firmware Compared", "ENG-118", "Firmware matches healthy packs.", "4.2.1")
    add_event(world, inc, at(2026, 9, 23, 19, 30), "Configuration Checked", "ENG-118", "Temperature threshold is the expected 60 C.", "Temperature Threshold")
    add_event(world, inc, at(2026, 9, 24, 8, 0), "Root Cause Suspected", "ENG-118", "Suspected the temperature sensor because the rise ignored current.", world.named["drift_sensor"])
    add_event(world, inc, DRIFT_REPLACE, "Root Cause Confirmed", "ENG-118", "Confirmed sensor drift. Temperature returned to the high 20s immediately after replacement.", world.named["drift_sensor_new"])
    add_event(world, inc, DRIFT_REPLACE + timedelta(hours=1), "Fix Developed", "ENG-118", "Sensor replacement, not a fan replacement and not a threshold change.", "THERM-155")
    add_event(world, inc, DRIFT_REPLACE + timedelta(hours=2), "Fix Deployed", "TECH-221", "New temperature sensor installed.", world.named["drift_sensor_new"])
    add_event(world, inc, DRIFT_REPLACE + timedelta(hours=3), "Incident Resolved", "ENG-118", "False thermal alerts stopped. Pack remained online throughout.", inc)

    power = world.named["power_inv"]
    inc = add_incident(
        world,
        "Sudden inverter power collapse",
        "High", "Mitigated", POWER_DROP, None,
        [power], "Inverter",
        "Power module or gate driver failed while the grid stayed nominal.",
        "Inverter power module failed. Output fell from about 78 kW to 6.5 kW in one 20-minute sample while grid frequency stayed near 60 Hz and the DC bus sagged.",
        f"{power} remains faulted. The site lost the evening discharge.",
        "Site transferred the evening discharge to the utility feed.",
        "Replace the inverter power module. Waiting on the replacement part.",
        False, "",
    )
    world.named["inc_power"] = inc
    add_event(world, inc, POWER_DROP, "Alert", "ENG-125", "INV-402 at the evening peak.", world.named["flt_power"])
    add_event(world, inc, at(2026, 9, 23, 18, 10), "Investigation Started", "ENG-125", "Output did not recover on the next samples.", power)
    add_event(world, inc, at(2026, 9, 23, 19, 0), "Telemetry Reviewed", "ENG-125", "Power stepped from about 78 kW to 6.5 kW. Grid frequency did not excursion.", "inverter telemetry")
    add_event(world, inc, at(2026, 9, 23, 19, 20), "Fault Identified", "ENG-125", "INV-402 with a sagging DC bus.", world.named["flt_power"])
    add_event(world, inc, at(2026, 9, 24, 9, 0), "Firmware Compared", "ENG-125", "No firmware change on the day of the drop.", "firmware history")
    add_event(world, inc, at(2026, 9, 24, 9, 30), "Configuration Checked", "ENG-125", "Inverter Power Limit matches 90 kW. This is not the 75 kW mismatch pattern.", "Inverter Power Limit")
    add_event(world, inc, at(2026, 9, 24, 11, 0), "Root Cause Suspected", "ENG-125", "Suspected the power module because the bus sagged and the grid did not.", world.named["power_module"])
    add_event(world, inc, at(2026, 9, 25, 10, 0), "Root Cause Confirmed", "ENG-125", "Confirmed a failed inverter power module.", world.named["power_module"])
    add_event(world, inc, at(2026, 9, 25, 15, 0), "Fix Developed", "ENG-125", "Power module replacement.", "INV-402")
    add_event(world, inc, at(2026, 9, 26, 11, 0), "Fix Deployed", "ENG-125", "Replacement is not installed. The ticket is blocked on the part.", "parts hold")

    soc = world.named["soc_bat"]
    inc = add_incident(
        world,
        "Unexpected SOC step with no confirmed cause",
        "High", "Investigating", SOC_STEP + timedelta(minutes=30), None,
        [soc], "Battery",
        "Unconfirmed hypotheses: SOC estimator bias, current-sensor offset, or standby parasitic load. None confirmed.",
        UNDER,
        f"{soc} reported SOC fell by about 50 points at 03:20 on 21 Sep while current and power stayed near zero at that sample.",
        "Discharge power limited to 40 kW while the investigation continues. No part has been condemned.",
        "",
        False, "",
    )
    world.named["inc_soc"] = inc
    check(inc == "INC-008", "unknown-cause incident must be INC-008")
    add_event(world, inc, SOC_STEP + timedelta(minutes=30), "Alert", "ENG-101", "BAT-330 unexpected SOC step.", world.named["flt_soc"])
    add_event(world, inc, at(2026, 9, 21, 8, 0), "Investigation Started", "ENG-101", "Opened because the step had no matching energy.", soc)
    add_event(world, inc, at(2026, 9, 21, 10, 0), "Telemetry Reviewed", "ENG-101", "At 03:20 SOC stepped down while battery current and charge/discharge power were near zero. Several explanations still fit.", "SOC telemetry")
    add_event(world, inc, at(2026, 9, 21, 11, 0), "Fault Identified", "ENG-101", "BAT-330 is the symptom code. It does not name a cause.", world.named["flt_soc"])
    add_event(world, inc, at(2026, 9, 22, 9, 0), "Firmware Compared", "ENG-101", "Firmware is 4.2.1, the same image as healthy peers. No regression signature.", "4.2.1")
    add_event(world, inc, at(2026, 9, 22, 11, 0), "Configuration Checked", "ENG-101", "SOC minimum and maximum match the approved values. The step is not a configuration mismatch.", "SOC Maximum")
    add_event(world, inc, at(2026, 9, 23, 15, 0), "Root Cause Suspected", "ENG-101", "Hypotheses recorded: estimator bias, current-sensor offset, standby parasitic load. None confirmed.", soc)

    hist_a = world.named["hist_a"]
    hist_b = world.named["hist_b"]
    shared_symptom = "The pack opened the main contactor during a routine discharge and stayed offline until repaired. No thermal alarm and no firmware change in the prior 7 days."
    inc = add_incident(
        world,
        "Contactor opened during discharge",
        "High", "Closed", at(2026, 9, 8, 19, 20), at(2026, 9, 10, 15, 0),
        [hist_a], "Battery",
        "Contactor coil driver.",
        "Contactor coil driver failed. Coil current stayed at zero while the close command was present.",
        shared_symptom,
        "Pack left open until the driver was replaced.",
        "Replaced the contactor coil driver.",
        False, "",
    )
    world.named["inc_hist_a"] = inc
    add_event(world, inc, at(2026, 9, 8, 19, 20), "Alert", "ENG-104", "BAT-340 contactor opened under load.", world.named["flt_hist_a"])
    add_event(world, inc, at(2026, 9, 8, 20, 0), "Investigation Started", "ENG-104", "Same outward symptom as other unexpected shutdowns.", hist_a)
    add_event(world, inc, at(2026, 9, 9, 9, 0), "Telemetry Reviewed", "ENG-104", "Current fell to zero when the contactor opened. Temperature was normal.", hist_a)
    add_event(world, inc, at(2026, 9, 9, 10, 0), "Fault Identified", "ENG-104", "REL-204 coil driver fault. Coil current was zero.", world.named["flt_hist_a"])
    add_event(world, inc, at(2026, 9, 9, 11, 0), "Firmware Compared", "ENG-104", "No firmware change in the prior week.", "firmware history")
    add_event(world, inc, at(2026, 9, 9, 11, 30), "Configuration Checked", "ENG-104", "No contactor timing parameter was edited.", "configuration")
    add_event(world, inc, at(2026, 9, 9, 14, 0), "Root Cause Suspected", "ENG-104", "Suspected the coil driver because coil current was zero.", "REL-204")
    add_event(world, inc, at(2026, 9, 10, 9, 0), "Root Cause Confirmed", "ENG-104", "Confirmed a failed contactor coil driver. This is not a precharge-resistor failure.", "REL-204")
    add_event(world, inc, at(2026, 9, 10, 10, 0), "Fix Developed", "ENG-104", "Replace the coil driver.", "REL-204")
    add_event(world, inc, at(2026, 9, 10, 11, 0), "Fix Deployed", "TECH-210", "Driver replaced.", hist_a)
    add_event(world, inc, at(2026, 9, 10, 15, 0), "Incident Resolved", "ENG-104", "Pack returned to service. Closed after a clean discharge.", inc)

    inc = add_incident(
        world,
        "Contactor opened during discharge",
        "High", "Closed", at(2026, 9, 11, 18, 40), at(2026, 9, 14, 12, 0),
        [hist_b], "Battery",
        "Precharge resistor.",
        "Precharge resistor was open. The main contactor correctly stayed open because DC bus voltage did not rise. Coil current was present.",
        shared_symptom,
        "Pack left open until the precharge resistor was replaced.",
        "Replaced the precharge resistor.",
        False, "",
    )
    world.named["inc_hist_b"] = inc
    add_event(world, inc, at(2026, 9, 11, 18, 40), "Alert", "ENG-104", "Contactor did not close for discharge. Outward symptom matches the 8 Sep event.", world.named["flt_hist_b"])
    add_event(world, inc, at(2026, 9, 11, 19, 10), "Investigation Started", "ENG-104", "Compared with the coil-driver shutdown before assuming the same part.", hist_b)
    add_event(world, inc, at(2026, 9, 12, 9, 0), "Telemetry Reviewed", "ENG-104", "No DC bus rise during precharge. Temperature was normal.", hist_b)
    add_event(world, inc, at(2026, 9, 12, 10, 0), "Fault Identified", "ENG-104", "REL-210 precharge resistor open. Coil current was present, unlike REL-204.", world.named["flt_hist_b"])
    add_event(world, inc, at(2026, 9, 12, 11, 0), "Firmware Compared", "ENG-104", "Firmware matches the other pack. Not a firmware split.", "firmware history")
    add_event(world, inc, at(2026, 9, 12, 11, 20), "Configuration Checked", "ENG-104", "Precharge timer matches the expected value.", "configuration")
    add_event(world, inc, at(2026, 9, 13, 9, 0), "Root Cause Suspected", "ENG-104", "Suspected the precharge resistor because voltage did not rise.", "REL-210")
    add_event(world, inc, at(2026, 9, 13, 15, 0), "Root Cause Confirmed", "ENG-104", "Confirmed an open precharge resistor. The coil driver from the earlier incident was healthy.", "REL-210")
    add_event(world, inc, at(2026, 9, 14, 8, 0), "Fix Developed", "ENG-104", "Replace the precharge resistor only.", "REL-210")
    add_event(world, inc, at(2026, 9, 14, 9, 20), "Fix Deployed", "TECH-214", "Resistor replaced.", hist_b)
    add_event(world, inc, at(2026, 9, 14, 12, 0), "Incident Resolved", "ENG-104", "Pack returned to service. Same symptom as the coil-driver incident, different confirmed cause.", inc)

    freq = world.named["freq_inv"]
    inc = add_incident(
        world,
        "Inverter latched after a grid frequency excursion",
        "High", "Mitigated", FREQ_PEAK, None,
        [freq], "Grid",
        "Utility frequency disturbance.",
        "Grid frequency reached 61.28 Hz. The inverter protection latch held output at zero after frequency returned to 60 Hz.",
        "Evening discharge at Lantern Field did not run. The inverter is still faulted.",
        "Leave the latch set until a supervised reset. Do not replace the power module for this event.",
        "Supervised reset after the grid trace is archived.",
        False, "",
    )
    world.named["inc_freq"] = inc
    add_event(world, inc, FREQ_PEAK, "Alert", "ENG-110", "GRID-302 then INV-201.", world.named["flt_freq"])
    add_event(world, inc, at(2026, 9, 25, 14, 30), "Investigation Started", "ENG-110", "Output stayed at zero after the grid recovered.", freq)
    add_event(world, inc, at(2026, 9, 25, 15, 10), "Telemetry Reviewed", "ENG-110", "Frequency hit 61.28 Hz and power went to zero. Frequency later returned and power stayed at zero.", "frequency telemetry")
    add_event(world, inc, at(2026, 9, 25, 15, 40), "Fault Identified", "ENG-110", "GRID-302 excursion followed by INV-201 latch.", world.named["flt_freq"])
    add_event(world, inc, at(2026, 9, 25, 16, 20), "Firmware Compared", "ENG-110", "No new firmware. Protection behavior matches the spec.", "firmware history")
    add_event(world, inc, at(2026, 9, 25, 16, 40), "Configuration Checked", "ENG-110", "Grid frequency limit matches the expected 0.5 Hz band.", "Grid Frequency Limit")
    add_event(world, inc, at(2026, 9, 26, 9, 0), "Root Cause Suspected", "ENG-110", "Suspected a real grid excursion because the frequency trace left the band before the latch.", "GRID-302")
    add_event(world, inc, at(2026, 9, 26, 11, 0), "Root Cause Confirmed", "ENG-110", "Confirmed a grid frequency excursion and a latched protection trip. The power module is not the failed part.", "GRID-302")
    add_event(world, inc, at(2026, 9, 26, 15, 0), "Fix Developed", "ENG-110", "Supervised reset procedure. No hardware swap.", "runbook")

    pro_devices = [world.named[role] for role in ("pro_temp", "pro_gw", "pro_minor")]
    inc = add_incident(
        world,
        "Proactive watch: early signals on three online systems",
        "Medium", "Monitoring", at(2026, 9, 25, 16, 0), None,
        pro_devices, "Battery",
        "No failure yet. Early signals only: flat elevated temperature, slowly rising latency, and repeated short watchdog restarts.",
        "",
        "None of the three devices is offline or faulted. The signals are below trip thresholds.",
        "Watch list only. Do not roll a firmware image or replace hardware on this evidence alone.",
        "",
        False, "",
    )
    world.named["inc_pro"] = inc
    add_event(world, inc, at(2026, 9, 25, 16, 0), "Alert", "ENG-101", "Watch items crossed the proactive review line.", "alerts")
    add_event(world, inc, at(2026, 9, 26, 9, 0), "Investigation Started", "ENG-101", "Opened a monitoring incident so the three signals stay visible.", "proactive")
    add_event(world, inc, at(2026, 9, 26, 11, 0), "Telemetry Reviewed", "ENG-101", "Temperature is stuck near 40 C, gateway latency is climbing through about 140 ms with stable RSSI, and the third pack shows isolated restarts.", "telemetry")
    add_event(world, inc, at(2026, 9, 27, 10, 0), "Configuration Checked", "ENG-101", "No mismatched limits on the three devices.", "configuration")


def build_anomalies(world):
    thermal = world.named["thermal"]
    world.named["ano_thermal"] = add_anomaly(
        world, thermal, THERMAL_RAMP_START, THERMAL_OFFLINE, "Temperature Spike",
        "battery_temperature_c", "24 to 35 C", "Critical", world.named["flt_thermal"],
        "Real pack temperature rise under discharge before THERM-201 and the offline transition.",
    )
    add_anomaly(
        world, thermal, CURRENT_SPIKE - STEP, CURRENT_SPIKE + STEP, "Current Spike",
        "battery_current", "-120 to 120 A", "Warning", world.named["flt_spike"],
        "Single-sample charge current spike on 15 Sep. Cleared as a transient and unrelated to the thermal shutdown.",
    )
    world.named["ano_voltage"] = add_anomaly(
        world, world.named["repeat_a"], VOLT_WINDOWS[-1][0], VOLT_WINDOWS[-1][1], "Voltage Instability",
        "battery_voltage", "740 to 770 V", "Error", world.named["flt_repeat"],
        "Pack voltage alternated well outside the normal band before the BAT-204 fault.",
    )
    add_anomaly(
        world, world.named["repeat_b"], VOLT_WINDOWS[-1][0], VOLT_WINDOWS[-1][1], "Voltage Instability",
        "battery_voltage", "740 to 770 V", "Error", "",
        "Second HW-C pack showing the same voltage swing during discharge.",
    )
    world.named["ano_comm"] = add_anomaly(
        world, world.named["comm_gw"], COMM_START, COMM_OFFLINE, "Communication Degradation",
        "communication_latency_ms", "15 to 50 ms", "Error", world.named["flt_comm"],
        "Latency climbed and signal strength fell before the gateway went offline.",
    )
    add_anomaly(
        world, world.named["comm_gw"], COMM_START, COMM_OFFLINE, "Unexpected Shutdown",
        "signal_strength_dbm", "-75 to -55 dBm", "Error", world.named["flt_comm"],
        "Signal strength collapse ending in an offline gateway. Both latency and RSSI moved.",
    )
    world.named["ano_soc"] = add_anomaly(
        world, world.named["soc_bat"], SOC_STEP - STEP, SOC_STEP + timedelta(hours=2), "SOC Anomaly",
        "battery_soc_percent", "25 to 90 %", "Error", world.named["flt_soc"],
        "SOC stepped sharply. At the step, current and power were near zero. Cause is not confirmed.",
    )
    world.named["ano_power"] = add_anomaly(
        world, world.named["power_inv"], POWER_DROP - timedelta(hours=2), POWER_DROP + timedelta(hours=2),
        "Power Drop", "inverter_power_kw", "60 to 90 kW during the evening peak", "Error",
        world.named["flt_power"],
        "Evening power fell from the normal peak to about 6.5 kW in one sample and stayed down.",
    )
    world.named["ano_freq"] = add_anomaly(
        world, world.named["freq_inv"], FREQ_START - STEP, FREQ_RECOVER, "Frequency Anomaly",
        "grid_frequency_hz", "59.95 to 60.05 Hz", "Error", world.named["flt_freq"],
        "Grid frequency left the normal band and the inverter then held power at zero.",
    )
    world.named["ano_drift"] = add_anomaly(
        world, world.named["drift_bat"], DRIFT_START, DRIFT_REPLACE - STEP, "Sensor Drift",
        "battery_temperature_c", "24 to 35 C", "Warning", world.named["flt_drift"],
        "Slow temperature climb over days with normal voltage. Reading snapped back after the sensor was replaced.",
    )
    world.named["ano_fw"] = add_anomaly(
        world, world.named["fw_stuck_bat"], FW_UPGRADE, NOW, "Communication Degradation",
        "communication_latency_ms", "15 to 50 ms", "Error", world.named["flt_fw_stuck_bat"],
        "Latency stepped up at the 4.3.0 install and stayed high. Signal strength did not fall.",
    )
    add_anomaly(
        world, world.named["fw_rollback_gw"], FW_UPGRADE, FW_ROLLBACK - STEP, "Communication Degradation",
        "communication_latency_ms", "15 to 50 ms", "Error", world.named["flt_fw_rollback_gw"],
        "Latency was high only while 4.3.0 was installed. It returned to normal after the rollback to 4.2.1.",
    )
    add_anomaly(
        world, world.named["fw_fixed_gw"], FW_UPGRADE, FW_PATCH - STEP, "Communication Degradation",
        "communication_latency_ms", "15 to 50 ms", "Error", world.named["flt_fw_fixed_gw"],
        "Latency was high on 4.3.0 and returned to normal after 4.3.1.",
    )
    world.named["ano_pro_temp"] = add_anomaly(
        world, world.named["pro_temp"], PRO_TEMP_START, NOW, "Temperature Spike",
        "battery_temperature_c", "24 to 35 C", "Warning", world.named["flt_pro_temp"],
        "Early warning. Temperature is mildly elevated and flat, below the thermal shutdown threshold. Device is online.",
    )
    world.named["ano_pro_lat"] = add_anomaly(
        world, world.named["pro_gw"], PRO_LAT_START, NOW, "Communication Degradation",
        "communication_latency_ms", "15 to 50 ms", "Warning", "",
        "Latency is rising slowly and signal strength is stable. The gateway is still online. Not a 4.3.0 regression.",
    )
    world.named["ano_pro_restart"] = add_anomaly(
        world, world.named["pro_minor"], at(2026, 9, 18, 0, 0), NOW, "Repeated Restart",
        "communication_latency_ms", "15 to 50 ms", "Warning", world.named["flt_pro_minor"],
        "Four isolated watchdog restarts. The pack stays online between them.",
    )


def add_ticket(world, title, description, priority, status, created, engineer, subsystem,
               device_id, error_code, incident_id, root_cause, resolution, firmware):
    site_id = next(d["site_id"] for d in world.devices if d["device_id"] == device_id)
    row = {
        "ticket_id": f"ET-{len(world.tickets)+1:03d}",
        "title": title,
        "description": description,
        "priority": priority,
        "status": status,
        "created_at": fmt(created),
        "assigned_engineer": engineer,
        "subsystem": subsystem,
        "affected_device_id": device_id,
        "affected_site_id": site_id,
        "related_error_code": error_code,
        "related_incident_id": incident_id,
        "root_cause": root_cause,
        "resolution": resolution,
        "linked_firmware_version": firmware,
    }
    world.tickets.append(row)
    return row["ticket_id"]


def build_tickets(world):
    thermal = world.named["thermal"]
    world.named["et_thermal"] = add_ticket(
        world, "Explain the Copper Elm battery offline event",
        "Why did the battery go offline after the temperature rise?",
        "Critical", "Closed", THERMAL_WARN, "ENG-104", "Thermal", thermal, "THERM-201",
        world.named["inc_thermal"],
        "Cooling fan bearing seizure",
        "Investigation closed. Fan replacement is a separate open field ticket. Pack is still offline.",
        "4.2.1",
    )
    world.named["et_fan"] = add_ticket(
        world, "Replace the seized cooling fan",
        f"Install the replacement for {world.named['thermal_fan']} and recommission the pack.",
        "High", "Open", at(2026, 9, 27, 13, 40), "TECH-210", "Thermal", thermal, "THERM-201",
        world.named["inc_thermal"],
        "Cooling fan bearing seizure",
        "",
        "",
    )
    add_ticket(
        world, "Halt 4.3.0 and finish the 4.3.1 move",
        "COM-214 started after the 4.3.0 install. 4.3.1 clears it in test and on the patched gateway.",
        "Critical", "Investigating", at(2026, 9, 15, 9, 10), "ENG-110", "Firmware",
        world.named["fw_stuck_bat"], "COM-214", world.named["inc_firmware"],
        "Firmware 4.3.0 heartbeat regression",
        "",
        "4.3.0",
    )
    add_ticket(
        world, "Restore the Limestone inverter power limit",
        "Inverter Power Limit was 75 kW against an expected 90 kW. Afternoon peaks were capped.",
        "High", "Resolved", at(2026, 9, 15, 9, 20), "ENG-125", "Inverter",
        world.named["config_inv"], "CFG-101", world.named["inc_config"],
        "Configuration mismatch, 75 kW versus expected 90 kW",
        "Restored to 90 kW on 18 Sep. Later discharge peaks were no longer capped.",
        "",
    )
    add_ticket(
        world, "Owl Hollow gateway offline",
        "Latency and signal strength both collapsed before the gateway stopped reporting.",
        "High", "Resolved", COMM_WARN, "ENG-104", "Communications",
        world.named["comm_gw"], "COM-101", world.named["inc_comm"],
        "Gateway radio path failure",
        "Cause confirmed. Radio replacement is staged and the gateway is still offline.",
        "4.2.1",
    )
    add_ticket(
        world, "HW-C busbar torque campaign",
        "BAT-204 at three sites on HW-C under the same discharge condition.",
        "High", "Open", at(2026, 9, 22, 15, 10), "ENG-125", "Battery",
        world.named["repeat_a"], "BAT-204", world.named["inc_repeat"],
        "HW-C power-module busbar torque below spec",
        "",
        "",
    )
    add_ticket(
        world, "Blue Sage temperature sensor drift",
        "False thermal warnings. Voltage stayed normal and the reading snapped back after replacement.",
        "Medium", "Closed", DRIFT_FAULTS[0], "ENG-118", "Thermal",
        world.named["drift_bat"], "THERM-155", world.named["inc_drift"],
        "Temperature sensor drift",
        "Sensor replaced. Distinct from the Copper Elm cooling-fan shutdown.",
        "",
    )
    world.named["et_power"] = add_ticket(
        world, "Warm Spring inverter power collapse",
        "Power fell from about 78 kW to 6.5 kW in one sample with a normal grid.",
        "High", "Blocked", POWER_DROP, "ENG-125", "Inverter",
        world.named["power_inv"], "INV-402", world.named["inc_power"],
        "Failed inverter power module",
        "",
        "",
    )
    world.named["et_soc_1"] = add_ticket(
        world, "Investigate the unexpected SOC step",
        "Symptom is real. Do not close this ticket with a guessed cause.",
        "High", "Open", SOC_STEP + timedelta(hours=1), "ENG-101", "Battery",
        world.named["soc_bat"], "BAT-330", world.named["inc_soc"],
        UNDER, "", "",
    )
    world.named["et_soc_2"] = add_ticket(
        world, "Hold instruments for the SOC step",
        "A calibrated current sensor may be used later as a test. The test is not a confirmed fix.",
        "Medium", "Investigating", at(2026, 9, 22, 9, 30), "ENG-101", "BMS",
        world.named["soc_bat"], "BAT-330", world.named["inc_soc"],
        UNDER, "", "",
    )
    add_ticket(
        world, "Coil driver replacement follow-up",
        "Unexpected contactor open. Coil current was zero.",
        "Medium", "Closed", at(2026, 9, 8, 20, 0), "ENG-104", "Battery",
        world.named["hist_a"], "REL-204", world.named["inc_hist_a"],
        "Contactor coil driver failed",
        "Driver replaced and the pack returned to service.",
        "",
    )
    add_ticket(
        world, "Precharge resistor replacement follow-up",
        "Same outward contactor symptom as the coil-driver case. Voltage did not rise and coil current was present.",
        "Medium", "Closed", at(2026, 9, 11, 19, 0), "ENG-104", "Battery",
        world.named["hist_b"], "REL-210", world.named["inc_hist_b"],
        "Open precharge resistor",
        "Resistor replaced. Cause is not the coil driver.",
        "",
    )
    add_ticket(
        world, "Reset the latched inverter after the frequency excursion",
        "Frequency hit 61.28 Hz and the inverter stayed at zero power after the grid recovered.",
        "High", "Investigating", FREQ_PEAK, "ENG-110", "Grid",
        world.named["freq_inv"], "GRID-302", world.named["inc_freq"],
        "Grid frequency excursion with a latched inverter protection trip",
        "",
        "",
    )
    for role, title, code in (
        ("pro_temp", "Review mildly elevated pack temperature", "BAT-141"),
        ("pro_gw", "Review rising gateway latency", "GW-090"),
        ("pro_minor", "Review repeated watchdog restarts", "BMS-218"),
    ):
        add_ticket(
            world, title,
            "Device is still online. This is a proactive review, not a failed-system repair.",
            "Medium", "Open", at(2026, 9, 26, 9, 30), "ENG-101", "Battery" if role != "pro_gw" else "Gateway",
            world.named[role], code, world.named["inc_pro"],
            "", "", "",
        )

    # Tickets with no incident.
    loose = [
        ("Update the HW-C installation checklist", "Add the busbar torque check to the installation guide.", "Low", "Open", "Battery"),
        ("Lab bench time for the 4.3.1 heartbeat test", "Reserve the hardware-in-loop bench.", "Low", "Closed", "Firmware"),
        ("Archive the September frequency trace", "Store the grid trace with the incident package.", "Low", "Resolved", "Grid"),
        ("Order a spare Sill-90 power module", "Stock one module for the faulted inverter.", "Medium", "Blocked", "Inverter"),
    ]
    spare_device = world.named["healthy_Battery_1"]
    for title, description, priority, status, subsystem in loose:
        device_id = world.named["power_inv"] if "module" in title else spare_device
        add_ticket(
            world, title, description, priority, status, at(2026, 9, 12, 10, 0), "ENG-118",
            subsystem, device_id, "", "", "", "Completed." if status in ("Closed", "Resolved") else "", "",
        )


def add_alert(world, ts, alert_type, severity, device_id, metric, observed, threshold, description,
              status, action, error_code, incident_id):
    site_id = next(d["site_id"] for d in world.devices if d["device_id"] == device_id)
    world.alerts.append({
        "alert_id": f"EAL-{len(world.alerts)+1:03d}",
        "created_at": fmt(ts),
        "alert_type": alert_type,
        "severity": severity,
        "device_id": device_id,
        "site_id": site_id,
        "metric": metric,
        "observed_value": observed,
        "threshold": threshold,
        "description": description,
        "status": status,
        "recommended_action": action,
        "related_error_code": error_code,
        "related_incident_id": incident_id,
    })
    return world.alerts[-1]["alert_id"]


def build_alerts(world):
    thermal = world.named["thermal"]
    world.named["eal_thermal_warn"] = add_alert(
        world, THERMAL_WARN, "Thermal", "Warning", thermal, "battery_temperature_c", "51 C", "48 C",
        "Pack temperature crossed the warning line during the rise that later tripped the pack.",
        "Closed", "Keep watching. Do not raise the threshold.", "THERM-110", world.named["inc_thermal"],
    )
    world.named["eal_thermal"] = add_alert(
        world, THERMAL_FAULT, "Thermal", "Critical", thermal, "battery_temperature_c", "66 C", "60 C",
        "THERM-201 protective shutdown. Cooling fan tach was zero.",
        "Closed", "Leave the pack offline and replace the cooling fan.", "THERM-201", world.named["inc_thermal"],
    )
    add_alert(
        world, THERMAL_OFFLINE, "Device Offline", "Critical", thermal, "operating_state", "Offline", "Online",
        "Battery stopped reporting after the thermal protective shutdown.",
        "Open", "Replace the fan before recommissioning.", "THERM-201", world.named["inc_thermal"],
    )
    add_alert(
        world, FW_UPGRADE + timedelta(hours=4, minutes=20), "Firmware", "Error", world.named["fw_stuck_bat"],
        "communication_latency_ms", "340 ms", "120 ms",
        "COM-214 after the 4.3.0 install. Signal strength still nominal.",
        "Open", "Upgrade this battery from 4.3.0 to 4.3.1.", "COM-214", world.named["inc_firmware"],
    )
    add_alert(
        world, FW_UPGRADE + timedelta(hours=4, minutes=40), "Communication", "Error", world.named["fw_stuck_gw"],
        "communication_latency_ms", "330 ms", "120 ms",
        "Gateway still on 4.3.0 with the heartbeat regression.",
        "Open", "Upgrade to 4.3.1. Do not replace the radio.", "COM-214", world.named["inc_firmware"],
    )
    add_alert(
        world, FW_ROLLBACK, "Firmware", "Info", world.named["fw_rollback_gw"],
        "firmware_version", "4.2.1", "4.3.0",
        "Rollback to 4.2.1 completed. Latency returned to the normal band.",
        "Closed", "Leave this gateway on 4.2.1 until 4.3.1 is scheduled.", "COM-214", world.named["inc_firmware"],
    )
    add_alert(
        world, at(2026, 9, 17, 18, 0), "Configuration", "Error", world.named["config_inv"],
        "Inverter Power Limit", "75 kW", "90 kW",
        "Running power limit did not match the expected 90 kW, and discharge peaks flatlined.",
        "Closed", "Restored. Confirm the latest configuration row is 90 kW.", "CFG-101", world.named["inc_config"],
    )
    add_alert(
        world, COMM_FAULT, "Communication", "Critical", world.named["comm_gw"],
        "signal_strength_dbm", "-104 dBm", "-95 dBm",
        "Signal strength and latency both degraded before the gateway went offline.",
        "Open", "Replace the radio path. This is not the 4.3.0 heartbeat fault.", "COM-101", world.named["inc_comm"],
    )
    add_alert(
        world, COMM_OFFLINE, "Device Offline", "Critical", world.named["comm_gw"],
        "operating_state", "Offline", "Online",
        "Gateway stopped reporting.",
        "Open", "Radio replacement is staged.", "COM-101", world.named["inc_comm"],
    )
    add_alert(
        world, VOLT_FAULTS[-1], "Voltage", "Error", world.named["repeat_a"],
        "battery_voltage", "705 to 812 V", "740 to 770 V",
        "HW-C pack voltage unstable before BAT-204.",
        "Open", "Keep the discharge cap until the busbar is re-torqued.", "BAT-204", world.named["inc_repeat"],
    )
    add_alert(
        world, VOLT_FAULTS[-1], "Repeated Fault", "Warning", world.named["repeat_b"],
        "battery_voltage", "outside 740 to 770 V", "740 to 770 V",
        "Second site with the HW-C BAT-204 pattern.",
        "Acknowledged", "Include this pack in the torque campaign.", "BAT-204", world.named["inc_repeat"],
    )
    add_alert(
        world, at(2026, 9, 24, 16, 40), "Repeated Fault", "Warning", world.named["repeat_c"],
        "error_code", "BAT-204", "none in 7 days",
        "Third HW-C site. No dense telemetry on this pack, same fault code and revision.",
        "Acknowledged", "Include in the same investigation.", "BAT-204", world.named["inc_repeat"],
    )
    add_alert(
        world, DRIFT_FAULTS[0], "Thermal", "Warning", world.named["drift_bat"],
        "battery_temperature_c", "36 C and rising slowly", "48 C warning",
        "Early false thermal warning. Later identified as sensor drift, not the Copper Elm failure.",
        "Closed", "Sensor replaced. Do not use the fan-replacement runbook for this one.", "THERM-110", world.named["inc_drift"],
    )
    add_alert(
        world, POWER_DROP, "Performance Degradation", "Error", world.named["power_inv"],
        "inverter_power_kw", "6.5 kW", "60 kW evening peak",
        "Sudden power collapse with nominal grid frequency.",
        "Open", "Replace the power module when the part arrives.", "INV-402", world.named["inc_power"],
    )
    add_alert(
        world, SOC_STEP, "Voltage", "Error", world.named["soc_bat"],
        "battery_soc_percent", "step of about 50 points", "change matched to energy",
        "Unexpected SOC step. The cause is under investigation. This alert does not name a failed part.",
        "Open", "Keep the 40 kW discharge limit. Do not close with a guessed cause.", "BAT-330", world.named["inc_soc"],
    )
    add_alert(
        world, FREQ_PEAK, "Performance Degradation", "Error", world.named["freq_inv"],
        "grid_frequency_hz", "61.28 Hz", "60.5 Hz",
        "Frequency excursion followed by a latched zero-power state.",
        "Acknowledged", "Supervised reset after the trace is archived.", "GRID-302", world.named["inc_freq"],
    )
    add_alert(
        world, at(2026, 9, 25, 15, 0), "Thermal", "Warning", world.named["pro_temp"],
        "battery_temperature_c", "40 C", "60 C trip",
        "Mild flat temperature elevation. The pack is online and below the shutdown threshold.",
        "Open", "Proactive review. Do not treat this as THERM-201.", "BAT-141", world.named["inc_pro"],
    )
    add_alert(
        world, at(2026, 9, 26, 8, 0), "Communication", "Warning", world.named["pro_gw"],
        "communication_latency_ms", "about 140 ms and rising", "250 ms timeout",
        "Latency rising with stable signal strength. Gateway is online and not on 4.3.0.",
        "Open", "Proactive review before this becomes a disconnect.", "GW-090", world.named["inc_pro"],
    )
    add_alert(
        world, at(2026, 9, 26, 4, 40), "Repeated Fault", "Warning", world.named["pro_minor"],
        "restart_count", "4 isolated restarts", "3 per day",
        "Repeated short watchdog restarts. The pack has not failed.",
        "Open", "Proactive review of the BMS supply and task timing.", "BMS-218", world.named["inc_pro"],
    )
    add_alert(
        world, at(2026, 9, 9, 13, 0), "Configuration", "Warning", world.named["mismatch_soc"],
        "SOC Maximum", "75 %", "90 %",
        "Live mismatch. SOC Maximum is 75 against an expected 90. This row is still open.",
        "Open", "Restore SOC Maximum to 90 or document an approved derate.", "CFG-101", "",
    )
    add_alert(
        world, at(2026, 9, 11, 8, 40), "Configuration", "Info", world.named["mismatch_timeout"],
        "Communication Timeout", "8 s", "30 s",
        "Live mismatch. Timeout is much shorter than the approved 30 s.",
        "Open", "Restore the 30 s timeout.", "CFG-101", "",
    )
    add_alert(
        world, at(2026, 9, 12, 15, 10), "Configuration", "Warning", world.named["mismatch_voltage"],
        "Grid Voltage Limit", "492 V", "504 V",
        "Live mismatch on the high grid-voltage limit.",
        "Acknowledged", "Restore 504 V unless a change record says otherwise.", "CFG-101", "",
    )
    add_alert(
        world, at(2026, 9, 17, 9, 20), "Communication", "Info", world.named["healthy_Gateway_1"],
        "communication_latency_ms", "inside band on the next sample", "50 ms",
        "Transient telemetry gap alert. Following samples were normal.",
        "Closed", "No action. Recorded as a false alarm.", "COM-118", "",
    )
    add_alert(
        world, at(2026, 9, 10, 11, 0), "Repeated Fault", "Info", world.named["hist_a"],
        "operating_state", "returned to service", "contactor closed",
        "Historical contactor event is closed.",
        "Closed", "No further action.", "REL-204", world.named["inc_hist_a"],
    )


def build_extra_incidents(world):
    """Additional incidents on non-scenario devices, including a shared failure mode."""
    used = {meta.get("alias") or meta.get("role") for meta in world.device_meta.values()}
    pool = {"Battery": [], "Inverter": [], "Gateway": [], "Energy Controller": []}
    for device in world.devices:
        meta = world.device_meta[device["device_id"]]
        if meta["role"]:
            continue
        if device["device_type"] in pool and device["status"] == "Online":
            pool[device["device_type"]].append(device)

    def take(kind):
        check(pool[kind], f"no filler {kind}")
        return pool[kind].pop(0)

    capacitor_cause = "DC bus capacitor ESR rise on the inverter power module"
    extras = [
        ("DC bus ripple on the first sister inverter", "Error", "Resolved", "Inverter", capacitor_cause, capacitor_cause, "INV-305", False),
        ("DC bus ripple on the second sister inverter", "Error", "Closed", "Inverter", capacitor_cause, capacitor_cause, "INV-305", False),
        ("Sense channel stale after a harness reseat", "Warning", "Resolved", "BMS", "Sense harness fretting", "Connector fretting on the voltage sense harness", "BMS-301", False),
        ("Ride-through recorded during a tap change", "Info", "Closed", "Grid", "Utility tap change", "Utility tap change, inverter stayed online", "INV-318", False),
        ("Balancing left running after charge", "Info", "Closed", "BMS", "Normal balancing", "Normal balancing, no fault", "BMS-104", False),
        ("Watchdog during a storm night", "Warning", "Resolved", "BMS", "Supply dip", "12 V supply dip during a storm, single restart", "BMS-218", False),
        ("Preferred-band voltage dip shared by two feeders", "Warning", "Closed", "Grid", "Utility regulation", "Shared feeder voltage dip, no inverter damage", "GRID-118", False),
        ("Restart delay held an inverter offline for one cycle", "Info", "Closed", "Inverter", "Configured delay", "Restart delay matched the approved 60 s setting", "INV-250", False),
        ("Gateway CPU blip during log harvest", "Warning", "Resolved", "Gateway", "Log harvest", "Operator log harvest, CPU returned to normal", "GW-101", False),
        ("Compressed frames enabled on a current image", "Info", "Closed", "Communications", "Expected 4.3.1 feature", "Expected behavior of 4.3.1 compressed frames", "COM-240", True),
        ("Nuisance BMS channel disagreement", "Warning", "Investigating", "BMS", "Possible harness issue, not confirmed", UNDER, "BMS-210", False),
        ("Grid relay inspection after a disconnect drill", "Medium", "Monitoring", "Grid", "Drill follow-up", "", "GRID-310", False),
    ]
    # The tuple severity for the drill was accidentally a word. Fix by using Warning.
    extras[11] = ("Grid relay inspection after a disconnect drill", "Warning", "Monitoring", "Grid", "Drill follow-up, no confirmed field failure", "", "GRID-310", False)
    extras.extend([
        ("Cell delta during an overnight charge", "Warning", "Closed", "BMS",
         "Balancer duty cycle too low", "Balancer duty cycle too low on one cell group", "BAT-101", False),
        ("Charge current overshoot for one sample", "Warning", "Resolved", "BMS",
         "Charger handshake glitch", "Single-sample charge current overshoot, did not repeat", "BAT-217", False),
        ("SOC residual reviewed and left alone", "Info", "Closed", "BMS",
         "Estimator residual inside a follow-up rest", "Open-circuit voltage agreed with SOC after a 20 minute rest", "BAT-118", False),
        ("Charge complete at the configured SOC", "Info", "Closed", "BMS",
         "Normal end of charge", "Normal end of charge, no field action", "BAT-102", False),
        ("Inverter heat-sink derate on a hot afternoon", "Warning", "Resolved", "Inverter",
         "High ambient and a dusty fan inlet", "Blocked inverter fan inlet, derate cleared after cleaning", "INV-214", False),
        ("Inverter came online after a planned stop", "Info", "Closed", "Inverter",
         "Normal start", "Normal start, grid inside limits", "INV-109", False),
        ("Hardware trip cleared after one restart", "Error", "Resolved", "Inverter",
         "Nuisance desaturation comparator", "Single hardware trip, no repeat, power module left in service", "INV-415", False),
        ("Grid returned to the nominal band", "Info", "Closed", "Grid",
         "Normal recovery", "Grid voltage and frequency returned to nominal", "GRID-201", False),
        ("Gateway RSSI dip during foliage growth", "Warning", "Monitoring", "Gateway",
         "Antenna path, not confirmed as a radio failure", "", "GW-090", False),
        ("Gateway reboot burst recovered", "Warning", "Resolved", "Gateway",
         "Supply dip", "Supply dip, reboots stopped after the storm", "GW-140", False),
        ("Short telemetry gaps on a healthy radio", "Warning", "Closed", "Communications",
         "Retransmission during a collector pause", "Collector pause, radio path was healthy", "COM-118", False),
        ("Firmware bank signature matched the manifest", "Info", "Closed", "Communications",
         "Normal update pre-check", "Inactive bank matched the release manifest", "FW-104", False),
    ])

    for title, severity, status, subsystem, suspected, confirmed, code, fw_related in extras:
        kind = {
            "Inverter": "Inverter",
            "BMS": "Battery",
            "Grid": "Inverter",
            "Gateway": "Gateway",
            "Communications": "Gateway",
        }[subsystem]
        device = take(kind)
        created = at(2026, 9, 3 + (len(world.incidents) % 20), 9, 15)
        resolved = created + timedelta(days=2) if status in ("Resolved", "Closed") else None
        if confirmed == UNDER:
            resolved = None
            status = "Investigating"
        inc = add_incident(
            world, title, severity if severity != "Medium" else "Warning", status, created, resolved,
            [device["device_id"]], subsystem, suspected, confirmed,
            f"Limited to {device['device_id']} at {device['site_id']}.",
            "See the ticket." if status not in ("Resolved", "Closed") else "Corrective work completed.",
            "" if confirmed in ("", UNDER) else confirmed,
            fw_related, "4.3.1" if fw_related else "",
        )
        add_event(world, inc, created, "Alert", "ENG-118", f"{code} reviewed during the weekly engineering pass.", code)
        add_event(world, inc, created + timedelta(hours=3), "Investigation Started", "ENG-118", "Scoped to one device.", device["device_id"])
        add_event(world, inc, created + timedelta(hours=6), "Telemetry Reviewed", "ENG-118", "Compared the device with its site peers.", device["device_id"])
        if confirmed and confirmed != UNDER:
            add_event(world, inc, created + timedelta(days=1), "Root Cause Confirmed", "ENG-118", confirmed, code)
        if status in ("Resolved", "Closed"):
            add_event(world, inc, created + timedelta(days=2), "Incident Resolved", "ENG-118", "Closed in the weekly pass.", inc)
        elif confirmed == UNDER:
            add_event(world, inc, created + timedelta(days=1), "Root Cause Suspected", "ENG-118",
                      "A harness issue is possible and is not confirmed.", device["device_id"])
        fault_status = "Cleared" if status in ("Resolved", "Closed") else "Active"
        cleared = resolved if fault_status == "Cleared" else None
        add_fault(
            world, device["device_id"], created, code, fault_status, "NOC",
            component_of(world, device["device_id"], next(e["related_component_type"] for e in world.errors if e["error_code"] == code)),
            "ENG-118", "", cleared,
            "" if not confirmed or confirmed == UNDER else confirmed,
            title,
        )
        add_ticket(
            world, title, suspected or title, "Medium",
            "Closed" if status in ("Resolved", "Closed") else ("Investigating" if status == "Investigating" else "Open"),
            created, "ENG-118", subsystem, device["device_id"], code, inc,
            confirmed if confirmed else "",
            "" if confirmed in ("", UNDER) else confirmed,
            "4.3.1" if fw_related else "",
        )
        add_alert(
            world, created, "Repeated Fault" if "ripple" in title else "Performance Degradation",
            "Info" if severity == "Info" else "Warning",
            device["device_id"], "case", code, "weekly review",
            title, "Closed" if status in ("Resolved", "Closed") else "Open",
            "Follow the related incident.", code, inc,
        )
    check(not used or True, "used set retained for readability")


def build_documents(world):
    thermal = world.named["thermal"]
    drift = world.named["drift_bat"]
    soc = world.named["soc_bat"]
    handcrafted = [
        ("THERM-201 Protective Shutdown Runbook", "Runbook", "Thermal", "2.1", "Published", "ENG-104",
         "Battery", "THERM-201;THERM-110", "",
         "Symptoms: pack temperature rises over minutes to hours while discharging, cooling fan tach falls to zero, THERM-110 warns, then THERM-201 opens the contactors and the battery goes offline. "
         "Steps: 1) Save the two-hour temperature trace. 2) Confirm fan tach. 3) If tach is zero and temperature is still rising, replace the cooling fan. 4) Do not raise the Temperature Threshold to clear THERM-201. 5) Recommission only after the new fan runs. "
         f"Use this runbook for {thermal}. Do not use it for a drifting sensor."),
        ("Field Configuration Guide: Thermal Thresholds", "Configuration Guide", "Thermal", "1.4", "Published", "ENG-118",
         "Battery", "THERM-201;THERM-110", "",
         "This guide conflicts with the THERM-201 Protective Shutdown Runbook. It tells the field to raise Temperature Threshold by 10 C when THERM-201 trips, and it treats cooling fan replacement as optional if the pack can be started again. "
         "The runbook forbids that threshold change. Both documents are Published. Engineering should follow the runbook, not this guide, until this guide is withdrawn."),
        ("Firmware 4.2.1 Release Note", "Firmware Release Note", "Firmware", "4.2.1", "Published", "ENG-110",
         "Battery;Inverter;Gateway", "", "4.2.1",
         "Previous stable release. Fixed 200 ms heartbeat, uncompressed telemetry frames, communication timeout handled in the gateway task. "
         "Known issues: none critical. 4.2.1 does not contain the COM-214 regression. It remains the rollback target from 4.3.0."),
        ("Firmware 4.3.0 Release Note", "Firmware Release Note", "Firmware", "4.3.0", "Published", "ENG-110",
         "Battery;Inverter;Gateway", "COM-214;FW-210", "4.3.0",
         "What changed from 4.2.1: the fixed heartbeat was replaced with an adaptive heartbeat, telemetry frames were compressed, and communication timeout handling moved from the gateway task into the shared session layer. "
         "Known issue: the new state machine drops a healthy session when one-way latency exceeds 120 ms (COM-214, FW-210). Signal strength is not affected. Rollout status: halted. Fix is 4.3.1."),
        ("Firmware 4.3.1 Release Note", "Firmware Release Note", "Firmware", "4.3.1", "Published", "ENG-110",
         "Battery;Inverter;Gateway;Energy Controller", "COM-214;FW-210", "4.3.1",
         "4.3.1 keeps compressed telemetry and restores the 4.2.1 heartbeat timing. It resolves COM-214 and the FW-210 signature introduced in 4.3.0. "
         "Hardware-in-loop test: 4.3.0 drops the session at 180 ms induced latency; 4.3.1 and 4.2.1 stay up."),
        ("Failure Analysis: 4.3.0 Communications Regression", "Failure Analysis", "Communications", "1.0", "Published", "ENG-110",
         "Battery;Inverter;Gateway", "COM-214;FW-210", "4.3.0;4.3.1;4.2.1",
         "Symptoms started within hours of the 4.3.0 install: latency stepped from about 30 ms to above 300 ms and COM-214 fired. RSSI stayed near -64 dBm. "
         "Peers that stayed on 4.2.1 did not fail. Rollback to 4.2.1 or upgrade to 4.3.1 clears the symptom. A radio replacement does not."),
        ("COM-101 Gateway Link Loss Diagnostic Procedure", "Diagnostic Procedure", "Communications", "1.2", "Published", "ENG-104",
         "Gateway", "COM-101;COM-118;GW-090", "4.2.1",
         "Symptoms: latency rises and signal strength falls together, telemetry gaps appear, then the gateway goes offline. "
         "Steps: 1) Plot latency and RSSI on the same axis. 2) If both degrade, inspect the antenna, cable, and radio. 3) If only latency rises and RSSI is steady, stop and check for the 4.3.0 COM-214 regression instead. "
         "The Owl Hollow gateway is the radio-path example."),
        ("COM-214 Heartbeat Session Drop Diagnostic Procedure", "Diagnostic Procedure", "Firmware", "1.0", "Published", "ENG-110",
         "Battery;Inverter;Gateway", "COM-214;FW-210", "4.3.0;4.3.1;4.2.1",
         "Symptoms: COM-214 or FW-210 shortly after a 4.3.0 install, latency high, signal strength unchanged. "
         "Steps: 1) Read firmware history. 2) Confirm the first fault is after the 4.3.0 installed_at. 3) Roll back to 4.2.1 or upgrade to 4.3.1. 4) Do not replace the radio."),
        ("Distinguishing Pack Thermal Rise from Temperature-Sensor Drift", "Troubleshooting Guide", "Thermal", "1.0", "Published", "ENG-118",
         "Battery", "THERM-201;THERM-110;THERM-155;SEN-112", "",
         f"Real thermal failure example is {thermal}: temperature rises over hours while discharging, fan tach is zero, voltage sags slightly, THERM-201 trips, and the pack goes offline. There is no snap-back. "
         f"Sensor drift example is {drift}: temperature climbs for days while current and voltage stay normal, THERM-110 and THERM-155 fire, the pack stays online, and the reading snaps back to about 28 C in one sample after the sensor is replaced. "
         "Do not replace a cooling fan for the drift case. Do not raise the threshold for the real shutdown."),
        ("Inverter Power Limit Configuration Guide", "Configuration Guide", "Inverter", "1.1", "Published", "ENG-125",
         "Inverter", "CFG-101;CFG-090;INV-360", "",
         "Symptoms of a mismatched Inverter Power Limit: afternoon power flatlines at the configured cap, INV-360 repeats, and the grid is healthy. "
         "Steps: 1) Open device_configuration. 2) A Mismatch row has parameter_value different from expected_value. The Limestone case was 75 kW versus expected 90 kW. "
         "3) Restore the expected value. 4) Confirm the next discharge exceeds the old cap. The latest row for that inverter is the corrected 90 kW value."),
        ("Failure Analysis: BAT-204 on Hardware Revision HW-C", "Failure Analysis", "Battery", "1.0", "Published", "ENG-125",
         "Battery", "BAT-204", "",
         "Three packs at three sites, all hardware revision HW-C, raised BAT-204 during discharge above 70 kW. Voltage swung outside 740 to 770 V before the fault. "
         "Firmware and current limits were not common. Confirmed cause: power-module busbar torque below spec. Temporary mitigation is a 60 kW discharge cap."),
        ("Proactive Watchlist: Early Degradation Signals", "Troubleshooting Guide", "Battery", "1.0", "Published", "ENG-101",
         "Battery;Gateway", "BAT-141;BMS-218;GW-090", "",
         "Investigate these while they are still online: a pack whose temperature sits near 40 C without approaching the 60 C trip, a gateway whose latency climbs through roughly 140 ms with stable RSSI and which is not on firmware 4.3.0, "
         "and a pack with isolated BMS-218 watchdog restarts that recovers each time. These are early warnings, not the Copper Elm shutdown and not the 4.3.0 regression."),
        ("Open Investigation Note: Unexpected SOC Step", "Failure Analysis", "Battery", "0.3", "Draft", "ENG-101",
         "Battery", "BAT-330", "4.2.1",
         f"{world.named['inc_soc']} on {soc} remains under investigation. The symptom is an SOC step of about 50 points while current and power at that sample were near zero. "
         "Unconfirmed hypotheses are SOC estimator bias, current-sensor offset, and standby parasitic load. None is confirmed. Firmware is 4.2.1, matching healthy peers. Do not write a confirmed cause into the ticket."),
        ("Grid Frequency Excursion and Inverter Latch Runbook", "Runbook", "Grid", "1.0", "Published", "ENG-110",
         "Inverter", "GRID-302;INV-201", "",
         "Symptoms: grid frequency leaves 59.5 to 60.5 Hz, inverter power falls, then frequency returns and power stays at zero because INV-201 latches. "
         "Steps: 1) Confirm the frequency peak on the inverter trace. 2) If the grid was really outside the band, do not replace the power module. 3) Reset only with a supervised procedure. The Lantern Field event peaked at 61.28 Hz."),
        ("Pack, Inverter, and Gateway Data Path", "Architecture Document", "Communications", "3.0", "Published", "ENG-110",
         "Battery;Inverter;Gateway;Energy Controller;Sensor", "", "4.2.1;4.3.0;4.3.1",
         "The BMS publishes pack telemetry to the site gateway. The inverter publishes AC power, grid voltage, and grid frequency. The gateway heartbeats to the collector. "
         "Firmware 4.2.1 heartbeats from the gateway task. Firmware 4.3.0 moved that work into a shared session layer. Firmware 4.3.1 keeps the session layer and restores 4.2.1 timing. Energy controllers and sensors were not built on 4.3.0."),
        ("Normal Operating Envelopes", "Engineering Spec", "Battery", "2.0", "Published", "ENG-125",
         "Battery;Inverter;Gateway", "", "",
         "Pack temperature 24 to 35 C in normal weather. Pack voltage about 740 to 770 V. Grid frequency 59.95 to 60.05 Hz outside of a disturbance. "
         "Heartbeat latency about 15 to 50 ms. RSSI about -75 to -55 dBm. Evening inverter peaks near the 90 kW rating unless a configuration cap is present. SOC moves with charge and discharge energy."),
        ("Arroyo-200 and Ledge-200 Installation Guide", "Installation Guide", "Battery", "1.3", "Published", "ENG-125",
         "Battery", "BAT-204", "",
         "Both pack models are 200 kWh. HW-C power modules need a recorded busbar torque at installation. Skip the torque record and BAT-204 is the likely field result under discharge above 70 kW. "
         "HW-A packs stay on firmware 4.1.4 or 4.2.1. 4.3.x requires HW-B or later."),
        ("Similar Shutdowns, Different Causes", "Failure Analysis", "Battery", "1.0", "Published", "ENG-104",
         "Battery", "REL-204;REL-210;BAT-340", "",
         "Two incidents share the symptom: the main contactor opened during a routine discharge, with no thermal alarm and no recent firmware change. "
         f"{world.named['inc_hist_a']} was a failed contactor coil driver (coil current zero, REL-204). {world.named['inc_hist_b']} was an open precharge resistor (coil current present, DC bus did not rise, REL-210). "
         "Do not copy the first repair onto the second symptom."),
        ("Configuration Mismatch Troubleshooting Guide", "Troubleshooting Guide", "Inverter", "1.0", "Published", "ENG-125",
         "Battery;Inverter;Gateway", "CFG-101;CFG-090", "",
         "A row with configuration_status Mismatch has parameter_value different from expected_value. Matching rows are equal. "
         "Live examples in this snapshot include SOC Maximum 75 versus expected 90, Communication Timeout 8 s versus 30 s, and Grid Voltage Limit 492 V versus 504 V. "
         "The Limestone inverter also keeps the historical 75 kW row; its later row is the corrected 90 kW value."),
        ("Repeated Fault Investigation Procedure", "Diagnostic Procedure", "Battery", "1.0", "Published", "ENG-125",
         "Battery;Inverter", "BAT-204;INV-305", "",
         "When the same error code appears at several sites, group by hardware revision, firmware, configuration, and operating condition before replacing parts. "
         "The HW-C BAT-204 cluster matched on revision and on discharge above 70 kW, not on firmware. The sister INV-305 cases matched on DC bus capacitor ESR."),
        ("Superseded Envelope Table", "Engineering Spec", "Battery", "1.0", "Superseded", "ENG-118",
         "Battery", "", "",
         "Superseded by Normal Operating Envelopes 2.0. The old table allowed pack temperature up to 45 C as normal. The current spec treats sustained temperature near 40 C as an early warning, not as a normal band."),
    ]
    for title, doc_type, subsystem, version, status, author, device_types, codes, firmware, summary in handcrafted:
        number = len(world.documents) + 1
        created = at(2026, 9, 1, 9, 0) + timedelta(days=number % 20)
        if "4.2.1" == version:
            created = at(2026, 4, 2, 9, 0)
        elif version == "4.3.0":
            created = at(2026, 9, 8, 9, 0)
        elif version == "4.3.1":
            created = at(2026, 9, 19, 9, 0)
        row = {
            "document_id": f"DOC-{number:03d}",
            "title": title,
            "document_type": doc_type,
            "subsystem": subsystem,
            "version": version,
            "created_at": fmt(created),
            "updated_at": fmt(created + timedelta(days=1)),
            "author": author,
            "status": status,
            "summary": summary,
            "applicable_device_types": device_types,
            "related_error_codes": codes,
            "related_firmware_versions": firmware,
        }
        world.documents.append(row)
        if title.startswith("THERM-201 Protective"):
            world.named["doc_thermal_runbook"] = row["document_id"]
        if title.startswith("Field Configuration Guide: Thermal"):
            world.named["doc_thermal_conflict"] = row["document_id"]
        if title.startswith("Open Investigation"):
            world.named["doc_soc"] = row["document_id"]

    covered = set()
    for doc in world.documents:
        for code in filter(None, doc["related_error_codes"].split(";")):
            covered.add(code)
    for error in world.errors:
        code = error["error_code"]
        if code in covered:
            continue
        number = len(world.documents) + 1
        created = at(2026, 9, 4, 8, 0)
        world.documents.append({
            "document_id": f"DOC-{number:03d}",
            "title": f"{code} Quick Diagnostic Card",
            "document_type": "Diagnostic Procedure",
            "subsystem": error["subsystem"],
            "version": "1.0",
            "created_at": fmt(created),
            "updated_at": fmt(created),
            "author": "ENG-118",
            "status": "Published",
            "summary": (
                f"{code} {error['title']}. Severity {error['severity']}. {error['description']} "
                f"Likely causes: {error['likely_causes']}. Steps: {error['recommended_diagnostic_steps']} "
                f"Related component: {error['related_component_type']}. "
                f"Firmware fix: {error['known_firmware_fix'] or 'none'}."
            ),
            "applicable_device_types": {
                "Battery": "Battery",
                "BMS": "Battery",
                "Inverter": "Inverter",
                "Communications": "Gateway",
                "Thermal": "Battery",
                "Grid": "Inverter",
                "Gateway": "Gateway",
                "Firmware": "Battery;Inverter;Gateway",
            }[error["subsystem"]],
            "related_error_codes": code,
            "related_firmware_versions": error["known_firmware_fix"],
        })

    fillers = [
        ("Cooling Fan Tach Check", "Service Bulletin", "Thermal", "Battery", "THERM-201", "4.2.1",
         "Check cooling fan tach before changing a temperature threshold. A zero tach with rising temperature means replace the fan."),
        ("HW-C Busbar Torque Record", "Installation Guide", "Battery", "Battery", "BAT-204", "",
         "Record busbar torque on every HW-C power module at installation. Low torque shows up later as BAT-204 under discharge."),
        ("Heartbeat Timing Comparison", "Engineering Spec", "Firmware", "Battery;Inverter;Gateway", "COM-214;FW-210", "4.2.1;4.3.0;4.3.1",
         "4.2.1 uses a fixed heartbeat. 4.3.0 drops sessions above 120 ms. 4.3.1 restores the 4.2.1 timing and keeps compressed frames."),
        ("Radio Path versus Heartbeat Regression", "Troubleshooting Guide", "Communications", "Gateway", "COM-101;COM-214", "4.2.1;4.3.0",
         "If latency and signal strength both move, inspect the radio. If only latency moves and the image is 4.3.0, treat it as the heartbeat regression."),
        ("Inverter Power Limit Audit", "Configuration Guide", "Inverter", "Inverter", "CFG-101;INV-360", "",
         "Compare parameter_value with expected_value. A mismatch row is not a hardware fault until the values are equal and the cap remains."),
        ("Sensor Replacement Note", "Service Bulletin", "Thermal", "Battery", "THERM-155;SEN-112", "4.2.1",
         "A drifting temperature sensor snaps back in one sample after replacement. A real thermal shutdown does not."),
        ("Contactor Coil versus Precharge", "Diagnostic Procedure", "Battery", "Battery", "REL-204;REL-210", "",
         "Zero coil current points at the coil driver. Coil current with no DC bus rise points at the precharge resistor."),
        ("Grid Latch Reset Procedure", "Runbook", "Grid", "Inverter", "GRID-302;INV-201", "",
         "After a real frequency excursion, leave the inverter latch set until a supervised reset. Do not swap the power module for the grid event."),
        ("DC Bus Capacitor ESR Check", "Diagnostic Procedure", "Inverter", "Inverter", "INV-305", "",
         "Sister inverters with the same ripple signature share a DC bus capacitor ESR rise. Compare them before blaming the grid."),
        ("Watchdog Restart Counting", "Troubleshooting Guide", "BMS", "Battery", "BMS-218", "4.2.1",
         "Count BMS-218 restarts in 24 hours. One restart can be a supply dip. More than three in a day is an escalation."),
        ("Gateway CPU Profile Request", "Service Bulletin", "Gateway", "Gateway", "GW-101", "4.2.1",
         "Capture a CPU profile before replacing a gateway that shows a short CPU blip. A 4.4.0 lab image is not approved for the field."),
        ("SOC Step Investigation Checklist", "Diagnostic Procedure", "Battery", "Battery", "BAT-330", "4.2.1",
         "When SOC steps without matching current, list estimator bias, current-sensor offset, and standby load as hypotheses. Do not confirm one from a single sample."),
        ("Proactive Temperature Watch", "Troubleshooting Guide", "Thermal", "Battery", "BAT-141;THERM-110", "",
         "A pack that sits near 40 C and stays online is an early warning. It is not a THERM-201 shutdown."),
        ("Communication Timeout Template", "Configuration Guide", "Communications", "Gateway", "CFG-101", "4.2.1",
         "The approved communication timeout is 30 s. A running value of 8 s is a mismatch and should be restored through a change record."),
        ("Release Bank Verification", "Firmware Release Note", "Firmware", "Battery;Inverter;Gateway", "FW-104", "4.3.1",
         "FW-104 means the inactive bank matched the manifest. It is an informational check, not a fault."),
    ]
    for title, doc_type, subsystem, device_types, codes, firmware, summary in fillers:
        number = len(world.documents) + 1
        created = at(2026, 9, 2, 10, 0) + timedelta(days=number % 18)
        world.documents.append({
            "document_id": f"DOC-{number:03d}",
            "title": title,
            "document_type": doc_type,
            "subsystem": subsystem,
            "version": "1.0",
            "created_at": fmt(created),
            "updated_at": fmt(created + timedelta(days=1)),
            "author": "ENG-125",
            "status": "Published",
            "summary": summary,
            "applicable_device_types": device_types,
            "related_error_codes": codes,
            "related_firmware_versions": firmware,
        })


def build_analyses(world):
    def add(incident_key, device_key, mode, symptoms, factors, method, evidence, cause, corrective, preventive, confidence, when):
        world.analyses.append({
            "analysis_id": f"FA-{len(world.analyses)+1:03d}",
            "incident_id": world.named[incident_key],
            "device_id": world.named[device_key],
            "failure_mode": mode,
            "symptoms": symptoms,
            "contributing_factors": factors,
            "investigation_method": method,
            "evidence": evidence,
            "root_cause": cause,
            "corrective_action": corrective,
            "preventive_action": preventive,
            "confidence": confidence,
            "analysis_date": when.strftime("%Y-%m-%d"),
        })

    add("inc_thermal", "thermal", "Cooling fan seizure with protective thermal shutdown",
        "Temperature rose from about 34 C to about 73 C during discharge, THERM-201 tripped, pack went offline.",
        "Sustained discharge with fan tach at zero.",
        "Telemetry review, fan tach, firmware comparison, configuration check.",
        f"Temperature trace on {world.named['thermal']}; fan component {world.named['thermal_fan']} status Failed; threshold matched expected.",
        "Cooling fan bearing seizure caused a real pack temperature rise and a THERM-201 protective shutdown.",
        "Replace the cooling fan and recommission.",
        "Add a fan-tach alarm before temperature reaches the warning line.",
        "High", at(2026, 9, 27, 15, 0))
    add("inc_firmware", "fw_stuck_bat", "Heartbeat session drop on firmware 4.3.0",
        "COM-214 after the 4.3.0 install, latency high, RSSI unchanged.",
        "Session-layer heartbeat change from 4.2.1.",
        "Firmware history aligned to fault time, lab latency injection, comparison with 4.3.1.",
        "Faults begin after installed_at of 4.3.0. 4.3.1 test passes the same case.",
        "Firmware 4.3.0 drops healthy sessions when one-way latency exceeds 120 ms.",
        "Roll back to 4.2.1 or upgrade to 4.3.1. Halt 4.3.0.",
        "Require the 180 ms heartbeat test before the next communications release.",
        "High", at(2026, 9, 21, 9, 0))
    add("inc_config", "config_inv", "Commanded power blocked by a low configured limit",
        "Afternoon peaks flatlined near 75 kW and INV-360 repeated.",
        "Field edit without a change record.",
        "Configuration diff and before/after telemetry.",
        "Historical configuration row parameter_value 75 expected_value 90. Later row is 90 and 90. Peaks recovered after 18 Sep 10:00.",
        "Inverter Power Limit was set to 75 kW against the expected 90 kW.",
        "Restored the limit to 90 kW.",
        "Block field edits that do not match expected_value.",
        "High", at(2026, 9, 18, 14, 0))
    add("inc_comm", "comm_gw", "Gateway radio path failure",
        "Latency up, RSSI down, then offline.",
        "Antenna or radio hardware. Firmware was 4.2.1.",
        "Dual-metric telemetry and firmware history.",
        "RSSI fell from about -68 dBm toward -107 dBm while latency climbed. No 4.3.0 install.",
        "Gateway radio path failed.",
        "Replace the radio and re-aim the antenna.",
        "Alert when RSSI and latency degrade together.",
        "High", at(2026, 9, 26, 16, 0))
    add("inc_repeat", "repeat_a", "Cell-group imbalance from low busbar torque",
        "BAT-204 at three HW-C sites during discharge above 70 kW, with pack voltage swinging outside 740 to 770 V.",
        "Shared hardware revision HW-C and similar discharge conditions.",
        "Cross-site comparison of revision, firmware, configuration, and telemetry.",
        "Three batteries, hardware_revision HW-C, same error code, voltage instability before the fault.",
        "HW-C power-module busbar torque below spec.",
        "Re-torque campaign and a temporary 60 kW cap.",
        "Record busbar torque in the HW-C installation guide.",
        "High", at(2026, 9, 25, 16, 0))
    add("inc_drift", "drift_bat", "Temperature sensor drift causing false thermal warnings",
        "Slow temperature climb, normal voltage and current, snap-back after replacement, pack stayed online.",
        "Aging temperature sensor.",
        "Compared the slope and the step change at replacement with the real thermal shutdown.",
        f"Reading fell by more than 12 C in one sample at the replacement time. {world.named['thermal']} did not snap back and went offline.",
        "Pack temperature sensor drift.",
        "Replaced the sensor.",
        "Use THERM-155 and a redundant channel before dispatching a fan crew.",
        "High", at(2026, 9, 24, 12, 0))
    add("inc_power", "power_inv", "Inverter power module failure",
        "Power fell from about 78 kW to 6.5 kW in one sample and stayed down. Grid frequency stayed near 60 Hz. DC bus sagged.",
        "Power module hardware.",
        "Compared grid frequency, grid voltage, DC bus, and configuration.",
        "Grid stayed nominal, so this is not the frequency-latch case. The power limit was already 90 kW, so this is not the 75 kW mismatch.",
        "Inverter power module failed.",
        "Replace the power module. Ticket is blocked on the part.",
        "None additional in this snapshot.",
        "High", at(2026, 9, 25, 10, 0))
    add("inc_soc", "soc_bat", "Unexpected SOC step",
        "SOC changed by about 50 points without matching energy at the step.",
        "Three unconfirmed hypotheses remain: SOC estimator bias, current-sensor offset, and standby parasitic load.",
        "Compared SOC to current and power, then compared firmware and configuration with healthy peers.",
        "Step at 2026-09-21 03:20 with current near zero. Firmware 4.2.1 matches peers. No hypothesis has confirming evidence.",
        UNDER,
        "",
        "",
        "Low", at(2026, 9, 23, 15, 0))
    add("inc_hist_a", "hist_a", "Contactor coil driver failure",
        "Main contactor opened during discharge. No thermal alarm.",
        "Coil driver hardware.",
        "Coil current measurement and comparison with the later precharge case.",
        "Coil current was zero while the close command was present.",
        "Contactor coil driver failed.",
        "Replaced the coil driver.",
        "Capture coil current on every contactor-open event before ordering parts.",
        "High", at(2026, 9, 10, 15, 0))
    add("inc_hist_b", "hist_b", "Open precharge resistor",
        "Main contactor stayed open during discharge. No thermal alarm. Same outward symptom as the coil-driver incident.",
        "Precharge circuit.",
        "Precharge voltage slope and coil current.",
        "Coil current was present and DC bus voltage did not rise.",
        "Precharge resistor was open.",
        "Replaced the precharge resistor.",
        "Do not assume the prior contactor incident's part is the cause.",
        "High", at(2026, 9, 14, 12, 0))
    add("inc_freq", "freq_inv", "Grid frequency excursion with latched inverter protection",
        "Frequency peaked at 61.28 Hz, power went to zero, frequency recovered, power stayed at zero.",
        "Utility disturbance and a latch that requires a reset.",
        "Frequency and power traces.",
        "Excursion is visible before the latch. DC bus did not sag the way the power-module failure did.",
        "Grid frequency excursion with a latched inverter protection trip.",
        "Supervised reset. Do not replace the power module.",
        "Archive the grid trace with the incident.",
        "High", at(2026, 9, 26, 11, 0))

    # The extra under-investigation incident, if present.
    for incident in world.incidents:
        if incident["confirmed_root_cause"] == UNDER and incident["incident_id"] != world.named["inc_soc"]:
            device_id = next(t["affected_device_id"] for t in world.tickets if t["related_incident_id"] == incident["incident_id"])
            world.analyses.append({
                "analysis_id": f"FA-{len(world.analyses)+1:03d}",
                "incident_id": incident["incident_id"],
                "device_id": device_id,
                "failure_mode": "BMS temperature channels disagree",
                "symptoms": "Two temperature channels differ. No shutdown.",
                "contributing_factors": "Harness fretting is possible and not confirmed.",
                "investigation_method": "Channel comparison only.",
                "evidence": "Not sufficient to pick a cause.",
                "root_cause": UNDER,
                "corrective_action": "",
                "preventive_action": "",
                "confidence": "Low",
                "analysis_date": "2026-09-20",
            })
            break

    for incident in world.incidents:
        if incident["confirmed_root_cause"].startswith("DC bus capacitor"):
            device_id = next(t["affected_device_id"] for t in world.tickets if t["related_incident_id"] == incident["incident_id"])
            world.analyses.append({
                "analysis_id": f"FA-{len(world.analyses)+1:03d}",
                "incident_id": incident["incident_id"],
                "device_id": device_id,
                "failure_mode": "DC bus capacitor ESR rise",
                "symptoms": "INV-305 ripple above 25 V peak to peak above 40 kW.",
                "contributing_factors": "Power module capacitor aging on HW-B.",
                "investigation_method": "Ripple capture compared with a sister inverter.",
                "evidence": "Ripple exceeded spec. Sister unit showed the same mode.",
                "root_cause": "DC bus capacitor ESR rise on the inverter power module",
                "corrective_action": "Replace the power module capacitors.",
                "preventive_action": "Add ripple to the annual inverter inspection.",
                "confidence": "Medium",
                "analysis_date": "2026-09-18",
            })


def build_changes(world):
    items = [
        ("Halt firmware 4.3.0 field installs", "Firmware", "Communications",
         "Stop new 4.3.0 installs and move installed devices to 4.3.1 or back to 4.2.1.",
         "COM-214 heartbeat regression.", "High", "Implemented", "4.3.0",
         [world.named[r] for r in ("fw_stuck_bat", "fw_stuck_gw", "fw_rollback_gw", "fw_fixed_gw", "fw_rollback_inv")]),
        ("Release firmware 4.3.1", "Firmware", "Communications",
         "4.3.1 restores 4.2.1 heartbeat timing and keeps compressed frames.",
         "Fix the 4.3.0 regression.", "Medium", "Implemented", "4.3.1",
         [world.named["fw_fixed_gw"]]),
        ("Restore Limestone inverter power limit", "Configuration", "Inverter",
         "Changed Inverter Power Limit from 75 kW back to the expected 90 kW.",
         "Mismatch caused repeated INV-360 caps.", "Medium", "Implemented", "",
         [world.named["config_inv"]]),
        ("Cooling fan replacement for the thermal shutdown", "Hardware", "Thermal",
         f"Replace failed fan {world.named['thermal_fan']}. The kit is issued and the pack is still offline.",
         "THERM-201 after fan seizure.", "High", "Approved", "",
         [world.named["thermal"]]),
        ("HW-C busbar torque campaign", "Process", "Battery",
         "Re-torque HW-C power-module busbars and record the torque. Temporary 60 kW discharge cap until then.",
         "Repeated BAT-204 on HW-C.", "High", "Approved", "",
         [world.named[r] for r in ("repeat_a", "repeat_b", "repeat_c")]),
        ("Replace drifting temperature sensor", "Hardware", "Thermal",
         f"Removed {world.named['drift_sensor']} and installed {world.named['drift_sensor_new']}.",
         "False thermal warnings from sensor drift.", "Low", "Implemented", "",
         [world.named["drift_bat"]]),
        ("Stage a Sill-90 power module", "Hardware", "Inverter",
         "Order and install a replacement power module for the collapsed inverter.",
         "INV-402 power collapse.", "Medium", "Approved", "",
         [world.named["power_inv"]]),
        ("Gateway radio replacement", "Hardware", "Communications",
         "Replace the radio after RSSI and latency collapsed together.",
         "COM-101 link loss. Not the firmware regression.", "Medium", "Approved", "",
         [world.named["comm_gw"]]),
        ("Add fan tach to the warning set", "Software", "Thermal",
         "Raise a maintenance warning when fan tach is zero before pack temperature reaches 48 C.",
         "The thermal shutdown was visible first as a tach failure.", "Low", "Proposed", "",
         []),
        ("Require heartbeat injection before a communications release", "Process", "Firmware",
         "A release cannot ship unless the 180 ms induced-latency heartbeat test passes.",
         "4.3.0 failed that case and 4.3.1 passes it.", "Medium", "Approved", "4.3.1",
         []),
        ("Supervised reset after frequency latch", "Process", "Grid",
         "Reset procedure for an inverter that latched on a real frequency excursion.",
         "GRID-302 then INV-201.", "Low", "Approved", "",
         [world.named["freq_inv"]]),
        ("Document the thermal-document conflict", "Process", "Thermal",
         "Withdraw or correct the field guide that says to raise the temperature threshold after THERM-201.",
         "Two published documents disagree.", "Medium", "Proposed", "",
         []),
    ]
    created = at(2026, 9, 9, 10, 0)
    for index, (title, change_type, subsystem, description, reason, risk, status, firmware, devices) in enumerate(items):
        start = created + timedelta(days=index)
        approved = start + timedelta(days=1) if status in ("Approved", "Implemented") else None
        implemented = start + timedelta(days=2) if status == "Implemented" else None
        if "power limit" in title:
            implemented = CONFIG_FIX
            approved = CONFIG_FIX - timedelta(hours=2)
        world.changes.append({
            "change_id": f"ECR-{index+1:03d}",
            "title": title,
            "change_type": change_type,
            "subsystem": subsystem,
            "description": description,
            "reason": reason,
            "created_at": fmt(start),
            "approved_at": fmt(approved) if approved else "",
            "implementation_date": fmt(implemented) if implemented else "",
            "status": status,
            "affected_devices": ";".join(devices),
            "affected_firmware": firmware,
            "risk_level": risk,
        })


def build_tests(world):
    cases = [
        ("Heartbeat holds at 180 ms induced latency", "Gateway", "4.3.0", "Fail",
         "Session stays up for 30 minutes at 180 ms one-way latency.",
         "Session dropped and COM-214 was raised within 4 minutes.",
         "COM-214 reproduced. This is the 4.3.0 failure."),
        ("Heartbeat holds at 180 ms induced latency", "Gateway", "4.3.1", "Pass",
         "Session stays up for 30 minutes at 180 ms one-way latency.",
         "Session stayed up for 30 minutes. COM-214 was not raised.",
         "4.3.1 passes the case that 4.3.0 fails."),
        ("Heartbeat holds at 180 ms induced latency", "Gateway", "4.2.1", "Pass",
         "Session stays up for 30 minutes at 180 ms one-way latency.",
         "Session stayed up. This is the previous stable baseline.",
         "Baseline for the 4.2.1 versus 4.3.0 comparison."),
        ("Heartbeat holds at 180 ms induced latency", "Battery", "4.3.0", "Fail",
         "Pack communication session stays up at 180 ms latency.",
         "COM-214 raised. FW-210 signature present. RSSI unchanged in the fixture.",
         "Battery image has the same regression as the gateway image."),
        ("Heartbeat holds at 180 ms induced latency", "Battery", "4.3.1", "Pass",
         "Pack communication session stays up at 180 ms latency.",
         "Session stayed up and FW-210 was absent.",
         "Battery fix confirmed."),
        ("Heartbeat holds at 180 ms induced latency", "Inverter", "4.3.0", "Fail",
         "Inverter session stays up at 180 ms latency.",
         "COM-214 raised.",
         "Inverter image regressed with the shared session layer."),
        ("Heartbeat holds at 180 ms induced latency", "Inverter", "4.3.1", "Pass",
         "Inverter session stays up at 180 ms latency.",
         "Session stayed up.",
         "Inverter fix confirmed."),
        ("Compressed frame decode", "Gateway", "4.3.1", "Pass",
         "Collector decodes compressed frames.",
         "Frames decoded. Feature retained from 4.3.0.",
         "4.3.1 did not drop the compression feature."),
        ("Thermal threshold must not be raised to clear THERM-201", "Battery", "4.2.1", "Pass",
         "Procedure rejects a threshold increase while fan tach is zero.",
         "Bench procedure blocked the change and required a fan replacement.",
         "Supports the runbook side of the document conflict."),
        ("HW-C imbalance reproduces above 70 kW", "Battery", "4.2.1", "Fail",
         "HW-C pack stays inside 740 to 770 V above 70 kW when torque is low.",
         "Voltage swung outside the band and BAT-204 latched. A re-torqued control stayed inside the band.",
         "Lab support for the HW-C torque finding."),
        ("Sensor snap-back is not a pack thermal transient", "Battery", "4.2.1", "Pass",
         "A pack cannot drop more than 12 C in one 20-minute sample with the fan stopped.",
         "Thermal mass model cannot produce the snap-back seen when a sensor is swapped.",
         "Separates drift from the real thermal shutdown."),
        ("Inverter remains latched after frequency returns", "Inverter", "4.2.1", "Pass",
         "After a 61.2 Hz excursion the inverter stays at zero power until reset.",
         "Latch held. Grid return alone did not restore power.",
         "Matches the Lantern Field trace."),
        ("Power-limit cap is visible in telemetry", "Inverter", "4.2.1", "Pass",
         "A 75 kW limit holds the peak at 75 while the unconstrained command is about 90.",
         "Peak held at 75 until the limit was restored.",
         "Matches the configuration mismatch."),
        ("SOC step fixture", "Battery", "4.2.1", "Blocked",
         "A single bench setup can distinguish estimator bias, current-sensor offset, and parasitic load.",
         "Blocked. The fixture cannot separate the three hypotheses with the captured trace.",
         "Leaves the SOC incident under investigation."),
        ("4.4.0 gateway CPU lab check", "Gateway", "4.4.0", "Pass",
         "Lab-only image stays under the CPU log threshold.",
         "CPU rose and stayed inside the lab threshold. No field install is approved.",
         "Beta image. No field device is on 4.4.0."),
        ("HW-A rejects 4.3.1", "Battery", "4.3.1", "Pass",
         "Installer refuses 4.3.1 on HW-A.",
         "Installer refused the image. HW-A remains on 4.1.4 or 4.2.1.",
         "Matches required_hardware_revision HW-B for 4.3.1."),
    ]
    for index, (name, device_type, version, result, expected, actual, notes) in enumerate(cases):
        world.tests.append({
            "test_id": f"TEST-{index+1:03d}",
            "test_name": name,
            "device_type": device_type,
            "firmware_version": version,
            "test_date": (at(2026, 9, 7, 0, 0) + timedelta(days=index)).strftime("%Y-%m-%d"),
            "test_environment": "Hardware-in-loop" if "Heartbeat" in name or "SOC" in name else "Lab",
            "expected_result": expected,
            "actual_result": actual,
            "result": result,
            "engineer": "ENG-110" if "Heartbeat" in name or "4.4.0" in name else "ENG-125",
            "related_issue": "COM-214" if "Heartbeat" in name else ("INC-008" if "SOC" in name else ""),
            "notes": notes,
        })


def build_anomalies_need_faults_first():
    return None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def median(values):
    return statistics.median(values)


def values_equal(left, right):
    try:
        return float(left) == float(right)
    except ValueError:
        return left.strip() == right.strip()


def validate(world):
    print("Running validation checks...")
    codes = {row["error_code"] for row in world.errors}
    sites = {row["site_id"] for row in world.sites}
    devices = {row["device_id"] for row in world.devices}
    device_rows = {row["device_id"]: row for row in world.devices}
    components = {row["component_id"] for row in world.components}
    faults = {row["fault_id"] for row in world.faults}
    incidents = {row["incident_id"] for row in world.incidents}
    fw_pairs = {(row["firmware_version"], row["device_type"]) for row in world.firmware}
    by_type = defaultdict(set)
    for row in world.firmware:
        by_type[row["device_type"]].add(row["firmware_version"])

    for device in world.devices:
        check(device["site_id"] in sites, f"{device['device_id']} site")
        check(device["customer_id"] == next(s["customer_id"] for s in world.sites if s["site_id"] == device["site_id"]),
              f"{device['device_id']} customer mismatch")
        check((device["firmware_version"], device["device_type"]) in fw_pairs,
              f"{device['device_id']} firmware {device['firmware_version']} not cataloged for {device['device_type']}")
        check(parse(device["commissioning_date"] + "T00:00:00-05:00") >= parse(device["installation_date"] + "T00:00:00-05:00"),
              "commission before install")

    by_site = defaultdict(list)
    for device in world.devices:
        by_site[device["site_id"]].append(device)
    for site in world.sites:
        devs = by_site[site["site_id"]]
        bats = [d for d in devs if d["device_type"] == "Battery"]
        invs = [d for d in devs if d["device_type"] == "Inverter"]
        check(int(site["number_of_batteries"]) == len(bats), f"{site['site_id']} battery count")
        check(int(site["number_of_inverters"]) == len(invs), f"{site['site_id']} inverter count")
        check(site["city"] in CITIES, site["city"])
        config = site["system_configuration"]
        n_bat, n_inv, n_ec = CONFIG_SHAPE[config]
        check(len(bats) == n_bat and len(invs) == n_inv, f"{site['site_id']} shape {config}")
        if n_ec:
            check(any(d["device_type"] == "Energy Controller" for d in devs), f"{site['site_id']} missing controller")
        check(int(site["battery_capacity_kwh"]) == sum(int(d["rated_capacity_kwh"] or 0) for d in bats), "battery kWh")
        check(int(site["inverter_capacity_kw"]) == sum(int(d["rated_power_kw"] or 0) for d in invs), "inverter kW")

    for row in world.components:
        check(row["device_id"] in devices, row["component_id"])
    for row in world.faults:
        check(row["device_id"] in devices, row["fault_id"])
        check(row["error_code"] in codes, row["fault_id"] + " code")
        if row["component_id"]:
            check(row["component_id"] in components, row["fault_id"] + " component")
            owner = next(c["device_id"] for c in world.components if c["component_id"] == row["component_id"])
            check(owner == row["device_id"], "fault component device")
        if row["fault_status"] == "Cleared":
            check(row["cleared_at"] and parse(row["cleared_at"]) >= parse(row["timestamp"]), "cleared_at")
        else:
            check(row["cleared_at"] == "", f"{row['fault_id']} cleared_at set while {row['fault_status']}")

    tel_by_device = defaultdict(list)
    for row in world.telemetry:
        check(row["device_id"] in devices, row["telemetry_id"])
        tel_by_device[row["device_id"]].append(row["timestamp"])
    for device_id, stamps in tel_by_device.items():
        parsed = [parse(s) for s in stamps]
        check(parsed == sorted(parsed), f"{device_id} telemetry order")
        check(len(parsed) == len(set(parsed)), f"{device_id} duplicate telemetry")

    for row in world.anomalies:
        check(row["device_id"] in devices, row["anomaly_id"])
        if row["related_fault_id"]:
            check(row["related_fault_id"] in faults, row["anomaly_id"])
        start, end = parse(row["start_time"]), parse(row["end_time"])
        check(start < end, row["anomaly_id"])
        inside = [
            t for t in tel_by_device[row["device_id"]]
            if start <= parse(t) <= end
        ]
        check(inside, f"{row['anomaly_id']} does not overlap telemetry")

    history = defaultdict(list)
    for row in world.fw_history:
        check(row["device_id"] in devices, row["deployment_id"])
        check(row["firmware_version"] in by_type[device_rows[row["device_id"]]["device_type"]], row["deployment_id"])
        if row["previous_version"]:
            check(row["previous_version"] in by_type[device_rows[row["device_id"]]["device_type"]], "previous fw")
        history[row["device_id"]].append(row)
    for device_id, rows in history.items():
        rows.sort(key=lambda row: row["installed_at"])
        check(rows[0]["previous_version"] == "", f"{device_id} first previous_version")
        for idx in range(1, len(rows)):
            check(rows[idx]["previous_version"] == rows[idx - 1]["firmware_version"],
                  f"{device_id} previous_version chain at {rows[idx]['deployment_id']}")
            check(parse(rows[idx]["installed_at"]) > parse(rows[idx - 1]["installed_at"]), "fw time")
        current = [row["firmware_version"] for row in rows if row["deployment_status"] in ("Successful", "Rolled Back")][-1]
        check(device_rows[device_id]["firmware_version"] == current, f"{device_id} current firmware")

    for row in world.configs:
        check(row["device_id"] in devices, row["configuration_id"])
        if row["configuration_status"] == "Mismatch":
            check(not values_equal(row["parameter_value"], row["expected_value"]), row["configuration_id"])
        else:
            check(values_equal(row["parameter_value"], row["expected_value"]), f"{row['configuration_id']} should match")

    events = defaultdict(list)
    for row in world.events:
        check(row["incident_id"] in incidents, row["event_id"])
        events[row["incident_id"]].append(row)
    for incident_id, rows in events.items():
        parsed = [parse(row["timestamp"]) for row in rows]
        check(parsed == sorted(parsed), f"{incident_id} events out of order")

    for row in world.tickets:
        if row["affected_device_id"]:
            check(row["affected_device_id"] in devices, row["ticket_id"])
        if row["affected_site_id"]:
            check(row["affected_site_id"] in sites, row["ticket_id"])
            if row["affected_device_id"]:
                check(device_rows[row["affected_device_id"]]["site_id"] == row["affected_site_id"], "ticket site")
        if row["related_error_code"]:
            check(row["related_error_code"] in codes, row["ticket_id"])
        if row["related_incident_id"]:
            check(row["related_incident_id"] in incidents, row["ticket_id"])
    for row in world.alerts:
        check(row["device_id"] in devices and row["site_id"] in sites, row["alert_id"])
        check(device_rows[row["device_id"]]["site_id"] == row["site_id"], "alert site")
        if row["related_error_code"]:
            check(row["related_error_code"] in codes, row["alert_id"])
        if row["related_incident_id"]:
            check(row["related_incident_id"] in incidents, row["alert_id"])
    for row in world.analyses:
        check(row["incident_id"] in incidents and row["device_id"] in devices, row["analysis_id"])
    for doc in world.documents:
        for code in filter(None, doc["related_error_codes"].split(";")):
            check(code in codes, doc["document_id"] + " " + code)
        for version in filter(None, doc["related_firmware_versions"].split(";")):
            check(any(row["firmware_version"] == version for row in world.firmware), version)
    for row in world.changes:
        for device_id in filter(None, row["affected_devices"].split(";")):
            check(device_id in devices, row["change_id"])
        if row["affected_firmware"]:
            check(any(f["firmware_version"] == row["affected_firmware"] for f in world.firmware), row["change_id"])
    for row in world.tests:
        check(any(f["firmware_version"] == row["firmware_version"] and f["device_type"] == row["device_type"] for f in world.firmware),
              row["test_id"])

    check(40 <= len(world.sites) <= 60, f"site scale {len(world.sites)}")
    check(100 <= len(world.devices) <= 150, f"device scale {len(world.devices)}")
    check(30 <= len(world.errors) <= 50, f"error scale {len(world.errors)}")
    check(10 <= len(world.firmware) <= 20, f"firmware scale {len(world.firmware)}")
    check(10000 <= len(world.telemetry) <= 30000, f"telemetry scale {len(world.telemetry)}")
    check(30 <= len(world.incidents) <= 50, f"incident scale {len(world.incidents)}")
    check(50 <= len(world.documents) <= 100, f"document scale {len(world.documents)}")

    online = sum(d["status"] == "Online" for d in world.devices)
    down = sum(d["status"] in ("Faulted", "Offline") for d in world.devices)
    check(online > down, f"online {online} vs down {down}")
    check(online > len(world.devices) / 2, "most devices online")
    unresolved = (
        any(i["status"] in ("Investigating", "Monitoring") for i in world.incidents)
        and any(t["status"] in ("Open", "Investigating", "Blocked") for t in world.tickets)
        and any(f["fault_status"] in ("Active", "Recurring", "Escalated") for f in world.faults)
        and any(a["status"] == "Open" for a in world.alerts)
    )
    check(unresolved, "expected some unresolved issues")
    critical_alerts = sum(a["severity"] == "Critical" for a in world.alerts)
    check(0 < critical_alerts < len(world.alerts), "alert severity mix")
    check(any(a["severity"] == "Info" for a in world.alerts), "info alerts")
    check(any(a["severity"] == "Warning" for a in world.alerts), "warning alerts")

    spot_check_patterns(world)
    assert_scenario_eight(world)
    print("All validation checks passed.")


def spot_check_patterns(world):
    thermal_id = world.named["thermal"]
    rows = series(world, thermal_id)
    temps = []
    ramp = []
    for row in rows:
        ts = parse(row["timestamp"])
        temp = float(row["battery_temperature_c"])
        if ts < THERMAL_RAMP_START:
            temps.append(temp)
        if THERMAL_RAMP_START <= ts <= THERMAL_OFFLINE:
            ramp.append(temp)
        check(ts <= THERMAL_OFFLINE, "thermal telemetry after offline")
    check(median(temps) < 34, f"pre-ramp temp median {median(temps)}")
    check(max(ramp) >= 65, f"ramp max {max(ramp)}")
    check(ramp[-1] - ramp[0] >= 25, "temperature did not rise enough")
    check(ramp[-1] > ramp[len(ramp) // 2] > ramp[0], "ramp not increasing")
    fault = next(f for f in world.faults if f["fault_id"] == world.named["flt_thermal"])
    check(THERMAL_RAMP_START <= parse(fault["timestamp"]) <= THERMAL_OFFLINE, "thermal fault outside rise")
    check(device_status(world, thermal_id) == "Offline", "thermal device status")

    volt_rows = [
        float(r["battery_voltage"]) for r in series(world, world.named["repeat_a"])
        if VOLT_WINDOWS[-1][0] <= parse(r["timestamp"]) <= VOLT_WINDOWS[-1][1]
    ]
    before_volt = [
        float(r["battery_voltage"]) for r in series(world, world.named["repeat_a"])
        if parse(r["timestamp"]) < VOLT_WINDOWS[0][0]
    ]
    check(statistics.pstdev(volt_rows) > 25, "voltage window not unstable")
    check(statistics.pstdev(before_volt) < 8, "voltage baseline not stable")

    comm_rows = series(world, world.named["comm_gw"])
    early = [float(r["communication_latency_ms"]) for r in comm_rows if parse(r["timestamp"]) < COMM_START]
    late = [float(r["communication_latency_ms"]) for r in comm_rows if parse(r["timestamp"]) >= COMM_START]
    early_s = [float(r["signal_strength_dbm"]) for r in comm_rows if parse(r["timestamp"]) < COMM_START]
    late_s = [float(r["signal_strength_dbm"]) for r in comm_rows if parse(r["timestamp"]) >= COMM_START]
    check(median(late) > 3 * median(early), "latency did not rise before disconnect")
    check(median(late_s) < median(early_s) - 15, "signal did not fall before disconnect")
    check(parse(comm_rows[-1]["timestamp"]) == COMM_OFFLINE, "comm telemetry did not stop at offline")

    soc_rows = series(world, world.named["soc_bat"])
    before = next(r for r in soc_rows if parse(r["timestamp"]) == SOC_STEP - STEP)
    at_step = next(r for r in soc_rows if parse(r["timestamp"]) == SOC_STEP)
    check(float(before["battery_soc_percent"]) - float(at_step["battery_soc_percent"]) > 30, "SOC did not step")
    check(abs(float(at_step["battery_current"])) < 8, "SOC step had real current")
    check(float(at_step["discharge_rate_kw"]) < 5 and float(at_step["charge_rate_kw"]) < 5, "SOC step had real power")

    power_rows = series(world, world.named["power_inv"])
    pre = next(r for r in power_rows if parse(r["timestamp"]) == POWER_DROP - STEP)
    post = next(r for r in power_rows if parse(r["timestamp"]) == POWER_DROP)
    check(float(pre["inverter_power_kw"]) > 50, "power before drop")
    check(float(post["inverter_power_kw"]) < 15, "power after drop")
    check(float(pre["grid_frequency_hz"]) < 60.2, "power drop should not be a frequency event")

    freq_rows = series(world, world.named["freq_inv"])
    peak = next(r for r in freq_rows if parse(r["timestamp"]) == FREQ_PEAK)
    after = [r for r in freq_rows if parse(r["timestamp"]) > FREQ_PEAK]
    before_freq = [r for r in freq_rows if parse(r["timestamp"]) < FREQ_START and r["operating_state"] == "Discharging"]
    check(float(peak["grid_frequency_hz"]) > 60.6, "frequency peak missing")
    check(all(float(r["inverter_power_kw"]) < 5 for r in after), "inverter did not stay tripped")
    check(max(float(r["inverter_power_kw"]) for r in before_freq) > 40, "frequency case had no prior power")

    # Firmware regression is scenario 2 and must be numerically distinct from the radio failure.
    stuck = series(world, world.named["fw_stuck_bat"])
    before_l = [float(r["communication_latency_ms"]) for r in stuck if parse(r["timestamp"]) < FW_UPGRADE]
    after_l = [float(r["communication_latency_ms"]) for r in stuck if parse(r["timestamp"]) >= FW_UPGRADE]
    before_sig = [float(r["signal_strength_dbm"]) for r in stuck if parse(r["timestamp"]) < FW_UPGRADE]
    after_sig = [float(r["signal_strength_dbm"]) for r in stuck if parse(r["timestamp"]) >= FW_UPGRADE]
    check(median(before_l) < 60 and median(after_l) > 250, "4.3.0 latency step missing")
    check(abs(median(before_sig) - median(after_sig)) < 8, "4.3.0 should not move signal strength")
    rolled = series(world, world.named["fw_rollback_gw"])
    mid = [float(r["communication_latency_ms"]) for r in rolled if FW_UPGRADE <= parse(r["timestamp"]) < FW_ROLLBACK]
    back = [float(r["communication_latency_ms"]) for r in rolled if parse(r["timestamp"]) >= FW_ROLLBACK]
    check(median(mid) > 250 and median(back) < 60, "rollback did not restore latency")

    drift_rows = series(world, world.named["drift_bat"])
    drift_before = [float(r["battery_temperature_c"]) for r in drift_rows if parse(r["timestamp"]) < DRIFT_START]
    drift_mid = [float(r["battery_temperature_c"]) for r in drift_rows if DRIFT_START <= parse(r["timestamp"]) < DRIFT_REPLACE]
    drift_after = [float(r["battery_temperature_c"]) for r in drift_rows if parse(r["timestamp"]) >= DRIFT_REPLACE]
    volts = [float(r["battery_voltage"]) for r in drift_rows if DRIFT_START <= parse(r["timestamp"]) < DRIFT_REPLACE]
    check(drift_mid[-1] - drift_mid[0] >= 15, "drift slope missing")
    check(median(drift_after) < 34, "drift did not snap back")
    check(drift_mid[-1] - drift_after[0] > 12, "snap-back too small")
    check(min(volts) > 730 and max(volts) < 790, "drift voltage should stay normal")
    check(median(drift_before) < 34, "drift baseline")

    config_rows = series(world, world.named["config_inv"])
    before_cap = [
        float(r["inverter_power_kw"]) for r in config_rows
        if parse(r["timestamp"]).astimezone(TZ).date().isoformat() == "2026-09-17"
    ]
    after_cap = [
        float(r["inverter_power_kw"]) for r in config_rows
        if parse(r["timestamp"]).astimezone(TZ).date().isoformat() == "2026-09-20"
    ]
    check(74 <= max(before_cap) <= 75.5, f"config cap before fix {max(before_cap)}")
    check(max(after_cap) >= 85, f"config cap after fix {max(after_cap)}")

    for alias in ("healthy_Battery_2", "healthy_Battery_1", "healthy_Inverter_1", "healthy_Gateway_1"):
        healthy = series(world, world.named[alias])
        if "Inverter" in alias:
            freqs = [float(r["grid_frequency_hz"]) for r in healthy]
            check(max(freqs) < 60.1 and min(freqs) > 59.9, alias)
        if "Gateway" in alias:
            lats = [float(r["communication_latency_ms"]) for r in healthy]
            check(max(lats) < 80, alias)
        if "Battery" in alias:
            temps = [float(r["battery_temperature_c"]) for r in healthy]
            check(max(temps) < 36, f"{alias} temp {max(temps)}")


def device_status(world, device_id):
    return next(d["status"] for d in world.devices if d["device_id"] == device_id)


def assert_scenario_eight(world):
    inc_id = world.named["inc_soc"]
    device_id = world.named["soc_bat"]
    incident = next(row for row in world.incidents if row["incident_id"] == inc_id)
    check(incident["confirmed_root_cause"] == UNDER, "INC-008 confirmed cause")
    check(incident["status"] == "Investigating", "INC-008 status")
    check(incident["permanent_fix"] == "", "INC-008 permanent fix")
    check("none confirmed" in incident["suspected_root_cause"].lower(), "INC-008 hypotheses")
    types = [row["event_type"] for row in world.events if row["incident_id"] == inc_id]
    check("Root Cause Confirmed" not in types, "INC-008 confirmed event")
    check("Incident Resolved" not in types, "INC-008 resolved event")
    for row in world.analyses:
        if row["incident_id"] == inc_id:
            check(row["root_cause"] == UNDER, "INC-008 analysis")
            check(row["corrective_action"] == "", "INC-008 corrective")
    for row in world.tickets:
        if row["related_incident_id"] == inc_id:
            check(row["root_cause"] == UNDER, "INC-008 ticket cause")
            check(row["resolution"] == "", "INC-008 ticket resolution")
            check(row["status"] in ("Open", "Investigating", "Blocked"), "INC-008 ticket status")
    for row in world.faults:
        if row["device_id"] == device_id and row["error_code"] == "BAT-330":
            check(row["resolution"] == "", "INC-008 fault resolution")
            check("confirmed" not in row["notes"].lower() or "not confirmed" in row["notes"].lower(), "fault notes")
    for row in world.changes:
        blob = " ".join(row.values()).lower()
        check(inc_id.lower() not in blob and device_id.lower() not in blob, "change names the unresolved incident")
    for row in world.documents:
        if inc_id in row["summary"] or device_id in row["summary"]:
            check("under investigation" in row["summary"].lower(), "SOC document")
            check("confirmed root cause is the" not in row["summary"].lower(), "SOC document confirms a cause")


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def device_line(world, key):
    device_id = world.named[key]
    device = next(d for d in world.devices if d["device_id"] == device_id)
    return f"{device_id} ({device['device_type']}, {device['status']}, firmware {device['firmware_version']}, {device['hardware_revision']}) at {device['site_id']}"


def write_markdown(world):
    thermal = world.named["thermal"]
    questions = [
        f"Why did battery {thermal} go offline?",
        f"What did pack temperature do in the hours before {thermal} went offline?",
        f"Which fault code tripped {thermal}, and which component failed?",
        f"What is the confirmed root cause of {world.named['inc_thermal']}?",
        f"What is the timeline of {world.named['inc_thermal']}?",
        f"Which troubleshooting document should an engineer follow for THERM-201 on {thermal}?",
        f"Did the communication faults on {world.named['fw_stuck_bat']} start after the firmware update?",
        "What changed between firmware 4.2.1 and 4.3.0?",
        "What is the known issue in firmware 4.3.0, and which version fixes it?",
        f"Which devices installed 4.3.0, which rolled back to 4.2.1, and which are still on 4.3.0?",
        f"What do the hardware-in-loop tests say about heartbeat behavior on 4.3.0 versus 4.3.1?",
        f"Which configuration row shows the Limestone inverter {world.named['config_inv']} was capped, and what is the value after the correction?",
        f"Did the repeated inverter faults on {world.named['config_inv']} stop after the configuration change?",
        "Which configuration parameters are outside the expected value in the current snapshot?",
        f"Why did gateway {world.named['comm_gw']} go offline?",
        f"How is the {world.named['comm_gw']} link loss different from the 4.3.0 heartbeat regression?",
        f"Which sites and devices share BAT-204, and what hardware revision do they have in common?",
        f"What did pack voltage do before the BAT-204 fault on {world.named['repeat_a']}?",
        f"How is the temperature event on {world.named['drift_bat']} different from the shutdown on {thermal}?",
        f"Were the thermal alerts on {world.named['drift_bat']} false alarms?",
        f"What happened to inverter power on {world.named['power_inv']}?",
        f"Which ticket tracks the inverter power collapse, and why is it blocked?",
        f"What is the confirmed root cause of {world.named['inc_soc']}?",
        f"Which hypotheses are still open for {world.named['inc_soc']}, and which tickets are still open?",
        f"What do {world.named['inc_hist_a']} and {world.named['inc_hist_b']} have in common, and how do their confirmed causes differ?",
        "Which systems should engineering investigate proactively, before they fail?",
        f"What early signals are present on {world.named['pro_temp']}, {world.named['pro_gw']}, and {world.named['pro_minor']}?",
        "Are there conflicting engineering documents?",
        f"Which documents disagree about the response to THERM-201, and which IDs are they?",
        f"What components are installed on {thermal}, and what is the cooling fan status?",
        f"What is the firmware history of {world.named['fw_fixed_gw']}?",
        "Which devices are still on firmware 4.1.4, and why have they not taken 4.3.1?",
        "Which open alerts are warnings or info rather than critical?",
        f"What is the status of the site that hosts {thermal}, and what else is installed there?",
        "How many devices are online compared with faulted or offline?",
        "What are the recommended diagnostic steps for COM-214?",
        "Which incidents are firmware related?",
        f"Which anomaly windows overlap the telemetry that shows the {thermal} temperature rise?",
        f"What preventive action came out of the HW-C investigation {world.named['inc_repeat']}?",
        f"What grid event latched inverter {world.named['freq_inv']}, and why is that not a power-module failure?",
        "Which incidents share the DC bus capacitor failure mode?",
        f"What is the current firmware of {thermal}, and was firmware ruled out for its shutdown?",
        "Which engineering change halted firmware 4.3.0?",
        "What does a configuration_status of Mismatch mean, and which live rows are mismatches?",
        f"What evidence separates sensor drift on {world.named['drift_bat']} from a real thermal shutdown?",
        "Which test is blocked, and which incident does that leave open?",
        f"What error-code document describes BAT-204, and which component type does it point to?",
        "Which devices are in Maintenance, Degraded, Faulted, or Offline?",
        f"After {world.named['fw_rollback_gw']} rolled back to 4.2.1, did latency recover?",
        f"What should the field do next for {thermal} even though the investigation is resolved?",
    ]
    check(len(questions) >= 40, "question count")

    lines = [
        "# Engineering test questions",
        "",
        "Synthetic questions for the Engineer persona. Identifiers match the generated CSVs.",
        f"Snapshot time: {fmt(NOW)} America/Chicago.",
        "",
    ]
    for index, question in enumerate(questions, start=1):
        lines.append(f"{index}. {question}")
    lines.append("")
    (OUT / "engineering_test_questions.md").write_text("\n".join(lines), encoding="utf-8")

    scenarios = f"""# Engineering demo scenarios

Snapshot: {fmt(NOW)} America/Chicago. All identifiers are synthetic.

## 1. Thermal failure

Battery {device_line(world, 'thermal')} went offline after a real temperature rise.

- Site: {world.named['site_thermal']} Copper Elm Node, Austin.
- Telemetry from 2026-09-26 08:00 through 14:40 shows pack temperature climbing from about 34 C to about 73 C while the pack was discharging. Earlier samples sit near 28 C.
- Warning fault THERM-110, then critical fault THERM-201 at 14:20 tied to cooling fan {world.named['thermal_fan']}. The fan status is Failed. The pack stops reporting at 14:40 and device status is Offline.
- Anomaly {world.named['ano_thermal']} overlaps that rise.
- Incident {world.named['inc_thermal']} is resolved. Confirmed root cause: cooling fan bearing seizure. The temperature threshold was not raised. Firmware is 4.2.1 and was ruled out.
- A field ticket remains open to install the replacement fan, so the pack is still offline in this snapshot.
- Follow {world.named['doc_thermal_runbook']}, not the conflicting threshold guide.

Supports: why this battery went offline; what the temperature did; which fault and component; the incident timeline.

## 2. Firmware regression

Several devices moved from 4.2.1 to 4.3.0 on 2026-09-15 02:00 and then raised COM-214. Signal strength stayed near -64 dBm while latency stepped from about 30 ms to about 340 ms.

- Rolled back to 4.2.1 on 2026-09-18: {device_line(world, 'fw_rollback_gw')} and {device_line(world, 'fw_rollback_inv')}. Latency on the gateway recovered after the rollback.
- Patched to 4.3.1 on 2026-09-20: {device_line(world, 'fw_fixed_gw')}. Latency recovered after 4.3.1.
- Still on 4.3.0 with active COM-214: {device_line(world, 'fw_stuck_bat')} and {device_line(world, 'fw_stuck_gw')}.
- Incident {world.named['inc_firmware']}. Firmware 4.3.0 release notes describe the heartbeat change from 4.2.1. 4.3.1 release notes describe the fix.
- Tests TEST-001 (4.3.0 Fail), TEST-002 (4.3.1 Pass), and TEST-003 (4.2.1 Pass) are the same heartbeat case.

Supports: did this start after the firmware update; what changed between 4.2.1 and 4.3.0; which devices rolled back.

## 3. Configuration mismatch

Inverter {device_line(world, 'config_inv')} at Limestone Yard.

- Historical configuration row: Inverter Power Limit parameter_value 75 kW, expected_value 90 kW, configuration_status Mismatch, last modified 2026-08-12.
- Corrected row: 90 kW equals expected 90 kW, last modified 2026-09-18 10:00.
- Before the correction, afternoon telemetry flatlines at 75 kW. After it, peaks reach the high 80s. Repeated INV-360 and CFG-101 faults are cleared at the correction time.
- Incident {world.named['inc_config']} is resolved.
- Live mismatches still open on other devices: SOC Maximum 75 versus expected 90 on {world.named['mismatch_soc']}, Communication Timeout 8 s versus 30 s on {world.named['mismatch_timeout']}, Grid Voltage Limit 492 V versus 504 V on {world.named['mismatch_voltage']}.

Supports: a parameter outside the expected value, repeated inverter faults, and a correction that clears them.

## 4. Communication failure

Gateway {device_line(world, 'comm_gw')} at Owl Hollow Pad.

- From 2026-09-24 18:00 to 2026-09-25 02:00, latency climbs from about 48 ms toward 1750 ms and signal strength falls from about -68 dBm toward -107 dBm.
- COM-118, GW-090, then COM-101. The gateway goes offline and telemetry stops. Firmware stays 4.2.1. There is no 4.3.0 install.
- Incident {world.named['inc_comm']}. Anomaly {world.named['ano_comm']}.
- This is a radio-path failure. The 4.3.0 regression moves latency only.

Supports: latency up, signal down, intermittent telemetry, then offline.

## 5. Repeated failure

BAT-204 on three HW-C batteries during discharge above 70 kW. One investigation.

- {device_line(world, 'repeat_a')}
- {device_line(world, 'repeat_b')}
- {device_line(world, 'repeat_c')}
- Voltage on the first pack swings between about 705 V and 812 V before the fault. Normal baseline voltage is stable near 750 V.
- Incident {world.named['inc_repeat']}. Confirmed cause: HW-C power-module busbar torque below spec. Firmware is not the common factor.
- Anomaly {world.named['ano_voltage']}.

Supports: same error code, same hardware revision, similar conditions, one investigation.

## 6. Sensor drift

Battery {device_line(world, 'drift_bat')} stayed online.

- From 2026-09-20 to the replacement at 2026-09-24 09:00, reported temperature climbs smoothly by more than 15 C while voltage stays inside the normal band.
- At the replacement, temperature snaps back to about 28 C in one sample. A real pack would not do that.
- False THERM-110 warnings and THERM-155. Sensor {world.named['drift_sensor']} is Replaced. New sensor {world.named['drift_sensor_new']} is In Service.
- Incident {world.named['inc_drift']} is resolved. This is not {world.named['inc_thermal']}.

Supports: telling a false thermal alert from the real Copper Elm shutdown.

## 7. Inverter power drop

Inverter {device_line(world, 'power_inv')}.

- The sample before 2026-09-23 17:40 is about 78 kW. The next sample is about 6.5 kW, and power stays down. Grid frequency stays near 60 Hz. The DC bus sags.
- Fault INV-402. Incident {world.named['inc_power']}. Ticket {world.named['et_power']} is Blocked on the replacement power module.
- The power limit on this inverter already matched 90 kW, so this is not scenario 3.

Supports: normal power, then a sudden reduction, with a fault and a ticket.

## 8. Unknown root cause

Battery {device_line(world, 'soc_bat')}. Incident {world.named['inc_soc']}.

- At 2026-09-21 03:20, SOC falls by about 50 points while current and charge/discharge power at that sample are near zero.
- Fault BAT-330 is Active. Confirmed root cause is exactly "{UNDER}".
- Unconfirmed hypotheses only: SOC estimator bias, current-sensor offset, standby parasitic load.
- Tickets {world.named['et_soc_1']} and {world.named['et_soc_2']} are open. There is no Root Cause Confirmed event and no permanent fix.
- Firmware is 4.2.1, the same as healthy peers. Do not treat a hypothesis as the cause.

Supports: a clear symptom with more than one possible cause, still unresolved.

## 9. Similar history, different causes

Both incidents are titled "Contactor opened during discharge". The symptom text matches: the main contactor opened during a routine discharge, with no thermal alarm and no firmware change in the prior 7 days.

- {world.named['inc_hist_a']} on {device_line(world, 'hist_a')}. Confirmed cause: contactor coil driver failed (REL-204, coil current zero).
- {world.named['inc_hist_b']} on {device_line(world, 'hist_b')}. Confirmed cause: precharge resistor open (REL-210, coil current present, DC bus did not rise).

Supports: similar incidents with different confirmed root causes.

## 10. Proactive investigation

None of these devices has failed. Status is Online. Incident {world.named['inc_pro']} is Monitoring.

- {device_line(world, 'pro_temp')}: temperature sits near 40 C, below the 60 C trip. Warning only.
- {device_line(world, 'pro_gw')}: latency climbs from about 42 ms toward about 140 ms. RSSI stays stable. Firmware is not 4.3.0.
- {device_line(world, 'pro_minor')}: four isolated BMS-218 watchdog restarts, then the pack returns.

Supports: which systems engineering should investigate before they fail.

## 11. Grid frequency excursion

Inverter {device_line(world, 'freq_inv')}. Incident {world.named['inc_freq']}.

Frequency reaches 61.28 Hz at 2026-09-25 13:40, power goes to zero, frequency returns, and the INV-201 latch holds power at zero. This is not the power-module collapse in scenario 7.

## 12. Conflicting documents

{world.named['doc_thermal_runbook']} THERM-201 Protective Shutdown Runbook says to replace the cooling fan and not to raise the temperature threshold.

{world.named['doc_thermal_conflict']} Field Configuration Guide: Thermal Thresholds says to raise the threshold by 10 C and treats fan replacement as optional.

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
"""
    (OUT / "engineering_demo_scenarios.md").write_text(scenarios, encoding="utf-8")

    dictionary = '''# Engineering data dictionary

Synthetic tables for the Engineer persona. Primary keys are unique inside each file. Foreign keys are enforced by `scripts/generate_engineering_data.py`.

There is no customer dimension file. `customer_id` is a shared synthetic key (`CUST-###`) on sites and devices. The fictional customer names live in the generator and in this dictionary:

'''
    dictionary += "\n".join(f"- {cid}: {name}" for cid, name in CUSTOMERS)
    dictionary += """

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
"""
    (OUT / "engineering_data_dictionary.md").write_text(dictionary, encoding="utf-8")

    readme = f"""# Synthetic engineering dataset

Generated for the Knowledge Platform Engineer persona. Everything in this folder is fictional. There are no real customers, street addresses, product serials, credentials, or personal data.

Regenerate with:

```bash
python3 scripts/generate_engineering_data.py
```

The generator builds sites, devices, components, faults, telemetry, and incidents from one in-memory model, writes the CSVs, and exits with an error if a foreign key, count, or scripted pattern check fails.

Snapshot time: {fmt(NOW)} America/Chicago.

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

- An offline battery: open the device, then its last telemetry, thermal faults, fan component, and incident {world.named['inc_thermal']}.
- A complaint that started after an update: compare `device_firmware_history.installed_at` with the first COM-214, then read the 4.2.1 and 4.3.0 release notes and the heartbeat tests.
- Repeated inverter limits: read configuration history and the power trace before and after the correction.
- A gateway that vanished: plot latency and signal strength, then check whether firmware changed.
- The same code at several sites: group by hardware revision and discharge condition.
- A thermal warning that might be false: compare the drift pack with the Copper Elm shutdown. One snaps back and stays online. The other trips and goes offline.
- An SOC step that nobody can explain yet: {world.named['inc_soc']} stays `{UNDER}`.
- Two old contactor incidents: same symptom, different confirmed parts.
- A watch list: the three online devices in {world.named['inc_pro']}.

## Example questions

- Why did battery {thermal} go offline?
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
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8")

    # Scenario 8 must stay unresolved in the prose as well as the tables.
    blob = "\n".join([
        (OUT / "engineering_demo_scenarios.md").read_text(encoding="utf-8"),
        (OUT / "engineering_test_questions.md").read_text(encoding="utf-8"),
        (OUT / "README.md").read_text(encoding="utf-8"),
    ])
    inc_id = world.named["inc_soc"]
    check(inc_id in blob, "scenario 8 missing from prose")
    for line in blob.splitlines():
        if inc_id in line or world.named["soc_bat"] in line:
            lower = line.lower()
            if "root cause" in lower:
                check(
                    "under investigation" in lower or "not confirmed" in lower or "none confirmed" in lower
                    or "no confirmed" in lower or "unconfirmed" in lower or "confirmed root cause of" in lower
                    or "does not confirm" in lower or "?" in line,
                    f"prose may confirm scenario 8: {line}",
                )


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fields})


def write_tables(world):
    OUT.mkdir(parents=True, exist_ok=True)
    write_csv(OUT / "engineering_sites.csv", world.sites, [
        "site_id", "customer_id", "site_name", "city", "latitude", "longitude",
        "system_configuration", "battery_capacity_kwh", "inverter_capacity_kw",
        "number_of_batteries", "number_of_inverters", "installation_date",
        "commissioning_date", "site_status",
    ])
    write_csv(OUT / "devices.csv", world.devices, [
        "device_id", "device_serial", "customer_id", "site_id", "device_type",
        "manufacturer", "model", "installation_date", "status", "firmware_version",
        "hardware_revision", "commissioning_date", "last_seen_at",
        "rated_capacity_kwh", "rated_power_kw",
    ])
    write_csv(OUT / "device_components.csv", world.components, [
        "component_id", "device_id", "component_type", "expected_lifespan_hours",
        "hardware_revision", "serial_number", "status",
    ])
    write_csv(OUT / "error_codes.csv", world.errors, [
        "error_code", "severity", "subsystem", "title", "description", "likely_causes",
        "recommended_diagnostic_steps", "escalation_required", "known_firmware_fix",
        "related_component_type",
    ])
    write_csv(OUT / "device_faults.csv", world.faults, [
        "fault_id", "device_id", "timestamp", "error_code", "severity", "fault_status",
        "detected_by", "component_id", "technician_id", "job_id", "cleared_at",
        "resolution", "notes",
    ])
    write_csv(OUT / "device_telemetry.csv", world.telemetry, [
        "telemetry_id", "device_id", "timestamp", "battery_soc_percent", "battery_voltage",
        "battery_current", "battery_temperature_c", "inverter_power_kw", "grid_voltage",
        "grid_frequency_hz", "dc_bus_voltage", "charge_rate_kw", "discharge_rate_kw",
        "communication_latency_ms", "signal_strength_dbm", "operating_state",
    ])
    write_csv(OUT / "telemetry_anomalies.csv", world.anomalies, [
        "anomaly_id", "device_id", "start_time", "end_time", "anomaly_type", "metric",
        "expected_range", "observed_range", "severity", "detected", "related_fault_id", "notes",
    ])
    write_csv(OUT / "firmware_versions.csv", world.firmware, [
        "firmware_version", "device_type", "release_date", "status", "previous_version",
        "release_notes", "known_issues", "resolved_issues", "required_hardware_revision",
        "rollout_status",
    ])
    write_csv(OUT / "device_firmware_history.csv", world.fw_history, [
        "deployment_id", "device_id", "firmware_version", "installed_at", "installed_by",
        "deployment_status", "previous_version", "rollback_reason",
    ])
    write_csv(OUT / "device_configuration.csv", world.configs, [
        "configuration_id", "device_id", "parameter_name", "parameter_value", "unit",
        "expected_value", "min_allowed", "max_allowed", "last_modified", "modified_by",
        "configuration_status",
    ])
    write_csv(OUT / "engineering_incidents.csv", world.incidents, [
        "incident_id", "incident_title", "severity", "status", "created_at", "resolved_at",
        "affected_device_count", "affected_site_count", "primary_subsystem",
        "suspected_root_cause", "confirmed_root_cause", "impact", "mitigation",
        "permanent_fix", "firmware_related", "related_firmware_version",
    ])
    write_csv(OUT / "incident_events.csv", world.events, [
        "event_id", "incident_id", "timestamp", "event_type", "engineer", "description",
        "evidence_reference",
    ])
    write_csv(OUT / "engineering_tickets.csv", world.tickets, [
        "ticket_id", "title", "description", "priority", "status", "created_at",
        "assigned_engineer", "subsystem", "affected_device_id", "affected_site_id",
        "related_error_code", "related_incident_id", "root_cause", "resolution",
        "linked_firmware_version",
    ])
    write_csv(OUT / "engineering_documents.csv", world.documents, [
        "document_id", "title", "document_type", "subsystem", "version", "created_at",
        "updated_at", "author", "status", "summary", "applicable_device_types",
        "related_error_codes", "related_firmware_versions",
    ])
    write_csv(OUT / "failure_analysis.csv", world.analyses, [
        "analysis_id", "incident_id", "device_id", "failure_mode", "symptoms",
        "contributing_factors", "investigation_method", "evidence", "root_cause",
        "corrective_action", "preventive_action", "confidence", "analysis_date",
    ])
    write_csv(OUT / "engineering_changes.csv", world.changes, [
        "change_id", "title", "change_type", "subsystem", "description", "reason",
        "created_at", "approved_at", "implementation_date", "status", "affected_devices",
        "affected_firmware", "risk_level",
    ])
    write_csv(OUT / "engineering_test_results.csv", world.tests, [
        "test_id", "test_name", "device_type", "firmware_version", "test_date",
        "test_environment", "expected_result", "actual_result", "result", "engineer",
        "related_issue", "notes",
    ])
    write_csv(OUT / "engineering_alerts.csv", world.alerts, [
        "alert_id", "created_at", "alert_type", "severity", "device_id", "site_id",
        "metric", "observed_value", "threshold", "description", "status",
        "recommended_action", "related_error_code", "related_incident_id",
    ])


def print_report(world):
    print("ROW COUNTS")
    print(f"sites: {len(world.sites)}")
    print(f"devices: {len(world.devices)}")
    print(f"components: {len(world.components)}")
    print(f"faults: {len(world.faults)}")
    print(f"telemetry: {len(world.telemetry)}")
    print(f"anomalies: {len(world.anomalies)}")
    print(f"firmware_versions: {len(world.firmware)}")
    print(f"incidents: {len(world.incidents)}")
    print(f"tickets: {len(world.tickets)}")
    print(f"documents: {len(world.documents)}")
    print(f"failure_analyses: {len(world.analyses)}")
    print(f"alerts: {len(world.alerts)}")
    print("SCENARIOS")
    for key in (
        "thermal", "inc_thermal", "fw_rollback_gw", "fw_fixed_gw", "fw_stuck_bat",
        "fw_stuck_gw", "fw_rollback_inv", "inc_firmware", "config_inv", "inc_config",
        "comm_gw", "inc_comm", "repeat_a", "repeat_b", "repeat_c", "inc_repeat",
        "drift_bat", "inc_drift", "power_inv", "inc_power", "et_power", "soc_bat",
        "inc_soc", "hist_a", "hist_b", "inc_hist_a", "inc_hist_b", "pro_temp",
        "pro_gw", "pro_minor", "inc_pro", "freq_inv", "inc_freq",
        "doc_thermal_runbook", "doc_thermal_conflict",
    ):
        print(f"  {key}: {world.named[key]}")


def main():
    world = World()
    world.errors = error_catalog()
    world.firmware = firmware_catalog()
    build_fleet(world)
    finalize_sites(world)
    build_components(world)
    build_firmware_history(world)
    build_configuration(world)
    build_telemetry(world)
    build_faults(world)
    build_scripted_incidents(world)
    build_extra_incidents(world)
    build_anomalies(world)
    build_tickets(world)
    build_alerts(world)
    build_documents(world)
    build_analyses(world)
    build_changes(world)
    build_tests(world)
    validate(world)
    write_tables(world)
    write_markdown(world)
    print_report(world)


if __name__ == "__main__":
    try:
        main()
    except BrokenPipeError:
        sys.exit(0)
