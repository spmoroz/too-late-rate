# Too Late rate report

Generated 2026-09-26 18:13 UTC with too-late-rate 1.0.0. Local timezone for naive timestamps and quarters: `Europe/Zurich`.

## Headline

- **Too Late rate:** 4.0% (235/5923; 95% CI 3.5-4.5%). Report finalized strictly before the AI result was available; no threshold.
- **Timing categories** (N=5863 with report creation time): before report creation 85.6%, during dictation 10.5%, after finalization 3.9%.
- **Total latency** (AI result available minus study end, N=5941): median 3.17 min [IQR 2.05-4.92].
- **Latency decomposition** (N=5941 with AI processing time): AI processing median 1.22 min [IQR 0.73-2.13]; routing time median 1.85 min; routing share (ratio of means) 60.1%.
- **Routing components** (N=5941): median fetching 0.90 min, upload 0.57 min, download 0.25 min.
- **Report TAT** (finalized minus created, N=5892): median 4.02 min [IQR 1.78-9.12].

## By AI solution

| ai_solution | Too Late n/N | Too Late % | 95% CI | Before creation % | During dictation % | After finalization % | Latency median [IQR], min | Processing median, min | Routing share % |
|---|---|---|---|---|---|---|---|---|---|
| AI solution A | 21/1207 | 1.7 | 1.1-2.6 | 89.5 | 8.8 | 1.8 | 1.80 [1.53-2.11] | 0.68 | 60.0 |
| AI solution B | 15/1165 | 1.3 | 0.8-2.1 | 91.8 | 6.9 | 1.3 | 3.60 [2.98-4.33] | 1.40 | 59.5 |
| AI solution C | 134/1222 | 11.0 | 9.3-12.8 | 71.2 | 17.9 | 10.9 | 10.43 [8.44-13.45] | 4.08 | 60.3 |
| AI solution D | 35/1150 | 3.0 | 2.2-4.2 | 87.1 | 9.9 | 3.0 | 2.07 [1.70-2.68] | 0.80 | 60.1 |
| AI solution E | 30/1179 | 2.5 | 1.8-3.6 | 88.9 | 8.7 | 2.4 | 3.50 [2.98-4.18] | 1.35 | 59.9 |

## By modality

| modality | Too Late n/N | Too Late % | 95% CI | Before creation % | During dictation % | After finalization % | Latency median [IQR], min | Processing median, min | Routing share % |
|---|---|---|---|---|---|---|---|---|---|
| CT | 134/1222 | 11.0 | 9.3-12.8 | 71.2 | 17.9 | 10.9 | 10.43 [8.44-13.45] | 4.08 | 60.3 |
| MG | 30/1179 | 2.5 | 1.8-3.6 | 88.9 | 8.7 | 2.4 | 3.50 [2.98-4.18] | 1.35 | 59.9 |
| MR | 15/1165 | 1.3 | 0.8-2.1 | 91.8 | 6.9 | 1.3 | 3.60 [2.98-4.33] | 1.40 | 59.5 |
| XR | 56/2357 | 2.4 | 1.8-3.1 | 88.3 | 9.3 | 2.4 | 1.90 [1.60-2.34] | 0.73 | 60.1 |

## By site

| site | Too Late n/N | Too Late % | 95% CI | Before creation % | During dictation % | After finalization % | Latency median [IQR], min | Processing median, min | Routing share % |
|---|---|---|---|---|---|---|---|---|---|
| Synthetic site 1 | 57/1232 | 4.6 | 3.6-5.9 | 85.8 | 9.6 | 4.7 | 3.10 [2.00-4.92] | 1.15 | 60.5 |
| Synthetic site 2 | 44/1158 | 3.8 | 2.8-5.1 | 86.3 | 9.9 | 3.7 | 3.18 [2.12-4.77] | 1.25 | 59.9 |
| Synthetic site 3 | 45/1134 | 4.0 | 3.0-5.3 | 84.7 | 11.3 | 4.0 | 3.12 [2.00-5.01] | 1.18 | 60.1 |
| Synthetic site 4 | 55/1245 | 4.4 | 3.4-5.7 | 85.0 | 10.7 | 4.2 | 3.25 [2.10-5.12] | 1.27 | 60.3 |
| Synthetic site 5 | 34/1154 | 2.9 | 2.1-4.1 | 86.1 | 11.0 | 2.9 | 3.22 [2.08-4.78] | 1.20 | 59.5 |

## By calendar quarter

