"""Fake company performance, revenue, and sample ERCOT series.

Numbers are invented for the local corpus. They are not a live ERCOT feed.
"""

from __future__ import annotations

MONTHS = (
    ("2026-04", 16905, 774, 97.9, 410, 3.40, 0.92, 12.1),
    ("2026-05", 17240, 789, 98.0, 455, 3.62, 1.01, 13.4),
    ("2026-06", 17580, 804, 98.1, 480, 3.88, 1.08, 14.2),
    ("2026-07", 17890, 818, 98.2, 510, 4.21, 1.15, 15.6),
    ("2026-08", 18160, 830, 98.3, 560, 4.77, 1.24, 16.8),
    ("2026-09", 18420, 842, 98.4, 640, 4.82, 1.36, 18.4),
)

REGION_GRID_REVENUE = (
    ("Houston", 1.83, 38),
    ("Dallas", 1.30, 27),
    ("Austin", 1.01, 21),
    ("San Antonio", 0.68, 14),
)

# Quarter-end stock, fleet MWh, availability, installs in the quarter, and
# revenue in millions. 2026 Q2 and Q3 revenue are the April-June and July-September
# sums of MONTHS. 2026 Q3 homes and fleet match September 2026.
QUARTERS = (
    ("2020-Q1", 820, 31, 96.2, 210, 0.42, 0.11, 2.4),
    ("2020-Q2", 960, 37, 96.3, 190, 0.51, 0.14, 2.8),
    ("2020-Q3", 1105, 43, 96.4, 185, 0.63, 0.17, 3.3),
    ("2020-Q4", 1240, 48, 96.5, 175, 0.78, 0.21, 3.9),
    ("2021-Q1", 1420, 56, 96.5, 240, 0.95, 0.26, 4.6),
    ("2021-Q2", 1640, 65, 96.6, 280, 1.12, 0.30, 5.2),
    ("2021-Q3", 1900, 76, 96.7, 320, 1.34, 0.36, 6.1),
    ("2021-Q4", 2180, 88, 96.8, 350, 1.58, 0.43, 7.0),
    ("2022-Q1", 2480, 100, 96.9, 380, 1.85, 0.50, 8.2),
    ("2022-Q2", 2820, 115, 97.0, 430, 2.10, 0.57, 9.1),
    ("2022-Q3", 3210, 132, 97.0, 490, 2.42, 0.66, 10.4),
    ("2022-Q4", 3640, 151, 97.1, 540, 2.78, 0.75, 11.8),
    ("2023-Q1", 4180, 174, 97.2, 640, 3.20, 0.86, 13.4),
    ("2023-Q2", 4780, 201, 97.3, 720, 3.65, 0.98, 15.1),
    ("2023-Q3", 5420, 229, 97.4, 780, 4.15, 1.12, 17.0),
    ("2023-Q4", 6150, 262, 97.5, 890, 4.70, 1.27, 19.2),
    ("2024-Q1", 6920, 296, 97.6, 940, 5.35, 1.44, 21.6),
    ("2024-Q2", 7780, 335, 97.6, 1040, 6.05, 1.63, 24.2),
    ("2024-Q3", 8760, 380, 97.7, 1180, 6.80, 1.84, 27.1),
    ("2024-Q4", 9820, 429, 97.8, 1280, 7.60, 2.05, 30.4),
    ("2025-Q1", 10950, 481, 97.9, 1360, 8.40, 2.27, 33.2),
    ("2025-Q2", 12180, 539, 98.0, 1480, 9.15, 2.47, 36.1),
    ("2025-Q3", 13540, 603, 98.1, 1620, 9.90, 2.67, 39.4),
    ("2025-Q4", 15020, 673, 98.1, 1760, 10.70, 2.89, 42.8),
    ("2026-Q1", 16440, 742, 98.2, 1680, 11.40, 3.08, 36.2),
    ("2026-Q2", 17580, 798, 98.3, 1345, 10.90, 3.01, 39.7),
    ("2026-Q3", 18420, 842, 98.4, 1710, 13.80, 3.75, 50.8),
)

# Stored 2026 Q4 plan. A later quarter is forecast by the model from this history.
FORECAST_2026_Q4 = ("2026-Q4", 19470, 890, 98.5, 2100, 14.60, 4.05, 54.0)

