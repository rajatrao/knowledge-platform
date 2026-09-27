# Lumenfield executive dataset

Synthetic operating pack for a CEO and the executive team of Lumenfield, a fictional Central Texas energy-storage company. It is shaped like a multi-market installer and service business. It is not Base Power, and it does not contain real financials, customers, employees, addresses, or credentials.

Snapshot date: 2026-09-27. Persona: CEO, COO, and functional VPs preparing a weekly business review.

## Purpose

Give an executive agent one consistent book of markets, installations, customers, workforce, inventory, engineering health, risks, and decisions. The figures are generated. The relationships are deliberate.

## Sources

This pack reuses ids from:

- `data/warehouses.csv` (W001, W002, W003)
- `data/technicians.csv` (city rollup into markets)
- `data/parts.csv` and `data/warehouse_inventory.csv` (part balances, including P006 at W001 and P018)
- `data/jobs.csv` and `data/customer_sites.csv` (field customer and job ids)
- `data/engineering/devices.csv`, `engineering_sites.csv`, `engineering_incidents.csv`, `firmware_versions.csv`

Field customer ids (`C001`) and engineering customer ids (`CUST-001`) are different lists. `customer_sites.csv` has no `site_id`. When `customer_issues.site_id` is filled, it is an engineering site id.

## Relationships

- `markets.warehouse_id` points at `warehouses.csv`. Several markets share one warehouse.
- `deployment_metrics` is the daily source of truth for installations, targets, critical incidents, and stockout events from 2026-04-01 through 2026-09-27.
- `market_performance` for a market-month is the sum of those days (month-end snapshot for jobs waiting; completion-weighted cycle time).
- `company_metrics` for 2026-04 through 2026-09 sums the seven markets. Months from 2025-10 through 2026-03 have no market drill-down.
- `customer_funnel` and `workforce_metrics` installation and schedule counts for a week match the daily file.
- `warehouse_metrics.stockout_events` for a week is the sum of daily stockout flags for the markets on that warehouse.
- `inventory_risk.current_available_quantity` is `warehouse_inventory.quantity_available` for that part and warehouse on the snapshot. `weeks_of_supply` divides that balance by a planning consumption rate.
- `engineering_health_metrics` for the week of 2026-09-15 is tied to INC-002 (firmware 4.3.0).
- `reliability_metrics.failure_rate` is `failure_count / installed_base`. Battery HW-C points at INC-005.
- Risks, alerts, initiatives, and documents point at scenario ids SCN-01 through SCN-12. They are labels, not a market ranking.

## Assumptions

- A week starts on Monday. The week of 2026-09-15 is the week starting 2026-09-14.
- Daily history runs from 2026-04-01 so April through September monthly totals equal the daily file. The latest 90 days are inside that range.
- Technician cities map once: Austin and Lakeway to Austin Metro; Manor to North Austin; Round Rock and Hutto to Round Rock; Cedar Park and Leander to Cedar Park; Georgetown to Georgetown; Buda to San Marcos; Pflugerville to Pflugerville.
- For every market except San Marcos, `technician_count` matches that city rollup. A technician with a non-empty certifications field counts as certified.
- San Marcos `technician_count` 5 and `certified_technician_count` 3 are the launch roster (60 percent). `field_extract_technician_count` is the Buda subset actually present in `technicians.csv`. Do not add those two counts together.
- Utilization uses scheduled installations divided by certified technicians times 8 installs per week. Above 100 means the book is larger than that capacity. San Marcos utilization is a training load, not install throughput.
- `installed_base` on reliability rows is the 2026-09-27 device census repeated for each month.
- `lines_below_reorder` on warehouse rows is the snapshot count, repeated each week. The time pattern is `stockout_events`.
- No revenue, margin, or headcount-cost dollars are included.

## How to regenerate

```bash
/Users/rajat/Downloads/hackathon/base/knowledge-proj/.venv/bin/python scripts/generate_executive_data.py
```

The script uses only the Python standard library (`csv`, `random`, `datetime`, `pathlib`) and `random.seed(27)`. It exits with an error if validation fails.

## Synthetic disclaimer

All names, customers, balances, and metrics are fictional. Warehouse and technician ids are carried forward from the other synthetic datasets in this repo so the executive pack can join to them. Do not describe these figures as real operating results.
