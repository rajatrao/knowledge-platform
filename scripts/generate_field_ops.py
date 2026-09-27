#!/usr/bin/env python3
"""Generate the synthetic Lumenfield Energy field-operations dataset.

All rows are built from shared in-memory records so foreign keys, van
assignments, stock, and the 2026-09-27 16:00 America/Chicago snapshot stay
aligned. The script exits non-zero if any validation check fails.

    python3 scripts/generate_field_ops.py
"""

from __future__ import annotations

import csv
import sys
from collections import defaultdict
from datetime import datetime, timedelta
from math import asin, cos, radians, sin, sqrt
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

TODAY = "2026-09-27"
TOMORROW = "2026-09-28"
NOW = "2026-09-27T16:00:00-05:00"
NOW_DT = datetime(2026, 9, 27, 16, 0, 0)
ONSITE_CUTOFF = "2026-09-27T14:00:00-05:00"

# Demo spine. These IDs are the ones the hackathon questions refer to.
DEMO_TECH = "T001"
DEMO_VAN = "V001"
DEMO_JOB = "J001"
DEMO_PART = "P001"
DEMO_WH = "W001"
URGENT_JOB = "J010"
DELAYED_JOB = "J007"
OVERDUE_JOB = "J030"
TODAY_SITE = "C020"
TODAY_SITE_JOB = "J021"
HERO_TECH = "T004"
HERO_VAN = "V004"
SPARE_VAN = "V020"
SHOP_VAN = "V018"
DUE_VAN = "V019"
OFFLINE_VAN = "V012"
SHORT_PART = "P018"  # missing on V001, required by J001
BLOCKED_PART = "P006"  # missing on V010, OOS at W001, in stock at W002

TECH_STATUSES = {"Available", "On Job", "En Route", "Off Duty", "Break"}
VAN_STATUSES = {"Available", "On Job", "En Route", "Parked", "Maintenance"}
JOB_TYPES = (
    "Installation",
    "Battery Replacement",
    "Battery Repair",
    "Inverter Repair",
    "Inspection",
    "Preventive Maintenance",
    "Emergency Service",
    "Troubleshooting",
)
JOB_STATUSES = {
    "Scheduled",
    "Assigned",
    "En Route",
    "Onsite",
    "In Progress",
    "Waiting for Parts",
    "Completed",
    "Cancelled",
}
PRIORITIES = {"Low", "Medium", "High", "Critical"}
PART_CATEGORIES = {
    "Battery",
    "Inverter",
    "Electrical",
    "Cable",
    "Connector",
    "Fuse",
    "Circuit Protection",
    "Mounting Hardware",
    "Sensors",
    "Tools",
}
TX_TYPES = {
    "Received",
    "Transfer",
    "Issued",
    "Reserved",
    "Installed",
    "Returned",
    "Scrapped",
    "Adjustment",
}
LOC_TYPES = {"Supplier", "Warehouse", "Van", "Job", "CustomerSite"}
EVENT_TYPES = {
    "Created",
    "Assigned",
    "Technician Dispatched",
    "En Route",
    "Arrived Onsite",
    "Diagnosis",
    "Part Required",
    "Waiting for Parts",
    "Repair Started",
    "Repair Completed",
    "Customer Signoff",
    "Job Completed",
    "Escalated",
}
VEH_TYPES = {
    "Check In",
    "Check Out",
    "Maintenance",
    "Inspection",
    "Warning",
    "Repair",
    "Fuel/Charge",
}
ALERT_TYPES = {
    "Low Inventory",
    "Out of Stock",
    "Missing Job Parts",
    "Technician Delayed",
    "Van Offline",
    "Maintenance Due",
    "Job Overdue",
    "Inventory Discrepancy",
    "Unassigned Critical Job",
}
SEVERITIES = {"Low", "Medium", "High", "Critical"}
JP_STATUSES = {"Required", "Allocated", "Installed", "Missing"}
FIELD_STATUSES = {"En Route", "Onsite", "In Progress", "Waiting for Parts"}
OPEN_STATUSES = JOB_STATUSES - {"Completed", "Cancelled"}

# Status -> event types that must appear in this order (extra events allowed).
STATUS_SEQUENCE = {
    "Scheduled": ["Created"],
    "Assigned": ["Created", "Assigned"],
    "En Route": ["Created", "Assigned", "Technician Dispatched", "En Route"],
    "Onsite": ["Created", "Assigned", "Technician Dispatched", "En Route", "Arrived Onsite"],
    "In Progress": [
        "Created",
        "Assigned",
        "Technician Dispatched",
        "En Route",
        "Arrived Onsite",
        "Diagnosis",
        "Repair Started",
    ],
    "Waiting for Parts": [
        "Created",
        "Assigned",
        "Technician Dispatched",
        "En Route",
        "Arrived Onsite",
        "Diagnosis",
        "Part Required",
        "Waiting for Parts",
    ],
    "Completed": [
        "Created",
        "Assigned",
        "Technician Dispatched",
        "En Route",
        "Arrived Onsite",
        "Diagnosis",
        "Repair Started",
        "Repair Completed",
        "Customer Signoff",
        "Job Completed",
    ],
    "Cancelled": ["Created"],
}

# Fictional anchors in the Austin metro. These are not street addresses.
CITIES = {
    "Austin": (30.29140, -97.76820),
    "Round Rock": (30.51860, -97.70140),
    "Cedar Park": (30.49120, -97.83150),
    "Georgetown": (30.64810, -97.66340),
    "Pflugerville": (30.44680, -97.64120),
    "Leander": (30.56940, -97.85980),
    "Hutto": (30.53720, -97.55860),
    "Manor": (30.35640, -97.54820),
    "Lakeway": (30.37150, -97.97940),
    "Buda": (30.09680, -97.85120),
}
CITY_CYCLE = list(CITIES)

SITE_NAMES = [
    "Copper Lantern Home",
    "Bluebonnet Storage Yard",
    "San Gabriel Clinic Backup",
    "Limestone Ridge House",
    "Barton Hollow Residence",
    "Pecan Switch Barn",
    "Cedar Kettle Works",
    "Lake Glass Pavilion",
    "Hutto Grain Office",
    "Prairie Switch Backup",
    "Lantern Orchard House",
    "Cinder Mesa Residence",
    "Driftwood Pump House",
    "Quail Run Backup",
    "Silver Thistle Market",
    "Redbud Workshop",
    "Cottonwood Depot Office",
    "Firefly Lane Cottage",
    "Aster Court Storage",
    "Mesquite Switch House",
    "Briar Pump Station",
    "Gable Ridge Hall",
    "Northwind Pavilion",
    "Lumen Court House",
    "Hollow Oak Bakery",
    "Sage Flat Residence",
    "Kite String Warehouse",
    "Marigold Yard Office",
    "Tin Roof Creamery",
    "Owl Creek Cabin",
    "Fern Basin Clinic",
    "Clover Stack Storage",
    "High Lamp House",
    "Dry Creek Pavilion",
    "Winter Grass Barn",
    "Little Anvil Shop",
    "Sunken Fence Office",
    "Bright Lot Storage",
    "Yellow Porch House",
    "Glasshill Backup",
    "Rope Bridge Lodge",
    "Kindling Yard",
    "Soft Rain House",
    "Cedar Dial Office",
    "Low Star Barn",
    "Paper Kite Residence",
    "Vine Switch Storage",
    "Quiet Motor Court",
    "Dust Lantern Hall",
    "Open Gate Pavilion",
]

# customer_id -> (city, lat, lon). Remaining sites are jittered around a city anchor.
SITE_FIX = {
    "C001": ("Round Rock", 30.50980, -97.72460),
    "C002": ("Cedar Park", 30.47840, -97.84890),
    "C003": ("Georgetown", 30.63620, -97.64180),
    "C004": ("Leander", 30.55870, -97.88140),
    "C005": ("Austin", 30.31280, -97.73950),
    "C006": ("Manor", 30.34890, -97.56140),
    "C007": ("Cedar Park", 30.50260, -97.80840),
    "C008": ("Lakeway", 30.38420, -97.96110),
    "C009": ("Hutto", 30.52240, -97.54680),
    "C010": ("Pflugerville", 30.45420, -97.62840),
    "C020": ("Austin", 30.27460, -97.79280),
    "C025": ("Austin", 30.26740, -97.81220),
    "C030": ("Cedar Park", 30.48650, -97.81940),
    "C031": ("Round Rock", 30.52640, -97.69210),
    "C032": ("Georgetown", 30.65540, -97.67120),
    "C033": ("Leander", 30.57410, -97.86650),
}

FILLER_KITS = {
    "Installation": [("P012", 2), ("P023", 1), ("P015", 4), ("P009", 1)],
    "Battery Replacement": [("P002", 1), ("P003", 1), ("P018", 1)],
    "Battery Repair": [("P002", 1), ("P004", 1)],
    "Inverter Repair": [("P008", 1), ("P007", 1)],
    "Inspection": [("P026", 1)],
    "Preventive Maintenance": [("P004", 1), ("P019", 2)],
    "Emergency Service": [("P018", 1), ("P012", 2), ("P020", 1)],
    "Troubleshooting": [("P028", 1), ("P014", 1)],
}

# Traveling consumables staged on working vans. Critical fuses and inverters
# are added only where the demo story needs them.
CARRY = [("P012", 4), ("P015", 6), ("P009", 2), ("P019", 4), ("P004", 2)]
FULL_KIT_VANS = {"V009", "V016"}
FULL_KIT = [("P002", 1), ("P018", 2), ("P020", 1), ("P007", 1), ("P016", 2)]
VAN_EXTRAS = {
    ("V001", "P020"): 1,
    ("V001", "P016"): 1,
    ("V004", "P018"): 2,
    ("V004", "P020"): 1,
}
# Applied last so a kit cannot put the demo short-part back on the van.
VAN_DENY = {("V001", "P018"), ("V010", "P006")}

SPECIAL_PARTS = {"P001", "P006"}
TOOLS = {"P029", "P030", "P031", "P032"}

# Final on-hand overrides. None means the warehouse does not stock the part
# (no inventory row and no bin). 0 means the bin exists and is empty.
OH_OVERRIDE = {
    ("W001", "P015"): 180,
    ("W001", "P005"): 90,
    ("W001", "P018"): 12,
    ("W002", "P018"): 3,
    ("W003", "P018"): 2,
    ("W003", "P003"): 0,
    ("W002", "P030"): 0,
    ("W002", "P021"): 2,
    ("W003", "P013"): None,
}
for _tool in TOOLS:
    OH_OVERRIDE[("W003", _tool)] = None

PAST_SLOTS = [("08:00", "10:00"), ("10:15", "12:15"), ("13:00", "15:00")]

ADJ_NOTE = (
    "Cycle count at Bluebonnet Service Warehouse W003 aisle C shelf 02 bin 07 "
    "found 3 LumenPack modules (P001); the book balance was 4. The missing module "
    "was not on any van and was not in the bin. On-hand corrected down by 1 pending review."
)


def r5(value: float) -> float:
    return round(value, 5)


def parse_ts(value: str) -> datetime:
    return datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")


def plus(ts: str, minutes: int) -> str:
    return (parse_ts(ts) + timedelta(minutes=minutes)).strftime("%Y-%m-%dT%H:%M:%S") + "-05:00"


def at(date: str, hm: str) -> str:
    return f"{date}T{hm}:00-05:00"


def prev_day(date: str, hm: str = "16:00") -> str:
    day = datetime.strptime(date, "%Y-%m-%d") - timedelta(days=1)
    return day.strftime("%Y-%m-%d") + f"T{hm}:00-05:00"


def minutes(hm: str) -> int:
    hour, minute = hm.split(":")
    return int(hour) * 60 + int(minute)


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    hav = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon / 2) ** 2
    return 2 * radius * asin(sqrt(hav))


def cid(number: int) -> str:
    return f"C{number:03d}"


def home_for(van_id: str) -> str:
    if van_id == "V018":
        return "W001"
    number = int(van_id[1:])
    if number <= 7:
        return "W001"
    if number <= 14:
        return "W002"
    return "W003"


class Ledger:
    """Physical stock and reservations. Transactions are applied in time order."""

    def __init__(self) -> None:
        self.wh: dict[tuple[str, str], int] = {}
        self.res: dict[tuple[str, str], int] = {}
        self.van: dict[tuple[str, str], int] = {}
        self.seen: set[tuple[str, str]] = set()
        self.txs: list[dict] = []
        self._seq = 0

    def add(self, **kwargs) -> None:
        self._seq += 1
        kwargs["_seq"] = self._seq
        self.txs.append(kwargs)

    def _wh(self, wh: str, part: str) -> int:
        return self.wh.get((wh, part), 0)

    def _add_wh(self, wh: str, part: str, qty: int) -> None:
        self.wh[(wh, part)] = self._wh(wh, part) + qty
        self.seen.add((wh, part))

    def _dec_wh(self, wh: str, part: str, qty: int, tx: dict) -> None:
        have = self._wh(wh, part)
        if have < qty:
            raise SystemExit(
                f"Warehouse {wh} {part} would go negative "
                f"(have {have}, remove {qty}) at {tx['timestamp']} {tx['transaction_type']}: {tx['notes']}"
            )
        self.wh[(wh, part)] = have - qty
        self.seen.add((wh, part))

    def _dec_van(self, van: str, part: str, qty: int, tx: dict) -> None:
        have = self.van.get((van, part), 0)
        if have < qty:
            raise SystemExit(
                f"Van {van} {part} would go negative "
                f"(have {have}, remove {qty}) at {tx['timestamp']} {tx['transaction_type']}: {tx['notes']}"
            )
        self.van[(van, part)] = have - qty

    def receive(self, part, wh, qty, ts, notes) -> None:
        self.add(
            timestamp=ts,
            part_id=part,
            quantity=qty,
            transaction_type="Received",
            from_location_type="Supplier",
            from_location_id="SUP-NORTHWIND",
            to_location_type="Warehouse",
            to_location_id=wh,
            technician_id="",
            van_id="",
            job_id="",
            notes=notes,
        )

    def transfer(self, part, src, dst, qty, ts, notes) -> None:
        self.add(
            timestamp=ts,
            part_id=part,
            quantity=qty,
            transaction_type="Transfer",
            from_location_type="Warehouse",
            from_location_id=src,
            to_location_type="Warehouse",
            to_location_id=dst,
            technician_id="",
            van_id="",
            job_id="",
            notes=notes,
        )

    def issue(self, part, wh, van, tech, qty, ts, notes, job="") -> None:
        self.add(
            timestamp=ts,
            part_id=part,
            quantity=qty,
            transaction_type="Issued",
            from_location_type="Warehouse",
            from_location_id=wh,
            to_location_type="Van",
            to_location_id=van,
            technician_id=tech,
            van_id=van,
            job_id=job,
            notes=notes,
        )

    def install(self, part, van, job, tech, qty, ts, notes) -> None:
        self.add(
            timestamp=ts,
            part_id=part,
            quantity=qty,
            transaction_type="Installed",
            from_location_type="Van",
            from_location_id=van,
            to_location_type="Job",
            to_location_id=job,
            technician_id=tech,
            van_id=van,
            job_id=job,
            notes=notes,
        )

    def reserve_wh(self, part, wh, job, qty, ts, notes) -> None:
        self.add(
            timestamp=ts,
            part_id=part,
            quantity=qty,
            transaction_type="Reserved",
            from_location_type="Warehouse",
            from_location_id=wh,
            to_location_type="Job",
            to_location_id=job,
            technician_id="",
            van_id="",
            job_id=job,
            notes=notes,
        )

    def reserve_van(self, part, van, job, tech, qty, ts, notes) -> None:
        self.add(
            timestamp=ts,
            part_id=part,
            quantity=qty,
            transaction_type="Reserved",
            from_location_type="Van",
            from_location_id=van,
            to_location_type="Job",
            to_location_id=job,
            technician_id=tech,
            van_id=van,
            job_id=job,
            notes=notes,
        )

    def returned(self, part, van, wh, tech, qty, ts, notes) -> None:
        self.add(
            timestamp=ts,
            part_id=part,
            quantity=qty,
            transaction_type="Returned",
            from_location_type="Van",
            from_location_id=van,
            to_location_type="Warehouse",
            to_location_id=wh,
            technician_id=tech,
            van_id=van,
            job_id="",
            notes=notes,
        )

    def scrap(self, part, wh, qty, ts, notes) -> None:
        self.add(
            timestamp=ts,
            part_id=part,
            quantity=qty,
            transaction_type="Scrapped",
            from_location_type="Warehouse",
            from_location_id=wh,
            to_location_type="Supplier",
            to_location_id="SCRAP",
            technician_id="",
            van_id="",
            job_id="",
            notes=notes,
        )

    def adjust(self, part, wh, qty, ts, notes) -> None:
        self.add(
            timestamp=ts,
            part_id=part,
            quantity=qty,
            transaction_type="Adjustment",
            from_location_type="Warehouse",
            from_location_id=wh,
            to_location_type="Warehouse",
            to_location_id=wh,
            technician_id="",
            van_id="",
            job_id="",
            notes=notes,
        )

    def apply_all(self) -> None:
        self.txs.sort(key=lambda row: (row["timestamp"], row["_seq"]))
        for tx in self.txs:
            self._apply(tx)

    def _apply(self, tx: dict) -> None:
        part = tx["part_id"]
        qty = tx["quantity"]
        kind = tx["transaction_type"]
        if kind == "Received":
            if qty <= 0:
                raise SystemExit(f"Received qty must be positive: {tx}")
            self._add_wh(tx["to_location_id"], part, qty)
        elif kind == "Transfer":
            self._dec_wh(tx["from_location_id"], part, qty, tx)
            self._add_wh(tx["to_location_id"], part, qty)
        elif kind == "Issued":
            self._dec_wh(tx["from_location_id"], part, qty, tx)
            key = (tx["van_id"], part)
            self.van[key] = self.van.get(key, 0) + qty
        elif kind == "Installed":
            self._dec_van(tx["van_id"], part, qty, tx)
        elif kind == "Reserved":
            if tx["from_location_type"] == "Warehouse":
                wh = tx["from_location_id"]
                held = self.res.get((wh, part), 0) + qty
                if held > self._wh(wh, part):
                    raise SystemExit(
                        f"Reservation exceeds on-hand for {wh} {part} "
                        f"(reserved {held}, on hand {self._wh(wh, part)}) at {tx['timestamp']}"
                    )
                self.res[(wh, part)] = held
                self.seen.add((wh, part))
            # A van reservation does not remove the unit from van_inventory.
        elif kind == "Returned":
            self._dec_van(tx["van_id"], part, qty, tx)
            self._add_wh(tx["to_location_id"], part, qty)
        elif kind == "Scrapped":
            self._dec_wh(tx["from_location_id"], part, qty, tx)
        elif kind == "Adjustment":
            wh = tx["from_location_id"]
            updated = self._wh(wh, part) + qty
            if updated < 0:
                raise SystemExit(f"Adjustment drove {wh} {part} negative at {tx['timestamp']}")
            self.wh[(wh, part)] = updated
            self.seen.add((wh, part))
        else:
            raise SystemExit(f"Unknown transaction type {kind}")


