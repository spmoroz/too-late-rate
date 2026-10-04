# too-late-rate

[![CI](https://github.com/spmoroz/too-late-rate/actions/workflows/ci.yml/badge.svg)](https://github.com/spmoroz/too-late-rate/actions/workflows/ci.yml)
[![DOI](https://zenodo.org/badge/DOI/ZENODO_CONCEPT_DOI.svg)](https://doi.org/ZENODO_CONCEPT_DOI)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)

`too-late-rate` is a Python package that measures whether results from deployed radiology AI reach the radiologist in time. It works on timestamps that most RIS and PACS already log through HL7.

It accompanies the article:

> Morozov S, Heracleous N, Korka D, Thouly C, Dufour B, Novarina O, Rizk B. AI Latency, Report Turnaround Time, and Adoption in a Multi-Vendor AI Ecosystem: A Multi-Site Observational Study. *J Am Coll Radiol*. 2026. doi:10.1016/j.jacr.2026.09.026

Research page: https://aimonitoring.drsergeymorozov.com

The repository contains code and synthetic data only. It contains no patient, examination or institutional data.

## What it measures

1. **PACS-to-PACS AI latency**: time from study end to the AI result being available in RIS/PACS, decomposed into **routing time** (fetching, upload and download) and **inference time** (AI processing), with the **routing share** per AI solution.
2. **Too Late rate**: the share of exams in which the report was finalized before the AI result was available. Each exam is also placed in an **arrival category**: before report creation, during dictation, or after finalization.
3. **Quarterly stability**: per AI solution, the median latency per calendar quarter, the coefficient of variation (CV) across quarters and a pattern flag that marks drift.

Report turnaround time (finalized minus created) is reported alongside.

## Why timing matters

An AI result that arrives after the report is finalized cannot change that report. Whatever the AI found, the radiologist signed without it. Latency averages hide this: a platform with a short median latency can still deliver a meaningful share of results too late for fast readings, such as radiographs reported within minutes. The Too Late rate counts those exams directly, and the quarterly table shows whether latency is stable, improving or drifting over time.

## Install

```bash
git clone https://github.com/spmoroz/too-late-rate
cd too-late-rate
pip install -e .            # add ".[dev]" for the test suite, ".[parquet]" for Parquet input
```

Python 3.9 or later. Dependencies: pandas, numpy, PyYAML. The package is not on PyPI yet.

## Quick start (synthetic demo data)

```bash
too-late-rate synth --out demo.csv --n 6000 --seed 42          # SYNTHETIC data, no real exams
too-late-rate compute demo.csv --timezone Europe/Zurich --out demo_report
```

```python
from too_late_rate import compute, Config
res = compute("demo.csv", Config(timezone="Europe/Zurich"))
print(res.overall[["too_late_rate_pct", "processing_median_min", "routing_share_pct"]])
print(res.tables["summary_by_ai_solution"][["ai_solution", "too_late_rate_pct"]])
print(res.tables["stability_by_ai_solution"][["ai_solution", "cv_pct", "pattern"]])
res.write("demo_report/")
```

The same synthetic dataset, its configuration file and the resulting output are in [`examples/`](examples/).

## Input schema

One row per exam and AI solution, as CSV, TSV, Parquet or a pandas DataFrame.

| Column | Required | Meaning |
|---|---|---|
| `exam_id` | yes | Any exam key, used only to drop duplicate (exam, AI solution) rows; the earliest AI result is kept. Pseudonymize before use. |
| `ai_solution` | yes | Free label, for example `AI solution A`. |
| `report_finalized_ts` | yes | Report finalized (validated, signed) time. |
| `ai_result_available_ts` | yes | Time the AI result became available in PACS/RIS. |
| `report_created_ts` | no | Report created (dictation start). Enables arrival categories and turnaround time. |
| `study_end_ts` | no | Study end (acquisition complete). Enables total latency and the stability table. |
| `ai_inference_start_ts`, `ai_inference_end_ts` | no | Start and end of AI inference. Processing time = end minus start. |
| `ai_processing_seconds` | no | Numeric AI processing time in seconds. Used for exams where the two inference timestamps are not both available. |
| `ai_fetched_ts` | no | Study fetched by the AI platform. Only used, together with both inference timestamps, to report fetching, upload and download separately. |
| `modality` | no | Filled with `unspecified` if absent. |
| `site` | no | Filled with `unspecified` if absent. |

Map other column names with a YAML file (`--config`, see [`examples/config.yaml`](examples/config.yaml)) or with `--col logical=your_column`.

### Timestamp format and time zones

- ISO 8601 with offset or `Z` (`2025-03-01T08:15:00+01:00`) is converted to UTC exactly.
- ISO 8601 without offset (`2025-03-01 08:15:00`) is read as local time in the configured `timezone` (IANA name, default `UTC`), then converted to UTC.
- HL7 v2 TS/DTM (`20250301081500`, `20250301081500.123+0100`) is supported; the offset is used when present.
- Formats may be mixed within a column. Local times that do not exist (spring-forward gap) are invalid. Local times that occur twice (fall-back) follow `ambiguous`: `NaT` (invalid, default), `earliest` or `latest`.
- Calendar quarters are assigned in the configured time zone, from study end, or from AI result time when study end is missing.
- Every missing, invalid or inconsistent value is counted in `data_quality.csv`.

## Metric definitions

As in the paper: total latency (T_total = t_RIS_available - t_study_end) is decomposed into routing time (fetching + upload + download) and inference time (AI processing). Routing share is the proportion of mean routing time relative to mean total latency.

| Metric | Definition |
|---|---|
| Too Late rate | Share of exams in which the report-finalized timestamp precedes AI result availability: `report_finalized_ts < ai_result_available_ts`. Binary, no minimum delay. Equal timestamps are not Too Late. Wilson 95% confidence interval. |
| Arrival category | Before report creation: `ai_result_available_ts <= report_created_ts`. During dictation: `report_created_ts < ai_result_available_ts <= report_finalized_ts`. After finalization: `ai_result_available_ts > report_finalized_ts` (same exams as Too Late). |
| Total (PACS-to-PACS) latency | T_total = t_RIS_available - t_study_end, that is `ai_result_available_ts - study_end_ts`. Median and IQR in minutes. |
| Inference time (AI processing) | `ai_inference_end_ts - ai_inference_start_ts`, or `ai_processing_seconds` / 60. Median and IQR. |
| Routing time (data transfer: fetching, upload and download) | Total latency minus inference time. |
| Routing share | Mean routing time divided by mean total latency, in percent (ratio of means), per AI solution and overall, on exams with both values. |
| Routing components (optional) | Fetching = `ai_fetched_ts - study_end_ts`; upload = `ai_inference_start_ts - ai_fetched_ts`; download = `ai_result_available_ts - ai_inference_end_ts`. Reported only when all these timestamps are present; they sum to routing time. |
| Report turnaround time | `report_finalized_ts - report_created_ts`. |
| Quarterly CV | Sample standard deviation of the quarterly median latencies divided by their mean, in percent. Quarters with fewer than 20 latency-eligible exams are not used (configurable). |
| Pattern flag | `steady_state` (CV below 15%, no sustained trend), `progressive_drift` (gradual monotonic increase), `post_deployment_convergence` (initially elevated latency that settles), `transient_incident` (elevation in one or two adjacent quarters with full recovery), `variable_unclassified`, `insufficient_data` (fewer than 3 usable quarters). Operational rules and thresholds are documented in `classify_pattern` and `StabilityThresholds` and can be changed. |

Exclusions: exams with report created after report finalized are excluded from the Too Late rate, arrival categories and turnaround time. Exams with AI result before study end are excluded from latency. Exams with negative processing time, or processing longer than total latency, are excluded from the decomposition only. Duplicate (exam, AI solution) rows keep the earliest AI result.

## Output

`too-late-rate compute` writes `report.md` (headline metrics, tables, stability, data quality, definitions), `summary_overall.csv`, summaries by AI solution, modality, site, quarter and AI solution x modality, `quarterly_by_ai_solution.csv`, `stability_by_ai_solution.csv`, `data_quality.csv` and, with `--exam-level`, `exam_level.csv`.

## Limitations

- The Too Late rate is a ceiling on potential inefficiency, not measured clinical loss. It counts exams in which the AI result could not have informed the signed report. It does not show whether a timely result was opened, whether it would have changed the report, or whether any patient was affected.
- Results depend on synchronized clocks between modality, PACS, AI platform and RIS. A few minutes of skew moves the Too Late rate; check clock drift before comparing sites.
- Use the timestamp that marks the finalized (signed) report, not a preliminary version. Addenda are not handled.
- The pattern flag is a screening heuristic for quarterly review, not a statistical test. CV depends on the number of quarters and is not comparable between solutions with different observation windows. Read the quarterly table before acting on the flag.
- The decomposition depends on the AI platform logging inference start and end (or processing time) on a clock consistent with the RIS. Routing time is derived as a remainder, so any clock offset between systems ends up in routing time.

## How to cite

Please cite the article, and the software release if you used the code:

- Article: Morozov S, Heracleous N, Korka D, Thouly C, Dufour B, Novarina O, Rizk B. AI Latency, Report Turnaround Time, and Adoption in a Multi-Vendor AI Ecosystem: A Multi-Site Observational Study. *J Am Coll Radiol*. 2026. doi:10.1016/j.jacr.2026.09.026
- Software: Morozov S, Heracleous N, Korka D, Thouly C, Dufour B, Novarina O, Rizk B. too-late-rate (version 1.0.0). Zenodo. 2026. doi:ZENODO_CONCEPT_DOI

Citation metadata are in [`CITATION.cff`](CITATION.cff); GitHub shows a "Cite this repository" button.

## Contact

Sergey Morozov, dr.morozov.sergey@gmail.com. Research page: https://aimonitoring.drsergeymorozov.com

## License

Apache License 2.0. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
