# Changelog

All notable changes to this project are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project uses
[Semantic Versioning](https://semver.org/).

## [1.0.0] - 2026-09-30

First public release.

### Added
- Too Late rate: share of exams in which the report was finalized strictly before the AI result was available (no threshold), with Wilson 95% CI.
- Arrival categories: before report creation, during dictation, after finalization.
- PACS-to-PACS total AI latency (AI result available minus study end), median and IQR, decomposed as in the paper into inference time (AI processing, from inference start and end timestamps or a numeric `ai_processing_seconds` column) and routing time (total minus processing: fetching, upload and download), with routing share as a ratio of means per AI solution and overall. Optional separate fetching, upload and download times when all timestamps are present.
- Report turnaround time (finalized minus created), median and IQR.
- Summaries overall and by AI solution, modality, site, calendar quarter and AI solution x modality.
- Quarterly stability table per AI solution: median latency per quarter, coefficient of variation (CV) and a pattern flag (steady state, progressive drift, post-deployment convergence, transient incident).
- Timezone-safe parsing of ISO 8601 and HL7 v2 timestamps, mixed formats, DST gap and fall-back handling.
- Data-quality table counting every missing, invalid, negative-interval and duplicate record.
- Command line (`too-late-rate compute`, `too-late-rate synth`), YAML or flag column mapping, Python API.
- Synthetic demo dataset, generator script and example output.
- Reproduction test: the stability rules return the published pattern and CV for all nine AI solutions of eTable 3 of the JACR article.
- Citation metadata (`CITATION.cff`, `.zenodo.json`) and a test that checks the version string is identical across files.
