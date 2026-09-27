# Lumenfield Energy field operations (synthetic)

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
| Van does **not** have everything for its job | V001 is short P018 need 2 have 0. Answer to "does V001 have everything for J001?" is **no**. |
| Critical part present on that same van | V001 is carrying P001 (LumenPack module) and other critical parts. P018 is the missing critical fuse. |
| Urgent unassigned job and who should take it | J010 Critical Emergency Service at C010 Prairie Switch Backup, Pflugerville, start 16:30, no technician. Closest available technician is T004 Maren Holt (0.86 km). Closest van is V004 (0.86 km). T004 holds Battery Installation Master and V004 already carries P001, P018, and P012. |
| Second available person nearby, not the right dispatch | T018 Ada Moss is Available in Pflugerville with no van and no Master certification. |
| Delayed job and why | J007 at C007 Cedar Kettle Works. T010 has been onsite since 13:00. Waiting-for-parts note: P006 is not on V010, W001 is out of stock, **W002 should supply the job**. |
| Overdue assigned job | J030 inspection at C025 Hollow Oak Bakery, window 13:00-15:00, still Assigned to T009. Schedule status is Missed. |
| What happened at a site today | C020 Mesquite Switch House. The only 2026-09-27 job is J021, completed by T005 Cassio Venn (van V005). Full event chain is on that job. |
| Chain of custody for the battery | P001 transactions, in order: Received -> Transfer -> Transfer -> Issued -> Issued -> Installed -> Issued -> Adjustment -> Reserved -> Reserved. Checkout to ask for first is T001 Rowan Pell, Issued to V001 on 2026-09-15. |
| Where P001 sits | W001 aisle A shelf 03 bin 14; W002 aisle B shelf 01 bin 02; W003 aisle C shelf 02 bin 07. Stock is not equal across depots: W001 on hand 9 reserved 1 available 8, W002 on hand 7 reserved 0 available 7, W003 on hand 3 reserved 0 available 3. |
| Discrepancy | Adjustment on P001 at W003 on 2026-09-25, bin C / 02 / 07, and open alert AL008. |
| Who physically has a P001 right now | V001 (T001 Rowan Pell), V004 (T004 Maren Holt). |
| Shop van, due-soon van, spare van | V018 In Shop at W001, unassigned (T028 is off duty and is not linked as the driver). V019 Due Soon on 2026-10-08 with a Warning, still with T021. V007 Due Soon on 2026-10-12. V020 Available, no driver, parked on the W003 coordinates. |
| Offline gateway | V012 last check-in 2026-09-26 17:10. Alert AL010. |
| Onsite more than two hours | T001, T002, T010. |
| Warehouses | W001 Mesa Volt Depot, Austin, manager Orla Mint. W002 Brushy Creek Parts Hub, Round Rock, manager Galen Moss. W003 Bluebonnet Service Warehouse, Georgetown, manager Ida Barrow. |

## Datasets

Primary keys, foreign keys, and row counts. Row counts exclude the header.

| File | Rows |
| --- | ---: |
| `technicians.csv` | 30 |
| `technician_locations.csv` | 89 |
| `vans.csv` | 20 |
| `van_inventory.csv` | 123 |
| `warehouses.csv` | 3 |
| `parts.csv` | 32 |
| `warehouse_inventory.csv` | 90 |
| `warehouse_locations.csv` | 90 |
| `customer_sites.csv` | 50 |
| `jobs.csv` | 100 |
| `job_parts.csv` | 235 |
| `inventory_transactions.csv` | 469 |
| `job_events.csv` | 752 |
| `vehicle_events.csv` | 81 |
| `schedules.csv` | 85 |
| `operational_alerts.csv` | 13 |

### technicians.csv

Primary key `technician_id`. Foreign keys: `assigned_van_id` to `vans.van_id` (blank allowed), `current_job_id` to `jobs.job_id` (blank allowed). One technician has at most one van. Status, skills, and certifications are the personnel columns. Current coordinates are the 16:00 snapshot (or the shift-end ping for someone already Off Duty).

### technician_locations.csv

Primary key `location_event_id`. Foreign keys: `technician_id`, and `job_id` when set. The latest row for each technician matches `technicians` latitude, longitude, city, status, and current job. Earlier rows on 2026-09-27 are the trail (yard, en route, onsite, completed).

### vans.csv

Primary key `van_id`. Foreign keys: `assigned_technician_id` to `technicians.technician_id` (blank allowed), `home_warehouse_id` to `warehouses.warehouse_id`. Assignment is one-to-one with `technicians.assigned_van_id`. When a technician is set, the van's coordinates match that technician. `vehicle_number` is a fleet number, not a VIN. `last_check_in` is the gateway, not the phone.