# Sample day 2026-09-15. Peak hour 17 is the headline, not a live settlement.
ZONE_BASE = {"LZ_HOUSTON": 42.0, "LZ_NORTH": 35.0, "LZ_SOUTH": 28.0, "LZ_WEST": 22.0}
ZONE_PEAK = {"LZ_HOUSTON": 187.40, "LZ_NORTH": 142.10, "LZ_SOUTH": 96.55, "LZ_WEST": 61.20}
SAMPLE_DAY = "2026-09-15"
LOAD_PEAK_MW = 78400

# Monthly peak settlement price for LZ_HOUSTON and system load peak. September matches the sample day.
ERCOT_MONTHLY_PEAKS = (
    ("2026-01", 48.20, 62400),
    ("2026-02", 44.10, 59800),
    ("2026-03", 39.50, 57200),
    ("2026-04", 52.80, 64100),
    ("2026-05", 71.40, 69200),
    ("2026-06", 118.60, 73400),
    ("2026-07", 156.20, 76100),
    ("2026-08", 171.80, 77600),
    ("2026-09", 187.40, 78400),
)


def company_quotes() -> list[dict]:
    """Citeable sentences. Each one is also copied into its source document."""
    return [
        {
            "id": "ki_doc_perf_2026_homes",
            "document_id": "doc_perf_2026",
            "title": "Installed homes, September 2026",
            "kind": "company_performance",
            "body": "Fleet installed homes reached 18420 in September 2026, up from 16905 in April 2026.",
        },
        {
            "id": "ki_doc_perf_2026_capacity",
            "document_id": "doc_perf_2026",
            "title": "Fleet capacity, September 2026",
            "kind": "company_performance",
            "body": "Fleet energy capacity was 842 MWh in September 2026, and the average member battery was 45.7 kWh.",
        },
        {
            "id": "ki_doc_perf_2026_availability",
            "document_id": "doc_perf_2026",
            "title": "Fleet availability, September 2026",
            "kind": "company_performance",
            "body": "Fleet availability was 98.4 percent in September 2026, and 640 installations were completed that month.",
        },
        {
            "id": "ki_doc_rev_2026_grid",
            "document_id": "doc_rev_2026",
            "title": "Grid services revenue, September 2026",
            "kind": "revenue",
            "body": "Grid services revenue was $4.82 million in September 2026.",
        },
        {
            "id": "ki_doc_rev_2026_savings",
            "document_id": "doc_rev_2026",
            "title": "Member bill savings, September 2026",
            "kind": "revenue",
            "body": "Member bill savings were $1.36 million in September 2026.",
        },
        {
            "id": "ki_doc_rev_2026_systems",
            "document_id": "doc_rev_2026",
            "title": "New system revenue, September 2026",
            "kind": "revenue",
            "body": "New system revenue was $18.4 million in September 2026.",
        },
        {
            "id": "ki_doc_rev_2026_trailing",
            "document_id": "doc_rev_2026",
            "title": "Trailing grid services revenue",
            "kind": "revenue",
            "body": "Trailing six-month grid services revenue was $24.70 million through September 2026.",
        },
        {
            "id": "ki_doc_rev_2026_houston",
            "document_id": "doc_rev_2026",
            "title": "Houston grid revenue share",
            "kind": "revenue",
            "body": "Houston accounted for 38 percent of September 2026 grid services revenue.",
        },
        {
            "id": "ki_doc_ercot_20260915_price",
            "document_id": "doc_ercot_20260915",
            "title": "Sample LZ_HOUSTON peak price",
            "kind": "ercot_grid",
            "body": "Sample ERCOT LZ_HOUSTON price peaked at $187.40 per MWh on 2026-09-15 at 17:00. This is fake sample data, not a live ERCOT feed.",
        },
        {
            "id": "ki_doc_ercot_20260915_load",
            "document_id": "doc_ercot_20260915",
            "title": "Sample system load peak",
            "kind": "ercot_grid",
            "body": "Sample ERCOT system load peaked at 78400 MW on 2026-09-15 at 17:00. This is fake sample data, not a live ERCOT feed.",
        },
        *_quarter_quotes(),
        *_ercot_history_quotes(),
    ]


