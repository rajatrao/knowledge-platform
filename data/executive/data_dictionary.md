# Data dictionary

Column definitions for `data/executive`. All figures are synthetic.

## markets.csv

- `market_id`: Market key MKT-001 through MKT-007.
- `market_name`: Austin Metro, North Austin, Round Rock, Cedar Park, Georgetown, San Marcos, or Pflugerville.
- `company_name`: Always Lumenfield, the fictional company.
- `region`: Always Central Texas.
- `status`: Planning, Launching, Active, Scaling, or Paused.
- `warehouse_id`: Serving warehouse. Must exist in data/warehouses.csv.
- `primary_cities`: Technician and customer cities rolled into this market.
- `technician_count`: Roster used for capacity. Matches technicians.csv except the San Marcos launch roster.
- `certified_technician_count`: Certified roster. Must be less than or equal to technician_count.
- `field_extract_technician_count`: Count of technicians.csv rows in primary_cities.
- `field_extract_certified_count`: Those rows whose certifications field is non-empty.
- `open_positions`: Unfilled requisitions. Not included in technician_count.
- `status_date`: Date the current status took effect.
- `service_note`: Short operating note. Not a rank.

## market_performance.csv

- `period`: Month YYYY-MM from 2026-04 through 2026-09.
- `market_id`: Market key.
- `installations_scheduled`: Sum of daily scheduled installs.
- `installations_completed`: Sum of daily completed installs. Source of truth for the month.
- `installations_target`: Sum of daily targets.
- `installation_attainment_percentage`: 100 times completed divided by target. Blank when target is 0.
- `first_time_completion_count`: Sum of daily first-time completions.
- `first_time_completion_rate`: first_time_completion_count divided by installations_completed.
- `rework_count`: Sum of daily rework. With first-time completions, equals installations_completed.
- `rework_rate`: rework_count divided by installations_completed.
- `average_cycle_time_days`: Completion-weighted average of daily cycle time.
- `jobs_waiting_for_parts`: Snapshot on the last day of the month in the daily file, not a sum.
- `customer_delay_count`: Sum of daily customer delays.
- `critical_incidents`: Sum of daily critical incident flags.
- `stockout_events`: Sum of daily stockout flags. A flag is a market-day, so two markets can both count the same warehouse day.

## deployment_metrics.csv

- `deployment_date`: Calendar day from 2026-04-01 through 2026-09-27.
- `market_id`: Market key.
- `installations_scheduled`: Installations booked that day.
- `installations_completed`: Installations finished that day.
- `installations_target`: Operating-plan target that day.
- `first_time_completion_count`: Completions that did not need rework.
- `rework_count`: Completions that were rework. Adds with first-time completions to installations_completed.
- `average_cycle_time_days`: Cycle time for completions that day. Blank when completed is 0.
- `jobs_waiting_for_parts`: End-of-day queue snapshot.
- `customer_delay_count`: Customers delayed that day.
- `critical_incidents`: Critical incident flags that day.
- `stockout_events`: 1 when that market-day was hit by a stockout, else 0.

## customer_funnel.csv

- `week_start`: Monday of the week.
- `market_id`: Market key.
- `leads`: New leads.
- `qualified_leads`: Leads that qualified. Less than or equal to leads.
- `site_surveys`: Surveys. Less than or equal to qualified leads.
- `proposals`: Proposals. Less than or equal to surveys.
- `contracts`: Contracts. Less than or equal to proposals.
- `installations_scheduled`: Sum of daily scheduled installs that week.
- `installations_completed`: Sum of daily completed installs that week.

## customer_experience_metrics.csv

- `week_start`: Monday of the week.
- `market_id`: Market key.
- `csat_score`: Customer satisfaction on a 0-100 scale.
- `nps`: Synthetic net promoter score derived from CSAT, from -100 to 100.
- `average_response_time_hours`: Average first-response time in hours.
- `repeat_contact_rate`: Share of contacts that were repeats, from 0 to 1.
- `installation_complaint_count`: Installation complaints opened that week.
- `survey_responses`: Survey responses that week.

## customer_issues.csv