| quarter | Too Late n/N | Too Late % | 95% CI | Before creation % | During dictation % | After finalization % | Latency median [IQR], min | Processing median, min | Routing share % |
|---|---|---|---|---|---|---|---|---|---|
| 2024Q1 | 47/729 | 6.4 | 4.9-8.5 | 83.5 | 10.4 | 6.1 | 2.83 [1.97-4.18] | 1.07 | 59.0 |
| 2024Q2 | 35/756 | 4.6 | 3.3-6.4 | 85.9 | 9.4 | 4.6 | 2.87 [1.97-4.42] | 1.10 | 61.7 |
| 2024Q3 | 22/769 | 2.9 | 1.9-4.3 | 86.5 | 10.6 | 2.9 | 2.85 [1.95-4.37] | 1.10 | 61.1 |
| 2024Q4 | 25/722 | 3.5 | 2.4-5.1 | 85.7 | 10.8 | 3.5 | 3.24 [2.05-5.14] | 1.27 | 59.8 |
| 2025Q1 | 37/772 | 4.8 | 3.5-6.5 | 83.6 | 11.7 | 4.7 | 3.52 [2.59-5.62] | 1.43 | 59.4 |
| 2025Q2 | 27/756 | 3.6 | 2.5-5.1 | 85.4 | 11.0 | 3.6 | 3.48 [2.55-5.18] | 1.38 | 59.2 |
| 2025Q3 | 20/726 | 2.8 | 1.8-4.2 | 87.0 | 10.3 | 2.6 | 3.17 [1.90-4.94] | 1.13 | 60.8 |
| 2025Q4 | 22/693 | 3.2 | 2.1-4.8 | 87.2 | 9.6 | 3.2 | 3.16 [1.97-5.60] | 1.22 | 59.8 |


## Quarterly latency stability by AI solution

| AI solution | Quarters | Window | CV % | Pattern | Why |
|---|---|---|---|---|---|
| AI solution A | 8 | 2024Q1 to 2025Q4 | 2.4 | steady_state | CV 2.4%, rho 0.01, last/first 1.00 |
| AI solution E | 8 | 2024Q1 to 2025Q4 | 4.0 | steady_state | CV 4.0%, rho -0.11, last/first 0.98 |
| AI solution B | 8 | 2024Q1 to 2025Q4 | 13.5 | progressive_drift | rho 0.98, last/first 1.36 |
| AI solution D | 8 | 2024Q1 to 2025Q4 | 27.2 | transient_incident | quarters 5-6 elevated (max 1.72x baseline 1.88), recovered in 2 later quarter(s) |
| AI solution C | 8 | 2024Q1 to 2025Q4 | 29.5 | post_deployment_convergence | rho -0.86, last/first 0.56 |


Quarters with fewer than 20 latency-eligible exams are not used. CV is the sample standard deviation of quarterly medians over their mean; it depends on the number of quarters and is not comparable between solutions with different windows. The pattern flag is a screening heuristic: inspect the quarterly table before acting on it.


## Data quality

| check | n |
|---|---|
| input_rows | 6012 |
| missing_exam_id | 0 |
| missing_ai_solution | 0 |
| missing_modality | 0 |
| missing_site | 0 |
| invalid_report_created_ts | 0 |
| invalid_report_finalized_ts | 0 |
| invalid_ai_result_available_ts | 0 |
| invalid_study_end_ts | 18 |
| invalid_ai_inference_start_ts | 0 |
| invalid_ai_inference_end_ts | 0 |
| invalid_ai_fetched_ts | 0 |
| column_absent_ai_processing_seconds | 1 |
| duplicate_exam_solution_rows_dropped | 12 |
| missing_report_finalized_ts | 30 |
| missing_ai_result_available_ts | 29 |
| missing_report_created_ts | 60 |
| missing_study_end_ts | 18 |
| negative_report_interval_created_after_finalized | 18 |
| negative_total_latency_ai_before_study_end | 12 |
| negative_processing_or_routing_time | 0 |
| negative_routing_component | 0 |
| info_report_finalized_before_study_end | 0 |
| rows_after_deduplication | 6000 |
| eligible_too_late | 5923 |
| eligible_timing_categories | 5863 |
| eligible_total_latency | 5941 |


## Definitions and caveats
- Unit of analysis: one (exam_id, ai_solution) pair. Duplicate pairs keep the earliest AI result.
- Too Late: `report_finalized_ts < ai_result_available_ts`. Equal timestamps are not Too Late.
- Before report creation: `ai_result_available_ts <= report_created_ts`. During dictation: `report_created_ts < ai_result_available_ts <= report_finalized_ts`. After finalization equals Too Late.
- Exams with report created after report finalized are excluded from the Too Late rate, the timing categories and TAT. Exams with AI result before study end are excluded from total latency.
- Total latency (AI result available minus study end) = routing time (fetching + upload + download) + inference time (AI processing). Processing = inference end minus inference start, or `ai_processing_seconds`; routing = total latency minus processing. Routing share = mean routing time / mean total latency (ratio of means), on exams with both values.
- The Too Late rate measures infrastructure-imposed temporal loss. It is a ceiling on lost opportunity for AI to inform the report, not a measure of clinical harm or of radiologist engagement.
- Results depend on synchronized clocks between the RIS, the AI platform and the modality. Check clock drift before comparing sites.
