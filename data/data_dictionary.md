# Lumenfield field operations data dictionary

Synthetic dataset. Snapshot 2026-09-27 16:00 America/Chicago, timestamps stored with offset `-05:00`.
Controlled vocabularies and null rules are in `README.md`. Blank strings mean "not set" for optional foreign keys.

## technicians.csv

Primary key: `technician_id`.

| Field | Meaning |
| --- | --- |
| `technician_id` | Primary key. T001-T030. |
| `name` | Fictional technician name. |
| `status` | Available, On Job, En Route, Off Duty, or Break at the 16:00 snapshot. |
| `current_latitude` | Latest known latitude, five decimal degrees. Matches the latest technician_locations row. |
| `current_longitude` | Latest known longitude, five decimal degrees. |
| `current_city` | City label for the latest ping. A fictional locality, not a street address. |
| `last_location_timestamp` | Timestamp of the latest ping, ISO-8601 with -05:00 offset. |
| `skills` | Semicolon-separated skills such as Battery Installation, Battery Repair, Inverter Repair, Electrical, Diagnostics. |
| `certifications` | Semicolon-separated certifications with a level: Level 1, Level 2, or Master. |
| `assigned_van_id` | Van currently assigned. Blank if the technician has no van. Symmetric with vans.assigned_technician_id. |
| `current_job_id` | Job they are on right now. Blank unless status is On Job or En Route. |
| `shift_start` | Sunday 2026-09-27 shift start, local HH:MM. Weekday hours are not stored on this row. |
| `shift_end` | Sunday 2026-09-27 shift end, local HH:MM. |

## technician_locations.csv

Primary key: `location_event_id`.

| Field | Meaning |
| --- | --- |
| `location_event_id` | Primary key. LE00001 and up. |
| `technician_id` | Foreign key to technicians.technician_id. |
| `timestamp` | Ping time, ISO-8601 with -05:00 offset. History is on 2026-09-27. |
| `latitude` | Latitude at that ping. |
| `longitude` | Longitude at that ping. |
| `city` | City label for that ping. |
| `status` | Technician status at that ping. Same vocabulary as technicians.status. |
| `job_id` | Job they were traveling to or on. Blank when they were not on a job. Foreign key to jobs.job_id when set. |

## vans.csv

Primary key: `van_id`.

| Field | Meaning |
| --- | --- |
| `van_id` | Primary key. V001-V020. |
| `vehicle_number` | Fictional fleet number such as LF-4801. This is not a VIN. |
| `status` | Available, On Job, En Route, Parked, or Maintenance. |
| `assigned_technician_id` | Technician who has the van. Blank if the van is spare or in the shop. Symmetric with technicians.assigned_van_id. |
| `current_latitude` | Current latitude. Matches the assigned technician when the van is with them. |
| `current_longitude` | Current longitude. |
| `current_city` | Current city label. |
| `last_check_in` | Last vehicle-gateway check-in. This can lag the technician phone ping. See V012. |
| `mileage` | Odometer in miles. Equals the latest vehicle_events.mileage for this van. |
| `fuel_or_charge_percent` | State of charge, 0-100. The fleet is battery-electric. |
| `maintenance_status` | OK, Due Soon, or In Shop. |
| `next_maintenance_date` | Next planned service date, YYYY-MM-DD. |
| `home_warehouse_id` | Foreign key to warehouses.warehouse_id. Depot the van is stocked from. |

## van_inventory.csv

Primary key: `van_inventory_id`.

| Field | Meaning |
| --- | --- |
| `van_inventory_id` | Primary key. VI00001 and up. |
| `van_id` | Foreign key to vans.van_id. |
| `part_id` | Foreign key to parts.part_id. One row per van and part. |
| `quantity` | Physical quantity on the van. Includes units reserved to a job. Always greater than zero. |
| `last_inventory_check` | When this van was last fully counted. Parts omitted from the van were zero at that count. |

## warehouses.csv

Primary key: `warehouse_id`.

| Field | Meaning |
| --- | --- |
| `warehouse_id` | Primary key. W001-W003. |
| `warehouse_name` | Fictional depot name. |
| `city` | City the depot sits in. |
| `latitude` | Fictional depot latitude. |
| `longitude` | Fictional depot longitude. |
| `operating_hours` | Local hours. All three depots are open daily 06:00-18:00. |
| `manager_name` | Fictional depot manager. |
| `status` | Open. |

## parts.csv

Primary key: `part_id`.