- `issue_id`: ISS-001 through ISS-080.
- `opened_date`: Date the issue was opened.
- `market_id`: Market key.
- `customer_id`: Field customer id from customer_sites.csv. Blank only if unset.
- `site_id`: Engineering site id when the issue references a device. Blank for field-only issues. customer_sites.csv has no site id.
- `related_job_id`: jobs.csv job id, or blank.
- `related_device_id`: devices.csv device id, or blank.
- `category`: Installation Delay, Installation Quality, Parts Wait, Firmware, Hardware Reliability, Scheduling, Communication, or Launch.
- `severity`: Critical, High, Medium, or Low.
- `status`: Open or Closed.
- `summary`: Two or three synthetic sentences.

## workforce_metrics.csv

- `week_start`: Monday of the week.
- `market_id`: Market key.
- `technician_count`: Roster that week. Flat in this pack.
- `certified_technician_count`: Certified roster. Less than or equal to technician_count.
- `open_positions`: Unfilled requisitions.
- `scheduled_installations`: Sum of daily scheduled installs that week.
- `installations_completed`: Sum of daily completed installs that week.
- `utilization_percentage`: 100 times scheduled divided by certified times 8, except San Marcos, which uses a training load of 40.
- `overtime_hours`: Two hours for each scheduled install above certified weekly capacity. Zero when the book fits.

## warehouse_metrics.csv

- `week_start`: Monday of the week.
- `warehouse_id`: W001, W002, or W003.
- `stockout_events`: Sum of daily stockout flags for markets served by this warehouse.
- `jobs_waiting_for_parts`: Sum of market waiting snapshots on the last day of the week that exists in the daily file.
- `fill_rate_percentage`: Modeled fill rate. W001 steps down after 2026-08-24.
- `inventory_accuracy_percentage`: Modeled cycle-count accuracy.
- `cycle_counts_completed`: Cycle counts finished that week.
- `lines_below_reorder`: Snapshot count of warehouse_inventory lines under reorder. Repeated every week.
- `wms_core_status`: Operational for all three warehouses.
- `launch_location_configured`: yes, except W003, where San Marcos launch locations are not configured.
- `notes`: Short warehouse note for the week.

## inventory_risk.csv

- `risk_id`: IR-001 through IR-020.
- `as_of_date`: 2026-09-27.
- `part_id`: Part id from parts.csv.
- `warehouse_id`: Warehouse id.
- `part_name`: Name from parts.csv.
- `part_criticality`: Criticality from parts.csv.
- `current_available_quantity`: quantity_available from warehouse_inventory.csv for this part and warehouse.
- `weekly_consumption`: Planning consumption per week. Not a purchase-order quantity.
- `weeks_of_supply`: current_available_quantity divided by weekly_consumption, rounded to 1 decimal.
- `stockout_risk`: Critical, High, Medium, or Low.
- `jobs_blocked`: Count of linked waiting jobs called out in the note.
- `affected_market_ids`: Markets whose warehouse_id matches this row.
- `note`: Why the line is on the register.

## engineering_health_metrics.csv

- `week_start`: Monday of the week.
- `firmware_related_incidents`: Firmware-related incidents opened or active in the executive rollup that week.
- `active_incidents`: Week-end open engineering incidents in this rollup.
- `new_incidents`: Incidents opened that week.
- `resolved_incidents`: Incidents resolved that week. active moves by new minus resolved.
- `devices_on_firmware_430`: Devices treated as on 4.3.0 that week. Latest week matches the devices.csv census.
- `rollout_affected_device_count`: INC-002 affected_device_count on the spike week; census count on the decline week.
- `primary_incident_id`: INC-002, INC-022, or blank.
- `notes`: Tie to the engineering incident file.

## reliability_metrics.csv

- `period`: Month YYYY-MM.
- `device_type`: Device type present in devices.csv.
- `hardware_revision`: Hardware revision present for that device type.
- `installed_base`: Device census count for that type and revision.
- `failure_count`: Failures in the month. failure_rate times installed_base.
- `failure_rate`: failure_count divided by installed_base.
- `related_incident_id`: INC-005 on Battery HW-C rows, else blank.
- `related_device_ids`: Degraded HW-C battery ids on Battery HW-C rows.
- `notes`: Limitation of the census and of the HW-C mechanism.