def company_documents() -> list[dict]:
    quotes = company_quotes()
    by_doc: dict[str, list[str]] = {}
    for quote in quotes:
        by_doc.setdefault(quote["document_id"], []).append(quote["body"])
    return [
        _document(
            "doc_perf_2026",
            "company_performance",
            "Base Power company performance, April-September 2026",
            _performance_body(by_doc["doc_perf_2026"]),
            "2026-09-26T12:00:00Z",
        ),
        _document(
            "doc_rev_2026",
            "revenue",
            "Base Power revenue, April-September 2026",
            _revenue_body(by_doc["doc_rev_2026"]),
            "2026-09-26T12:00:00Z",
        ),
        _document(
            "doc_ercot_20260915",
            "ercot",
            "Sample ERCOT grid prices and load, 2026-09-15",
            _ercot_body(by_doc["doc_ercot_20260915"]),
            "2026-09-16T12:00:00Z",
        ),
        _document(
            "doc_ercot_2026",
            "ercot",
            "Sample ERCOT peaks, January-September 2026",
            _ercot_history_body(by_doc["doc_ercot_2026"]),
            "2026-09-30T12:00:00Z",
        ),
        _document(
            "doc_perf_quarters",
            "company_performance",
            "Base Power quarterly performance, 2020 Q1 through 2026 Q3",
            _quarter_performance_body(by_doc["doc_perf_quarters"]),
            "2026-09-26T12:00:00Z",
        ),
        _document(
            "doc_rev_quarters",
            "revenue",
            "Base Power quarterly revenue, 2020 Q1 through 2026 Q3",
            _quarter_revenue_body(by_doc["doc_rev_quarters"]),
            "2026-09-26T12:00:00Z",
        ),
        *_record_documents(by_doc),
    ]


def _record_documents(by_doc: dict[str, list[str]]) -> list[dict]:
    """One corpus row per quarter so the JSON files list each record."""
    docs = []
    for doc_id, lines in sorted(by_doc.items()):
        if doc_id.startswith("doc_qp_"):
            source = "company_performance"
        elif doc_id.startswith("doc_qr_"):
            source = "revenue"
        else:
            continue
        docs.append(
            _document(
                doc_id,
                source,
                lines[0].split(":", 1)[0],
                "\n".join(lines),
                "2026-09-26T12:00:00Z",
            )
        )
    return docs


def company_knowledge_items() -> list[dict]:
    return [
        {
            "id": row["id"],
            "document_id": row["document_id"],
            "issue_id": None,
            "title": row["title"],
            "body": row["body"],
            "kind": row["kind"],
        }
        for row in company_quotes()
    ]


def _document(doc_id: str, source_type: str, title: str, body: str, created_at: str) -> dict:
    return {
        "id": doc_id,
        "source_type": source_type,
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
        "created_at": created_at,
    }


def _rows_for(year: str) -> list[tuple]:
    return [row for row in QUARTERS if row[0].startswith(year)]


def _year_ends() -> list[tuple]:
    last: dict[str, tuple] = {}
    for row in QUARTERS:
        last[row[0][:4]] = row
    return [last[year] for year in sorted(last)]


def _sum_field(rows: list[tuple], index: int) -> float:
    return round(sum(row[index] for row in rows), 2)


def _millions(value: float, places: int) -> str:
    return f"${value:.{places}f} million"


def _and_join(parts: list[str]) -> str:
    if len(parts) == 1:
        return parts[0]
    return ", ".join(parts[:-1]) + ", and " + parts[-1]


