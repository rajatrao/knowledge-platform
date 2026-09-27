# Executive scenarios

Twelve situations encoded in the metric tables. Scenario ids are pointers. They are not a ranking.

A coincidence of staffing and inventory shortages does not prove which constraint was primary.

## SCN-01 Installation slowdown

Question: Why are installations down?

Ids: Market North Austin (North Austin is MKT-002), warehouse W001, part P006.

What the numbers show: 2026-09 installations_completed for MKT-002 are 11, versus 69 in 2026-07. The break starts 2026-08-24. Rework rate is 0.636 in September versus 0.072 in July. Cycle time is 18.0 days. Jobs waiting are 8. The field extract for Manor is the North Austin roster, and open_positions is 4. P006 at W001 has weeks_of_supply 0.0.

Do not conclude: Staffing and inventory are both bad in this window. That co-occurrence does not prove which constraint was primary.

## SCN-02 Market ready to scale

Question: Which market can take more volume?

Ids: Cedar Park is MKT-004, warehouse W002. There is no best-market column.

What the numbers show: September installations_completed are 128 with first_time_completion_rate 0.992. Stockout events and jobs waiting are 0. Critical incidents are 0. September overtime hours are 0. Certified headcount equals the Cedar Park and Leander extract. W002 is not the P006 stockout warehouse.

Do not conclude: High volume alone is not the signal. Austin Metro has high volume and is over capacity.

## SCN-03 Launch blocked

Question: Why has San Marcos not launched?

Ids: San Marcos is MKT-006, status Launching, warehouse W003.

What the numbers show: Certified technicians are 3 of 5 on the launch roster (60 percent). field_extract_technician_count is only the Buda rows in technicians.csv. September installations_completed are 0. warehouse_metrics.launch_location_configured is no for W003. DOC-001 and RSK-04 say the WMS configuration is unfinished. P003 at W003 is on the inventory register with available 0.

Do not conclude: Georgetown also uses W003 and is installing. The WMS gap is the San Marcos launch locations, not a dead warehouse.

## SCN-04 Inventory-driven delays

Question: Which part is short, and who is waiting?

Ids: Part P006 at W001 is the Critical line. Part P018 at W002 is a separate High line. J001 (Round Rock, W002) is the Class T fuse wait and lines up with low P018 at W002. J007 (Cedar Park, W002) is an inverter repair waiting on parts; W002 still has P006 available, so J007 does not explain the W001 stockout.

What the numbers show: P006 available is 0, weekly consumption is 4, weeks_of_supply is 0.0. North Austin stockout_events in September are 19 and customer_delay_count is 38. P018 at W002 has weeks_of_supply 1.0 and available 2.

Do not conclude: A part at zero weeks of supply is a fact about the balance. It is not, by itself, the proven cause of every missed install.

## SCN-05 Firmware spike after 4.3.0

Question: What happened the week of 2026-09-15?

Ids: Incident INC-002. Firmware 4.3.0. Week starting 2026-09-14, then the week starting 2026-09-21.

What the numbers show: INC-002 affected_device_count is 5. firmware_related_incidents went to 7 and active_incidents to 12, then the next week they were 3 and 8. devices.csv still has 2 devices on 4.3.0. ALT-003, RSK-03, INIT-05, and DOC-002 point here.

Do not conclude: The following week is a partial decline, not a return to the earlier baseline, and not a closed incident.

## SCN-06 Customer satisfaction decline

Question: How did customers in the slowdown market react?

Ids: North Austin, MKT-002.

What the numbers show: CSAT moved from 82 in the week of 2026-07-06 to 56 in the week of 2026-09-21. Latest response time is 23 hours, repeat contact rate is 0.26, and installation complaints are 9.

Do not conclude: Cedar Park CSAT stays high in the same weeks. The decline is not company-wide in every market.

## SCN-07 Workforce bottleneck

Question: Where is demand outrunning certified techs?

Ids: Austin Metro, MKT-001. North Austin is the smaller absolute crew in SCN-01.

What the numbers show: Austin Metro scheduled installations rose from 30 in the week of 2026-04-06 to 84 in the week of 2026-09-21. Certified headcount is flat. Utilization is 131 and overtime is 40 hours. open_positions is 3.

Do not conclude: Utilization above 100 is the capacity rule in this pack. It is not a timecard feed.

## SCN-08 Hardware revision reliability

Question: Which revision fails more often?

Ids: Hardware revision HW-C, incident INC-005, degraded batteries DEV-026;DEV-031;DEV-034.

What the numbers show: Battery HW-C failure_rate in 2026-09 is 0.4286 (3 / 7). Battery HW-B is 0.0333. Other HW-C device types are also higher than their peers; INC-005 only confirms the battery mechanism.

Do not conclude: installed_base is today's census, so the rate is not a historical survival curve. Small bases move the rate a lot.

## SCN-09 Operational improvement

Question: Which market got better, and after which start date?

Ids: Georgetown, MKT-005. Initiative INIT-01 started 2026-07-06.

What the numbers show: Cycle time went from 15.0 days in 2026-06 to 8.0 days in 2026-09. First-time completion went from 0.667 to 0.947. Rework fell because first-time and rework add to one. Technician count did not change.

Do not conclude: This is a different market from the North Austin slowdown.

## SCN-10 Open risks with metric backing

Question: Which open risks are more than a label?

Ids: RSK-01 Critical open, installations_completed, MKT-002. RSK-02 Critical open, weeks_of_supply, P006. RSK-03 High open, firmware_related_incidents, INC-002. RSK-04 High open, certified_technician_count, MKT-006. RSK-05 High open, failure_rate, INC-005. RSK-06 High open, utilization_percentage, MKT-001. RSK-07 High open, csat_score, MKT-002.

What the numbers show: Each observed_value is copied from the metric table named in affected_metric. Statuses also include mitigating, monitoring, and closed. Severities include Medium and Low.

Do not conclude: A closed Critical risk, such as RSK-15, is not a current fire.

## SCN-11 Week-over-week change

Question: What moved in the latest business review?

Ids: weekly_business_review weeks of 2026-09-21 and 2026-09-14.

What the numbers show: Installs 122 then 127. CSAT 77.1 then 76.6. Critical incidents 2 then 1. Stockouts 11 then 6. Utilization 68.1 then 69.0. Firmware-related incidents 7 then 3.

Do not conclude: The install increase is the 2026-09-16 short completion day in Cedar Park falling out of the later week. North Austin completions did not recover.

## SCN-12 Drill-down path

Question: How do I go from the company number to a job, a part, and an incident?

Ids: company_metrics -> market_performance -> deployment_metrics -> jobs.csv, technicians.csv, warehouse_inventory.csv, engineering incidents and devices.

What the numbers show: Start at company_metrics 2026-09 installations_completed. Split it by market_performance. Open MKT-002 and confirm the month equals the sum of deployment_metrics days. P006 at W001 and P018 at W002 are inventory_risk rows whose quantities match warehouse_inventory.csv. J001 is the Round Rock fuse job next to low P018 at W002. J007 is a Cedar Park inverter job and is not a W001 customer. Technician cities for MKT-002 are Manor in technicians.csv. For the firmware week, open INC-002 and the devices still on 4.3.0. For the hardware revision, open INC-005 and Battery HW-C in reliability_metrics.

Do not conclude: Field customer ids and engineering customer ids do not join. Site ids on customer issues, when present, are engineering site ids.
