# Executive test questions

Synthetic questions for the Lumenfield CEO pack. Snapshot 2026-09-27.
Answer from `data/executive` and the field-ops and engineering CSVs. Do not treat a coincidence of two bad metrics as proof of a single cause.

## COMPANY

1. What is company installations_completed for 2026-09, and which file is the source of truth behind it?
2. Do 2026-09 company installations equal the sum of market_performance for MKT-001 through MKT-007?
3. Which months from 2025-10 through 2026-09 missed the company installation target?
4. How do company stockout_events in 2026-09 compare with 2026-07?
5. How do company critical_incidents in 2026-09 compare with 2026-08?
6. Why can a CEO not drill company_metrics before 2026-04 into a market?
7. What is installation attainment for the latest company month?
8. Did installations_completed rise in every month from 2025-10 through 2026-09?
9. How should company_metrics.installations_completed be reconciled to deployment_metrics?
10. What is the snapshot date of this executive pack, and which markets are in it?

## MARKETS

11. Why are installations down in North Austin (MKT-002)?
12. Which market is Scaling, and do demand, first-time completion, incidents, certified techs, and inventory support more volume there?
13. Why is San Marcos (MKT-006) still Launching?
14. What is the status of Austin Metro (MKT-001), and which warehouse serves it?
15. Which markets share W001 Mesa Volt Depot?
16. Compare 2026-09 installations_completed for Cedar Park (MKT-004) and North Austin (MKT-002).
17. What changed in Georgetown (MKT-005) cycle time and first-time completion after 2026-07-06?
18. Why is Pflugerville (MKT-007) Paused, and what were its September installations?
19. Do all seven markets have the same installation total?
20. How does Round Rock (MKT-003) September volume compare with the North Austin slowdown?
21. Which Active market, other than a launch or a pause, shows the installation slowdown?
22. Map MKT-001 through MKT-007 to warehouse ids and statuses.

## CUSTOMERS

23. How did North Austin CSAT move from the week of 2026-07-06 to the week of 2026-09-21?
24. Did response time, repeat contacts, and installation complaints rise in the same market where CSAT fell?
25. Where did installation complaints concentrate in the latest week?
26. How does Cedar Park CSAT in the latest week compare with North Austin?
27. How many customer_issues are tagged to MKT-002, and what categories dominate?
28. Which customer_issues reference J001 or J007, and what is each job's status in jobs.csv?
29. customer_sites.csv has no site_id. When is customer_issues.site_id populated, and where must that id exist?
30. What does the San Marcos funnel show for site surveys versus installations_completed?
31. Are Cedar Park contracts being followed by completed installs?
32. In North Austin, did contracts disappear, or did completed installs fall while scheduled work stayed up?

## OPERATIONS

33. For MKT-002 in 2026-09, show that market monthly installations equal the daily deployment sum.
34. What happened to jobs_waiting_for_parts in North Austin between June and September 2026?
35. How did rework_rate in MKT-002 change after 2026-08-24?
36. What is first_time_completion_rate for Cedar Park in 2026-09?
37. What is average cycle time in Georgetown for 2026-06 versus 2026-09?
38. Which warehouse weekly rows show the W001 stockout pattern after 2026-08-24?
39. How is installation_attainment_percentage calculated on the weekly business review?
40. What happened on 2026-09-16 in Cedar Park, and how did that change the company week?
41. What date range does deployment_metrics cover, and why is it longer than the latest 90 days?
42. Drill from company 2026-09 installations to MKT-002, then to one September day in deployment_metrics.

## WORKFORCE

43. How many technicians.csv rows roll up to North Austin, and what is certified_technician_count?
44. Where is scheduled installation demand rising faster than certified technician capacity?
45. What is open_positions for Austin Metro versus Cedar Park?
46. Is certified_technician_count ever greater than technician_count?
47. Why is San Marcos certified coverage 3 of 5, and how many of those people are in technicians.csv?
48. What do utilization and overtime look like for MKT-001 in the week of 2026-09-21?
49. Did Georgetown's improvement come from hiring, or from INIT-01 with flat headcount?
50. Which market is understaffed in the same window that installations fell?
51. What does utilization_percentage above 100 mean in this pack?

## INVENTORY

52. What is weeks_of_supply for P006 at W001, and what is quantity_available in warehouse_inventory.csv?
53. Which inventory_risk rows are Critical, and which are Low?
54. How does P018 at W002 compare with P018 at W001?
55. Which markets are exposed to the W001 P006 stockout?
56. Show that weeks_of_supply equals available quantity divided by weekly consumption for P006.
57. Which warehouses serve the customers on J001 and J007, and which short parts are actually in those warehouses?
58. Is W003 inventory and WMS setup complete enough for the San Marcos launch?
59. What is the reorder situation for P018, the 200A Class T Fuse?
60. Does a Critical stockout_risk on P006 by itself prove that parts, rather than staffing, caused the North Austin miss?

## ENGINEERING

61. What happened to firmware_related_incidents and active_incidents in the week of 2026-09-15?
62. Did those incident counts fully recover in the week of 2026-09-21?
63. Which incident is the firmware 4.3.0 regression, and how many devices did it affect?
64. Which devices are still on firmware 4.3.0 in devices.csv?
65. Which hardware revision has the higher failure_rate, and what is failure_count divided by installed_base?
66. Which incident describes the HW-C battery issue, and which degraded HW-C battery ids are in devices.csv?
67. How is engineering_health_metrics related to company_metrics.critical_incidents?
68. Compare Battery HW-C and Battery HW-B failure rates in 2026-09.
69. Why is INC-022 not the 4.3.0 spike?

## RISK

70. Which open Critical risks have an affected_metric that can be checked in another table?
71. Are all executive risks Critical?
72. What is the status mix of executive_risks across open, mitigating, monitoring, and closed?
73. Which risk says the San Marcos WMS configuration is unfinished?
74. Which risk tracks HW-C failure_rate, and what observed value does it carry?
75. Which risks are closed, and should they drive this week's review?
76. What is the difference between stockout_risk on inventory_risk and a row in executive_risks?
77. Which open High risks mention utilization, CSAT, or firmware?

## EXECUTIVE

78. What changed week over week in the 2026-09-21 business review versus 2026-09-14 for installs, CSAT, incidents, stockouts, and utilization?
79. Which initiatives are active, and which one started on 2026-07-06?
80. What should the CEO weigh before adding volume in Cedar Park while North Austin is missing plan?
81. Which executive alerts are still Open, and which Open alerts are Critical?
82. Which launch-plan document says the W003 WMS configuration is unfinished?
83. What does this pack warn against concluding when North Austin staffing and P006 are both short?
84. Which documents should be read before a review of INC-002?
85. What are SCN-01 through SCN-12, and which ids would you open for a Monday staff meeting?
86. Does the latest weekly business review install increase mean North Austin recovered?
87. Walk the drill-down from company_metrics to market_performance to deployment_metrics to a job, a part, a technician city, and an engineering incident.