def build_parts() -> dict[str, dict]:
    rows = [
        ("P001", "LF-BATT-135", "LumenPack 13.5 Battery Module", "Battery", "Field-replaceable 13.5 kWh LumenPack battery module.", "each", 4280, "Critical", 2, 12),
        ("P002", "LF-BMS-014", "LumenPack BMS Control Board", "Battery", "Battery management board for a LumenPack module.", "each", 640, "Critical", 3, 8),
        ("P003", "LF-BUS-220", "Battery Interconnect Busbar Kit", "Battery", "Busbar kit that ties LumenPack modules together.", "kit", 185, "High", 4, 10),
        ("P004", "LF-TIP-090", "Thermal Interface Pad Set", "Battery", "Replacement thermal pads for a battery enclosure.", "set", 42, "Medium", 6, 20),
        ("P005", "LF-GSK-011", "Battery Enclosure Gasket", "Battery", "Weather gasket for a LumenPack enclosure door.", "each", 18, "Low", 10, 30),
        ("P006", "LF-INV-760", "HaloWave 7.6 Hybrid Inverter", "Inverter", "7.6 kW hybrid inverter used on whole-home backups.", "each", 2150, "Critical", 2, 6),
        ("P007", "LF-DCS-060", "Inverter DC Disconnect Switch", "Inverter", "DC disconnect mounted beside the hybrid inverter.", "each", 128, "High", 3, 8),
        ("P008", "LF-FAN-033", "Inverter Cooling Fan Assembly", "Inverter", "Replacement cooling fan for a HaloWave inverter.", "each", 76, "Medium", 4, 10),
        ("P009", "LF-BRK-060", "60A AC Breaker", "Electrical", "60 amp AC breaker for the backup service panel.", "each", 54, "High", 6, 16),
        ("P010", "LF-GND-006", "Grounding Electrode Conductor Kit", "Electrical", "Grounding conductor kit for a residential backup.", "kit", 39, "Medium", 5, 12),
        ("P011", "LF-LUG-100", "Service Entrance Lug Kit", "Electrical", "Lug kit for the backup service entrance.", "kit", 27, "Medium", 5, 12),
        ("P012", "LF-CBL-4AWG", "4 AWG Battery Cable 3m", "Cable", "Three-meter 4 AWG battery cable pair.", "each", 48, "High", 8, 24),
        ("P013", "LF-CBL-PV10", "PV String Cable 10m", "Cable", "Ten-meter PV string cable.", "each", 36, "Medium", 6, 18),
        ("P014", "LF-CBL-CAT", "Communication Cable 15m", "Cable", "Fifteen-meter communications cable for the gateway.", "each", 22, "Low", 6, 16),
        ("P015", "LF-MC4-PAIR", "MC4 Connector Pair", "Connector", "Paired MC4 connectors for PV string terminations.", "pair", 8, "Medium", 20, 40),
        ("P016", "LF-AND-175", "Anderson SB175 Connector", "Connector", "High-current connector used on battery leads.", "each", 34, "High", 6, 16),
        ("P017", "LF-LUG-BATT", "Battery Terminal Lug Set", "Connector", "Lug set for LumenPack battery terminals.", "set", 16, "Medium", 8, 20),
        ("P018", "LF-FUSE-200T", "200A Class T Fuse", "Fuse", "200 amp Class T fuse for the battery DC bus.", "each", 46, "Critical", 6, 18),
        ("P019", "LF-FUSE-30PV", "30A PV String Fuse", "Fuse", "30 amp fuse for a PV string combiner.", "each", 6, "Medium", 15, 40),
        ("P020", "LF-RSD-001", "Rapid Shutdown Device", "Circuit Protection", "Module-level rapid shutdown device.", "each", 210, "Critical", 3, 8),
        ("P021", "LF-SPD-T2", "Surge Protection Device Type 2", "Circuit Protection", "Type 2 surge protector for the backup panel.", "each", 95, "High", 3, 8),
        ("P022", "LF-AFD-010", "DC Arc-Fault Detector", "Circuit Protection", "DC arc-fault detector for the PV input.", "each", 160, "High", 2, 6),
        ("P023", "LF-RAIL-WM", "Wall Mount Rail Kit", "Mounting Hardware", "Wall rail kit for a LumenPack enclosure.", "kit", 120, "Medium", 4, 10),
        ("P024", "LF-ANC-CON", "Concrete Anchor Bolt Pack", "Mounting Hardware", "Anchor bolts for a pad-mounted enclosure.", "pack", 14, "Low", 8, 20),
        ("P025", "LF-SEIS-04", "Seismic Restraint Bracket", "Mounting Hardware", "Restraint bracket for a wall-mounted battery.", "each", 33, "Medium", 4, 12),
        ("P026", "LF-CT-200", "CT Clamp 200A", "Sensors", "200 amp current transformer clamp.", "each", 68, "Medium", 4, 10),
        ("P027", "LF-TEMP-4", "Temperature Probe Pack", "Sensors", "Pack of enclosure temperature probes.", "pack", 29, "Low", 4, 10),
        ("P028", "LF-GW-COM", "Gateway Communications Module", "Sensors", "Site gateway module for monitoring and dispatch.", "each", 240, "High", 2, 6),
        ("P029", "LF-TOOL-TQ", "Insulated Torque Wrench Set", "Tools", "Insulated torque set kept in depot tool cribs.", "set", 180, "Medium", 1, 3),
        ("P030", "LF-TOOL-IR", "Insulation Resistance Tester", "Tools", "Insulation resistance tester shared across crews.", "each", 420, "High", 1, 2),
        ("P031", "LF-TOOL-DGL", "Commissioning Interface Dongle", "Tools", "Dongle used to commission a LumenPack site.", "each", 95, "Medium", 2, 4),
        ("P032", "LF-PPE-AFS", "Arc-Flash Face Shield", "Tools", "Arc-flash face shield issued from the depot.", "each", 62, "Low", 2, 6),
    ]
    parts = {}
    for item in rows:
        parts[item[0]] = {
            "part_id": item[0],
            "part_number": item[1],
            "part_name": item[2],
            "category": item[3],
            "description": item[4],
            "unit": item[5],
            "unit_cost": f"{item[6]:.2f}",
            "criticality": item[7],
            "reorder_point": item[8],
            "preferred_stock_level": item[9],
        }
    return parts


def build_techs() -> dict[str, dict]:
    # id, name, status, base city, skills, certs, shift start, shift end, van, current job
    rows = [
        ("T001", "Rowan Pell", "On Job", "Round Rock", "Battery Installation; Battery Repair; Diagnostics", "Battery Installation Level 2; Battery Repair Level 2; Diagnostics Level 1", "07:00", "18:00", "V001", "J001"),
        ("T002", "Sable Quill", "On Job", "Cedar Park", "Battery Repair; Diagnostics; Electrical", "Battery Repair Master; Diagnostics Level 2; Electrical Level 1", "07:00", "18:00", "V002", "J002"),
        ("T003", "Idris Fen", "En Route", "Georgetown", "Inverter Repair; Electrical; Diagnostics", "Inverter Repair Level 2; Electrical Level 2", "08:00", "19:00", "V003", "J003"),
        ("T004", "Maren Holt", "Available", "Pflugerville", "Battery Installation; Electrical; Diagnostics", "Battery Installation Master; Electrical Level 2; Diagnostics Level 2", "08:00", "18:00", "V004", ""),
        ("T005", "Cassio Venn", "Break", "Austin", "Electrical; Diagnostics; Battery Installation", "Electrical Level 2; Battery Installation Level 1; Diagnostics Level 1", "07:00", "18:00", "V005", ""),
        ("T006", "Lumen Drake", "On Job", "Leander", "Diagnostics; Electrical; Inverter Repair", "Diagnostics Level 2; Inverter Repair Level 1; Electrical Level 1", "07:00", "18:00", "V006", "J004"),
        ("T007", "Nova Brigg", "On Job", "Austin", "Electrical; Battery Installation; Battery Repair", "Electrical Master; Battery Installation Level 2", "07:00", "18:00", "V007", "J005"),
        ("T008", "Harlow Finch", "En Route", "Manor", "Inverter Repair; Diagnostics; Electrical", "Inverter Repair Level 2; Diagnostics Level 1", "07:00", "18:00", "V008", "J006"),
        ("T009", "Petra Sol", "Available", "Round Rock", "Battery Repair; Diagnostics", "Battery Repair Level 2; Diagnostics Level 2", "08:00", "18:00", "V009", ""),
        ("T010", "Quinn Ashby", "On Job", "Cedar Park", "Inverter Repair; Electrical; Diagnostics", "Inverter Repair Level 2; Electrical Level 1; Diagnostics Level 1", "07:00", "18:00", "V010", "J007"),
        ("T011", "Ellis Marrow", "Available", "Georgetown", "Battery Installation; Electrical", "Battery Installation Level 2; Electrical Level 1", "08:00", "18:00", "V011", ""),
        ("T012", "Wynn Calder", "Break", "Austin", "Diagnostics; Battery Repair", "Diagnostics Level 1; Battery Repair Level 1", "07:00", "18:00", "V012", ""),
        ("T013", "Juniper Vale", "On Job", "Lakeway", "Inverter Repair; Electrical; Diagnostics", "Inverter Repair Master; Electrical Level 2", "07:00", "18:00", "V013", "J008"),
        ("T014", "Theo Bramble", "En Route", "Hutto", "Electrical; Diagnostics; Battery Installation", "Electrical Level 2; Battery Installation Level 1", "07:00", "18:00", "V014", "J009"),
        ("T015", "Nia Plover", "Off Duty", "Round Rock", "Battery Installation; Diagnostics", "Battery Installation Level 1; Diagnostics Level 1", "06:00", "14:00", "V015", ""),
        ("T016", "Remy Oak", "Available", "Austin", "Battery Installation; Battery Repair; Inverter Repair; Electrical; Diagnostics", "Battery Installation Level 2; Inverter Repair Level 2; Electrical Level 2; Diagnostics Level 2", "08:00", "18:00", "V016", ""),
        ("T017", "Soren Pike", "Off Duty", "Leander", "Electrical; Diagnostics", "Electrical Level 1; Diagnostics Level 1", "06:00", "14:00", "V017", ""),
        ("T018", "Ada Moss", "Available", "Pflugerville", "Diagnostics; Electrical", "Diagnostics Level 1; Electrical Level 1", "08:00", "18:00", "", ""),
        ("T019", "Kit Lantern", "Off Duty", "Cedar Park", "Battery Repair", "Battery Repair Level 1", "06:00", "14:00", "", ""),
        ("T020", "Vera Dunn", "Off Duty", "Austin", "Inverter Repair; Diagnostics", "Inverter Repair Level 1", "06:00", "14:00", "", ""),
        ("T021", "Hollis Reed", "Break", "Georgetown", "Electrical; Battery Installation", "Electrical Level 2; Battery Installation Level 1", "08:00", "18:00", "V019", ""),
        ("T022", "Bram Yarrow", "Off Duty", "Buda", "Diagnostics", "Diagnostics Level 1", "06:00", "14:00", "", ""),
        ("T023", "Leif Morrow", "Off Duty", "Manor", "Battery Installation; Electrical", "Battery Installation Level 1", "06:00", "14:00", "", ""),
        ("T024", "Calla Voss", "Off Duty", "Lakeway", "Inverter Repair", "Inverter Repair Level 1", "06:00", "14:00", "", ""),
        ("T025", "Indigo Shaw", "Off Duty", "Hutto", "Electrical; Diagnostics", "Electrical Level 1; Diagnostics Level 2", "06:00", "14:00", "", ""),
        ("T026", "Pax Holm", "Available", "Buda", "Battery Repair; Diagnostics", "Battery Repair Level 2; Diagnostics Level 1", "08:00", "18:00", "", ""),
        ("T027", "Rhett Juno", "Available", "Lakeway", "Electrical; Inverter Repair", "Electrical Level 2; Inverter Repair Level 1", "08:00", "18:00", "", ""),
        ("T028", "Mira Toll", "Off Duty", "Round Rock", "Battery Installation", "Battery Installation Level 1", "06:00", "14:00", "", ""),
        ("T029", "Jules North", "Off Duty", "Cedar Park", "Diagnostics; Battery Repair", "Diagnostics Level 1", "06:00", "14:00", "", ""),
        ("T030", "Eden Crowe", "Off Duty", "Georgetown", "Electrical", "Electrical Level 1", "06:00", "14:00", "", ""),
    ]
    techs = {}
    for item in rows:
        techs[item[0]] = {
            "technician_id": item[0],
            "name": item[1],
            "status": item[2],
            "base_city": item[3],
            "skills": item[4],
            "certifications": item[5],
            "shift_start": item[6],
            "shift_end": item[7],
            "assigned_van_id": item[8],
            "current_job_id": item[9],
            "current_latitude": 0.0,
            "current_longitude": 0.0,
            "current_city": item[3],
            "last_location_timestamp": NOW,
        }
    return techs


def build_vans(techs: dict[str, dict]) -> dict[str, dict]:
    tech_for_van = {}
    for tech in techs.values():
        if tech["assigned_van_id"]:
            tech_for_van[tech["assigned_van_id"]] = tech["technician_id"]
    vans = {}
    for number in range(1, 21):
        van_id = f"V{number:03d}"
        if van_id == SHOP_VAN:
            maint_status = "In Shop"
            next_date = "2026-10-01"
        elif van_id == DUE_VAN:
            maint_status = "Due Soon"
            next_date = "2026-10-08"
        elif van_id == "V007":
            maint_status = "Due Soon"
            next_date = "2026-10-12"
        else:
            maint_status = "OK"
            next_date = (datetime(2026, 11, 18) + timedelta(days=number * 3)).strftime("%Y-%m-%d")
        vans[van_id] = {
            "van_id": van_id,
            "vehicle_number": f"LF-{4800 + number}",
            "status": "Maintenance" if van_id == SHOP_VAN else "Parked",
            "assigned_technician_id": tech_for_van.get(van_id, ""),
            "current_latitude": 0.0,
            "current_longitude": 0.0,
            "current_city": "",
            "last_check_in": "",
            "mileage": 0,
            "fuel_or_charge_percent": 28 + (number * 9) % 67,
            "maintenance_status": maint_status,
            "next_maintenance_date": next_date,
            "home_warehouse_id": home_for(van_id),
        }
    return vans


def build_warehouses() -> dict[str, dict]:
    rows = [
        ("W001", "Mesa Volt Depot", "Austin", 30.30480, -97.72160, "Daily 06:00-18:00", "Orla Mint", "Open"),
        ("W002", "Brushy Creek Parts Hub", "Round Rock", 30.53440, -97.68920, "Daily 06:00-18:00", "Galen Moss", "Open"),
        ("W003", "Bluebonnet Service Warehouse", "Georgetown", 30.64150, -97.67040, "Daily 06:00-18:00", "Ida Barrow", "Open"),
    ]
    return {
        row[0]: {
            "warehouse_id": row[0],
            "warehouse_name": row[1],
            "city": row[2],
            "latitude": row[3],
            "longitude": row[4],
            "operating_hours": row[5],
            "manager_name": row[6],
            "status": row[7],
        }
        for row in rows
    }


def build_sites() -> dict[str, dict]:
    system_types = ["Whole-Home Battery", "Commercial Storage", "Backup Power", "Solar-Plus-Storage"]
    sites = {}
    for index, name in enumerate(SITE_NAMES, start=1):
        site_id = f"C{index:03d}"
        if site_id in SITE_FIX:
            city, lat, lon = SITE_FIX[site_id]
        else:
            city = CITY_CYCLE[(index - 1) % len(CITY_CYCLE)]
            base_lat, base_lon = CITIES[city]
            lat = r5(base_lat + (((index * 17) % 41) - 20) * 0.0012)
            lon = r5(base_lon + (((index * 29) % 41) - 20) * 0.0012)
        commercial = system_types[index % 4] == "Commercial Storage"
        if commercial:
            kwh = 100 + (index % 4) * 100
            kw = 50 + (index % 3) * 50
        else:
            kwh = 13.5 * (1 + (index % 3))
            kw = 7.6 if index % 2 == 0 else 11.4
        if site_id == "C049":
            status = "Offline"
        elif site_id == "C050":
            status = "Commissioning"
        else:
            status = "Active"
        installed = datetime(2022, 6, 1) + timedelta(days=(index * 23) % 1400)
        sites[site_id] = {
            "customer_id": site_id,
            "site_name": name,
            "city": city,
            "latitude": r5(lat),
            "longitude": r5(lon),
            "system_type": system_types[index % 4],
            "battery_capacity_kwh": kwh,
            "inverter_capacity_kw": kw,
            "installation_date": installed.strftime("%Y-%m-%d"),
            "site_status": status,
        }
    return sites


def base_point(tech: dict) -> tuple[float, float, str]:
    lat, lon = CITIES[tech["base_city"]]
    number = int(tech["technician_id"][1:])
    return (
        r5(lat + ((number % 7) - 3) * 0.0035),
        r5(lon + ((number % 5) - 2) * 0.0035),
        tech["base_city"],
    )


def place_people(techs, vans, jobs, sites, warehouses) -> None:
    for tech in techs.values():
        status = tech["status"]
        job_id = tech["current_job_id"]
        if status in ("On Job", "En Route"):
            site = sites[jobs[job_id]["customer_id"]]
            if status == "On Job":
                lat, lon, city = site["latitude"], site["longitude"], site["city"]
            else:
                lat = r5(site["latitude"] - 0.015)
                lon = r5(site["longitude"] + 0.010)
                city = site["city"]
        elif tech["technician_id"] == HERO_TECH:
            lat, lon, city = 30.44910, -97.63520, "Pflugerville"
        elif tech["technician_id"] == "T018":
            lat, lon, city = 30.46940, -97.65180, "Pflugerville"
        else:
            lat, lon, city = base_point(tech)
        tech["current_latitude"] = lat
        tech["current_longitude"] = lon
        tech["current_city"] = city
        if status == "Off Duty":
            tech["last_location_timestamp"] = at(TODAY, tech["shift_end"])
        elif status == "Break":
            tech["last_location_timestamp"] = at(TODAY, "15:40")
        else:
            tech["last_location_timestamp"] = at(TODAY, "15:58")

    status_for_van = {
        "On Job": "On Job",
        "En Route": "En Route",
        "Available": "Available",
        "Break": "Parked",
        "Off Duty": "Parked",
    }
    for van in vans.values():
        tech_id = van["assigned_technician_id"]
        if tech_id:
            tech = techs[tech_id]
            van["current_latitude"] = tech["current_latitude"]
            van["current_longitude"] = tech["current_longitude"]
            van["current_city"] = tech["current_city"]
            van["status"] = status_for_van[tech["status"]]
        elif van["van_id"] == SHOP_VAN:
            wh = warehouses["W001"]
            van["current_latitude"] = wh["latitude"]
            van["current_longitude"] = wh["longitude"]
            van["current_city"] = wh["city"]
            van["status"] = "Maintenance"
        elif van["van_id"] == SPARE_VAN:
            wh = warehouses["W003"]
            van["current_latitude"] = wh["latitude"]
            van["current_longitude"] = wh["longitude"]
            van["current_city"] = wh["city"]
            van["status"] = "Available"