## company_metrics.csv

- `period`: Month from 2025-10 through 2026-09.
- `installations_scheduled`: Sum of markets from 2026-04. Earlier months are company-only history.
- `installations_completed`: Sum of markets from 2026-04.
- `installations_target`: Sum of market targets from 2026-04.
- `installation_attainment_percentage`: 100 times completed divided by target.
- `first_time_completion_rate`: Company first-time completions divided by completed installs, from 2026-04.
- `critical_incidents`: Sum of market critical incidents from 2026-04.
- `stockout_events`: Sum of market stockout events from 2026-04.
- `average_csat`: Unweighted mean of market-week CSAT scores whose week_start falls in the month.
- `workforce_utilization_percentage`: Unweighted mean of market-week utilization whose week_start falls in the month.
- `open_critical_risks`: 2026-09 matches open Critical rows in executive_risks. Earlier months are a synthetic history of the count.
- `drilldown_available`: yes from 2026-04, no before that.
- `notes`: How the month relates to market_performance.

## executive_risks.csv

- `risk_id`: RSK-01 through RSK-20.
- `opened_date`: Date opened.
- `severity`: Critical, High, Medium, or Low.
- `status`: open, mitigating, monitoring, or closed.
- `market_id`: Market key or blank.
- `warehouse_id`: Warehouse id or blank.
- `part_id`: Part id or blank.
- `related_incident_id`: Engineering incident id or blank.
- `related_initiative_id`: Initiative id or blank.
- `scenario_id`: SCN id or blank.
- `affected_metric`: Metric name that exists in another table.
- `observed_value`: Value of that metric taken from the generated tables.
- `title`: Short title.
- `summary`: What the risk claims, in a sentence or two.

## executive_initiatives.csv

- `initiative_id`: INIT-01 through INIT-08.
- `initiative_name`: Name of the initiative.
- `status`: Active or On Hold.
- `start_date`: Start date. Georgetown's initiative starts 2026-07-06.
- `target_end_date`: Target end date.
- `owner_role`: Role only. No employee name.
- `market_id`: Market key or blank.
- `related_risk_id`: Risk id or blank.
- `related_incident_id`: Incident id or blank.
- `scenario_id`: SCN id.
- `expected_effect`: What the initiative is supposed to change.
- `status_note`: Whether the metric tables already show the effect.

## weekly_business_review.csv

- `week_start`: Monday. Sixteen weeks ending 2026-09-21.
- `installations_completed`: Company sum of daily completions that week.
- `installations_target`: Company sum of daily targets that week.
- `installation_attainment_percentage`: 100 times completed divided by target.
- `average_csat`: Unweighted mean of the seven market CSAT scores that week.
- `critical_incidents`: Sum of daily critical flags that week.
- `stockout_events`: Sum of daily stockout flags that week.
- `workforce_utilization_percentage`: Unweighted mean of the seven market utilization figures.
- `firmware_related_incidents`: From engineering_health_metrics for the same week.
- `major_risks`: Short text pointing at scenario ids.
- `executive_attention_items`: Short text pointing at scenario ids.

## executive_alerts.csv

- `alert_id`: ALT-001 through ALT-015.
- `created_at`: Date raised.
- `severity`: Critical, High, Medium, or Low.
- `status`: Open, Acknowledged, or Resolved.
- `market_id`: Market key or blank.
- `scenario_id`: SCN id or blank.
- `related_risk_id`: Risk id or blank.
- `related_incident_id`: Incident id or blank.
- `title`: Short title.
- `summary`: What the alert says.

## executive_documents.csv

- `document_id`: DOC-001 through DOC-050.
- `document_type`: Strategy, Operating Plan, Market Review, Weekly Business Review, Product Review, Engineering Review, Operations Review, Risk Review, Launch Plan, or Executive Decision Memo.
- `title`: Document title.
- `document_date`: Document date.
- `author_role`: Role only. No employee name.
- `market_id`: Market key or blank.
- `related_risk_id`: Risk id or blank.
- `related_initiative_id`: Initiative id or blank.
- `related_incident_id`: Incident id or blank.
- `summary`: A few synthetic sentences.