### van_inventory.csv

Primary key `van_inventory_id`. Foreign keys: `van_id`, `part_id`. Absence means zero. V001's rows are the "what is in this van?" answer: P001 x2, P004 x2, P009 x2, P012 x4, P015 x6, P016 x1, P019 x4, P020 x1.

### warehouses.csv

Primary key `warehouse_id`. Three depots, three cities, all Open.

### parts.csv

Primary key `part_id`. P001 is the LumenPack 13.5 battery module, category Battery, criticality Critical. Categories cover battery, inverter, electrical, cable, connector, fuse, circuit protection, mounting hardware, sensors, and tools.

### warehouse_inventory.csv

Primary key `warehouse_inventory_id`. Foreign keys: `warehouse_id`, `part_id`. `quantity_available` is always `quantity_on_hand - quantity_reserved`. Includes healthy, low, empty, and overstocked rows. Battery available quantities: W001 132, W002 66, W003 57.

### warehouse_locations.csv

Composite primary key (`warehouse_id`, `part_id`). Foreign keys to those tables. One bin per part per depot. P001 is in more than one depot: W001 aisle A shelf 03 bin 14; W002 aisle B shelf 01 bin 02; W003 aisle C shelf 02 bin 07.

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

1. **Who is currently available?** `technicians.status = Available`. Answer: T004 Maren Holt, T009 Petra Sol, T011 Ellis Marrow, T016 Remy Oak, T018 Ada Moss, T026 Pax Holm, T027 Rhett Juno.
2. **Who is closest to this job?** For J010 / site C010, haversine on `technicians` current coordinates, usually filtered to Available. Answer: T004 Maren Holt (0.86 km).
3. **Which technician has the required certification?** `technicians.certifications` contains the level text. Battery Installation Master: T004. Electrical Master is T007 Nova Brigg. Inverter Repair Master is T013 Juniper Vale.
4. **Where is technician T001?** `technicians` plus the latest `technician_locations` row. Answer: Round Rock at Copper Lantern Home (30.50980, -97.72460), status On Job, job J001, ping 2026-09-27T15:58:00-05:00.
5. **Where is van V001?** `vans`. Answer: Round Rock (30.50980, -97.72460), status On Job, with T001.
6. **What inventory is inside van V001?** `van_inventory` where `van_id = V001`. Answer: P001 x2, P004 x2, P009 x2, P012 x4, P015 x6, P016 x1, P019 x4, P020 x1. Omitted parts are zero.
7. **Does van V001 have everything required for job J001?** Compare `van_inventory.quantity` to each `job_parts.required_quantity` for J001. Treat a missing row as zero. Answer: **no**. Short: P018 need 2 have 0.
8. **Which vans are available?** `vans.status = Available`. Answer: V004, V009, V011, V016, V020. V020 is the spare parked at its home warehouse. The others are with Available technicians.
9. **Which jobs are currently in progress?** `jobs.status = In Progress`. Answer: J002, J005, J008.
10. **Which jobs are waiting for parts?** `jobs.status = Waiting for Parts`. Answer: J001, J007.
11. **Which jobs are missing parts?** Any `job_parts.status = Missing`. Answer: J001, J007, J015.
12. **Which critical jobs are unassigned?** `priority = Critical` and `technician_id` blank. Answer: J010.
13. **How many batteries are available in each warehouse?** Sum `warehouse_inventory.quantity_available` for `parts.category = Battery`. Answer: W001 132, W002 66, W003 57.
14. **Where is part P001 located?** `warehouse_locations` for P001. Answer: W001 aisle A shelf 03 bin 14; W002 aisle B shelf 01 bin 02; W003 aisle C shelf 02 bin 07. Vans that currently hold one are in question 21.
15. **Which warehouse has this part?** `warehouse_inventory` with `quantity_available > 0`. P001 is in W001, W002, and W003 (W001 on hand 9 reserved 1 available 8, W002 on hand 7 reserved 0 available 7, W003 on hand 3 reserved 0 available 3). P006 is available at W002 only; W001 is zero and W003 has no row.
16. **Which parts are below their reorder point?** `quantity_available < reorder_point` on `warehouse_inventory`. Low (still above zero): W002 P018 available 2 reorder 6; W002 P021 available 2 reorder 3; W003 P018 available 2 reorder 6. Out-of-stock rows are also below reorder.
17. **What parts are out of stock?** `quantity_on_hand = 0`. Answer: W001 P006; W002 P030; W003 P003. A missing row is "not stocked here," which is different from an empty bin.
18. **What inventory is reserved?** `quantity_reserved > 0`. Answer: W001 P001 reserved 1; W001 P009 reserved 1; W001 P012 reserved 2; W001 P015 reserved 4; W001 P023 reserved 1; W002 P004 reserved 1; W002 P006 reserved 1; W002 P008 reserved 1; W002 P012 reserved 2; W002 P018 reserved 1; W002 P026 reserved 1. Matching `Reserved` transactions name the job.
19. **Where did the missing inventory go?** P001 Adjustment at W003 on 2026-09-25. The note says the module was not in bin C-02-07 and not on a van. Alert AL008 is the same story. Separately, P006 left W001 by a Transfer to W002 on 2026-09-12.
20. **Who checked out this part?** `inventory_transactions` where `transaction_type = Issued` and `technician_id` is set. For P001, T001 Rowan Pell checked two modules out to V001 on 2026-09-15. T002 and T004 also have Issued rows.
21. **Which technician currently has this equipment?** Join `van_inventory` to `vans.assigned_technician_id` where quantity is greater than zero. P001 is on V001 (T001 Rowan Pell), V004 (T004 Maren Holt).
22. **What parts are required for tomorrow's jobs?** `job_parts` joined to `jobs` where `scheduled_date = 2026-09-28`. Jobs: J011, J012, J013, J014, J015, J016, J017, J018, J019, J020. Line count: 25.
23. **Which jobs are fully kitted?** Every part line is Allocated or Installed. Still open: J002, J003, J004, J005, J006, J008, J009, J011, J012, J016, J030. J011 and J012 are Monday. J030 was kitted and then missed. Another 65 completed jobs are kitted because every line is Installed. J001, J007, J010, and J015 are not kitted. J013, J014, and J017-J020 are still Required only.
24. **Which jobs are blocked because of missing inventory?** `jobs.status = Waiting for Parts` (each has a Missing line). Answer: J001, J007. J015 is Missing a part but is still only Assigned for Monday, so it is short, not yet blocked in the field.
25. **Which van is closest to this customer site?** Haversine from `vans` to the site. For C010 Prairie Switch Backup: V004 (0.86 km).
26. **Which technician and van should handle this urgent job?** J010. Recommend **T004 Maren Holt and V004**: available, closest, Battery Installation Master, and the van covers P001, P018, and P012. T018 is nearer than the Austin crews but has no van.
27. **What operational issues should I know about right now?** `operational_alerts.status = Open`. Answer: AL001 Unassigned Critical Job Critical Job J010; AL002 Missing Job Parts High Job J001; AL003 Missing Job Parts High Job J007; AL004 Out of Stock High Part P006; AL005 Low Inventory Medium Part P018; AL006 Maintenance Due Medium Van V019; AL007 Technician Delayed High Technician T010; AL008 Inventory Discrepancy High Part P001; AL009 Job Overdue High Job J030; AL010 Van Offline Medium Van V012; AL011 Maintenance Due Low Van V018.
28. **Which vans need maintenance?** `maintenance_status` is Due Soon or In Shop, or `next_maintenance_date <= 2026-10-15`. Answer: V007 Due Soon next 2026-10-12; V018 In Shop next 2026-10-01; V019 Due Soon next 2026-10-08.
29. **Which technicians have been onsite for more than 2 hours?** Status On Job, `Arrived Onsite` at or before 14:00, job not completed. Answer: T001, T002, T010.
30. **Show me the chain of custody for this battery.** `inventory_transactions` for P001 ordered by timestamp. Sequence: Received -> Transfer -> Transfer -> Issued -> Issued -> Installed -> Issued -> Adjustment -> Reserved -> Reserved.
31. **What happened at this customer site today?** Customer C020 Mesquite Switch House, `jobs.scheduled_date = 2026-09-27`, then `job_events` for J021. T005 replaced a 60A breaker and an MC4 pair, the customer signed off, and the job completed at 11:20.
32. **What has already been done on this job?** `job_events` for that job, in timestamp order. J021 is the finished example. J001 stops at Waiting for Parts (diagnosis done, fuse still missing). J010 was only created and escalated.
33. **Why is this job delayed?** J007. Events `Part Required`, `Waiting for Parts`, and `Escalated`. The note says P006 is not on V010, W001 is empty, and W002 has the inverter. J001 is the same pattern for P018, with W001 able to supply it.
34. **What inventory discrepancies do we have?** Alert AL008 plus the P001 Adjustment on 2026-09-25 at W003 (quantity -1). The bin is aisle C, shelf 02, bin 07.
35. **Which warehouse should supply this job?** For J007, W002, because it has P006 available and W001 does not. For J001, W001, because it has P018 available while V001 has none.

## Files

CSVs and this note live in `data/`. Field definitions for every column are in `data/data_dictionary.md`. The generator is `scripts/generate_field_ops.py`.