| Field | Meaning |
| --- | --- |
| `part_id` | Primary key. P001-P032. |
| `part_number` | Fictional catalog number, LF- prefix. |
| `part_name` | Part name. |
| `category` | Battery, Inverter, Electrical, Cable, Connector, Fuse, Circuit Protection, Mounting Hardware, Sensors, or Tools. |
| `description` | What the part is. |
| `unit` | Unit of measure: each, kit, set, pair, or pack. |
| `unit_cost` | Synthetic unit cost in USD, two decimals. Not a real price. |
| `criticality` | Critical, High, Medium, or Low. |
| `reorder_point` | Catalog reorder point used as the default warehouse reorder point. |
| `preferred_stock_level` | Target on-hand. On-hand at least twice this value is treated as overstocked in the demo notes. |

## warehouse_inventory.csv

Primary key: `warehouse_inventory_id`.

| Field | Meaning |
| --- | --- |
| `warehouse_inventory_id` | Primary key. WI00001 and up. |
| `warehouse_id` | Foreign key to warehouses.warehouse_id. |
| `part_id` | Foreign key to parts.part_id. |
| `quantity_on_hand` | Physical quantity, including units that are reserved. May be zero when the bin is empty. |
| `quantity_reserved` | Quantity held for a job and not available to promise. |
| `quantity_available` | quantity_on_hand minus quantity_reserved. Always exact. |
| `reorder_point` | Reorder point for this warehouse-part row. Copied from parts.reorder_point. |
| `last_counted_at` | Last cycle count, ISO-8601 with -05:00 offset. |

## warehouse_locations.csv

Primary key: `warehouse_id, part_id`.

| Field | Meaning |
| --- | --- |
| `warehouse_id` | Foreign key to warehouses.warehouse_id. Part of the composite primary key. |
| `part_id` | Foreign key to parts.part_id. Part of the composite primary key. |
| `aisle` | Aisle letter. A at W001, B at W002, C at W003, except where a demo bin is called out. |
| `shelf` | Shelf number, zero-padded. |
| `bin` | Bin number, zero-padded. |

## customer_sites.csv

Primary key: `customer_id`.

| Field | Meaning |
| --- | --- |
| `customer_id` | Primary key. C001-C050. There is no separate customer table; the site is the customer. |
| `site_name` | Fictional site name. No street address. |
| `city` | City label. |
| `latitude` | Fictional site latitude near the named city. |
| `longitude` | Fictional site longitude. |
| `system_type` | Whole-Home Battery, Commercial Storage, Backup Power, or Solar-Plus-Storage. |
| `battery_capacity_kwh` | Installed battery energy, kWh. |
| `inverter_capacity_kw` | Installed inverter power, kW. |
| `installation_date` | Original install date, YYYY-MM-DD. |
| `site_status` | Active, Commissioning, or Offline. |

## jobs.csv

Primary key: `job_id`.

| Field | Meaning |
| --- | --- |
| `job_id` | Primary key. J001-J100. |
| `customer_id` | Foreign key to customer_sites.customer_id. |
| `job_type` | Installation, Battery Replacement, Battery Repair, Inverter Repair, Inspection, Preventive Maintenance, Emergency Service, or Troubleshooting. |
| `priority` | Low, Medium, High, or Critical. |
| `status` | Scheduled, Assigned, En Route, Onsite, In Progress, Waiting for Parts, Completed, or Cancelled. |
| `scheduled_date` | Local work date, YYYY-MM-DD. |
| `scheduled_start` | Planned start, ISO-8601 with -05:00 offset. |
| `scheduled_end` | Planned end, ISO-8601 with -05:00 offset. A crew can still be onsite after this time. |
| `technician_id` | Assigned technician. Blank when unassigned. Foreign key when set. |
| `van_id` | Van on the job. Blank when unassigned. On open jobs this is the technician's current van. |
| `created_at` | When the job was opened. |
| `estimated_duration_minutes` | Planned duration in minutes. |
| `actual_duration_minutes` | Minutes from Arrived Onsite to Job Completed. Blank unless the job is Completed. |
| `issue_description` | Plain-language reason for the visit. |

## job_parts.csv

Primary key: `job_part_id`.

| Field | Meaning |
| --- | --- |
| `job_part_id` | Primary key. JP00001 and up. |
| `job_id` | Foreign key to jobs.job_id. |
| `part_id` | Foreign key to parts.part_id. |
| `required_quantity` | Quantity the job needs. |
| `allocated_quantity` | Quantity reserved or staged. Never above required in this dataset. |
| `installed_quantity` | Quantity already installed. Never above allocated. |
| `status` | Required (not kitted yet, allocated 0), Allocated (allocated equals required, not fully installed), Installed (installed equals required), or Missing (kitting ran and allocated is still below required). |

