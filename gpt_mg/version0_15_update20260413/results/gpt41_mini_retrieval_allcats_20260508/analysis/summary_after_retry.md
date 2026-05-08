# GPT-4.1 mini Retrieval Category Study Summary

- Full-run pass: 273/280 (97.50%)
- After targeted retry pass: 276/280 (98.57%)
- After targeted retry avg DET: 97.0821
- Remaining failures: 4

| Cat | Rows | Pass | Fail | Pass rate | Avg DET | GT exact | Avg prompt tok | Avg latency |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 30 | 30 | 0 | 100.00% | 99.652 | 25/30 | 26844.1 | 2.4103s |
| 2 | 30 | 30 | 0 | 100.00% | 98.5588 | 23/30 | 23754.6 | 2.0799s |
| 3 | 30 | 29 | 1 | 96.67% | 98.1758 | 23/30 | 25244.4 | 2.1359s |
| 4 | 30 | 28 | 2 | 93.33% | 96.2227 | 18/30 | 25184.3 | 2.1145s |
| 5 | 30 | 29 | 1 | 96.67% | 96.7384 | 19/30 | 25433.8 | 2.3176s |
| 6 | 30 | 30 | 0 | 100.00% | 98.4998 | 20/30 | 25585.0 | 2.4562s |
| 7 | 50 | 50 | 0 | 100.00% | 95.099 | 18/50 | 25771.6 | 2.5738s |
| 8 | 50 | 50 | 0 | 100.00% | 95.8522 | 20/50 | 25593.3 | 2.557s |

## Remaining failures
- Row 63 / Cat 3: DET 69.9000, reasons ["gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]. If the cloud service is activated, upload test.png file to the cloud.
- Row 107 / Cat 4: DET 69.7752, reasons ["enum_grounding", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage", "semantic"]. When motion is detected in the bedroom, turn on the bedroom air conditioner.
- Row 118 / Cat 4: DET 69.9000, reasons ["extraneous", "gt_mismatch", "gt_receiver_coverage", "gt_service_coverage"]. When any presence sensor in the hallway detects presence, set all hallway lights to purple.
- Row 150 / Cat 5: DET 69.9000, reasons ["dataflow", "gt_mismatch", "semantic"]. Check the wine cellar temperature now and again in 10 minutes. If it has changed by 1 degree or higher, announce through the speaker that the wine cellar temperature has changed rapidly.
