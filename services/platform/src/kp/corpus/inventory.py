"""Fake warehouse inventory and the stored Q4 2026 forecast.

Each installation consumes one battery cabinet, one inverter, and one gateway.
September issues match the 640 installations in the performance series.
Regional shares match September grid-revenue shares. Numbers are invented.
"""

from __future__ import annotations

from kp.corpus.performance import MONTHS

WAREHOUSES = ("Houston", "Dallas", "Austin", "San Antonio")
SHARES = {"Houston": 38, "Dallas": 27, "Austin": 21, "San Antonio": 14}
SKUS = (
    ("BP-BATT-46", "46 kWh battery cabinet"),
    ("BP-INV-11", "11.5 kW hybrid inverter"),
    ("BP-GATE-1", "site gateway"),
)
AS_OF = "2026-09-30"
Q4_INSTALLS = 2100

# On hand at 2026-09-30, then scheduled Q4 receipts. Issues equal forecast installs.
ON_HAND = {
    "BP-BATT-46": {"Houston": 980, "Dallas": 620, "Austin": 340, "San Antonio": 200},
    "BP-INV-11": {"Houston": 1240, "Dallas": 820, "Austin": 500, "San Antonio": 300},
    "BP-GATE-1": {"Houston": 1500, "Dallas": 960, "Austin": 580, "San Antonio": 370},
}
Q4_RECEIPTS = {
    "BP-BATT-46": {"Houston": 720, "Dallas": 500, "Austin": 400, "San Antonio": 80},
    "BP-INV-11": {"Houston": 800, "Dallas": 600, "Austin": 450, "San Antonio": 200},
    "BP-GATE-1": {"Houston": 900, "Dallas": 650, "Austin": 500, "San Antonio": 250},
}

# Month-end BP-BATT-46 units. September matches ON_HAND. San Antonio draws down.
BATTERY_MONTH_END = {
    "2026-04": {"Houston": 720, "Dallas": 540, "Austin": 300, "San Antonio": 260},
    "2026-05": {"Houston": 760, "Dallas": 560, "Austin": 310, "San Antonio": 250},
    "2026-06": {"Houston": 810, "Dallas": 580, "Austin": 320, "San Antonio": 240},
    "2026-07": {"Houston": 860, "Dallas": 590, "Austin": 325, "San Antonio": 230},
    "2026-08": {"Houston": 920, "Dallas": 600, "Austin": 330, "San Antonio": 215},
    "2026-09": {"Houston": 980, "Dallas": 620, "Austin": 340, "San Antonio": 200},
}
SAFETY_STOCK = {"Houston": 400, "Dallas": 280, "Austin": 180, "San Antonio": 160}
# Not included in Q4_RECEIPTS. Arriving in November does not cover an October gap.
OPEN_PO = ("PO-SAT-1048", "San Antonio", "BP-BATT-46", 120, "2026-11-15")