def _quarter_quotes() -> list[dict]:
    ends = _year_ends()
    first = QUARTERS[0]
    home_parts = [f"{first[1]} in 2020 Q1"]
    for row in ends:
        year = row[0][:4]
        label = "2026 Q3" if year == "2026" else year
        home_parts.append(f"{row[1]} in {label}")
    full_years = [row for row in ends if row[0][:4] != "2026"]
    grid_parts = [
        f"{_millions(_sum_field(_rows_for(row[0][:4]), 5), 2)} in {row[0][:4]}" for row in full_years
    ]
    savings_parts = [
        f"{_millions(_sum_field(_rows_for(row[0][:4]), 6), 2)} in {row[0][:4]}" for row in full_years
    ]
    system_parts = [
        f"{_millions(_sum_field(_rows_for(row[0][:4]), 7), 1)} in {row[0][:4]}" for row in full_years
    ]
    y2026 = _rows_for("2026")
    quotes = [
        {
            "id": "ki_q00_homes",
            "document_id": "doc_perf_quarters",
            "title": "Quarter-end installed homes, 2020-2026",
            "kind": "company_performance",
            "body": f"Quarter-end installed homes were {_and_join(home_parts)}.",
        },
        {
            "id": "ki_q01_grid",
            "document_id": "doc_rev_quarters",
            "title": "Annual grid services revenue, 2020-2025",
            "kind": "revenue",
            "body": f"Annual grid services revenue was {_and_join(grid_parts)}.",
        },
        {
            "id": "ki_q02_2026_grid",
            "document_id": "doc_rev_quarters",
            "title": "2026 quarterly grid services revenue",
            "kind": "revenue",
            "body": (
                "2026 Q1 through Q3 grid services revenue was "
                f"{_millions(_sum_field(y2026, 5), 2)}. The quarters were "
                f"{_millions(y2026[0][5], 2)}, {_millions(y2026[1][5], 2)}, and {_millions(y2026[2][5], 2)}."
            ),
        },
        {
            "id": "ki_q03_fleet",
            "document_id": "doc_perf_quarters",
            "title": "Fleet capacity, 2020 Q1 and 2026 Q3",
            "kind": "company_performance",
            "body": (
                f"Fleet energy capacity at quarter end was {first[2]} MWh in 2020 Q1 "
                f"and {QUARTERS[-1][2]} MWh in 2026 Q3."
            ),
        },
        {
            "id": "ki_q04_savings",
            "document_id": "doc_rev_quarters",
            "title": "Annual member bill savings, 2020-2025",
            "kind": "revenue",
            "body": f"Annual member bill savings were {_and_join(savings_parts)}.",
        },
        {
            "id": "ki_q05_systems",
            "document_id": "doc_rev_quarters",
            "title": "Annual new system revenue, 2020-2025",
            "kind": "revenue",
            "body": f"Annual new system revenue was {_and_join(system_parts)}.",
        },
    ]
    for year in ("2020", "2021", "2022", "2023", "2024", "2025", "2026"):
        rows = _rows_for(year)
        homes = ", ".join(f"{row[0][-2:]} {row[1]}" for row in rows)
        grid = ", ".join(f"{row[0][-2:]} {_millions(row[5], 2)}" for row in rows)
        quotes.append(
            {
                "id": f"ki_q10_{year}",
                "document_id": "doc_perf_quarters",
                "title": f"{year} quarterly homes and grid revenue",
                "kind": "company_performance",
                "body": f"{year} quarter-end homes: {homes}. Grid services revenue: {grid}.",
            }
        )
    quotes.extend(_quarter_detail_quotes())
    for quote in quotes:
        if len(quote["body"]) > 180:
            raise ValueError(f"{quote['id']} is {len(quote['body'])} characters")
    return quotes


def _quarter_detail_quotes() -> list[dict]:
    """One performance record and one revenue record per quarter from 2022 through 2026.

    Closed quarters use QUARTERS. 2026 Q4 is a forecast, and its installation count
    matches the warehouse plan of 2100.
    """
    quotes = []
    for quarter, homes, fleet, availability, installs, grid, savings, systems in QUARTERS:
        if not quarter.startswith(("2022", "2023", "2024", "2025", "2026")):
            continue
        label = quarter.replace("-", " ")
        slug = quarter.lower().replace("-", "")
        quotes.append(
            {
                "id": f"ki_qp_{slug}",
                "document_id": f"doc_qp_{slug}",
                "title": f"{label} performance",
                "kind": "company_performance",
                "body": (
                    f"{label} performance: {homes} installed homes, {fleet} MWh fleet, "
                    f"{availability} percent availability, and {installs} installations."
                ),
            }
        )
        quotes.append(
            {
                "id": f"ki_qr_{slug}",
                "document_id": f"doc_qr_{slug}",
                "title": f"{label} revenue",
                "kind": "revenue",
                "body": (
                    f"{label} revenue: grid services {_millions(grid, 2)}, "
                    f"member bill savings {_millions(savings, 2)}, and new systems {_millions(systems, 1)}."
                ),
            }
        )
    quarter, homes, fleet, availability, installs, grid, savings, systems = FORECAST_2026_Q4
    label = quarter.replace("-", " ")
    quotes.append(
        {
            "id": "ki_qp_2026q4",
            "document_id": "doc_qp_2026q4",
            "title": f"{label} forecast performance",
            "kind": "company_performance",
            "body": (
                f"{label} forecast performance: {homes} installed homes, {fleet} MWh fleet, "
                f"{availability} percent availability, and {installs} installations."
            ),
        }
    )
    quotes.append(
        {
            "id": "ki_qr_2026q4",
            "document_id": "doc_qr_2026q4",
            "title": f"{label} forecast revenue",
            "kind": "revenue",
            "body": (
                f"{label} forecast revenue: grid services ${grid:.2f} million, "
                f"member bill savings ${savings:.2f} million, and new systems ${systems:.1f} million."
            ),
        }
    )
    return quotes


