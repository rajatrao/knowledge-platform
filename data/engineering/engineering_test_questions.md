# Engineering test questions

Synthetic questions for the Engineer persona. Identifiers match the generated CSVs.
Snapshot time: 2026-09-27T16:00:00-05:00 America/Chicago.

1. Why did battery DEV-001 go offline?
2. What did pack temperature do in the hours before DEV-001 went offline?
3. Which fault code tripped DEV-001, and which component failed?
4. What is the confirmed root cause of INC-001?
5. What is the timeline of INC-001?
6. Which troubleshooting document should an engineer follow for THERM-201 on DEV-001?
7. Did the communication faults on DEV-012 start after the firmware update?
8. What changed between firmware 4.2.1 and 4.3.0?
9. What is the known issue in firmware 4.3.0, and which version fixes it?
10. Which devices installed 4.3.0, which rolled back to 4.2.1, and which are still on 4.3.0?
11. What do the hardware-in-loop tests say about heartbeat behavior on 4.3.0 versus 4.3.1?
12. Which configuration row shows the Limestone inverter DEV-019 was capped, and what is the value after the correction?
13. Did the repeated inverter faults on DEV-019 stop after the configuration change?
14. Which configuration parameters are outside the expected value in the current snapshot?
15. Why did gateway DEV-025 go offline?
16. How is the DEV-025 link loss different from the 4.3.0 heartbeat regression?
17. Which sites and devices share BAT-204, and what hardware revision do they have in common?
18. What did pack voltage do before the BAT-204 fault on DEV-026?
19. How is the temperature event on DEV-037 different from the shutdown on DEV-001?
20. Were the thermal alerts on DEV-037 false alarms?
21. What happened to inverter power on DEV-043?
22. Which ticket tracks the inverter power collapse, and why is it blocked?
23. What is the confirmed root cause of INC-008?
24. Which hypotheses are still open for INC-008, and which tickets are still open?
25. What do INC-009 and INC-010 have in common, and how do their confirmed causes differ?
26. Which systems should engineering investigate proactively, before they fail?
27. What early signals are present on DEV-054, DEV-061, and DEV-062?
28. Are there conflicting engineering documents?
29. Which documents disagree about the response to THERM-201, and which IDs are they?
30. What components are installed on DEV-001, and what is the cooling fan status?
31. What is the firmware history of DEV-011?
32. Which devices are still on firmware 4.1.4, and why have they not taken 4.3.1?
33. Which open alerts are warnings or info rather than critical?
34. What is the status of the site that hosts DEV-001, and what else is installed there?
35. How many devices are online compared with faulted or offline?
36. What are the recommended diagnostic steps for COM-214?
37. Which incidents are firmware related?
38. Which anomaly windows overlap the telemetry that shows the DEV-001 temperature rise?
39. What preventive action came out of the HW-C investigation INC-005?
40. What grid event latched inverter DEV-066, and why is that not a power-module failure?
41. Which incidents share the DC bus capacitor failure mode?
42. What is the current firmware of DEV-001, and was firmware ruled out for its shutdown?
43. Which engineering change halted firmware 4.3.0?
44. What does a configuration_status of Mismatch mean, and which live rows are mismatches?
45. What evidence separates sensor drift on DEV-037 from a real thermal shutdown?
46. Which test is blocked, and which incident does that leave open?
47. What error-code document describes BAT-204, and which component type does it point to?
48. Which devices are in Maintenance, Degraded, Faulted, or Offline?
49. After DEV-008 rolled back to 4.2.1, did latency recover?
50. What should the field do next for DEV-001 even though the investigation is resolved?