class World:
    def __init__(self) -> None:
        self.parts = build_parts()
        self.techs = build_techs()
        self.vans = build_vans(self.techs)
        self.warehouses = build_warehouses()
        self.sites = build_sites()
        self.jobs: dict[str, dict] = {}
        self.job_parts: list[dict] = []
        self.job_events: list[dict] = []
        self.locations: list[dict] = []
        self.vehicle_events: list[dict] = []
        self.schedules: list[dict] = []
        self.alerts: list[dict] = []
        self.van_rows: list[dict] = []
        self.wh_rows: list[dict] = []
        self.wh_locs: list[dict] = []
        self.ledger = Ledger()
        self.busy: dict[tuple[str, str], list[tuple[int, int]]] = defaultdict(list)
        self._part_seq = 0

    def reserve_slot(self, tech: str, date: str, start_hm: str, end_hm: str) -> None:
        if not tech:
            return
        start, end = minutes(start_hm), minutes(end_hm)
        if start >= end:
            raise SystemExit(f"Bad window {tech} {date} {start_hm}-{end_hm}")
        for other_start, other_end in self.busy[(tech, date)]:
            if start < other_end and other_start < end:
                raise SystemExit(
                    f"Schedule overlap for {tech} on {date}: {start_hm}-{end_hm} "
                    f"hits {other_start}-{other_end}"
                )
        self.busy[(tech, date)].append((start, end))

    def slot_free(self, tech: str, date: str, start_hm: str, end_hm: str) -> bool:
        start, end = minutes(start_hm), minutes(end_hm)
        return all(
            not (start < other_end and other_start < end)
            for other_start, other_end in self.busy[(tech, date)]
        )

    def add_job(
        self,
        job_id: str,
        customer_id: str,
        job_type: str,
        priority: str,
        status: str,
        scheduled_date: str,
        start_hm: str,
        end_hm: str,
        technician_id: str,
        van_id: str,
        issue: str,
        parts: list[tuple],
        created_at: str | None = None,
        events: list[tuple] | None = None,
        estimated: int | None = None,
    ) -> None:
        if job_id in self.jobs:
            raise SystemExit(f"Duplicate job {job_id}")
        start_iso = at(scheduled_date, start_hm)
        end_iso = at(scheduled_date, end_hm)
        if events is None:
            created_at = created_at or prev_day(scheduled_date)
            event_rows = self._autobuild_events(
                status, created_at, start_iso, end_iso, technician_id, issue
            )
        else:
            created_at = events[0][1]
            event_rows = events
        job = {
            "job_id": job_id,
            "customer_id": customer_id,
            "job_type": job_type,
            "priority": priority,
            "status": status,
            "scheduled_date": scheduled_date,
            "scheduled_start": start_iso,
            "scheduled_end": end_iso,
            "technician_id": technician_id,
            "van_id": van_id,
            "created_at": created_at,
            "estimated_duration_minutes": str(estimated if estimated is not None else minutes(end_hm) - minutes(start_hm)),
            "actual_duration_minutes": "",
            "issue_description": issue,
        }
        self.jobs[job_id] = job
        if technician_id and status != "Cancelled":
            self.reserve_slot(technician_id, scheduled_date, start_hm, end_hm)
        for event in event_rows:
            self.job_events.append(
                {
                    "job_id": job_id,
                    "timestamp": event[1],
                    "event_type": event[0],
                    "technician_id": event[2],
                    "notes": event[3],
                }
            )
        for part_id, required, allocated, installed, part_status in parts:
            self._part_seq += 1
            self.job_parts.append(
                {
                    "job_part_id": f"JP{self._part_seq:05d}",
                    "job_id": job_id,
                    "part_id": part_id,
                    "required_quantity": required,
                    "allocated_quantity": allocated,
                    "installed_quantity": installed,
                    "status": part_status,
                }
            )

    def _autobuild_events(self, status, created, start_iso, end_iso, tech, issue):
        site_note = issue.split(".")[0]
        if status == "Scheduled":
            return [("Created", created, "", site_note)]
        if status == "Cancelled":
            return [
                ("Created", created, "", site_note),
                ("Escalated", plus(created, 90), "", "Cancelled before dispatch: customer postponed the visit."),
            ]
        assigned_at = plus(created, 40)
        if status == "Assigned":
            return [
                ("Created", created, "", site_note),
                ("Assigned", assigned_at, tech, f"Assigned to {tech}."),
            ]
        if status != "Completed":
            raise SystemExit(f"Autobuild does not handle status {status}")
        steps = [
            ("Created", created, "", site_note),
            ("Assigned", assigned_at, tech, f"Assigned to {tech}."),
            ("Technician Dispatched", plus(start_iso, -20), tech, "Technician dispatched."),
            ("En Route", plus(start_iso, -5), tech, "En route to the site."),
            ("Arrived Onsite", plus(start_iso, 20), tech, "Arrived onsite."),
            ("Diagnosis", plus(start_iso, 40), tech, "Diagnosis complete."),
            ("Repair Started", plus(start_iso, 55), tech, "Work started with the parts on the van."),
            ("Repair Completed", plus(end_iso, -25), tech, "Repair completed."),
            ("Customer Signoff", plus(end_iso, -12), tech, "Customer signed off."),
            ("Job Completed", plus(end_iso, -5), tech, "Job completed."),
        ]
        previous = ""
        for _kind, ts, _tech, _note in steps:
            if previous and ts <= previous:
                raise SystemExit(f"Autobuild event order failed around {ts}")
            previous = ts
        return steps

    def add_explicit_jobs(self) -> None:
        j001_wait = (
            "Delayed: P018 200A Class T Fuse qty 2 is not on van V001. "
            "Mesa Volt Depot W001 has the fuse in stock and can supply this job."
        )
        j007_wait = (
            "Job delayed because P006 HaloWave 7.6 Hybrid Inverter is not on van V010 "
            "and Mesa Volt Depot (W001) is out of stock. Brushy Creek Parts Hub (W002) "
            "has units available; transfer requested."
        )
        specs = [
            dict(
                job_id="J001", customer_id="C001", job_type="Battery Repair", priority="High",
                status="Waiting for Parts", scheduled_date=TODAY, start_hm="12:00", end_hm="15:00",
                technician_id="T001", van_id="V001",
                issue="LumenPack module showing an isolation fault. The Class T fuse is open and is not on the van.",
                parts=[("P001", 1, 1, 0, "Allocated"), ("P012", 2, 2, 0, "Allocated"), ("P018", 2, 0, 0, "Missing")],
                events=[
                    ("Created", "2026-09-26T16:05:00-05:00", "", "Battery repair opened for an isolation fault at Copper Lantern Home."),
                    ("Assigned", "2026-09-26T16:40:00-05:00", "T001", "Assigned to T001 Rowan Pell."),
                    ("Technician Dispatched", "2026-09-27T11:20:00-05:00", "T001", "Dispatched from the Round Rock area."),
                    ("En Route", "2026-09-27T11:35:00-05:00", "T001", "En route to Copper Lantern Home."),
                    ("Arrived Onsite", "2026-09-27T12:10:00-05:00", "T001", "Arrived onsite."),
                    ("Diagnosis", "2026-09-27T12:40:00-05:00", "T001", "Isolation fault confirmed. The Class T fuse is open."),
                    ("Part Required", "2026-09-27T12:55:00-05:00", "T001", "Need P018 qty 2. Van V001 does not have a Class T fuse."),
                    ("Waiting for Parts", "2026-09-27T13:05:00-05:00", "T001", j001_wait),
                ],
            ),
            dict(
                job_id="J002", customer_id="C002", job_type="Battery Repair", priority="High",
                status="In Progress", scheduled_date=TODAY, start_hm="10:30", end_hm="13:30",
                technician_id="T002", van_id="V002",
                issue="BMS board reporting a sensor mismatch on a commercial LumenPack bank.",
                parts=[("P002", 1, 1, 0, "Allocated"), ("P004", 1, 1, 1, "Installed")],
                events=[
                    ("Created", "2026-09-26T14:00:00-05:00", "", "Battery repair opened for a BMS sensor mismatch."),
                    ("Assigned", "2026-09-26T15:00:00-05:00", "T002", "Assigned to T002 Sable Quill."),
                    ("Technician Dispatched", "2026-09-27T10:00:00-05:00", "T002", "Dispatched with the BMS board on the van."),
                    ("En Route", "2026-09-27T10:15:00-05:00", "T002", "En route to Bluebonnet Storage Yard."),
                    ("Arrived Onsite", "2026-09-27T10:40:00-05:00", "T002", "Arrived onsite."),
                    ("Diagnosis", "2026-09-27T11:00:00-05:00", "T002", "BMS board is the failed component. Thermal pads will be replaced with it."),
                    ("Repair Started", "2026-09-27T11:20:00-05:00", "T002", "BMS board swap in progress. Required parts were on van V002."),
                ],
            ),
            dict(
                job_id="J003", customer_id="C003", job_type="Emergency Service", priority="Critical",
                status="En Route", scheduled_date=TODAY, start_hm="15:30", end_hm="17:30",
                technician_id="T003", van_id="V003",
                issue="Clinic backup inverter dropped offline during a transfer test.",
                parts=[("P006", 1, 1, 0, "Allocated"), ("P020", 1, 1, 0, "Allocated"), ("P012", 2, 2, 0, "Allocated")],
                events=[
                    ("Created", "2026-09-27T14:10:00-05:00", "", "Emergency opened: clinic backup inverter offline."),
                    ("Assigned", "2026-09-27T14:25:00-05:00", "T003", "Assigned to T003 Idris Fen."),
                    ("Technician Dispatched", "2026-09-27T15:20:00-05:00", "T003", "Dispatched with a HaloWave inverter on van V003."),
                    ("En Route", "2026-09-27T15:40:00-05:00", "T003", "En route to San Gabriel Clinic Backup."),
                ],
            ),
            dict(
                job_id="J004", customer_id="C004", job_type="Inspection", priority="Medium",
                status="Onsite", scheduled_date=TODAY, start_hm="15:00", end_hm="16:30",
                technician_id="T006", van_id="V006",
                issue="Annual inspection of a whole-home battery and CT clamp check.",
                parts=[("P026", 1, 1, 0, "Allocated")],
                events=[
                    ("Created", "2026-09-26T11:00:00-05:00", "", "Annual inspection scheduled."),
                    ("Assigned", "2026-09-26T11:30:00-05:00", "T006", "Assigned to T006 Lumen Drake."),
                    ("Technician Dispatched", "2026-09-27T14:40:00-05:00", "T006", "Dispatched to Limestone Ridge House."),
                    ("En Route", "2026-09-27T14:55:00-05:00", "T006", "En route."),
                    ("Arrived Onsite", "2026-09-27T15:20:00-05:00", "T006", "Arrived onsite for the inspection."),
                ],
            ),
            dict(
                job_id="J005", customer_id="C005", job_type="Battery Replacement", priority="Medium",
                status="In Progress", scheduled_date=TODAY, start_hm="14:00", end_hm="17:00",
                technician_id="T007", van_id="V007",
                issue="Capacity test failed. Replace the interconnect kit and confirm the fuse.",
                parts=[("P002", 1, 1, 0, "Allocated"), ("P003", 1, 1, 1, "Installed"), ("P018", 1, 1, 0, "Allocated")],
                events=[
                    ("Created", "2026-09-26T09:00:00-05:00", "", "Battery replacement opened after a failed capacity test."),
                    ("Assigned", "2026-09-26T10:00:00-05:00", "T007", "Assigned to T007 Nova Brigg."),
                    ("Technician Dispatched", "2026-09-27T13:40:00-05:00", "T007", "Dispatched with the replacement kit."),
                    ("En Route", "2026-09-27T13:55:00-05:00", "T007", "En route to Barton Hollow Residence."),
                    ("Arrived Onsite", "2026-09-27T14:30:00-05:00", "T007", "Arrived onsite."),
                    ("Diagnosis", "2026-09-27T14:50:00-05:00", "T007", "Busbar discoloration matches the capacity loss."),
                    ("Repair Started", "2026-09-27T15:10:00-05:00", "T007", "Busbar kit installed. BMS board swap is next."),
                ],
            ),
            dict(
                job_id="J006", customer_id="C006", job_type="Troubleshooting", priority="High",
                status="En Route", scheduled_date=TODAY, start_hm="15:15", end_hm="17:15",
                technician_id="T008", van_id="V008",
                issue="Gateway stopped reporting. Site may have lost its communications module.",
                parts=[("P028", 1, 1, 0, "Allocated"), ("P014", 1, 1, 0, "Allocated")],
                events=[
                    ("Created", "2026-09-27T12:00:00-05:00", "", "Troubleshooting opened for a silent gateway."),
                    ("Assigned", "2026-09-27T12:20:00-05:00", "T008", "Assigned to T008 Harlow Finch."),
                    ("Technician Dispatched", "2026-09-27T15:00:00-05:00", "T008", "Dispatched to Pecan Switch Barn."),
                    ("En Route", "2026-09-27T15:25:00-05:00", "T008", "En route."),
                ],
            ),
            dict(
                job_id="J007", customer_id="C007", job_type="Inverter Repair", priority="High",
                status="Waiting for Parts", scheduled_date=TODAY, start_hm="12:30", end_hm="15:30",
                technician_id="T010", van_id="V010",
                issue="HaloWave inverter failed to reconnect after a grid event. Replacement is not on the van.",
                parts=[("P006", 1, 0, 0, "Missing"), ("P008", 1, 1, 0, "Allocated"), ("P014", 1, 1, 0, "Allocated")],
                events=[
                    ("Created", "2026-09-26T13:00:00-05:00", "", "Inverter repair opened after a failed reconnect."),
                    ("Assigned", "2026-09-26T13:40:00-05:00", "T010", "Assigned to T010 Quinn Ashby."),
                    ("Technician Dispatched", "2026-09-27T12:15:00-05:00", "T010", "Dispatched to Cedar Kettle Works."),
                    ("En Route", "2026-09-27T12:30:00-05:00", "T010", "En route."),
                    ("Arrived Onsite", "2026-09-27T13:00:00-05:00", "T010", "Arrived onsite."),
                    ("Diagnosis", "2026-09-27T13:30:00-05:00", "T010", "HaloWave unit will not produce. Fan spins, DC bus is dead."),
                    ("Part Required", "2026-09-27T13:50:00-05:00", "T010", "P006 is required and is not on van V010."),
                    ("Waiting for Parts", "2026-09-27T14:05:00-05:00", "T010", j007_wait),
                    ("Escalated", "2026-09-27T15:10:00-05:00", "T010", "Still waiting on the inverter transfer from W002."),
                ],
            ),
            dict(
                job_id="J008", customer_id="C008", job_type="Preventive Maintenance", priority="Low",
                status="In Progress", scheduled_date=TODAY, start_hm="14:30", end_hm="16:30",
                technician_id="T013", van_id="V013",
                issue="Quarterly preventive visit: thermal pads and PV fuses.",
                parts=[("P004", 1, 1, 0, "Allocated"), ("P019", 2, 2, 0, "Allocated")],
                events=[
                    ("Created", "2026-09-25T16:00:00-05:00", "", "Quarterly preventive maintenance scheduled."),
                    ("Assigned", "2026-09-26T09:00:00-05:00", "T013", "Assigned to T013 Juniper Vale."),
                    ("Technician Dispatched", "2026-09-27T14:05:00-05:00", "T013", "Dispatched to Lake Glass Pavilion."),
                    ("En Route", "2026-09-27T14:20:00-05:00", "T013", "En route."),
                    ("Arrived Onsite", "2026-09-27T14:50:00-05:00", "T013", "Arrived onsite."),
                    ("Diagnosis", "2026-09-27T15:10:00-05:00", "T013", "Pads are compressed. String fuses are due."),
                    ("Repair Started", "2026-09-27T15:25:00-05:00", "T013", "Preventive maintenance underway."),
                ],
            ),
            dict(
                job_id="J009", customer_id="C009", job_type="Preventive Maintenance", priority="Medium",
                status="En Route", scheduled_date=TODAY, start_hm="15:30", end_hm="17:00",
                technician_id="T014", van_id="V014",
                issue="Scheduled pad and fuse refresh at the grain office backup.",
                parts=[("P004", 1, 1, 0, "Allocated"), ("P019", 2, 2, 0, "Allocated")],
                events=[
                    ("Created", "2026-09-26T08:30:00-05:00", "", "Preventive maintenance scheduled."),
                    ("Assigned", "2026-09-26T09:00:00-05:00", "T014", "Assigned to T014 Theo Bramble."),
                    ("Technician Dispatched", "2026-09-27T15:05:00-05:00", "T014", "Dispatched to Hutto Grain Office."),
                    ("En Route", "2026-09-27T15:45:00-05:00", "T014", "En route."),
                ],
            ),
            dict(
                job_id="J010", customer_id="C010", job_type="Emergency Service", priority="Critical",
                status="Scheduled", scheduled_date=TODAY, start_hm="16:30", end_hm="18:30",
                technician_id="", van_id="",
                issue="Prairie Switch Backup is offline. Whole-home battery will not close in. No technician is assigned.",
                parts=[("P001", 1, 0, 0, "Required"), ("P018", 1, 0, 0, "Required"), ("P012", 2, 0, 0, "Required")],
                events=[
                    ("Created", "2026-09-27T08:40:00-05:00", "", "Emergency: Prairie Switch Backup battery is offline."),
                    ("Escalated", "2026-09-27T15:10:00-05:00", "", "Critical job still unassigned 80 minutes before the 16:30 start."),
                ],
            ),
            dict(
                job_id="J021", customer_id="C020", job_type="Troubleshooting", priority="High",
                status="Completed", scheduled_date=TODAY, start_hm="08:00", end_hm="11:30",
                technician_id="T005", van_id="V005",
                issue="Backup test failed on the AC breaker and a connector pair. Both parts were on the van.",
                parts=[("P009", 1, 1, 1, "Installed"), ("P015", 2, 2, 2, "Installed")],
                events=[
                    ("Created", "2026-09-26T15:00:00-05:00", "", "Troubleshooting opened after a failed backup test."),
                    ("Assigned", "2026-09-26T15:30:00-05:00", "T005", "Assigned to T005 Cassio Venn."),
                    ("Technician Dispatched", "2026-09-27T07:40:00-05:00", "T005", "Dispatched to Mesquite Switch House."),
                    ("En Route", "2026-09-27T07:55:00-05:00", "T005", "En route."),
                    ("Arrived Onsite", "2026-09-27T08:25:00-05:00", "T005", "Arrived onsite."),
                    ("Diagnosis", "2026-09-27T08:45:00-05:00", "T005", "60A breaker will not reset. MC4 pair on string 2 is heat-stained."),
                    ("Part Required", "2026-09-27T09:00:00-05:00", "T005", "P009 and P015 are required. Both are on van V005."),
                    ("Repair Started", "2026-09-27T09:15:00-05:00", "T005", "Breaker and connector replacement started."),
                    ("Repair Completed", "2026-09-27T10:50:00-05:00", "T005", "Backup transfer test passed."),
                    ("Customer Signoff", "2026-09-27T11:05:00-05:00", "T005", "Customer confirmed the backup test passed."),
                    ("Job Completed", "2026-09-27T11:20:00-05:00", "T005", "Site returned to normal operation."),
                ],
            ),
            dict(
                job_id="J030", customer_id="C025", job_type="Inspection", priority="High",
                status="Assigned", scheduled_date=TODAY, start_hm="13:00", end_hm="15:00",
                technician_id="T009", van_id="V009",
                issue="Inspection window was 13:00-15:00. The assigned technician has not left Round Rock.",
                parts=[("P026", 1, 1, 0, "Allocated")],
                created_at="2026-09-26T11:00:00-05:00",
            ),
        ]
        for spec in specs:
            self.add_job(**spec)

        # Monday jobs. J011 is fully kitted from a W001 reservation, including P001.
        self.add_job(
            job_id="J011", customer_id="C011", job_type="Installation", priority="High",
            status="Assigned", scheduled_date=TOMORROW, start_hm="08:00", end_hm="11:00",
            technician_id="T004", van_id="V004",
            issue="Monday installation. Battery module is reserved at Mesa Volt Depot.",
            parts=[
                ("P001", 1, 1, 0, "Allocated"),
                ("P012", 2, 2, 0, "Allocated"),
                ("P023", 1, 1, 0, "Allocated"),
                ("P015", 4, 4, 0, "Allocated"),
                ("P009", 1, 1, 0, "Allocated"),
            ],
            created_at="2026-09-27T09:30:00-05:00",
        )
        self.add_job(
            job_id="J012", customer_id="C012", job_type="Inverter Repair", priority="High",
            status="Assigned", scheduled_date=TOMORROW, start_hm="08:00", end_hm="11:00",
            technician_id="T008", van_id="V008",
            issue="Monday inverter swap. P006 is reserved at Brushy Creek Parts Hub.",
            parts=[("P006", 1, 1, 0, "Allocated"), ("P008", 1, 1, 0, "Allocated")],
            created_at="2026-09-27T09:40:00-05:00",
        )
        self.add_job(
            job_id="J015", customer_id="C015", job_type="Emergency Service", priority="High",
            status="Assigned", scheduled_date=TOMORROW, start_hm="13:00", end_hm="15:30",
            technician_id="T013", van_id="V013",
            issue="Monday staging is short one rapid shutdown device.",
            parts=[("P020", 1, 0, 0, "Missing"), ("P012", 2, 2, 0, "Allocated")],
            created_at="2026-09-27T10:15:00-05:00",
        )
        self.add_job(
            job_id="J016", customer_id="C016", job_type="Preventive Maintenance", priority="Medium",
            status="Assigned", scheduled_date=TOMORROW, start_hm="13:00", end_hm="15:30",
            technician_id="T014", van_id="V014",
            issue="Monday preventive visit, kitted from Brushy Creek.",
            parts=[("P018", 1, 1, 0, "Allocated"), ("P004", 1, 1, 0, "Allocated")],
            created_at="2026-09-27T10:20:00-05:00",
        )
        monday = [
            ("J013", "T001", "V001", "C013", "Battery Repair", "High", "13:00", "15:30"),
            ("J014", "T002", "V002", "C014", "Inspection", "Medium", "13:00", "15:30"),
            ("J017", "T003", "V003", "C017", "Preventive Maintenance", "Medium", "13:00", "15:30"),
            ("J018", "T006", "V006", "C018", "Troubleshooting", "Medium", "13:00", "15:30"),
            ("J019", "T007", "V007", "C019", "Installation", "Medium", "13:00", "15:30"),
            ("J020", "T010", "V010", "C021", "Emergency Service", "High", "13:00", "15:30"),
        ]
        for job_id, tech, van, customer, job_type, priority, start_hm, end_hm in monday:
            parts = [(part, qty, 0, 0, "Required") for part, qty in FILLER_KITS[job_type]]
            self.add_job(
                job_id=job_id, customer_id=customer, job_type=job_type, priority=priority,
                status="Assigned", scheduled_date=TOMORROW, start_hm=start_hm, end_hm=end_hm,
                technician_id=tech, van_id=van,
                issue=f"Monday {job_type.lower()} planned for {self.sites[customer]['site_name']}. Parts are listed and not yet picked.",
                parts=parts,
                created_at="2026-09-27T11:00:00-05:00",
            )

        # Historical jobs that the P001 / P006 custody chains install against.
        history = [
            ("J041", "2026-09-18", "T002", "V002", "C030", "Battery Replacement", [("P001", 1, 1, 1, "Installed")]),
            ("J042", "2026-09-16", "T008", "V008", "C031", "Inverter Repair", [("P006", 1, 1, 1, "Installed"), ("P008", 1, 1, 1, "Installed")]),
            ("J043", "2026-09-17", "T009", "V009", "C032", "Inverter Repair", [("P006", 1, 1, 1, "Installed")]),
            ("J044", "2026-09-13", "T011", "V011", "C033", "Inverter Repair", [("P006", 1, 1, 1, "Installed"), ("P007", 1, 1, 1, "Installed")]),
        ]
        for job_id, date, tech, van, customer, job_type, parts in history:
            self.add_job(
                job_id=job_id, customer_id=customer, job_type=job_type, priority="Medium",
                status="Completed", scheduled_date=date, start_hm="09:00", end_hm="12:00",
                technician_id=tech, van_id=van,
                issue=f"Completed {job_type.lower()} recorded so the part custody chain has an install.",
                parts=parts,
                created_at=prev_day(date, "15:00"),
            )

    def add_filler_jobs(self) -> None:
        explicit = set(self.jobs)
        filler_ids = [f"J{number:03d}" for number in range(1, 101) if f"J{number:03d}" not in explicit]
        if len(filler_ids) != 74:
            raise SystemExit(f"Expected 74 filler jobs, found {len(filler_ids)}")
        techs = [tech_id for tech_id, tech in self.techs.items() if tech["assigned_van_id"]]
        dates = [f"2026-09-{day:02d}" for day in range(1, 27)]
        types = list(JOB_TYPES)
        priorities = ["Low", "Medium", "High", "Medium", "Critical"]
        completed_ids = filler_ids[:60]
        cancelled_ids = filler_ids[60:68]
        future_ids = filler_ids[68:]
        future_dates = ["2026-09-29", "2026-09-30", "2026-10-01", "2026-10-02", "2026-09-29", "2026-10-01"]

        for index, job_id in enumerate(completed_ids):
            placed = False
            for attempt in range(len(techs) * len(dates) * len(PAST_SLOTS)):
                tech_id = techs[(index + attempt) % len(techs)]
                date = dates[(index * 3 + attempt) % len(dates)]
                start_hm, end_hm = PAST_SLOTS[(index + attempt) % len(PAST_SLOTS)]
                if self.slot_free(tech_id, date, start_hm, end_hm):
                    job_type = types[index % len(types)]
                    customer = cid((index * 7) % 50 + 1)
                    parts = [(part, qty, qty, qty, "Installed") for part, qty in FILLER_KITS[job_type]]
                    self.add_job(
                        job_id=job_id,
                        customer_id=customer,
                        job_type=job_type,
                        priority=priorities[index % len(priorities)],
                        status="Completed",
                        scheduled_date=date,
                        start_hm=start_hm,
                        end_hm=end_hm,
                        technician_id=tech_id,
                        van_id=self.techs[tech_id]["assigned_van_id"],
                        issue=f"{job_type} at {self.sites[customer]['site_name']}. Closed earlier in September.",
                        parts=parts,
                    )
                    placed = True
                    break
            if not placed:
                raise SystemExit(f"No open slot for filler job {job_id}")

        for index, job_id in enumerate(cancelled_ids):
            job_type = types[index % len(types)]
            customer = cid((40 + index) % 50 + 1)
            date = f"2026-09-{10 + index:02d}"
            parts = [(part, qty, 0, 0, "Required") for part, qty in FILLER_KITS[job_type]]
            self.add_job(
                job_id=job_id, customer_id=customer, job_type=job_type, priority="Low",
                status="Cancelled", scheduled_date=date, start_hm="09:00", end_hm="11:00",
                technician_id="", van_id="",
                issue=f"{job_type} cancelled before dispatch at {self.sites[customer]['site_name']}.",
                parts=parts,
                created_at=prev_day(date, "11:00"),
            )

        for index, job_id in enumerate(future_ids):
            job_type = types[(index + 3) % len(types)]
            customer = cid((20 + index * 3) % 50 + 1)
            date = future_dates[index]
            parts = [(part, qty, 0, 0, "Required") for part, qty in FILLER_KITS[job_type]]
            priority = "High" if index == 0 else "Medium"
            self.add_job(
                job_id=job_id, customer_id=customer, job_type=job_type, priority=priority,
                status="Scheduled", scheduled_date=date, start_hm="09:00", end_hm="11:30",
                technician_id="", van_id="",
                issue=f"Unassigned {job_type.lower()} later in the week at {self.sites[customer]['site_name']}.",
                parts=parts,
                created_at="2026-09-27T12:00:00-05:00",
            )

    def fill_actuals(self) -> None:
        by_job = defaultdict(list)
        for event in self.job_events:
            by_job[event["job_id"]].append(event)
        for job in self.jobs.values():
            if job["status"] != "Completed":
                job["actual_duration_minutes"] = ""
                continue
            events = sorted(by_job[job["job_id"]], key=lambda row: row["timestamp"])
            arrived = next(row["timestamp"] for row in events if row["event_type"] == "Arrived Onsite")
            done = next(row["timestamp"] for row in events if row["event_type"] == "Job Completed")
            mins = int((parse_ts(done) - parse_ts(arrived)).total_seconds() // 60)
            if mins <= 0:
                raise SystemExit(f"Non-positive duration on {job['job_id']}")
            job["actual_duration_minutes"] = str(mins)

    def plan_stock(self) -> None:
        ledger = self.ledger
        self._emit_p001(ledger)
        self._emit_p006(ledger)

        van_target: dict[tuple[str, str], int] = defaultdict(int)
        install_need: dict[tuple[str, str], int] = defaultdict(int)
        install_rows = []
        reserve_need: dict[tuple[str, str], int] = defaultdict(int)

        for row in self.job_parts:
            if row["part_id"] in SPECIAL_PARTS:
                continue
            job = self.jobs[row["job_id"]]
            van_id = job["van_id"]
            if row["installed_quantity"] > 0:
                if not van_id:
                    raise SystemExit(f"Installed part on a job with no van: {job['job_id']}")
                install_need[(van_id, row["part_id"])] += row["installed_quantity"]
                install_rows.append(row)
            remaining = row["allocated_quantity"] - row["installed_quantity"]
            if remaining > 0 and job["status"] in FIELD_STATUSES:
                van_target[(van_id, row["part_id"])] = max(van_target[(van_id, row["part_id"])], remaining)
            if row["status"] == "Allocated" and job["status"] in {"Assigned", "Scheduled"}:
                reserve_need[(home_for(van_id), row["part_id"])] += row["allocated_quantity"]

        for van_id, van in self.vans.items():
            if van_id == SHOP_VAN:
                continue
            for part_id, qty in CARRY:
                van_target[(van_id, part_id)] = max(van_target[(van_id, part_id)], qty)
            if van_id in FULL_KIT_VANS:
                for part_id, qty in FULL_KIT:
                    van_target[(van_id, part_id)] = max(van_target[(van_id, part_id)], qty)
        for (van_id, part_id), qty in VAN_EXTRAS.items():
            van_target[(van_id, part_id)] = max(van_target[(van_id, part_id)], qty)
        for van_id, part_id in VAN_DENY:
            van_target.pop((van_id, part_id), None)

        end_oh: dict[tuple[str, str], int] = {}
        for part_id, part in self.parts.items():
            if part_id in SPECIAL_PARTS:
                continue
            for wh_id in self.warehouses:
                override = OH_OVERRIDE.get((wh_id, part_id), "formula")
                if override is None:
                    continue
                if override == "formula":
                    wh_index = int(wh_id[1:])
                    part_index = int(part_id[1:])
                    oh = part["reorder_point"] + 4 + wh_index * 2 + (part_index % 3)
                else:
                    oh = override
                oh = max(oh, reserve_need.get((wh_id, part_id), 0))
                end_oh[(wh_id, part_id)] = oh

        for (wh_id, part_id), oh in sorted(end_oh.items()):
            issue_qty = 0
            for van_id, van in self.vans.items():
                if van["home_warehouse_id"] != wh_id:
                    continue
                issue_qty += van_target.get((van_id, part_id), 0) + install_need.get((van_id, part_id), 0)
            scrap_qty = 2 if part_id == "P019" and wh_id == "W001" else 0
            if oh == 0 and issue_qty == 0:
                scrap_qty = max(scrap_qty, 2)
            wh_index = int(wh_id[1:])
            part_index = int(part_id[1:])
            receive_ts = plus("2026-09-01T06:00:00-05:00", wh_index * 5 + part_index)
            ledger.receive(
                part_id,
                wh_id,
                oh + issue_qty + scrap_qty,
                receive_ts,
                f"Opening receipt of {part_id} into {wh_id} for September field stock.",
            )
            if scrap_qty:
                ledger.scrap(
                    part_id,
                    wh_id,
                    scrap_qty,
                    plus(receive_ts, 30),
                    "Scrapped units that failed incoming inspection."
                    if part_id == "P019"
                    else "Scrapped the only units received; the bin was counted empty afterward.",
                )

        issue_groups: dict[tuple[str, str], int] = defaultdict(int)
        for key, qty in list(van_target.items()) + list(install_need.items()):
            issue_groups[key] += qty
        for (van_id, part_id), qty in sorted(issue_groups.items()):
            if qty <= 0:
                continue
            tech_id = self.vans[van_id]["assigned_technician_id"] or "T030"
            wh_id = self.vans[van_id]["home_warehouse_id"]
            stamp = plus("2026-09-01T07:00:00-05:00", int(van_id[1:]))
            ledger.issue(
                part_id,
                wh_id,
                van_id,
                tech_id,
                qty,
                stamp,
                f"Issued {qty} {part_id} to van {van_id}. Checked out by {tech_id}.",
            )

        for row in install_rows:
            job = self.jobs[row["job_id"]]
            events = [event for event in self.job_events if event["job_id"] == job["job_id"]]
            repair = next(event["timestamp"] for event in events if event["event_type"] == "Repair Started")
            ledger.install(
                row["part_id"],
                job["van_id"],
                job["job_id"],
                job["technician_id"],
                row["installed_quantity"],
                plus(repair, 15),
                f"Installed on job {job['job_id']} at {self.sites[job['customer_id']]['site_name']}.",
            )

        for (wh_id, part_id), qty in sorted(reserve_need.items()):
            job_id = next(
                row["job_id"]
                for row in self.job_parts
                if row["part_id"] == part_id
                and row["status"] == "Allocated"
                and self.jobs[row["job_id"]]["status"] in {"Assigned", "Scheduled"}
                and home_for(self.jobs[row["job_id"]]["van_id"]) == wh_id
            )
            ledger.reserve_wh(
                part_id,
                wh_id,
                job_id,
                qty,
                "2026-09-26T15:30:00-05:00",
                f"Reserved {qty} {part_id} at {wh_id} for job {job_id}.",
            )

        # Net-zero return so the Returned type is real and stock still lands on the plan.
        ledger.issue(
            "P004", "W001", "V001", "T001", 1,
            "2026-09-27T06:30:00-05:00",
            "Extra thermal pad set pulled during Sunday staging.",
        )
        ledger.returned(
            "P004", "V001", "W001", "T001", 1,
            "2026-09-27T06:50:00-05:00",
            "Unused thermal pad set returned from van V001 to Mesa Volt Depot.",
        )
        ledger.apply_all()

    def _emit_p001(self, ledger: Ledger) -> None:
        ledger.receive("P001", "W001", 24, "2026-09-02T09:00:00-05:00", "PO-4401 receipt of LumenPack 13.5 modules from supplier SUP-NORTHWIND.")
        ledger.transfer("P001", "W001", "W002", 8, "2026-09-08T10:15:00-05:00", "Rebalance stock to Brushy Creek Parts Hub.")
        ledger.transfer("P001", "W001", "W003", 4, "2026-09-10T11:00:00-05:00", "Seed Bluebonnet Service Warehouse.")
        ledger.issue("P001", "W001", "V001", "T001", 2, "2026-09-15T07:35:00-05:00", "Checked out by technician T001 Rowan Pell onto van V001.")
        ledger.issue("P001", "W002", "V002", "T002", 1, "2026-09-18T07:50:00-05:00", "Checked out by technician T002 Sable Quill onto van V002 for job J041.", job="J041")
        ledger.install("P001", "V002", "J041", "T002", 1, "2026-09-18T11:10:00-05:00", "Installed one LumenPack module on job J041 at Owl Creek Cabin.")
        ledger.issue("P001", "W001", "V004", "T004", 1, "2026-09-22T07:40:00-05:00", "Checked out by technician T004 Maren Holt onto van V004.")
        ledger.adjust("P001", "W003", -1, "2026-09-25T16:20:00-05:00", ADJ_NOTE)
        ledger.reserve_wh("P001", "W001", "J011", 1, "2026-09-26T15:10:00-05:00", "Reserved one LumenPack module at W001 for Monday job J011.")
        ledger.reserve_van("P001", "V001", "J001", "T001", 1, "2026-09-27T12:25:00-05:00", "Reserved one LumenPack module from van V001 onto job J001. The unit is still physically on the van.")

    def _emit_p006(self, ledger: Ledger) -> None:
        ledger.receive("P006", "W001", 3, "2026-09-03T09:10:00-05:00", "Receipt of HaloWave inverters into Mesa Volt Depot.")
        ledger.receive("P006", "W002", 8, "2026-09-04T09:10:00-05:00", "Receipt of HaloWave inverters into Brushy Creek Parts Hub.")
        ledger.issue("P006", "W002", "V011", "T011", 1, "2026-09-11T07:40:00-05:00", "Checked out by T011 Ellis Marrow onto van V011 for job J044.", job="J044")
        ledger.transfer("P006", "W001", "W002", 3, "2026-09-12T10:00:00-05:00", "All remaining HaloWave units moved from W001 to W002. W001 bin is now empty.")
        ledger.install("P006", "V011", "J044", "T011", 1, "2026-09-13T10:40:00-05:00", "Installed HaloWave inverter on job J044.")
        ledger.issue("P006", "W002", "V008", "T008", 1, "2026-09-14T07:40:00-05:00", "Checked out by T008 Harlow Finch onto van V008 for job J042.", job="J042")
        ledger.issue("P006", "W002", "V009", "T009", 1, "2026-09-15T07:45:00-05:00", "Checked out by T009 Petra Sol onto van V009 for job J043.", job="J043")
        ledger.install("P006", "V008", "J042", "T008", 1, "2026-09-16T10:40:00-05:00", "Installed HaloWave inverter on job J042.")
        ledger.install("P006", "V009", "J043", "T009", 1, "2026-09-17T10:40:00-05:00", "Installed HaloWave inverter on job J043.")
        ledger.issue("P006", "W002", "V003", "T003", 1, "2026-09-20T07:40:00-05:00", "Checked out by T003 Idris Fen onto van V003.")
        ledger.issue("P006", "W002", "V004", "T004", 1, "2026-09-21T07:40:00-05:00", "Checked out by T004 Maren Holt onto van V004.")
        ledger.issue("P006", "W002", "V006", "T006", 1, "2026-09-22T07:50:00-05:00", "Checked out by T006 Lumen Drake onto van V006.")
        ledger.reserve_wh("P006", "W002", "J012", 1, "2026-09-26T15:20:00-05:00", "Reserved one HaloWave inverter at W002 for Monday job J012.")

    def materialize_inventory(self) -> None:
        check_ts = "2026-09-27T06:40:00-05:00"
        counter = 0
        for (van_id, part_id), qty in sorted(self.ledger.van.items()):
            if qty <= 0:
                continue
            counter += 1
            self.van_rows.append(
                {
                    "van_inventory_id": f"VI{counter:05d}",
                    "van_id": van_id,
                    "part_id": part_id,
                    "quantity": qty,
                    "last_inventory_check": check_ts,
                }
            )
        counter = 0
        for wh_id, part_id in sorted(self.ledger.seen):
            on_hand = self.ledger.wh.get((wh_id, part_id), 0)
            reserved = self.ledger.res.get((wh_id, part_id), 0)
            counted = "2026-09-25T16:20:00-05:00" if (wh_id, part_id) == ("W003", "P001") else "2026-09-26T18:00:00-05:00"
            counter += 1
            self.wh_rows.append(
                {
                    "warehouse_inventory_id": f"WI{counter:05d}",
                    "warehouse_id": wh_id,
                    "part_id": part_id,
                    "quantity_on_hand": on_hand,
                    "quantity_reserved": reserved,
                    "quantity_available": on_hand - reserved,
                    "reorder_point": self.parts[part_id]["reorder_point"],
                    "last_counted_at": counted,
                }
            )
            part_index = int(part_id[1:])
            aisle = {"W001": "A", "W002": "B", "W003": "C"}[wh_id]
            if part_id == "P001":
                shelf, bin_no = {"W001": ("03", "14"), "W002": ("01", "02"), "W003": ("02", "07")}[wh_id]
            else:
                shelf = f"{(part_index % 4) + 1:02d}"
                bin_no = f"{(part_index % 16) + 1:02d}"
            self.wh_locs.append(
                {"warehouse_id": wh_id, "part_id": part_id, "aisle": aisle, "shelf": shelf, "bin": bin_no}
            )

    def build_locations(self) -> None:
        events_by_tech = defaultdict(list)
        for event in self.job_events:
            if event["technician_id"] and event["timestamp"].startswith(TODAY):
                events_by_tech[event["technician_id"]].append(event)
        points = []
        for tech in self.techs.values():
            tech_id = tech["technician_id"]
            base_lat, base_lon, base_city = base_point(tech)
            final_ts = tech["last_location_timestamp"]
            trail = []
            shift_ts = at(TODAY, tech["shift_start"])
            if shift_ts < final_ts:
                trail.append((shift_ts, base_lat, base_lon, base_city, "Available", ""))
            if tech["status"] == "Off Duty":
                mid = at(TODAY, "10:00")
                if shift_ts < mid < final_ts:
                    trail.append((mid, base_lat, base_lon, base_city, "Available", ""))
            for event in events_by_tech.get(tech_id, []):
                if event["timestamp"] >= final_ts:
                    continue
                job = self.jobs[event["job_id"]]
                site = self.sites[job["customer_id"]]
                if event["event_type"] == "En Route":
                    lat = r5((base_lat + site["latitude"]) / 2)
                    lon = r5((base_lon + site["longitude"]) / 2)
                    trail.append((event["timestamp"], lat, lon, site["city"], "En Route", job["job_id"]))
                elif event["event_type"] == "Arrived Onsite":
                    trail.append((event["timestamp"], site["latitude"], site["longitude"], site["city"], "On Job", job["job_id"]))
                elif event["event_type"] == "Job Completed":
                    trail.append((event["timestamp"], site["latitude"], site["longitude"], site["city"], "Available", job["job_id"]))
            trail.append(
                (
                    final_ts,
                    tech["current_latitude"],
                    tech["current_longitude"],
                    tech["current_city"],
                    tech["status"],
                    tech["current_job_id"],
                )
            )
            trail.sort(key=lambda item: item[0])
            # Keep the snapshot as the unique latest ping.
            trimmed = [item for item in trail if item[0] < final_ts]
            trimmed.append(trail[-1] if trail[-1][0] == final_ts else trail[-1])
            seen_ts = set()
            for item in trimmed:
                ts = item[0]
                while ts in seen_ts:
                    ts = plus(ts, 1)
                seen_ts.add(ts)
                points.append((tech_id, ts, item[1], item[2], item[3], item[4], item[5]))
        points.sort(key=lambda item: (item[0], item[1]))
        for index, item in enumerate(points, start=1):
            self.locations.append(
                {
                    "location_event_id": f"LE{index:05d}",
                    "technician_id": item[0],
                    "timestamp": item[1],
                    "latitude": item[2],
                    "longitude": item[3],
                    "city": item[4],
                    "status": item[5],
                    "job_id": item[6],
                }
            )

    def build_vehicle_events(self) -> None:
        drafted = []
        for van in self.vans.values():
            van_id = van["van_id"]
            number = int(van_id[1:])
            base = 18000 + number * 3470
            rows = [
                ("2026-09-12T08:00:00-05:00", "Inspection", f"Routine safety inspection for fleet number {van['vehicle_number']}."),
                ("2026-09-20T07:30:00-05:00", "Fuel/Charge", "Depot charge before the week."),
            ]
            if van_id in {DUE_VAN, "V007"}:
                rows.append(("2026-09-26T16:10:00-05:00", "Warning", "Service interval is inside the next three weeks."))
            if van_id == SHOP_VAN:
                rows.append(("2026-09-24T09:00:00-05:00", "Maintenance", "Shop intake at W001 for brake and charger service."))
                rows.append(("2026-09-26T13:00:00-05:00", "Repair", "Repair in progress. Expected release 2026-10-01."))
                rows.append(("2026-09-27T11:00:00-05:00", "Check In", "Shop bay check-in. Vehicle is not released."))
            elif van_id == OFFLINE_VAN:
                rows.append(("2026-09-26T17:10:00-05:00", "Check In", "Last telematics heartbeat. Gateway has not checked in since."))
            elif van_id == SPARE_VAN:
                rows.append(("2026-09-27T15:20:00-05:00", "Check In", "Parked at home warehouse W003 and available for dispatch."))
            else:
                rows.append(("2026-09-27T06:45:00-05:00", "Check Out", "Checked out for the Sunday rotation."))
                rows.append(("2026-09-27T15:50:00-05:00", "Check In", "Afternoon telematics check-in."))
            rows.sort()
            miles = base
            for ts, kind, note in rows:
                bump = {
                    "Inspection": 1,
                    "Fuel/Charge": 5,
                    "Warning": 0,
                    "Maintenance": 2,
                    "Repair": 0,
                    "Check Out": 15,
                    "Check In": 22,
                }[kind]
                miles += bump
                drafted.append((ts, van_id, kind, miles, note))
            van["mileage"] = miles
            checkins = [ts for ts, kind, _note in rows if kind == "Check In"]
            van["last_check_in"] = max(checkins)
        drafted.sort(key=lambda item: (item[1], item[0]))
        for index, item in enumerate(drafted, start=1):
            self.vehicle_events.append(
                {
                    "event_id": f"VE{index:05d}",
                    "van_id": item[1],
                    "timestamp": item[0],
                    "event_type": item[2],
                    "mileage": item[3],
                    "notes": item[4],
                }
            )

    def build_schedules(self) -> None:
        rows = []
        for job in self.jobs.values():
            if not job["technician_id"]:
                continue
            if job["status"] == "Completed":
                status = "Completed"
            elif job["status"] == "Cancelled":
                status = "Cancelled"
            elif (
                job["scheduled_date"] == TODAY
                and job["scheduled_end"] < NOW
                and job["status"] in {"Assigned", "Scheduled"}
            ):
                status = "Missed"
            elif job["status"] in FIELD_STATUSES:
                status = "In Progress"
            else:
                status = "Scheduled"
            rows.append(
                {
                    "date": job["scheduled_date"],
                    "technician_id": job["technician_id"],
                    "job_id": job["job_id"],
                    "start_time": job["scheduled_start"][11:16],
                    "end_time": job["scheduled_end"][11:16],
                    "location_city": self.sites[job["customer_id"]]["city"],
                    "status": status,
                }
            )
        rows.sort(key=lambda row: (row["date"], row["technician_id"], row["start_time"], row["job_id"]))
        for index, row in enumerate(rows, start=1):
            row["schedule_id"] = f"SC{index:05d}"
            self.schedules.append(row)

    def build_alerts(self) -> None:
        p006_w001 = self._available("W001", "P006")
        p018_w002 = self._available("W002", "P018")
        p018_w001 = self._available("W001", "P018")
        specs = [
            ("AL001", "Unassigned Critical Job", "Critical", "2026-09-27T15:12:00-05:00", "Job", "J010", "Open",
             "Emergency Service at Prairie Switch Backup (C010) in Pflugerville has no technician. The battery is offline and the start window is 16:30.",
             "Dispatch T004 Maren Holt with van V004. They are available about 1 km away, hold Battery Installation Master, and the van carries P001, P018, and P012."),
            ("AL002", "Missing Job Parts", "High", "2026-09-27T13:06:00-05:00", "Job", "J001", "Open",
             "J001 needs P018 200A Class T Fuse qty 2 and van V001 has none. The crew has been onsite since 12:10.",
             f"Issue two P018 fuses from W001 Mesa Volt Depot (available {p018_w001}) to van V001."),
            ("AL003", "Missing Job Parts", "High", "2026-09-27T14:06:00-05:00", "Job", "J007", "Open",
             "J007 is blocked on P006 HaloWave 7.6 Hybrid Inverter. Van V010 does not have one, and W001 is out of stock.",
             "Transfer or issue P006 from W002 Brushy Creek Parts Hub, which has available units."),
            ("AL004", "Out of Stock", "High", "2026-09-27T08:15:00-05:00", "Part", "P006", "Open",
             f"P006 on-hand at W001 is {self._on_hand('W001', 'P006')}. Available quantity is {p006_w001}. W002 still has stock; W003 does not stock this part.",
             "Replenish Mesa Volt Depot from Brushy Creek or from supplier SUP-NORTHWIND."),
            ("AL005", "Low Inventory", "Medium", "2026-09-27T08:20:00-05:00", "Part", "P018", "Open",
             f"P018 available at W002 is {p018_w002}, under the reorder point of {self.parts['P018']['reorder_point']}. W003 is also below its reorder point. W001 is healthy.",
             "Reorder Class T fuses for W002 and W003. Use W001 to cover today's J001 shortage."),
            ("AL006", "Maintenance Due", "Medium", "2026-09-26T16:20:00-05:00", "Van", "V019", "Open",
             "Van V019 next maintenance date is 2026-10-08 and a warning was logged on 2026-09-26. It is still in service with T021.",
             "Book V019 into W003 before 2026-10-08 and avoid multi-day trips until the service is done."),
            ("AL007", "Technician Delayed", "High", "2026-09-27T15:15:00-05:00", "Technician", "T010", "Open",
             "T010 Quinn Ashby has been onsite at J007 since 13:00 (more than two hours) because the job is Waiting for Parts.",
             "Either release T010 once the W002 inverter transfer is confirmed, or reassign the waiting job."),
            ("AL008", "Inventory Discrepancy", "High", "2026-09-25T16:25:00-05:00", "Part", "P001", "Open",
             "Cycle count at W003 on 2026-09-25 shorted one LumenPack module (P001) in aisle C shelf 02 bin 07. An Adjustment corrected the book quantity.",
             "Review dock cameras for the 2026-09-10 transfer into W003 before the next LumenPack order."),
            ("AL009", "Job Overdue", "High", "2026-09-27T15:05:00-05:00", "Job", "J030", "Open",
             "J030 was scheduled 13:00-15:00 at Hollow Oak Bakery and is still Assigned. T009 has not dispatched.",
             "Call T009 Petra Sol or reassign J030 before the site closes."),
            ("AL010", "Van Offline", "Medium", "2026-09-27T09:05:00-05:00", "Van", "V012", "Open",
             "Van V012 telematics last checked in at 2026-09-26 17:10. Technician T012 phone location is current; the vehicle gateway is not.",
             "Have T012 power-cycle the van gateway at the next stop."),
            ("AL011", "Maintenance Due", "Low", "2026-09-24T09:30:00-05:00", "Van", "V018", "Open",
             "Van V018 is in the shop at W001. Expected release is 2026-10-01. Usual driver T028 is off duty and has no van assigned today.",
             "Keep V018 unassigned until the shop releases it."),
            ("AL012", "Low Inventory", "Low", "2026-09-22T11:00:00-05:00", "Part", "P021", "Acknowledged",
             "P021 at W002 was counted under its reorder point. A replenishment PO is open with SUP-NORTHWIND.",
             "Confirm the PO arrives before Wednesday."),
            ("AL013", "Technician Delayed", "Low", "2026-09-20T16:40:00-05:00", "Technician", "T015", "Resolved",
             "T015 ran long on a Sep 20 inspection. The job has since been completed and the alert is closed.",
             "No action. Kept as history."),
        ]
        for item in specs:
            self.alerts.append(
                {
                    "alert_id": item[0],
                    "alert_type": item[1],
                    "severity": item[2],
                    "created_at": item[3],
                    "entity_type": item[4],
                    "entity_id": item[5],
                    "status": item[6],
                    "description": item[7],
                    "recommended_action": item[8],
                }
            )

    def _on_hand(self, wh: str, part: str) -> int:
        return self.ledger.wh.get((wh, part), 0)

    def _available(self, wh: str, part: str) -> int:
        return self._on_hand(wh, part) - self.ledger.res.get((wh, part), 0)

    def van_qty(self, van_id: str, part_id: str) -> int:
        return self.ledger.van.get((van_id, part_id), 0)


def build_world() -> World:
    world = World()
    world.add_explicit_jobs()
    world.add_filler_jobs()
    if len(world.jobs) != 100:
        raise SystemExit(f"Expected 100 jobs, built {len(world.jobs)}")
    world.fill_actuals()
    world.plan_stock()
    place_people(world.techs, world.vans, world.jobs, world.sites, world.warehouses)
    world.materialize_inventory()
    world.build_locations()
    world.build_vehicle_events()
    world.build_schedules()
    world.build_alerts()
    _renumber_transactions(world)
    _number_events(world)
    return world


def _renumber_transactions(world: World) -> None:
    ordered = sorted(world.ledger.txs, key=lambda row: (row["timestamp"], row["_seq"]))
    for index, row in enumerate(ordered, start=1):
        row["transaction_id"] = f"TX{index:05d}"
    world.ledger.txs = ordered


def _number_events(world: World) -> None:
    world.job_events.sort(key=lambda row: (row["job_id"], row["timestamp"]))
    for index, row in enumerate(world.job_events, start=1):
        row["event_id"] = f"JE{index:05d}"


def _subsequence(need: list[str], have: list[str]) -> bool:
    index = 0
    for event_type in have:
        if index < len(need) and event_type == need[index]:
            index += 1
    return index == len(need)


def _fmt_coord(value: float) -> str:
    return f"{value:.5f}"


def _fmt_capacity(value: float) -> str:
    if float(value).is_integer():
        return str(int(value))
    return f"{value:.1f}"


SCHEMAS: list[tuple[str, str, list[tuple[str, str]]]] = [
    ("technicians.csv", "technician_id", [
        ("technician_id", "Primary key. T001-T030."),
        ("name", "Fictional technician name."),
        ("status", "Available, On Job, En Route, Off Duty, or Break at the 16:00 snapshot."),
        ("current_latitude", "Latest known latitude, five decimal degrees. Matches the latest technician_locations row."),
        ("current_longitude", "Latest known longitude, five decimal degrees."),
        ("current_city", "City label for the latest ping. A fictional locality, not a street address."),
        ("last_location_timestamp", "Timestamp of the latest ping, ISO-8601 with -05:00 offset."),
        ("skills", "Semicolon-separated skills such as Battery Installation, Battery Repair, Inverter Repair, Electrical, Diagnostics."),
        ("certifications", "Semicolon-separated certifications with a level: Level 1, Level 2, or Master."),
        ("assigned_van_id", "Van currently assigned. Blank if the technician has no van. Symmetric with vans.assigned_technician_id."),
        ("current_job_id", "Job they are on right now. Blank unless status is On Job or En Route."),
        ("shift_start", "Sunday 2026-09-27 shift start, local HH:MM. Weekday hours are not stored on this row."),
        ("shift_end", "Sunday 2026-09-27 shift end, local HH:MM."),
    ]),
    ("technician_locations.csv", "location_event_id", [
        ("location_event_id", "Primary key. LE00001 and up."),
        ("technician_id", "Foreign key to technicians.technician_id."),
        ("timestamp", "Ping time, ISO-8601 with -05:00 offset. History is on 2026-09-27."),
        ("latitude", "Latitude at that ping."),
        ("longitude", "Longitude at that ping."),
        ("city", "City label for that ping."),
        ("status", "Technician status at that ping. Same vocabulary as technicians.status."),
        ("job_id", "Job they were traveling to or on. Blank when they were not on a job. Foreign key to jobs.job_id when set."),
    ]),
    ("vans.csv", "van_id", [
        ("van_id", "Primary key. V001-V020."),
        ("vehicle_number", "Fictional fleet number such as LF-4801. This is not a VIN."),
        ("status", "Available, On Job, En Route, Parked, or Maintenance."),
        ("assigned_technician_id", "Technician who has the van. Blank if the van is spare or in the shop. Symmetric with technicians.assigned_van_id."),
        ("current_latitude", "Current latitude. Matches the assigned technician when the van is with them."),
        ("current_longitude", "Current longitude."),
        ("current_city", "Current city label."),
        ("last_check_in", "Last vehicle-gateway check-in. This can lag the technician phone ping. See V012."),
        ("mileage", "Odometer in miles. Equals the latest vehicle_events.mileage for this van."),
        ("fuel_or_charge_percent", "State of charge, 0-100. The fleet is battery-electric."),
        ("maintenance_status", "OK, Due Soon, or In Shop."),
        ("next_maintenance_date", "Next planned service date, YYYY-MM-DD."),
        ("home_warehouse_id", "Foreign key to warehouses.warehouse_id. Depot the van is stocked from."),
    ]),
    ("van_inventory.csv", "van_inventory_id", [
        ("van_inventory_id", "Primary key. VI00001 and up."),
        ("van_id", "Foreign key to vans.van_id."),
        ("part_id", "Foreign key to parts.part_id. One row per van and part."),
        ("quantity", "Physical quantity on the van. Includes units reserved to a job. Always greater than zero."),
        ("last_inventory_check", "When this van was last fully counted. Parts omitted from the van were zero at that count."),
    ]),
    ("warehouses.csv", "warehouse_id", [
        ("warehouse_id", "Primary key. W001-W003."),
        ("warehouse_name", "Fictional depot name."),
        ("city", "City the depot sits in."),
        ("latitude", "Fictional depot latitude."),
        ("longitude", "Fictional depot longitude."),
        ("operating_hours", "Local hours. All three depots are open daily 06:00-18:00."),
        ("manager_name", "Fictional depot manager."),
        ("status", "Open."),
    ]),
    ("parts.csv", "part_id", [
        ("part_id", "Primary key. P001-P032."),
        ("part_number", "Fictional catalog number, LF- prefix."),
        ("part_name", "Part name."),
        ("category", "Battery, Inverter, Electrical, Cable, Connector, Fuse, Circuit Protection, Mounting Hardware, Sensors, or Tools."),
        ("description", "What the part is."),
        ("unit", "Unit of measure: each, kit, set, pair, or pack."),
        ("unit_cost", "Synthetic unit cost in USD, two decimals. Not a real price."),
        ("criticality", "Critical, High, Medium, or Low."),
        ("reorder_point", "Catalog reorder point used as the default warehouse reorder point."),
        ("preferred_stock_level", "Target on-hand. On-hand at least twice this value is treated as overstocked in the demo notes."),
    ]),
    ("warehouse_inventory.csv", "warehouse_inventory_id", [
        ("warehouse_inventory_id", "Primary key. WI00001 and up."),
        ("warehouse_id", "Foreign key to warehouses.warehouse_id."),
        ("part_id", "Foreign key to parts.part_id."),
        ("quantity_on_hand", "Physical quantity, including units that are reserved. May be zero when the bin is empty."),
        ("quantity_reserved", "Quantity held for a job and not available to promise."),
        ("quantity_available", "quantity_on_hand minus quantity_reserved. Always exact."),
        ("reorder_point", "Reorder point for this warehouse-part row. Copied from parts.reorder_point."),
        ("last_counted_at", "Last cycle count, ISO-8601 with -05:00 offset."),
    ]),
    ("warehouse_locations.csv", "warehouse_id, part_id", [
        ("warehouse_id", "Foreign key to warehouses.warehouse_id. Part of the composite primary key."),
        ("part_id", "Foreign key to parts.part_id. Part of the composite primary key."),
        ("aisle", "Aisle letter. A at W001, B at W002, C at W003, except where a demo bin is called out."),
        ("shelf", "Shelf number, zero-padded."),
        ("bin", "Bin number, zero-padded."),
    ]),
    ("customer_sites.csv", "customer_id", [
        ("customer_id", "Primary key. C001-C050. There is no separate customer table; the site is the customer."),
        ("site_name", "Fictional site name. No street address."),
        ("city", "City label."),
        ("latitude", "Fictional site latitude near the named city."),
        ("longitude", "Fictional site longitude."),
        ("system_type", "Whole-Home Battery, Commercial Storage, Backup Power, or Solar-Plus-Storage."),
        ("battery_capacity_kwh", "Installed battery energy, kWh."),
        ("inverter_capacity_kw", "Installed inverter power, kW."),
        ("installation_date", "Original install date, YYYY-MM-DD."),
        ("site_status", "Active, Commissioning, or Offline."),
    ]),
    ("jobs.csv", "job_id", [
        ("job_id", "Primary key. J001-J100."),
        ("customer_id", "Foreign key to customer_sites.customer_id."),
        ("job_type", "Installation, Battery Replacement, Battery Repair, Inverter Repair, Inspection, Preventive Maintenance, Emergency Service, or Troubleshooting."),
        ("priority", "Low, Medium, High, or Critical."),
        ("status", "Scheduled, Assigned, En Route, Onsite, In Progress, Waiting for Parts, Completed, or Cancelled."),
        ("scheduled_date", "Local work date, YYYY-MM-DD."),
        ("scheduled_start", "Planned start, ISO-8601 with -05:00 offset."),
        ("scheduled_end", "Planned end, ISO-8601 with -05:00 offset. A crew can still be onsite after this time."),
        ("technician_id", "Assigned technician. Blank when unassigned. Foreign key when set."),
        ("van_id", "Van on the job. Blank when unassigned. On open jobs this is the technician's current van."),
        ("created_at", "When the job was opened."),
        ("estimated_duration_minutes", "Planned duration in minutes."),
        ("actual_duration_minutes", "Minutes from Arrived Onsite to Job Completed. Blank unless the job is Completed."),
        ("issue_description", "Plain-language reason for the visit."),
    ]),
    ("job_parts.csv", "job_part_id", [
        ("job_part_id", "Primary key. JP00001 and up."),
        ("job_id", "Foreign key to jobs.job_id."),
        ("part_id", "Foreign key to parts.part_id."),
        ("required_quantity", "Quantity the job needs."),
        ("allocated_quantity", "Quantity reserved or staged. Never above required in this dataset."),
        ("installed_quantity", "Quantity already installed. Never above allocated."),
        ("status", "Required (not kitted yet, allocated 0), Allocated (allocated equals required, not fully installed), Installed (installed equals required), or Missing (kitting ran and allocated is still below required)."),
    ]),
    ("inventory_transactions.csv", "transaction_id", [
        ("transaction_id", "Primary key. TX00001 and up, assigned in timestamp order."),
        ("timestamp", "When the movement posted, ISO-8601 with -05:00 offset."),
        ("part_id", "Foreign key to parts.part_id."),
        ("quantity", "Positive quantity for every type except Adjustment, where it is a signed on-hand delta."),
        ("transaction_type", "Received, Transfer, Issued, Reserved, Installed, Returned, Scrapped, or Adjustment."),
        ("from_location_type", "Supplier, Warehouse, Van, Job, or CustomerSite."),
        ("from_location_id", "Source id. SUP-NORTHWIND and SCRAP are external party codes, not warehouses."),
        ("to_location_type", "Supplier, Warehouse, Van, Job, or CustomerSite."),
        ("to_location_id", "Destination id."),
        ("technician_id", "Technician who checked the part out or installed it. Blank when no person was involved. Foreign key when set."),
        ("van_id", "Van involved. Blank otherwise. Foreign key when set."),
        ("job_id", "Job involved. Blank otherwise. Foreign key when set."),
        ("notes", "Human-readable reason. The P001 discrepancy note matches alert AL008."),
    ]),
    ("job_events.csv", "event_id", [
        ("event_id", "Primary key. JE00001 and up."),
        ("job_id", "Foreign key to jobs.job_id."),
        ("timestamp", "When the event happened."),
        ("event_type", "Created, Assigned, Technician Dispatched, En Route, Arrived Onsite, Diagnosis, Part Required, Waiting for Parts, Repair Started, Repair Completed, Customer Signoff, Job Completed, or Escalated."),
        ("technician_id", "Technician on the event. Blank before a person is involved."),
        ("notes", "What happened. Waiting for Parts notes explain delays."),
    ]),
    ("vehicle_events.csv", "event_id", [
        ("event_id", "Primary key. VE00001 and up."),
        ("van_id", "Foreign key to vans.van_id."),
        ("timestamp", "When the vehicle event posted."),
        ("event_type", "Check In, Check Out, Maintenance, Inspection, Warning, Repair, or Fuel/Charge."),
        ("mileage", "Odometer after the event. Non-decreasing for each van."),
        ("notes", "What the event was."),
    ]),
    ("schedules.csv", "schedule_id", [
        ("schedule_id", "Primary key. SC00001 and up."),
        ("date", "Local date, YYYY-MM-DD."),
        ("technician_id", "Foreign key to technicians.technician_id. Unassigned jobs have no schedule row."),
        ("job_id", "Foreign key to jobs.job_id."),
        ("start_time", "Planned local start, HH:MM, America/Chicago."),
        ("end_time", "Planned local end, HH:MM. Back-to-back windows touch but do not overlap."),
        ("location_city", "City of the customer site."),
        ("status", "Scheduled, In Progress, Completed, Missed, or Cancelled. Missed means the planned window ended and the job was still only Assigned."),
    ]),
    ("operational_alerts.csv", "alert_id", [
        ("alert_id", "Primary key. AL001 and up."),
        ("alert_type", "Low Inventory, Out of Stock, Missing Job Parts, Technician Delayed, Van Offline, Maintenance Due, Job Overdue, Inventory Discrepancy, or Unassigned Critical Job."),
        ("severity", "Low, Medium, High, or Critical."),
        ("created_at", "When the alert was raised."),
        ("entity_type", "Job, Part, Technician, Van, or Warehouse."),
        ("entity_id", "Id of that entity. Always exists in the matching table."),
        ("description", "What is wrong, with the ids a dispatcher would need."),
        ("status", "Open, Acknowledged, or Resolved. 'Right now' means status = Open."),
        ("recommended_action", "Suggested next step for the demo."),
    ]),
]


def validate(world: World) -> list[str]:
    errors: list[str] = []

    def check(condition: bool, message: str) -> None:
        if not condition:
            errors.append(message)

    techs, vans, parts = world.techs, world.vans, world.parts
    sites, warehouses, jobs = world.sites, world.warehouses, world.jobs

    check(len(techs) == 30 and set(techs) == {f"T{i:03d}" for i in range(1, 31)}, "technician count/ids")
    check(len(vans) == 20 and set(vans) == {f"V{i:03d}" for i in range(1, 21)}, "van count/ids")
    check(len(warehouses) == 3 and set(warehouses) == {"W001", "W002", "W003"}, "warehouse ids")
    check(len(sites) == 50 and set(sites) == {f"C{i:03d}" for i in range(1, 51)}, "site ids")
    check(len(jobs) == 100 and set(jobs) == {f"J{i:03d}" for i in range(1, 101)}, "job ids")
    check(len(parts) == 32 and set(parts) == {f"P{i:03d}" for i in range(1, 33)}, "part ids")
    check(parts["P001"]["category"] == "Battery", "P001 must be a battery")

    for tech in techs.values():
        check(tech["status"] in TECH_STATUSES, f"bad tech status {tech['technician_id']}")
        if tech["assigned_van_id"]:
            check(tech["assigned_van_id"] in vans, f"bad van on {tech['technician_id']}")
        if tech["current_job_id"]:
            check(tech["current_job_id"] in jobs, f"bad job on {tech['technician_id']}")
        check(bool(tech["current_job_id"]) == (tech["status"] in {"On Job", "En Route"}), f"current job vs status {tech['technician_id']}")
        parse_ts(tech["last_location_timestamp"])

    van_to_tech = {}
    for tech in techs.values():
        if not tech["assigned_van_id"]:
            continue
        check(tech["assigned_van_id"] not in van_to_tech, f"van double-booked {tech['assigned_van_id']}")
        van_to_tech[tech["assigned_van_id"]] = tech["technician_id"]
    for van in vans.values():
        check(van["status"] in VAN_STATUSES, f"bad van status {van['van_id']}")
        check(van["home_warehouse_id"] in warehouses, f"bad home warehouse {van['van_id']}")
        assigned = van["assigned_technician_id"]
        if assigned:
            check(assigned in techs, f"bad tech on {van['van_id']}")
            check(van_to_tech.get(van["van_id"]) == assigned, f"asymmetric assignment {van['van_id']}")
        else:
            check(van["van_id"] not in van_to_tech, f"tech points at unassigned van {van['van_id']}")
        if assigned:
            tech = techs[assigned]
            check(tech["current_latitude"] == van["current_latitude"], f"van lat {van['van_id']}")
            check(tech["current_longitude"] == van["current_longitude"], f"van lon {van['van_id']}")
            check(tech["current_city"] == van["current_city"], f"van city {van['van_id']}")

    for row in world.wh_rows:
        check(row["warehouse_id"] in warehouses, "bad warehouse inventory fk")
        check(row["part_id"] in parts, "bad part on warehouse inventory")
        check(
            row["quantity_available"] == row["quantity_on_hand"] - row["quantity_reserved"],
            f"available math {row['warehouse_id']} {row['part_id']}",
        )
        check(row["quantity_available"] >= 0, f"negative available {row['warehouse_id']} {row['part_id']}")
        parse_ts(row["last_counted_at"])
    wh_keys = [(row["warehouse_id"], row["part_id"]) for row in world.wh_rows]
    check(len(wh_keys) == len(set(wh_keys)), "duplicate warehouse inventory")
    loc_keys = [(row["warehouse_id"], row["part_id"]) for row in world.wh_locs]
    check(set(loc_keys) == set(wh_keys), "bin rows do not match inventory rows")

    for row in world.van_rows:
        check(row["van_id"] in vans and row["part_id"] in parts, "bad van inventory fk")
        check(row["quantity"] > 0, "zero van row should have been omitted")
        parse_ts(row["last_inventory_check"])
    van_keys = [(row["van_id"], row["part_id"]) for row in world.van_rows]
    check(len(van_keys) == len(set(van_keys)), "duplicate van inventory")

    parts_by_job = defaultdict(list)
    for row in world.job_parts:
        check(row["job_id"] in jobs and row["part_id"] in parts, "bad job part fk")
        check(row["status"] in JP_STATUSES, f"bad part status {row['job_part_id']}")
        required, allocated, installed = row["required_quantity"], row["allocated_quantity"], row["installed_quantity"]
        check(installed <= allocated <= required, f"part qty {row['job_id']} {row['part_id']}")
        if row["status"] == "Missing":
            check(allocated < required, f"Missing but not short {row['job_id']} {row['part_id']}")
        elif row["status"] == "Required":
            check(allocated == 0 and installed == 0, f"Required row not unallocated {row['job_id']}")
        elif row["status"] == "Allocated":
            check(allocated == required and installed < required, f"Allocated row inconsistent {row['job_id']} {row['part_id']}")
        elif row["status"] == "Installed":
            check(installed == required == allocated, f"Installed row inconsistent {row['job_id']} {row['part_id']}")
        parts_by_job[row["job_id"]].append(row)

    events_by_job = defaultdict(list)
    for event in world.job_events:
        check(event["job_id"] in jobs, "bad job event fk")
        check(event["event_type"] in EVENT_TYPES, f"bad event type {event['event_type']}")
        if event["technician_id"]:
            check(event["technician_id"] in techs, "bad event tech")
        parse_ts(event["timestamp"])
        events_by_job[event["job_id"]].append(event)
    for job_id, events in events_by_job.items():
        ordered = sorted(events, key=lambda row: row["timestamp"])
        check([row["timestamp"] for row in events] == [row["timestamp"] for row in ordered], f"events not sorted {job_id}")
        stamps = [row["timestamp"] for row in ordered]
        check(all(stamps[i] < stamps[i + 1] for i in range(len(stamps) - 1)), f"event times not increasing {job_id}")
        check(ordered[0]["event_type"] == "Created", f"first event {job_id}")
        check(ordered[0]["timestamp"] == jobs[job_id]["created_at"], f"created_at mismatch {job_id}")
        have = [row["event_type"] for row in ordered]
        check(_subsequence(STATUS_SEQUENCE[jobs[job_id]["status"]], have), f"events do not match status {job_id} {jobs[job_id]['status']}")

    for job in jobs.values():
        check(job["customer_id"] in sites, f"bad customer {job['job_id']}")
        check(job["job_type"] in JOB_TYPES, f"bad type {job['job_id']}")
        check(job["priority"] in PRIORITIES, f"bad priority {job['job_id']}")
        check(job["status"] in JOB_STATUSES, f"bad job status {job['job_id']}")
        parse_ts(job["scheduled_start"])
        parse_ts(job["scheduled_end"])
        parse_ts(job["created_at"])
        check(job["created_at"] <= job["scheduled_start"], f"created after start {job['job_id']}")
        check(job["scheduled_start"] < job["scheduled_end"], f"bad window {job['job_id']}")
        check(bool(job["technician_id"]) == bool(job["van_id"]), f"tech/van pair {job['job_id']}")
        if job["technician_id"]:
            check(job["technician_id"] in techs, f"bad job tech {job['job_id']}")
        if job["van_id"]:
            check(job["van_id"] in vans, f"bad job van {job['job_id']}")
        if job["status"] in OPEN_STATUSES and job["technician_id"]:
            check(
                techs[job["technician_id"]]["assigned_van_id"] == job["van_id"],
                f"open job van is not the technician's current van {job['job_id']}",
            )
        if job["status"] == "Completed":
            check(job["actual_duration_minutes"] != "", f"completed without duration {job['job_id']}")
        else:
            check(job["actual_duration_minutes"] == "", f"open job has actual duration {job['job_id']}")
        if job["status"] == "Waiting for Parts":
            check(any(row["status"] == "Missing" for row in parts_by_job[job["job_id"]]), f"waiting without missing part {job['job_id']}")
            notes = " ".join(row["notes"] for row in events_by_job[job["job_id"]] if row["event_type"] == "Waiting for Parts")
            check("delay" in notes.lower() or "Delayed" in notes, f"waiting note missing delay reason {job['job_id']}")

    for row in world.locations:
        check(row["technician_id"] in techs, "bad location tech")
        check(row["status"] in TECH_STATUSES, "bad location status")
        if row["job_id"]:
            check(row["job_id"] in jobs, "bad location job")
            check(jobs[row["job_id"]]["technician_id"] == row["technician_id"], f"location job not assigned to tech {row['location_event_id']}")
        parse_ts(row["timestamp"])
    latest = {}
    for row in world.locations:
        current = latest.get(row["technician_id"])
        if current is None or row["timestamp"] > current["timestamp"]:
            latest[row["technician_id"]] = row
    check(set(latest) == set(techs), "missing location history")
    for tech_id, tech in techs.items():
        row = latest[tech_id]
        check(row["latitude"] == tech["current_latitude"], f"latest lat {tech_id}")
        check(row["longitude"] == tech["current_longitude"], f"latest lon {tech_id}")
        check(row["city"] == tech["current_city"], f"latest city {tech_id}")
        check(row["status"] == tech["status"], f"latest status {tech_id}")
        check(row["job_id"] == tech["current_job_id"], f"latest job {tech_id}")
        check(row["timestamp"] == tech["last_location_timestamp"], f"latest timestamp {tech_id}")

    miles = defaultdict(list)
    for row in world.vehicle_events:
        check(row["van_id"] in vans, "bad vehicle event van")
        check(row["event_type"] in VEH_TYPES, "bad vehicle event type")
        parse_ts(row["timestamp"])
        miles[row["van_id"]].append(row)
    for van_id, rows in miles.items():
        ordered = sorted(rows, key=lambda row: row["timestamp"])
        readings = [row["mileage"] for row in ordered]
        check(readings == sorted(readings), f"mileage decreased {van_id}")
        check(ordered[-1]["mileage"] == vans[van_id]["mileage"], f"mileage snapshot {van_id}")

    for row in world.schedules:
        check(row["technician_id"] in techs, "bad schedule tech")
        check(row["job_id"] in jobs, "bad schedule job")
        check(jobs[row["job_id"]]["technician_id"] == row["technician_id"], f"schedule tech {row['schedule_id']}")
        datetime.strptime(row["date"], "%Y-%m-%d")
        datetime.strptime(row["start_time"], "%H:%M")
        datetime.strptime(row["end_time"], "%H:%M")
        check(row["start_time"] < row["end_time"], f"bad schedule window {row['schedule_id']}")
        if row["date"] == TODAY and techs[row["technician_id"]]["status"] == "Off Duty":
            check(row["end_time"] <= techs[row["technician_id"]]["shift_end"], f"off-duty tech scheduled late {row['schedule_id']}")
    by_person = defaultdict(list)
    for row in world.schedules:
        by_person[(row["technician_id"], row["date"])].append(row)
    for key, rows in by_person.items():
        ordered = sorted(rows, key=lambda row: row["start_time"])
        for left, right in zip(ordered, ordered[1:]):
            check(left["end_time"] <= right["start_time"], f"overlapping schedule {key}")

    for tx in world.ledger.txs:
        check(tx["part_id"] in parts, "bad tx part")
        check(tx["transaction_type"] in TX_TYPES, "bad tx type")
        check(tx["from_location_type"] in LOC_TYPES and tx["to_location_type"] in LOC_TYPES, "bad location type")
        parse_ts(tx["timestamp"])
        if tx["transaction_type"] != "Adjustment":
            check(tx["quantity"] > 0, f"non-adjustment qty {tx['transaction_id']}")
        for field, table in (("technician_id", techs), ("van_id", vans), ("job_id", jobs)):
            if tx[field]:
                check(tx[field] in table, f"bad tx {field} {tx['transaction_id']}")
        for side in ("from", "to"):
            kind = tx[f"{side}_location_type"]
            value = tx[f"{side}_location_id"]
            if kind == "Warehouse":
                check(value in warehouses, f"bad tx warehouse {tx['transaction_id']}")
            elif kind == "Van":
                check(value in vans, f"bad tx van loc {tx['transaction_id']}")
            elif kind == "Job":
                check(value in jobs, f"bad tx job loc {tx['transaction_id']}")
            elif kind == "CustomerSite":
                check(value in sites, f"bad tx site {tx['transaction_id']}")
            elif kind == "Supplier":
                check(value in {"SUP-NORTHWIND", "SCRAP"}, f"bad supplier code {value}")

    for alert in world.alerts:
        check(alert["alert_type"] in ALERT_TYPES, "bad alert type")
        check(alert["severity"] in SEVERITIES, "bad severity")
        parse_ts(alert["created_at"])
        table = {"Job": jobs, "Part": parts, "Technician": techs, "Van": vans, "Warehouse": warehouses}[alert["entity_type"]]
        check(alert["entity_id"] in table, f"alert entity missing {alert['alert_id']}")

    # Demo edge cases -------------------------------------------------------
    check(techs["T001"]["status"] == "On Job" and techs["T001"]["current_job_id"] == "J001", "T001 story")
    check(techs["T001"]["assigned_van_id"] == "V001", "T001 van")
    check(world.van_qty("V001", "P018") == 0, "V001 should not carry P018")
    check(world.van_qty("V001", "P001") >= 1, "V001 should carry P001")
    j001_parts = {row["part_id"]: row for row in parts_by_job["J001"]}
    check(j001_parts["P018"]["status"] == "Missing", "J001 missing P018")
    check(not _covers(world, "V001", "J001"), "V001 should not cover J001")
    check(_covers(world, "V004", "J010"), "V004 should cover J010")
    check(jobs["J010"]["priority"] == "Critical" and jobs["J010"]["technician_id"] == "", "J010 unassigned critical")
    check(vans["V018"]["status"] == "Maintenance" and vans["V018"]["assigned_technician_id"] == "", "V018 shop")
    check(vans["V020"]["status"] == "Available" and vans["V020"]["assigned_technician_id"] == "", "V020 spare")
    check(vans["V020"]["current_latitude"] == warehouses["W003"]["latitude"], "V020 not at home warehouse")
    check(vans["V019"]["next_maintenance_date"] <= "2026-10-15", "V019 maintenance date")
    check(any(row["van_id"] == "V019" and row["event_type"] == "Warning" for row in world.vehicle_events), "V019 warning")
    check(any(row["van_id"] == "V007" and row["event_type"] == "Warning" for row in world.vehicle_events), "V007 warning")

    p001_tx = [tx for tx in world.ledger.txs if tx["part_id"] == "P001"]
    p001_types = [tx["transaction_type"] for tx in p001_tx]
    check(p001_tx == sorted(p001_tx, key=lambda tx: tx["timestamp"]), "P001 not sorted")
    for needed in ("Received", "Transfer", "Issued", "Installed", "Reserved", "Adjustment"):
        check(needed in p001_types, f"P001 chain missing {needed}")
    check(any(tx["transaction_type"] == "Issued" and tx["technician_id"] == "T001" for tx in p001_tx), "T001 checkout")
    check(world.ledger.wh[("W001", "P001")] != world.ledger.wh[("W002", "P001")], "P001 stock should differ by warehouse")
    check(("W001", "P001") in {(row["warehouse_id"], row["part_id"]) for row in world.wh_locs}, "P001 bin")

    long_onsite = _long_onsite(world)
    check(len(long_onsite) >= 2, f"need two long onsite techs, found {long_onsite}")
    check({"T001", "T002", "T010"} <= set(long_onsite), f"expected T001 T002 T010 onsite long, found {long_onsite}")

    urgent_site = sites["C010"]
    available = [tech for tech in techs.values() if tech["status"] == "Available"]
    check(available, "no available techs")
    closest = min(available, key=lambda tech: haversine_km(tech["current_latitude"], tech["current_longitude"], urgent_site["latitude"], urgent_site["longitude"]))
    distance = haversine_km(closest["current_latitude"], closest["current_longitude"], urgent_site["latitude"], urgent_site["longitude"])
    check(closest["technician_id"] == "T004" and distance < 5, f"closest available to J010 is {closest['technician_id']} at {distance:.2f} km")
    closest_van = min(vans.values(), key=lambda van: haversine_km(van["current_latitude"], van["current_longitude"], urgent_site["latitude"], urgent_site["longitude"]))
    check(closest_van["van_id"] == "V004", f"closest van is {closest_van['van_id']}")

    check(any(row["status"] == "Open" for row in world.alerts), "no open alerts")
    open_types = {row["alert_type"] for row in world.alerts if row["status"] == "Open"}
    for needed in ("Unassigned Critical Job", "Missing Job Parts", "Out of Stock", "Low Inventory", "Maintenance Due", "Technician Delayed", "Inventory Discrepancy", "Job Overdue", "Van Offline"):
        check(needed in open_types, f"missing open alert {needed}")

    today_at_site = [job["job_id"] for job in jobs.values() if job["customer_id"] == TODAY_SITE and job["scheduled_date"] == TODAY and job["status"] == "Completed"]
    check(today_at_site == [TODAY_SITE_JOB], f"today at C020 should be J021 only, found {today_at_site}")
    check(any(job["scheduled_date"] == TOMORROW for job in jobs.values()), "no tomorrow jobs")

    low = [row for row in world.wh_rows if 0 < row["quantity_available"] < row["reorder_point"]]
    oos = [row for row in world.wh_rows if row["quantity_on_hand"] == 0]
    over = [row for row in world.wh_rows if row["quantity_on_hand"] >= 2 * parts[row["part_id"]]["preferred_stock_level"]]
    check(low, "no low-stock row")
    check(oos, "no out-of-stock row")
    check(over, "no overstock row")
    check(any(row["warehouse_id"] == "W001" and row["part_id"] == "P006" and row["quantity_on_hand"] == 0 for row in oos), "P006 not OOS at W001")
    check(world._available("W002", "P006") > 0, "P006 should be available at W002")
    check(all(tx["transaction_type"] in TX_TYPES for tx in world.ledger.txs), "tx types")
    check({tx["transaction_type"] for tx in world.ledger.txs} == TX_TYPES, "not every transaction type is present")

    battery_wh = defaultdict(int)
    part_category = {part["part_id"]: part["category"] for part in parts.values()}
    for row in world.wh_rows:
        if part_category[row["part_id"]] == "Battery":
            battery_wh[row["warehouse_id"]] += row["quantity_available"]
    check(len(battery_wh) == 3 and len(set(battery_wh.values())) > 1, f"battery availability not varied {dict(battery_wh)}")

    return errors


def _covers(world: World, van_id: str, job_id: str) -> bool:
    needed = [row for row in world.job_parts if row["job_id"] == job_id]
    return all(world.van_qty(van_id, row["part_id"]) >= row["required_quantity"] for row in needed)


def _shorts(world: World, van_id: str, job_id: str) -> list[str]:
    shorts = []
    for row in world.job_parts:
        if row["job_id"] != job_id:
            continue
        have = world.van_qty(van_id, row["part_id"])
        if have < row["required_quantity"]:
            shorts.append(f"{row['part_id']} need {row['required_quantity']} have {have}")
    return shorts


def _long_onsite(world: World) -> list[str]:
    arrived = {}
    completed = set()
    for event in world.job_events:
        if event["event_type"] == "Arrived Onsite":
            arrived[event["job_id"]] = event["timestamp"]
        if event["event_type"] == "Job Completed":
            completed.add(event["job_id"])
    found = []
    for tech in world.techs.values():
        job_id = tech["current_job_id"]
        if tech["status"] == "On Job" and job_id and job_id not in completed and arrived.get(job_id, "9999") <= ONSITE_CUTOFF:
            found.append(tech["technician_id"])
    return found


def _fully_kitted(world: World) -> list[str]:
    grouped = defaultdict(list)
    for row in world.job_parts:
        grouped[row["job_id"]].append(row)
    ready = []
    for job_id, rows in grouped.items():
        if rows and all(row["status"] in {"Allocated", "Installed"} and row["allocated_quantity"] >= row["required_quantity"] for row in rows):
            ready.append(job_id)
    return sorted(ready)


def _jobs_with_status(world: World, status: str) -> list[str]:
    return sorted(job_id for job_id, job in world.jobs.items() if job["status"] == status)


def _missing_jobs(world: World) -> list[str]:
    return sorted({row["job_id"] for row in world.job_parts if row["status"] == "Missing"})


def collect_facts(world: World) -> dict[str, str]:
    def names(ids: list[str]) -> str:
        return ", ".join(f"{tech_id} {world.techs[tech_id]['name']}" for tech_id in ids)

    available = sorted(tech["technician_id"] for tech in world.techs.values() if tech["status"] == "Available")
    site = world.sites["C010"]
    available_dist = sorted(
        (
            (
                haversine_km(world.techs[tech_id]["current_latitude"], world.techs[tech_id]["current_longitude"], site["latitude"], site["longitude"]),
                tech_id,
            )
            for tech_id in available
        )
    )
    van_dist = sorted(
        (
            haversine_km(van["current_latitude"], van["current_longitude"], site["latitude"], site["longitude"]),
            van["van_id"],
        )
        for van in world.vans.values()
    )
    masters = sorted(tech_id for tech_id, tech in world.techs.items() if "Battery Installation Master" in tech["certifications"])
    v001_parts = [
        f"{row['part_id']} x{row['quantity']}"
        for row in world.van_rows
        if row["van_id"] == "V001"
    ]
    battery = defaultdict(int)
    for row in world.wh_rows:
        if world.parts[row["part_id"]]["category"] == "Battery":
            battery[row["warehouse_id"]] += row["quantity_available"]
    low = [f"{row['warehouse_id']} {row['part_id']} available {row['quantity_available']} reorder {row['reorder_point']}" for row in world.wh_rows if 0 < row["quantity_available"] < row["reorder_point"]]
    oos = [f"{row['warehouse_id']} {row['part_id']}" for row in world.wh_rows if row["quantity_on_hand"] == 0]
    over = [
        f"{row['warehouse_id']} {row['part_id']} on hand {row['quantity_on_hand']} preferred {world.parts[row['part_id']]['preferred_stock_level']}"
        for row in world.wh_rows
        if row["quantity_on_hand"] >= 2 * world.parts[row["part_id"]]["preferred_stock_level"]
    ]
    reserved = [f"{row['warehouse_id']} {row['part_id']} reserved {row['quantity_reserved']}" for row in world.wh_rows if row["quantity_reserved"] > 0]
    p001_locs = [
        f"{row['warehouse_id']} aisle {row['aisle']} shelf {row['shelf']} bin {row['bin']}"
        for row in world.wh_locs
        if row["part_id"] == "P001"
    ]
    p001_holders = sorted({row["van_id"] for row in world.van_rows if row["part_id"] == "P001"})
    holder_text = ", ".join(
        f"{van_id} ({world.vans[van_id]['assigned_technician_id']} {world.techs[world.vans[van_id]['assigned_technician_id']]['name']})"
        for van_id in p001_holders
    )
    kitted = _fully_kitted(world)
    kitted_open = [job_id for job_id in kitted if world.jobs[job_id]["status"] != "Completed"]
    open_alerts = [f"{row['alert_id']} {row['alert_type']} {row['severity']} {row['entity_type']} {row['entity_id']}" for row in world.alerts if row["status"] == "Open"]
    maint = [
        f"{van['van_id']} {van['maintenance_status']} next {van['next_maintenance_date']}"
        for van in world.vans.values()
        if van["maintenance_status"] != "OK" or van["next_maintenance_date"] <= "2026-10-15"
    ]
    available_vans = sorted(van["van_id"] for van in world.vans.values() if van["status"] == "Available")
    tomorrow_lines = [row for row in world.job_parts if world.jobs[row["job_id"]]["scheduled_date"] == TOMORROW]
    return {
        "available": names(available),
        "closest_tech": f"{available_dist[0][1]} {world.techs[available_dist[0][1]]['name']} ({available_dist[0][0]:.2f} km)",
        "closest_van": f"{van_dist[0][1]} ({van_dist[0][0]:.2f} km)",
        "masters": ", ".join(masters),
        "t001_where": (
            f"{world.techs['T001']['current_city']} at {world.sites['C001']['site_name']} "
            f"({_fmt_coord(world.techs['T001']['current_latitude'])}, {_fmt_coord(world.techs['T001']['current_longitude'])}), "
            f"status {world.techs['T001']['status']}, job J001, ping {world.techs['T001']['last_location_timestamp']}"
        ),
        "v001_where": (
            f"{world.vans['V001']['current_city']} ({_fmt_coord(world.vans['V001']['current_latitude'])}, "
            f"{_fmt_coord(world.vans['V001']['current_longitude'])}), status {world.vans['V001']['status']}, "
            f"with {world.vans['V001']['assigned_technician_id']}"
        ),
        "v001_parts": ", ".join(v001_parts),
        "j001_short": "; ".join(_shorts(world, "V001", "J001")),
        "available_vans": ", ".join(available_vans),
        "in_progress": ", ".join(_jobs_with_status(world, "In Progress")),
        "waiting": ", ".join(_jobs_with_status(world, "Waiting for Parts")),
        "missing": ", ".join(_missing_jobs(world)),
        "unassigned_critical": ", ".join(
            job_id for job_id, job in world.jobs.items() if job["priority"] == "Critical" and not job["technician_id"]
        ),
        "batteries": ", ".join(f"{wh} {battery[wh]}" for wh in ("W001", "W002", "W003")),
        "p001_locs": "; ".join(p001_locs),
        "p001_stock": ", ".join(
            f"{wh} on hand {world.ledger.wh[(wh, 'P001')]} "
            f"reserved {world.ledger.res.get((wh, 'P001'), 0)} available {world._available(wh, 'P001')}"
            for wh in ("W001", "W002", "W003")
        ),
        "low": "; ".join(low),
        "oos": "; ".join(oos),
        "over": "; ".join(over),
        "reserved": "; ".join(reserved),
        "holders": holder_text,
        "kitted": ", ".join(kitted_open),
        "kitted_completed_count": str(len(kitted) - len(kitted_open)),
        "tomorrow_count": str(len(tomorrow_lines)),
        "tomorrow_jobs": ", ".join(sorted({row["job_id"] for row in tomorrow_lines})),
        "open_alerts": "; ".join(open_alerts),
        "maint": "; ".join(sorted(maint)),
        "long_onsite": ", ".join(_long_onsite(world)),
        "p001_types": " -> ".join(tx["transaction_type"] for tx in world.ledger.txs if tx["part_id"] == "P001"),
        "tech_count": "30",
        "van_count": "20",
        "wh_count": "3",
        "site_count": "50",
        "job_count": "100",
        "part_count": "32",
    }


def render_readme(world: World, facts: dict[str, str], counts: dict[str, int]) -> str:
    count_lines = "\n".join(f"| `{name}` | {counts[name]} |" for name in counts)
    return f"""# Lumenfield Energy field operations (synthetic)

Synthetic snapshot for an Operations Knowledge Platform demo. Lumenfield Energy is a fictional battery and backup-power field service. Nothing in this folder is a real person, customer, address, phone number, VIN, or surveyed building.

The clock is **2026-09-27 16:00 America/Chicago** (stored as `-05:00`, which is Central Daylight Time on this date). Tomorrow for scheduling questions is **2026-09-28**.

Regenerate every CSV from the shared model:

```bash
python3 scripts/generate_field_ops.py
```

The script refuses to write if a relationship check fails. It does not touch `data/corpus/`.

## Assumptions that change query results

- Timestamps are local America/Chicago with a fixed `-05:00` offset. Do not convert them to UTC before comparing.
- `technicians.shift_start` and `shift_end` are the Sunday 2026-09-27 shift. Monday rows in `schedules.csv` use a normal daytime window even when that technician's Sunday shift ended at 14:00.
- **Van inventory omits zero rows.** If a van has no row for a part, quantity on hand is 0. Every row that does exist was counted at `last_inventory_check` (a full-van count). `quantity` is physical on-hand and still includes units reserved to a job.
- **Warehouse inventory keeps zero rows** when a depot stocks that bin but the count is empty. No `warehouse_inventory` row means the depot does not stock that part.
- `quantity_available = quantity_on_hand - quantity_reserved` on every warehouse row.
- `job_parts.status = Required` means the line is demand only (`allocated_quantity` 0). `Missing` means kitting already failed (`allocated_quantity < required_quantity`). `Allocated` and `Installed` lines have `allocated_quantity = required_quantity`.
- A job is **fully kitted** when it has at least one part line and every line is `Allocated` or `Installed`. That can be a warehouse reservation (`inventory_transactions` type `Reserved`) rather than units already on the van. "Does this van have everything for this job?" compares `van_inventory` to `required_quantity`, not to `job_parts.status`.
- Open jobs (`Scheduled`, `Assigned`, `En Route`, `Onsite`, `In Progress`, `Waiting for Parts`) that name both a technician and a van use that technician's current `assigned_van_id`. Completed jobs record the van used that day; in this file those vans still match the technician's current assignment.
- `schedules.csv` stores the planned window. A crew can still be onsite after `end_time`. Unassigned jobs have **no schedule row**.
- `vans.last_check_in` is the vehicle gateway. `technician_locations` is the technician phone. Those clocks can differ. V012's gateway is stale while T012's phone is current.
- `actual_duration_minutes` is minutes from `Arrived Onsite` to `Job Completed`. It is blank on every job that is not `Completed`.
- Onsite longer than two hours means `technicians.status = On Job`, the job has an `Arrived Onsite` event at or before 2026-09-27 14:00, and the job is not completed. Snapshot time is 16:00.
- Closest technician or van is haversine distance on the current latitude and longitude.
- Battery availability is `SUM(quantity_available)` for parts whose `category` is `Battery`, grouped by warehouse.
- `SUP-NORTHWIND` and `SCRAP` are external party codes on transactions. They are not warehouse ids.
- Adjustment `quantity` is a signed on-hand delta. Every other transaction quantity is positive.
- Coordinates are fictional points in the named city. They are not street addresses.

## Demo spine

| Story | Ids |
| --- | --- |
| Technician on a job, with a van and a live location | T001 Rowan Pell, van V001, job J001, site C001 Copper Lantern Home in Round Rock. Onsite since 12:10. |
| Van does **not** have everything for its job | V001 is short {facts['j001_short']}. Answer to "does V001 have everything for J001?" is **no**. |
| Critical part present on that same van | V001 is carrying P001 (LumenPack module) and other critical parts. P018 is the missing critical fuse. |
| Urgent unassigned job and who should take it | J010 Critical Emergency Service at C010 Prairie Switch Backup, Pflugerville, start 16:30, no technician. Closest available technician is {facts['closest_tech']}. Closest van is {facts['closest_van']}. T004 holds Battery Installation Master and V004 already carries P001, P018, and P012. |
| Second available person nearby, not the right dispatch | T018 Ada Moss is Available in Pflugerville with no van and no Master certification. |
| Delayed job and why | J007 at C007 Cedar Kettle Works. T010 has been onsite since 13:00. Waiting-for-parts note: P006 is not on V010, W001 is out of stock, **W002 should supply the job**. |
| Overdue assigned job | J030 inspection at C025 Hollow Oak Bakery, window 13:00-15:00, still Assigned to T009. Schedule status is Missed. |
| What happened at a site today | C020 Mesquite Switch House. The only 2026-09-27 job is J021, completed by T005 Cassio Venn (van V005). Full event chain is on that job. |
| Chain of custody for the battery | P001 transactions, in order: {facts['p001_types']}. Checkout to ask for first is T001 Rowan Pell, Issued to V001 on 2026-09-15. |
| Where P001 sits | {facts['p001_locs']}. Stock is not equal across depots: {facts['p001_stock']}. |
| Discrepancy | Adjustment on P001 at W003 on 2026-09-25, bin C / 02 / 07, and open alert AL008. |
| Who physically has a P001 right now | {facts['holders']}. |
| Shop van, due-soon van, spare van | V018 In Shop at W001, unassigned (T028 is off duty and is not linked as the driver). V019 Due Soon on 2026-10-08 with a Warning, still with T021. V007 Due Soon on 2026-10-12. V020 Available, no driver, parked on the W003 coordinates. |
| Offline gateway | V012 last check-in 2026-09-26 17:10. Alert AL010. |
| Onsite more than two hours | {facts['long_onsite']}. |
| Warehouses | W001 Mesa Volt Depot, Austin, manager Orla Mint. W002 Brushy Creek Parts Hub, Round Rock, manager Galen Moss. W003 Bluebonnet Service Warehouse, Georgetown, manager Ida Barrow. |

## Datasets

Primary keys, foreign keys, and row counts. Row counts exclude the header.

| File | Rows |
| --- | ---: |
{count_lines}

### technicians.csv

Primary key `technician_id`. Foreign keys: `assigned_van_id` to `vans.van_id` (blank allowed), `current_job_id` to `jobs.job_id` (blank allowed). One technician has at most one van. Status, skills, and certifications are the personnel columns. Current coordinates are the 16:00 snapshot (or the shift-end ping for someone already Off Duty).

### technician_locations.csv

Primary key `location_event_id`. Foreign keys: `technician_id`, and `job_id` when set. The latest row for each technician matches `technicians` latitude, longitude, city, status, and current job. Earlier rows on 2026-09-27 are the trail (yard, en route, onsite, completed).

### vans.csv

Primary key `van_id`. Foreign keys: `assigned_technician_id` to `technicians.technician_id` (blank allowed), `home_warehouse_id` to `warehouses.warehouse_id`. Assignment is one-to-one with `technicians.assigned_van_id`. When a technician is set, the van's coordinates match that technician. `vehicle_number` is a fleet number, not a VIN. `last_check_in` is the gateway, not the phone.

### van_inventory.csv

Primary key `van_inventory_id`. Foreign keys: `van_id`, `part_id`. Absence means zero. V001's rows are the "what is in this van?" answer: {facts['v001_parts']}.

### warehouses.csv

Primary key `warehouse_id`. Three depots, three cities, all Open.

### parts.csv

Primary key `part_id`. P001 is the LumenPack 13.5 battery module, category Battery, criticality Critical. Categories cover battery, inverter, electrical, cable, connector, fuse, circuit protection, mounting hardware, sensors, and tools.

### warehouse_inventory.csv

Primary key `warehouse_inventory_id`. Foreign keys: `warehouse_id`, `part_id`. `quantity_available` is always `quantity_on_hand - quantity_reserved`. Includes healthy, low, empty, and overstocked rows. Battery available quantities: {facts['batteries']}.

### warehouse_locations.csv

Composite primary key (`warehouse_id`, `part_id`). Foreign keys to those tables. One bin per part per depot. P001 is in more than one depot: {facts['p001_locs']}.

### customer_sites.csv

Primary key `customer_id`. Fifty fictional sites. No street addresses. C049 is Offline, C050 is Commissioning, the rest are Active.

### jobs.csv

Primary key `job_id`. Foreign keys: `customer_id`, `technician_id` when set, `van_id` when set. Mix of ready work, missing parts, unassigned work, a missed window, waiting on parts, and high or critical priority. Completed jobs have `actual_duration_minutes`. Open jobs leave it blank.

### job_parts.csv

Primary key `job_part_id`. Foreign keys: `job_id`, `part_id`. This is the kit list. J001's P018 line is `Missing`. J010's lines are `Required` because nobody has kitted the unassigned emergency yet. J011's lines are `Allocated` (fully kitted for Monday).

### inventory_transactions.csv

Primary key `transaction_id`. Foreign keys: `part_id`, plus `technician_id`, `van_id`, and `job_id` when set. Location ids point at a warehouse, van, job, or the external codes `SUP-NORTHWIND` and `SCRAP`. Sort by `timestamp` to rebuild custody. The ledger is plausible (no unexplained negative on-hand). It is not a claim that every historical unit since company founding is in the file.

### job_events.csv

Primary key `event_id`. Foreign keys: `job_id`, `technician_id` when set. Event order matches job status. J007 and J001 include `Part Required` and `Waiting for Parts`. J021 includes the full chain through `Job Completed`. J010 includes `Created` and `Escalated` and was never assigned. Cancelled jobs use `Escalated` with a postponement note because there is no separate Cancelled event type.

### vehicle_events.csv

Primary key `event_id`. Foreign key `van_id`. Mileage does not go backward. V018 has Maintenance and Repair. V019 and V007 have a Warning. V012 has no check-in on 2026-09-27.

### schedules.csv

Primary key `schedule_id`. Foreign keys: `technician_id`, `job_id`. Covers 2026-09-27, 2026-09-28, earlier September completions, and a few later unassigned jobs that never appear here because they have no technician. No overlapping intervals for the same technician on the same date.

### operational_alerts.csv

Primary key `alert_id`. `entity_id` matches `entity_type`. Open alerts are the "what should I know right now?" list.

## Relationships

- Technician 1—1 van, both directions, blanks allowed on either side.
- Technician 1—many location pings, jobs, schedule rows, and events.
- Van 1—many inventory rows, vehicle events, and jobs.
- Warehouse 1—many inventory rows, bins, and vans (via `home_warehouse_id`).
- Part 1—many van rows, warehouse rows, bins, job lines, and transactions.
- Customer site 1—many jobs.
- Job 1—many part lines, events, transactions, and at most the schedule rows for its assigned technician.

## Example questions

1. **Who is currently available?** `technicians.status = Available`. Answer: {facts['available']}.
2. **Who is closest to this job?** For J010 / site C010, haversine on `technicians` current coordinates, usually filtered to Available. Answer: {facts['closest_tech']}.
3. **Which technician has the required certification?** `technicians.certifications` contains the level text. Battery Installation Master: {facts['masters']}. Electrical Master is T007 Nova Brigg. Inverter Repair Master is T013 Juniper Vale.
4. **Where is technician T001?** `technicians` plus the latest `technician_locations` row. Answer: {facts['t001_where']}.
5. **Where is van V001?** `vans`. Answer: {facts['v001_where']}.
6. **What inventory is inside van V001?** `van_inventory` where `van_id = V001`. Answer: {facts['v001_parts']}. Omitted parts are zero.
7. **Does van V001 have everything required for job J001?** Compare `van_inventory.quantity` to each `job_parts.required_quantity` for J001. Treat a missing row as zero. Answer: **no**. Short: {facts['j001_short']}.
8. **Which vans are available?** `vans.status = Available`. Answer: {facts['available_vans']}. V020 is the spare parked at its home warehouse. The others are with Available technicians.
9. **Which jobs are currently in progress?** `jobs.status = In Progress`. Answer: {facts['in_progress']}.
10. **Which jobs are waiting for parts?** `jobs.status = Waiting for Parts`. Answer: {facts['waiting']}.
11. **Which jobs are missing parts?** Any `job_parts.status = Missing`. Answer: {facts['missing']}.
12. **Which critical jobs are unassigned?** `priority = Critical` and `technician_id` blank. Answer: {facts['unassigned_critical']}.
13. **How many batteries are available in each warehouse?** Sum `warehouse_inventory.quantity_available` for `parts.category = Battery`. Answer: {facts['batteries']}.
14. **Where is part P001 located?** `warehouse_locations` for P001. Answer: {facts['p001_locs']}. Vans that currently hold one are in question 21.
15. **Which warehouse has this part?** `warehouse_inventory` with `quantity_available > 0`. P001 is in W001, W002, and W003 ({facts['p001_stock']}). P006 is available at W002 only; W001 is zero and W003 has no row.
16. **Which parts are below their reorder point?** `quantity_available < reorder_point` on `warehouse_inventory`. Low (still above zero): {facts['low']}. Out-of-stock rows are also below reorder.
17. **What parts are out of stock?** `quantity_on_hand = 0`. Answer: {facts['oos']}. A missing row is "not stocked here," which is different from an empty bin.
18. **What inventory is reserved?** `quantity_reserved > 0`. Answer: {facts['reserved']}. Matching `Reserved` transactions name the job.
19. **Where did the missing inventory go?** P001 Adjustment at W003 on 2026-09-25. The note says the module was not in bin C-02-07 and not on a van. Alert AL008 is the same story. Separately, P006 left W001 by a Transfer to W002 on 2026-09-12.
20. **Who checked out this part?** `inventory_transactions` where `transaction_type = Issued` and `technician_id` is set. For P001, T001 Rowan Pell checked two modules out to V001 on 2026-09-15. T002 and T004 also have Issued rows.
21. **Which technician currently has this equipment?** Join `van_inventory` to `vans.assigned_technician_id` where quantity is greater than zero. P001 is on {facts['holders']}.
22. **What parts are required for tomorrow's jobs?** `job_parts` joined to `jobs` where `scheduled_date = 2026-09-28`. Jobs: {facts['tomorrow_jobs']}. Line count: {facts['tomorrow_count']}.
23. **Which jobs are fully kitted?** Every part line is Allocated or Installed. Still open: {facts['kitted']}. J011 and J012 are Monday. J030 was kitted and then missed. Another {facts['kitted_completed_count']} completed jobs are kitted because every line is Installed. J001, J007, J010, and J015 are not kitted. J013, J014, and J017-J020 are still Required only.
24. **Which jobs are blocked because of missing inventory?** `jobs.status = Waiting for Parts` (each has a Missing line). Answer: {facts['waiting']}. J015 is Missing a part but is still only Assigned for Monday, so it is short, not yet blocked in the field.
25. **Which van is closest to this customer site?** Haversine from `vans` to the site. For C010 Prairie Switch Backup: {facts['closest_van']}.
26. **Which technician and van should handle this urgent job?** J010. Recommend **T004 Maren Holt and V004**: available, closest, Battery Installation Master, and the van covers P001, P018, and P012. T018 is nearer than the Austin crews but has no van.
27. **What operational issues should I know about right now?** `operational_alerts.status = Open`. Answer: {facts['open_alerts']}.
28. **Which vans need maintenance?** `maintenance_status` is Due Soon or In Shop, or `next_maintenance_date <= 2026-10-15`. Answer: {facts['maint']}.
29. **Which technicians have been onsite for more than 2 hours?** Status On Job, `Arrived Onsite` at or before 14:00, job not completed. Answer: {facts['long_onsite']}.
30. **Show me the chain of custody for this battery.** `inventory_transactions` for P001 ordered by timestamp. Sequence: {facts['p001_types']}.
31. **What happened at this customer site today?** Customer C020 Mesquite Switch House, `jobs.scheduled_date = 2026-09-27`, then `job_events` for J021. T005 replaced a 60A breaker and an MC4 pair, the customer signed off, and the job completed at 11:20.
32. **What has already been done on this job?** `job_events` for that job, in timestamp order. J021 is the finished example. J001 stops at Waiting for Parts (diagnosis done, fuse still missing). J010 was only created and escalated.
33. **Why is this job delayed?** J007. Events `Part Required`, `Waiting for Parts`, and `Escalated`. The note says P006 is not on V010, W001 is empty, and W002 has the inverter. J001 is the same pattern for P018, with W001 able to supply it.
34. **What inventory discrepancies do we have?** Alert AL008 plus the P001 Adjustment on 2026-09-25 at W003 (quantity -1). The bin is aisle C, shelf 02, bin 07.
35. **Which warehouse should supply this job?** For J007, W002, because it has P006 available and W001 does not. For J001, W001, because it has P018 available while V001 has none.

## Files

CSVs and this note live in `data/`. Field definitions for every column are in `data/data_dictionary.md`. The generator is `scripts/generate_field_ops.py`.
"""


def render_dictionary() -> str:
    lines = [
        "# Lumenfield field operations data dictionary",
        "",
        "Synthetic dataset. Snapshot 2026-09-27 16:00 America/Chicago, timestamps stored with offset `-05:00`.",
        "Controlled vocabularies and null rules are in `README.md`. Blank strings mean \"not set\" for optional foreign keys.",
        "",
    ]
    for filename, pk, fields in SCHEMAS:
        lines.append(f"## {filename}")
        lines.append("")
        lines.append(f"Primary key: `{pk}`.")
        lines.append("")
        lines.append("| Field | Meaning |")
        lines.append("| --- | --- |")
        for name, meaning in fields:
            lines.append(f"| `{name}` | {meaning} |")
        lines.append("")
    lines.append("## Location ids that are not table keys")
    lines.append("")
    lines.append("| Code | Meaning |")
    lines.append("| --- | --- |")
    lines.append("| `SUP-NORTHWIND` | Fictional parts supplier. Appears as `from_location_id` on Received transactions. |")
    lines.append("| `SCRAP` | Fictional scrap destination. Appears as `to_location_id` on Scrapped transactions. |")
    lines.append("")
    return "\n".join(lines)


def _readme_path() -> Path:
    path = DATA / "README.md"
    if not path.exists():
        return path
    current = path.read_text(encoding="utf-8")
    if "Lumenfield Energy field operations" in current:
        return path
    return DATA / "FIELD_OPS_README.md"


def write_outputs(world: World) -> tuple[dict[str, int], Path]:
    tables = {
        "technicians.csv": list(world.techs.values()),
        "technician_locations.csv": world.locations,
        "vans.csv": list(world.vans.values()),
        "van_inventory.csv": world.van_rows,
        "warehouses.csv": list(world.warehouses.values()),
        "parts.csv": list(world.parts.values()),
        "warehouse_inventory.csv": world.wh_rows,
        "warehouse_locations.csv": world.wh_locs,
        "customer_sites.csv": list(world.sites.values()),
        "jobs.csv": list(world.jobs.values()),
        "job_parts.csv": world.job_parts,
        "inventory_transactions.csv": world.ledger.txs,
        "job_events.csv": world.job_events,
        "vehicle_events.csv": world.vehicle_events,
        "schedules.csv": world.schedules,
        "operational_alerts.csv": world.alerts,
    }
    for filename, _pk, fields in SCHEMAS:
        rows = tables[filename]
        fieldnames = [name for name, _meaning in fields]
        path = DATA / filename
        if "corpus" in path.parts:
            raise SystemExit(f"Refusing to write into corpus: {path}")
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n", extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({name: _csv_value(name, row.get(name, "")) for name in fieldnames})
    counts = {filename: len(rows) for filename, rows in tables.items()}
    facts = collect_facts(world)
    readme_path = _readme_path()
    readme_path.write_text(render_readme(world, facts, counts), encoding="utf-8")
    (DATA / "data_dictionary.md").write_text(render_dictionary(), encoding="utf-8")
    counts[readme_path.name] = 1
    counts["data_dictionary.md"] = 1
    return counts, readme_path


def _csv_value(field: str, value) -> str:
    if value is None:
        return ""
    if field in {"current_latitude", "current_longitude", "latitude", "longitude"}:
        return f"{float(value):.5f}"
    if field in {"battery_capacity_kwh", "inverter_capacity_kw"}:
        return _fmt_capacity(float(value))
    return str(value)


def print_demo(world: World, facts: dict[str, str]) -> None:
    print("DEMO SCENARIOS")
    print(f"Snapshot: {NOW} America/Chicago")
    print(f"Available technicians: {facts['available']}")
    print(f"Closest available to J010 (C010): {facts['closest_tech']}")
    print(f"Closest van to C010: {facts['closest_van']}")
    print(f"Battery Installation Master: {facts['masters']}")
    print(f"T001: {facts['t001_where']}")
    print(f"V001: {facts['v001_where']}")
    print(f"V001 inventory: {facts['v001_parts']}")
    print(f"V001 covers J001: no. Short: {facts['j001_short']}")
    print(f"V004 covers J010: yes")
    print(f"In progress: {facts['in_progress']}")
    print(f"Waiting for parts: {facts['waiting']}")
    print(f"Missing-part jobs: {facts['missing']}")
    print(f"Unassigned critical: {facts['unassigned_critical']}")
    print(f"Battery available by warehouse: {facts['batteries']}")
    print(f"P001 bins: {facts['p001_locs']}")
    print(f"P001 stock: {facts['p001_stock']}")
    print(f"Below reorder (available > 0): {facts['low']}")
    print(f"Out of stock: {facts['oos']}")
    print(f"Reserved: {facts['reserved']}")
    print(f"P001 currently on: {facts['holders']}")
    print(f"Fully kitted: {facts['kitted']}")
    print(f"Tomorrow jobs: {facts['tomorrow_jobs']}")
    print(f"Onsite > 2 hours: {facts['long_onsite']}")
    print(f"Maintenance: {facts['maint']}")
    print(f"Open alerts: {facts['open_alerts']}")
    print(f"P001 custody: {facts['p001_types']}")
    print("Today at C020 Mesquite Switch House: J021 completed by T005")
    print("Delayed job: J007. Supply P006 from W002. J001 supply P018 from W001.")
    print("Discrepancy: P001 Adjustment at W003 on 2026-09-25, alert AL008")
    print(f"Validation passed. Jobs={len(world.jobs)} techs={len(world.techs)} vans={len(world.vans)}")


def main() -> int:
    world = build_world()
    errors = validate(world)
    if errors:
        print("VALIDATION FAILED")
        for message in errors:
            print(f" - {message}")
        return 1
    facts = collect_facts(world)
    print_demo(world, facts)
    counts, readme_path = write_outputs(world)
    print("WROTE")
    for filename, _pk, _fields in SCHEMAS:
        path = DATA / filename
        print(f"{path} rows={counts[filename]}")
    print(f"{readme_path} rows=1")
    print(f"{DATA / 'data_dictionary.md'} rows=1")
    if readme_path.name != "README.md":
        print("NOTE: data/README.md already existed and was left alone. Ops guide is FIELD_OPS_README.md.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
