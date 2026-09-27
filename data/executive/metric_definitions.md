# Metric definitions

Each definition is how this pack computed the figure. Examples use the generated files.

A coincidence of staffing and inventory shortages does not prove which constraint was primary. In North Austin (MKT-002), certified headcount is tight and P006 at W001 is out of stock in the same weeks. The tables show that those conditions occurred together. They do not identify which one caused the installation decline.

## installations_completed

- Name: `installations_completed`
- Definition: Installations finished.
- Formula: Sum of deployment_metrics.installations_completed.
- Source file: deployment_metrics.csv, rolled to market_performance.csv and company_metrics.csv
- Time period: Day, month, and company month.
- Example: MKT-002 completed 11 installations in 2026-09. Company installations_completed for 2026-09 is 477, the sum of the seven markets.
- Limitation: Market-days are the source of truth only from 2026-04-01. Earlier company months have no market split. A coincidence of staffing and inventory shortages does not prove which constraint was primary. In North Austin (MKT-002), certified headcount is tight and P006 at W001 is out of stock in the same weeks. The tables show that those conditions occurred together. They do not identify which one caused the installation decline.

## installations_scheduled

- Name: `installations_scheduled`
- Definition: Installations booked.
- Formula: Sum of daily installations_scheduled.
- Source file: deployment_metrics.csv
- Time period: Day and week.
- Example: Austin Metro scheduled 84 installations in the week of 2026-09-21, up from 30 in the week of 2026-04-06.
- Limitation: Scheduled work is demand. It is not completions, and it is not proof that a crew or a part was available.

## installations_target

- Name: `installations_target`
- Definition: Operating-plan completions.
- Formula: Sum of daily installations_target.
- Source file: deployment_metrics.csv
- Time period: Day, week, and month.
- Example: Company target for 2026-09 is 726.
- Limitation: The San Marcos target stays on the books after completions stop. A target is a plan, not a forecast that was achieved.

## installation_attainment_percentage

- Name: `installation_attainment_percentage`
- Definition: Plan attainment.
- Formula: 100 * installations_completed / installations_target.
- Source file: weekly_business_review.csv and market_performance.csv
- Time period: Week or month.
- Example: The week of 2026-09-21 completed 127 against its target. Attainment is blank when the target is 0.
- Limitation: Attainment can rise because the prior week had a one-day shortfall. Check the market split before calling it a recovery.

## first_time_completion_rate

- Name: `first_time_completion_rate`
- Definition: Share of completions that were clean the first time.
- Formula: first_time_completion_count / installations_completed.
- Source file: market_performance.csv
- Time period: Month.
- Example: Cedar Park 2026-09 first_time_completion_rate is 0.992. Georgetown moved from 0.667 in 2026-06 to 0.947 in 2026-09.
- Limitation: Blank when completions are 0, as in San Marcos in September. A high rate on a tiny base is not the same as a high rate on a full book.

## rework_rate

- Name: `rework_rate`
- Definition: Share of completions that were rework.
- Formula: rework_count / installations_completed.
- Source file: market_performance.csv
- Time period: Month.
- Example: North Austin rework_rate was 0.072 in 2026-07 and 0.636 in 2026-09.
- Limitation: First-time and rework counts add to completions, so the two rates add to 1 when both are present. Rework rising with a stockout still does not name the cause.

## average_cycle_time_days

- Name: `average_cycle_time_days`
- Definition: Completion-weighted cycle time.
- Formula: Sum of daily cycle time times completions, divided by completions.
- Source file: market_performance.csv
- Time period: Month.
- Example: Georgetown cycle time was 15.0 days in 2026-06 and 8.0 days in 2026-09. North Austin September cycle time is 18.0 days.
- Limitation: Days with zero completions are left out of the weight. The average does not say why the cycle moved.

## jobs_waiting_for_parts

- Name: `jobs_waiting_for_parts`
- Definition: Queue snapshot.
- Formula: Last daily snapshot in the period, not a sum.
- Source file: deployment_metrics.csv and market_performance.csv
- Time period: Day or month-end.
- Example: North Austin jobs_waiting_for_parts at September month-end is 8.
- Limitation: A coincidence of staffing and inventory shortages does not prove which constraint was primary. In North Austin (MKT-002), certified headcount is tight and P006 at W001 is out of stock in the same weeks. The tables show that those conditions occurred together. They do not identify which one caused the installation decline.

## customer_delay_count

- Name: `customer_delay_count`
- Definition: Customers delayed.
- Formula: Sum of daily customer_delay_count.
- Source file: deployment_metrics.csv
- Time period: Day and month.
- Example: North Austin customer_delay_count for 2026-09 is 38.
- Limitation: A delay count does not say whether the customer was waiting on a crew, a part, or a schedule change.