def _quarter_performance_body(headlines: list[str]) -> str:
    lines = list(headlines)
    lines.append("Quarter-end company performance from 2020 Q1 through 2026 Q3. Homes are installed members. Capacity is fleet MWh.")
    lines.append("quarter homes_installed fleet_mwh availability_pct installations_completed")
    for quarter, homes, mwh, availability, installs, _, _, _ in QUARTERS:
        lines.append(f"{quarter} {homes} {mwh} {availability} {installs}")
    return "\n".join(lines)


def _quarter_revenue_body(headlines: list[str]) -> str:
    lines = list(headlines)
    lines.append("Quarterly revenue in millions of dollars from 2020 Q1 through 2026 Q3.")
    lines.append("quarter grid_services_million member_savings_million new_systems_million")
    for quarter, _, _, _, _, grid, savings, systems in QUARTERS:
        lines.append(f"{quarter} {grid:.2f} {savings:.2f} {systems:.1f}")
    return "\n".join(lines)


def _performance_body(headlines: list[str]) -> str:
    lines = list(headlines)
    lines.append("Monthly company performance. Homes are installed members. Capacity is fleet MWh.")
    lines.append("month homes_installed fleet_mwh availability_pct installations_completed")
    for month, homes, mwh, availability, installs, _, _, _ in MONTHS:
        lines.append(f"{month} {homes} {mwh} {availability} {installs}")
    return "\n".join(lines)


def _revenue_body(headlines: list[str]) -> str:
    lines = list(headlines)
    lines.append("Monthly revenue in millions of dollars. Grid services, member bill savings, and new system sales.")
    lines.append("month grid_services_million member_savings_million new_systems_million")
    for month, _, _, _, _, grid, savings, systems in MONTHS:
        lines.append(f"{month} {grid:.2f} {savings:.2f} {systems:.1f}")
    lines.append("September 2026 grid services revenue by region, millions of dollars and share.")
    for region, millions, share in REGION_GRID_REVENUE:
        lines.append(f"{region} {millions:.2f} {share} percent")
    return "\n".join(lines)


def september_daily_peaks() -> list[tuple[str, float, int]]:
    """Daily LZ_HOUSTON peak price and system load. 2026-09-15 is the sample-day peak."""
    rows = []
    for day in range(1, 31):
        distance = abs(day - 15)
        price = round(ZONE_PEAK["LZ_HOUSTON"] * (1 - 0.035 * distance), 2)
        load = int(round(LOAD_PEAK_MW * (1 - 0.012 * distance)))
        rows.append((f"2026-09-{day:02d}", price, load))
    return rows