## inventory_transactions.csv

Primary key: `transaction_id`.

| Field | Meaning |
| --- | --- |
| `transaction_id` | Primary key. TX00001 and up, assigned in timestamp order. |
| `timestamp` | When the movement posted, ISO-8601 with -05:00 offset. |
| `part_id` | Foreign key to parts.part_id. |
| `quantity` | Positive quantity for every type except Adjustment, where it is a signed on-hand delta. |
| `transaction_type` | Received, Transfer, Issued, Reserved, Installed, Returned, Scrapped, or Adjustment. |
| `from_location_type` | Supplier, Warehouse, Van, Job, or CustomerSite. |
| `from_location_id` | Source id. SUP-NORTHWIND and SCRAP are external party codes, not warehouses. |
| `to_location_type` | Supplier, Warehouse, Van, Job, or CustomerSite. |
| `to_location_id` | Destination id. |
| `technician_id` | Technician who checked the part out or installed it. Blank when no person was involved. Foreign key when set. |
| `van_id` | Van involved. Blank otherwise. Foreign key when set. |
| `job_id` | Job involved. Blank otherwise. Foreign key when set. |
| `notes` | Human-readable reason. The P001 discrepancy note matches alert AL008. |

## job_events.csv

Primary key: `event_id`.

| Field | Meaning |
| --- | --- |
| `event_id` | Primary key. JE00001 and up. |
| `job_id` | Foreign key to jobs.job_id. |
| `timestamp` | When the event happened. |
| `event_type` | Created, Assigned, Technician Dispatched, En Route, Arrived Onsite, Diagnosis, Part Required, Waiting for Parts, Repair Started, Repair Completed, Customer Signoff, Job Completed, or Escalated. |
| `technician_id` | Technician on the event. Blank before a person is involved. |
| `notes` | What happened. Waiting for Parts notes explain delays. |

## vehicle_events.csv

Primary key: `event_id`.

| Field | Meaning |
| --- | --- |
| `event_id` | Primary key. VE00001 and up. |
| `van_id` | Foreign key to vans.van_id. |
| `timestamp` | When the vehicle event posted. |
| `event_type` | Check In, Check Out, Maintenance, Inspection, Warning, Repair, or Fuel/Charge. |
| `mileage` | Odometer after the event. Non-decreasing for each van. |
| `notes` | What the event was. |

## schedules.csv

Primary key: `schedule_id`.

| Field | Meaning |
| --- | --- |
| `schedule_id` | Primary key. SC00001 and up. |
| `date` | Local date, YYYY-MM-DD. |
| `technician_id` | Foreign key to technicians.technician_id. Unassigned jobs have no schedule row. |
| `job_id` | Foreign key to jobs.job_id. |
| `start_time` | Planned local start, HH:MM, America/Chicago. |
| `end_time` | Planned local end, HH:MM. Back-to-back windows touch but do not overlap. |
| `location_city` | City of the customer site. |
| `status` | Scheduled, In Progress, Completed, Missed, or Cancelled. Missed means the planned window ended and the job was still only Assigned. |

## operational_alerts.csv

Primary key: `alert_id`.

| Field | Meaning |
| --- | --- |
| `alert_id` | Primary key. AL001 and up. |
| `alert_type` | Low Inventory, Out of Stock, Missing Job Parts, Technician Delayed, Van Offline, Maintenance Due, Job Overdue, Inventory Discrepancy, or Unassigned Critical Job. |
| `severity` | Low, Medium, High, or Critical. |
| `created_at` | When the alert was raised. |
| `entity_type` | Job, Part, Technician, Van, or Warehouse. |
| `entity_id` | Id of that entity. Always exists in the matching table. |
| `description` | What is wrong, with the ids a dispatcher would need. |
| `status` | Open, Acknowledged, or Resolved. 'Right now' means status = Open. |
| `recommended_action` | Suggested next step for the demo. |

## Location ids that are not table keys

| Code | Meaning |
| --- | --- |
| `SUP-NORTHWIND` | Fictional parts supplier. Appears as `from_location_id` on Received transactions. |
| `SCRAP` | Fictional scrap destination. Appears as `to_location_id` on Scrapped transactions. |