## critical_incidents

- Name: `critical_incidents`
- Definition: Field critical-incident flags.
- Formula: Sum of daily critical_incidents.
- Source file: deployment_metrics.csv, summed to market and company.
- Time period: Day and month.
- Example: Company critical_incidents for 2026-09 is 4.
- Limitation: This is not the engineering incident register. Firmware volume lives in engineering_health_metrics.

## stockout_events

- Name: `stockout_events`
- Definition: Market-days flagged for a stockout.
- Formula: Sum of daily stockout_events.
- Source file: deployment_metrics.csv
- Time period: Day, week, and month.
- Example: North Austin stockout_events in 2026-09 are 19. The week of 2026-09-14 company stockout_events were 11, then 6 the next week.
- Limitation: Two markets on the same warehouse can each flag the same calendar day. Summing markets is not a count of unique parts.

## csat_score

- Name: `csat_score`
- Definition: Customer satisfaction.
- Formula: 0-100 score on the weekly experience row.
- Source file: customer_experience_metrics.csv
- Time period: Week.
- Example: North Austin CSAT was 82 in the week of 2026-07-06 and 56 in the week of 2026-09-21.
- Limitation: Company average CSAT is an unweighted mean of market-weeks. It is not weighted by survey responses.

## nps

- Name: `nps`
- Definition: Net promoter score.
- Formula: Clipped (csat_score - 75) * 2.
- Source file: customer_experience_metrics.csv
- Time period: Week.
- Example: North Austin's latest CSAT of 56 produces a negative NPS.
- Limitation: NPS here is derived from CSAT. It is not a separate survey.

## average_response_time_hours

- Name: `average_response_time_hours`
- Definition: First response time.
- Formula: Weekly average hours.
- Source file: customer_experience_metrics.csv
- Time period: Week.
- Example: North Austin response time in the latest week is 23 hours.
- Limitation: Response time moving with CSAT shows co-movement, not the cause of the installation miss.

## repeat_contact_rate

- Name: `repeat_contact_rate`
- Definition: Repeat contact share.
- Formula: Repeats divided by contacts, stored from 0 to 1.
- Source file: customer_experience_metrics.csv
- Time period: Week.
- Example: North Austin repeat_contact_rate in the latest week is 0.26.
- Limitation: The rate is not a ticket-system extract.

## installation_complaint_count

- Name: `installation_complaint_count`
- Definition: Installation complaints.
- Formula: Count of complaints that week.
- Source file: customer_experience_metrics.csv
- Time period: Week.
- Example: North Austin installation complaints in the latest week are 9.
- Limitation: Complaint counts are not the same object as customer_issues rows, though both concentrate on North Austin.

## technician_count

- Name: `technician_count`
- Definition: Roster headcount.
- Formula: City rollup from technicians.csv, except the San Marcos launch roster of 5.
- Source file: workforce_metrics.csv
- Time period: Week.
- Example: North Austin technician_count is the Manor rollup. San Marcos technician_count is 5 while field_extract_technician_count is the Buda subset.
- Limitation: Do not add the San Marcos roster to the field extract.

## certified_technician_count

- Name: `certified_technician_count`
- Definition: Certified headcount.
- Formula: Non-empty certifications in the extract, except San Marcos where the launch roster certified count is 3.
- Source file: workforce_metrics.csv
- Time period: Week.
- Example: San Marcos certified_technician_count 3 divided by technician_count 5 is 0.6.
- Limitation: Certification here is not a specific license level except where the service note says otherwise.

## open_positions

- Name: `open_positions`
- Definition: Unfilled roles.
- Formula: Constant requisition count by market.
- Source file: workforce_metrics.csv
- Time period: Week.
- Example: Austin Metro open_positions is 3. North Austin open_positions is 4.
- Limitation: Open positions are not included in technician_count.

## utilization_percentage

- Name: `utilization_percentage`
- Definition: Booked load versus certified capacity.
- Formula: 100 * scheduled_installations / (certified_technician_count * 8). San Marcos is fixed at 40.
- Source file: workforce_metrics.csv
- Time period: Week.
- Example: Austin Metro utilization in the week of 2026-09-21 is 131.
- Limitation: Above 100 means scheduled work exceeds the capacity rule. It does not, by itself, prove overtime was worked or that parts were available. A coincidence of staffing and inventory shortages does not prove which constraint was primary. In North Austin (MKT-002), certified headcount is tight and P006 at W001 is out of stock in the same weeks. The tables show that those conditions occurred together. They do not identify which one caused the installation decline.