def _ercot_history_quotes() -> list[dict]:
    daily = september_daily_peaks()
    low_day, low_price, low_load = min(daily, key=lambda row: row[1])
    week = [row for row in daily if "2026-09-13" <= row[0] <= "2026-09-17"]
    week_prices = ", ".join(f"${row[1]:.2f}" for row in week)
    price_parts = [f"{row[0][5:7]} ${row[1]:.2f}" for row in ERCOT_MONTHLY_PEAKS]
    load_parts = [f"{row[0][5:7]} {row[2]}" for row in ERCOT_MONTHLY_PEAKS]
    zone_parts = [f"{zone} ${ZONE_PEAK[zone]:.2f}" for zone in ZONE_PEAK]
    quotes = [
        {
            "id": "ki_ercot00_month_price",
            "document_id": "doc_ercot_2026",
            "title": "2026 monthly LZ_HOUSTON peak prices",
            "kind": "ercot_grid",
            "body": f"2026 LZ_HOUSTON monthly peak prices per MWh were {_and_join(price_parts)}.",
        },
        {
            "id": "ki_ercot01_month_load",
            "document_id": "doc_ercot_2026",
            "title": "2026 monthly system load peaks",
            "kind": "ercot_grid",
            "body": f"2026 ERCOT system load peaks in MW were {_and_join(load_parts)}.",
        },
        {
            "id": "ki_ercot02_week",
            "document_id": "doc_ercot_2026",
            "title": "Mid-September 2026 price week",
            "kind": "ercot_grid",
            "body": (
                "From 2026-09-13 to 2026-09-17, LZ_HOUSTON daily peaks were "
                f"{week_prices} per MWh. This is fake sample data, not a live ERCOT feed."
            ),
        },
        {
            "id": "ki_ercot03_low",
            "document_id": "doc_ercot_2026",
            "title": "Lowest September 2026 daily peak",
            "kind": "ercot_grid",
            "body": (
                f"The lowest September 2026 daily peak was LZ_HOUSTON ${low_price:.2f} per MWh "
                f"and {low_load} MW on {low_day}."
            ),
        },
        {
            "id": "ki_ercot04_zones",
            "document_id": "doc_ercot_2026",
            "title": "Sample day peaks by zone",
            "kind": "ercot_grid",
            "body": f"On {SAMPLE_DAY} at 17:00 sample zone peaks per MWh were {_and_join(zone_parts)}.",
        },
    ]
    for quote in quotes:
        if len(quote["body"]) > 180:
            raise ValueError(f"{quote['id']} is {len(quote['body'])} characters")
    return quotes


def _ercot_history_body(headlines: list[str]) -> str:
    lines = list(headlines)
    lines.append("Monthly peak price is LZ_HOUSTON dollars per MWh. Load is the system peak in MW. Fake sample data.")
    lines.append("month houston_peak_usd_per_mwh north south west system_load_mw")
    for month, houston, load in ERCOT_MONTHLY_PEAKS:
        zones = [round(ZONE_PEAK[zone] / ZONE_PEAK["LZ_HOUSTON"] * houston, 2) for zone in ZONE_PEAK]
        rendered = " ".join(f"{price:.2f}" for price in zones)
        lines.append(f"{month} {rendered} {load}")
    lines.append("day houston_peak_usd_per_mwh system_load_mw")
    for day, price, load in september_daily_peaks():
        lines.append(f"{day} {price:.2f} {load}")
    return "\n".join(lines)


def _ercot_body(headlines: list[str]) -> str:
    lines = list(headlines)
    lines.append("Hourly sample settlement prices in dollars per MWh and system load in MW for 2026-09-15.")
    lines.append("interval zone price_usd_per_mwh system_load_mw")
    for hour in range(24):
        load = _load_mw(hour)
        for zone in ZONE_BASE:
            price = _price(zone, hour)
            lines.append(f"{SAMPLE_DAY}T{hour:02d}:00Z {zone} {price:.2f} {load}")
    return "\n".join(lines)


def _price(zone: str, hour: int) -> float:
    base = ZONE_BASE[zone]
    peak = ZONE_PEAK[zone]
    # Triangle that is 0 at hour 8 and 1 at hour 17, then falls through hour 21.
    if hour < 8 or hour > 21:
        weight = 0.0
    elif hour <= 17:
        weight = (hour - 8) / 9
    else:
        weight = (21 - hour) / 4
    return round(base + (peak - base) * weight, 2)


def _load_mw(hour: int) -> int:
    if hour < 8 or hour > 21:
        weight = 0.15
    elif hour <= 17:
        weight = 0.15 + 0.85 * ((hour - 8) / 9)
    else:
        weight = 0.15 + 0.85 * ((21 - hour) / 4)
    return int(round(52000 + (LOAD_PEAK_MW - 52000) * weight))