def allocate(total: int) -> dict[str, int]:
    """Split a count by the regional shares. The parts sum to total."""
    floors = {name: total * pct // 100 for name, pct in SHARES.items()}
    remainder = total - sum(floors.values())
    fractional = sorted(
        ((total * pct / 100) - floors[name], name) for name, pct in SHARES.items()
    )
    fractional.reverse()
    for _, name in fractional:
        if remainder == 0:
            break
        floors[name] += 1
        remainder -= 1
    return floors


def monthly_issues() -> list[tuple[str, dict[str, int]]]:
    """Installations issued from each warehouse. One unit of every SKU per install."""
    return [(month, allocate(installs)) for month, _, _, _, installs, _, _, _ in MONTHS]


def q4_issues() -> dict[str, int]:
    return allocate(Q4_INSTALLS)


def projected_end(sku: str, warehouse: str) -> int:
    return ON_HAND[sku][warehouse] + Q4_RECEIPTS[sku][warehouse] - q4_issues()[warehouse]


def days_of_cover(sku: str, warehouse: str) -> int:
    september = monthly_issues()[-1][1][warehouse]
    return round(ON_HAND[sku][warehouse] / september * 30)


def inventory_documents() -> list[dict]:
    quotes = inventory_quotes()
    by_doc: dict[str, list[str]] = {}
    for quote in quotes:
        by_doc.setdefault(quote["document_id"], []).append(quote["body"])
    return [
        _document(
            "doc_wh_onhand",
            "Warehouse on-hand inventory, 30 September 2026",
            _onhand_body(by_doc["doc_wh_onhand"]),
        ),
        _document(
            "doc_wh_forecast",
            "Warehouse inventory forecast, Q4 2026",
            _forecast_body(by_doc["doc_wh_forecast"]),
        ),
        *[
            _document(doc_id, lines[0].split(".", 1)[0], "\n".join(lines))
            for doc_id, lines in sorted(by_doc.items())
            if doc_id not in {"doc_wh_onhand", "doc_wh_forecast"}
        ],
    ]


def inventory_knowledge_items() -> list[dict]:
    return [
        {
            "id": row["id"],
            "document_id": row["document_id"],
            "issue_id": None,
            "title": row["title"],
            "body": row["body"],
            "kind": row["kind"],
        }
        for row in inventory_quotes()
    ]


def inventory_quotes() -> list[dict]:
    september = monthly_issues()[-1][1]
    battery = "BP-BATT-46"
    issued = ", ".join(f"{name} {september[name]}" for name in WAREHOUSES)
    on_hand = ", ".join(f"{name} {ON_HAND[battery][name]}" for name in WAREHOUSES)
    cover = ", ".join(f"{name} {days_of_cover(battery, name)}" for name in WAREHOUSES)
    trend_parts = [f"{_month_name(month)} {sum(counts.values())}" for month, counts in monthly_issues()]
    trend = ", ".join(trend_parts[:-1]) + ", and " + trend_parts[-1]
    other_parts = [
        f"{name} {projected_end(battery, name)}" for name in WAREHOUSES if name != "San Antonio"
    ]
    others = ", ".join(other_parts[:-1]) + ", and " + other_parts[-1]
    shortfall = -projected_end(battery, "San Antonio")
    quotes = [
        _quote(
            "ki_wh00_onhand",
            "doc_wh_onhand",
            "Battery cabinets on hand",
            f"On {AS_OF} on-hand {battery} battery cabinets were {on_hand}, totaling {sum(ON_HAND[battery].values())}.",
        ),
        _quote(
            "ki_wh01_trend",
            "doc_wh_onhand",
            "Battery cabinets issued, April-September 2026",
            f"In 2026, {battery} cabinets issued were {trend}, matching installations in each month.",
        ),
        _quote(
            "ki_wh02_forecast",
            "doc_wh_forecast",
            "Q4 2026 installation forecast",
            (
                f"The stored Q4 2026 installation forecast is {Q4_INSTALLS}, or 700 a month, "
                "up from 640 installations in September 2026."
            ),
        ),
        _quote(
            "ki_wh03_short",
            "doc_wh_forecast",
            "San Antonio battery shortfall",
            (
                f"San Antonio Q4 forecast issues {q4_issues()['San Antonio']} {battery}, with "
                f"{ON_HAND[battery]['San Antonio']} on hand and {Q4_RECEIPTS[battery]['San Antonio']} receipts, "
                f"a shortfall of {shortfall} cabinets."
            ),
        ),
        _quote(
            "ki_wh04_projected",
            "doc_wh_forecast",
            "Projected battery stock outside San Antonio",
            f"Q4 projected {battery} ending stock is {others} after receipts and the forecast issues.",
        ),
        _quote(
            "ki_wh05_cover",
            "doc_wh_onhand",
            "Days of battery cover",
            f"Days of battery cover at the September issue rate were {cover}.",
        ),
        _quote(
            "ki_wh06_september",
            "doc_wh_onhand",
            "September warehouse issues",
            f"September 2026 issued {sum(september.values())} {battery} cabinets: {issued}.",
        ),
        _quote(
            "ki_wh08_month_end",
            "doc_wh_onhand",
            "Battery month-end stock",
            _month_end_sentence(),
        ),
        _quote(
            "ki_wh09_safety",
            "doc_wh_forecast",
            "Battery safety stock",
            _safety_sentence(),
        ),
        _quote(
            "ki_wh10_po",
            "doc_wh_forecast",
            "Open San Antonio battery purchase order",
            (
                f"Open {OPEN_PO[0]} is {OPEN_PO[3]} BP-BATT-46 for {OPEN_PO[1]} due {OPEN_PO[4]} "
                f"and is not included in the Q4 receipt plan of {Q4_RECEIPTS['BP-BATT-46']['San Antonio']}."
            ),
        ),
        *_warehouse_quotes(),
        _quote(
            "ki_wh07_other_skus",
            "doc_wh_onhand",
            "Inverter and gateway on hand",
            (
                f"On {AS_OF} BP-INV-11 inverters on hand were {sum(ON_HAND['BP-INV-11'].values())} "
                f"and BP-GATE-1 gateways were {sum(ON_HAND['BP-GATE-1'].values())}. "
                "Neither SKU is short in the Q4 forecast."
            ),
        ),
    ]
    for quote in quotes:
        if len(quote["body"]) > 180:
            raise ValueError(f"{quote['id']} is {len(quote['body'])} characters")
    return quotes


def _warehouse_quotes() -> list[dict]:
    quotes = []
    for name in WAREHOUSES:
        slug = name.lower().replace(" ", "_")
        battery = ON_HAND["BP-BATT-46"][name]
        inverter = ON_HAND["BP-INV-11"][name]
        gateway = ON_HAND["BP-GATE-1"][name]
        quotes.append(
            _quote(
                f"ki_wh_{slug}",
                f"doc_wh_{slug}",
                f"{name} warehouse inventory",
                (
                    f"{name} warehouse on {AS_OF} held BP-BATT-46 {battery}, "
                    f"BP-INV-11 {inverter}, and BP-GATE-1 {gateway}. "
                    f"Battery safety stock is {SAFETY_STOCK[name]}."
                ),
            )
        )
    return quotes


def _quote(quote_id: str, document_id: str, title: str, body: str) -> dict:
    return {
        "id": quote_id,
        "document_id": document_id,
        "title": title,
        "kind": "warehouse_inventory",
        "body": body,
    }


def _document(doc_id: str, title: str, body: str) -> dict:
    return {
        "id": doc_id,
        "source_type": "warehouse_inventory",
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
        "created_at": "2026-09-30T12:00:00Z",
    }


def _month_end_sentence() -> str:
    parts = []
    for month, counts in BATTERY_MONTH_END.items():
        parts.append(f"{_month_name(month)} {sum(counts.values())}")
    return (
        "BP-BATT-46 ending stock was "
        + ", ".join(parts[:-1])
        + ", and "
        + parts[-1]
        + "."
    )


def _safety_sentence() -> str:
    parts = [f"{name} {SAFETY_STOCK[name]}" for name in WAREHOUSES]
    cushion = ON_HAND["BP-BATT-46"]["San Antonio"] - SAFETY_STOCK["San Antonio"]
    return (
        f"Battery safety stock is {', '.join(parts[:-1])}, and {parts[-1]}. "
        f"San Antonio has {cushion} units of cushion."
    )


def _onhand_body(headlines: list[str]) -> str:
    lines = list(headlines)
    lines.append(f"On-hand units at {AS_OF}. Each installation consumes one of each SKU.")
    lines.append("warehouse sku description on_hand")
    for sku, description in SKUS:
        for warehouse in WAREHOUSES:
            lines.append(f"{warehouse} {sku} {description} {ON_HAND[sku][warehouse]}")
    lines.append("month warehouse BP-BATT-46 ending_on_hand")
    for month, counts in BATTERY_MONTH_END.items():
        for warehouse in WAREHOUSES:
            lines.append(f"{month} {warehouse} BP-BATT-46 {counts[warehouse]}")
    lines.append("month warehouse sku issued")
    for month, counts in monthly_issues():
        for sku, _ in SKUS:
            for warehouse in WAREHOUSES:
                lines.append(f"{month} {warehouse} {sku} {counts[warehouse]}")
    return "\n".join(lines)


def _forecast_body(headlines: list[str]) -> str:
    lines = list(headlines)
    lines.append(
        "Stored Q4 2026 forecast. Projected end is on hand plus scheduled receipts minus forecast issues."
    )
    lines.append(
        f"Safety stock BP-BATT-46: "
        + ", ".join(f"{name} {SAFETY_STOCK[name]}" for name in WAREHOUSES)
        + f". Open {OPEN_PO[0]} {OPEN_PO[3]} {OPEN_PO[2]} for {OPEN_PO[1]} due {OPEN_PO[4]}, excluded from Q4 receipts."
    )
    lines.append("warehouse sku on_hand q4_receipts q4_forecast_issues projected_end")
    forecast = q4_issues()
    for sku, _ in SKUS:
        for warehouse in WAREHOUSES:
            end = projected_end(sku, warehouse)
            lines.append(
                f"{warehouse} {sku} {ON_HAND[sku][warehouse]} "
                f"{Q4_RECEIPTS[sku][warehouse]} {forecast[warehouse]} {end}"
            )
    return "\n".join(lines)


def _month_name(month: str) -> str:
    names = {
        "2026-04": "April",
        "2026-05": "May",
        "2026-06": "June",
        "2026-07": "July",
        "2026-08": "August",
        "2026-09": "September",
    }
    return names[month]