## overtime_hours

- Name: `overtime_hours`
- Definition: Hours above the capacity rule.
- Formula: 2 * max(0, scheduled_installations - certified_technician_count * 8).
- Source file: workforce_metrics.csv
- Time period: Week.
- Example: Austin Metro overtime in the week of 2026-09-21 is 40 hours. Cedar Park September overtime is 0.
- Limitation: The formula is a planning conversion, not a payroll extract.

## weeks_of_supply

- Name: `weeks_of_supply`
- Definition: Coverage of the on-hand available balance.
- Formula: current_available_quantity / weekly_consumption, rounded to 1 decimal.
- Source file: inventory_risk.csv
- Time period: Snapshot 2026-09-27.
- Example: P006 at W001 has available 0, weekly consumption 4, and weeks_of_supply 0.0.
- Limitation: Consumption is a planning rate. A value of 0.0 means the available balance is 0, not that demand was measured that week. A coincidence of staffing and inventory shortages does not prove which constraint was primary. In North Austin (MKT-002), certified headcount is tight and P006 at W001 is out of stock in the same weeks. The tables show that those conditions occurred together. They do not identify which one caused the installation decline.

## stockout_risk

- Name: `stockout_risk`
- Definition: Register severity for a part-warehouse line.
- Formula: Set from the balance versus consumption, with P006 at W001 forced to Critical.
- Source file: inventory_risk.csv
- Time period: Snapshot.
- Example: P006 at W001 is Critical. At least one other line is Low.
- Limitation: stockout_risk is not the same column as executive_risks.severity.

## current_available_quantity

- Name: `current_available_quantity`
- Definition: Available on-hand balance.
- Formula: warehouse_inventory.quantity_available for the part and warehouse.
- Source file: inventory_risk.csv
- Time period: Snapshot 2026-09-27.
- Example: P006 at W001 current_available_quantity is 0. P018 at W002 is 2.
- Limitation: Van inventory is not included. A warehouse can show stock while a job still waits on a van.

## firmware_related_incidents

- Name: `firmware_related_incidents`
- Definition: Firmware-related incident count in the executive rollup.
- Formula: Set so the week of 2026-09-15 spikes and the next week declines part way, using INC-002's affected device count.
- Source file: engineering_health_metrics.csv
- Time period: Week.
- Example: Week starting 2026-09-14 has 7 firmware_related_incidents. Week starting 2026-09-21 has 3. INC-002 affected_device_count is 5.
- Limitation: This rollup is not a raw count of every engineering_incidents.csv row. INC-022 is a different firmware note on 4.3.1.

## active_incidents

- Name: `active_incidents`
- Definition: Week-end open incidents in the executive engineering rollup.
- Formula: Prior active + new_incidents - resolved_incidents.
- Source file: engineering_health_metrics.csv
- Time period: Week.
- Example: Active incidents were 12 in the spike week and 8 the next week.
- Limitation: A partial decline is not a close. INC-002 remains the primary incident.

## failure_rate

- Name: `failure_rate`
- Definition: Share of the installed base that failed in the month.
- Formula: failure_count / installed_base.
- Source file: reliability_metrics.csv
- Time period: Month, by device type and hardware revision.
- Example: Battery HW-C in 2026-09 failed 3 times on a base of 7, rate 0.4286. Battery HW-B rate is 0.0333.
- Limitation: installed_base is the 2026-09-27 census for every month. Small bases make rates jump. INC-005 supports a battery mechanism, not every HW-C device type.

## failure_count

- Name: `failure_count`
- Definition: Failures in the month.
- Formula: Numerator of failure_rate.
- Source file: reliability_metrics.csv
- Time period: Month.
- Example: Battery HW-C failure_count in 2026-09 is 3.
- Limitation: Counts are synthetic monthly totals consistent with the rate. They are not a dump of device_faults.csv.

## installed_base

- Name: `installed_base`
- Definition: Devices of that type and revision.
- Formula: Count of devices.csv rows.
- Source file: reliability_metrics.csv
- Time period: Census repeated each month.
- Example: Battery HW-C installed_base is 7.
- Limitation: The census does not reconstruct how many units were installed in April versus September.

## leads

- Name: `leads`
- Definition: Top of the weekly funnel.
- Formula: Generated weekly stage above qualified leads.
- Source file: customer_funnel.csv
- Time period: Week.
- Example: San Marcos keeps leads and surveys while installations_completed stays at 0 in September.
- Limitation: Funnel stages are not the same object as customer_issues.
