import math

import pandas as pd
import pytest

from too_late_rate import Config, compute, prepare, summarize
from too_late_rate.metrics import AFTER, BEFORE, DURING, wilson_ci


def _dq(dq, key):
    return int(dq.set_index("check").loc[key, "n"])


def test_basic_categories(basic_df):
    p, dq = prepare(basic_df)
    assert list(p["timing_category"]) == [BEFORE, DURING, AFTER, BEFORE]
    assert list(p["too_late"]) == [False, False, True, False]
    s = summarize(p).iloc[0]
    assert s["n_too_late"] == 1 and s["n_too_late_eligible"] == 4
    assert s["too_late_rate_pct"] == pytest.approx(25.0)
    assert s["pct_before_report_creation"] == pytest.approx(50.0)
    assert s["pct_during_dictation"] == pytest.approx(25.0)
    assert s["pct_after_finalization"] == pytest.approx(25.0)
    # latencies 2, 12, 20, 3 minutes -> median 7.5
    assert s["total_latency_median_min"] == pytest.approx(7.5)
    assert _dq(dq, "eligible_too_late") == 4


def test_equal_timestamps_not_too_late_and_before_on_tie():
    df = pd.DataFrame([
        dict(exam_id="1", ai_solution="S", report_created_ts="2025-01-01 10:00:00",
             report_finalized_ts="2025-01-01 10:05:00", ai_result_available_ts="2025-01-01 10:05:00"),
        dict(exam_id="2", ai_solution="S", report_created_ts="2025-01-01 10:00:00",
             report_finalized_ts="2025-01-01 10:05:00", ai_result_available_ts="2025-01-01 10:00:00"),
    ])
    p, _ = prepare(df)
    assert list(p["too_late"]) == [False, False]
    assert list(p["timing_category"]) == [DURING, BEFORE]


def test_no_threshold_one_second_counts():
    df = pd.DataFrame([dict(exam_id="1", ai_solution="S",
                            report_finalized_ts="2025-01-01T10:05:00Z", ai_result_available_ts="2025-01-01T10:05:01Z")])
    p, _ = prepare(df)
    assert bool(p["too_late"].iloc[0]) is True


def test_two_timestamp_mode():
    df = pd.DataFrame([
        dict(exam_id="1", ai_solution="S", report_finalized_ts="2025-01-01 10:05", ai_result_available_ts="2025-01-01 10:06"),
        dict(exam_id="2", ai_solution="S", report_finalized_ts="2025-01-01 10:05", ai_result_available_ts="2025-01-01 10:01"),
    ])
    res = compute(df)
    o = res.overall
    assert o["too_late_rate_pct"] == pytest.approx(50.0)
    assert o["n_timing_eligible"] == 0
    assert math.isnan(o["total_latency_median_min"])
    assert _dq(res.data_quality, "column_absent_report_created_ts") == 1
    assert _dq(res.data_quality, "column_absent_study_end_ts") == 1
    assert res.tables["stability_by_ai_solution"].empty
    assert "Too Late rate" in res.to_markdown()


def test_missing_and_negative_handling():
    df = pd.DataFrame([
        # missing finalized
        dict(exam_id="1", ai_solution="S", study_end_ts="2025-01-01 10:00", report_created_ts="2025-01-01 10:10",
             report_finalized_ts=None, ai_result_available_ts="2025-01-01 10:02"),
        # created after finalized: excluded from too late, timing, TAT
        dict(exam_id="2", ai_solution="S", study_end_ts="2025-01-01 10:00", report_created_ts="2025-01-01 10:20",
             report_finalized_ts="2025-01-01 10:10", ai_result_available_ts="2025-01-01 10:30"),
        # AI before study end: excluded from latency, kept for too late
        dict(exam_id="3", ai_solution="S", study_end_ts="2025-01-01 10:00", report_created_ts="2025-01-01 10:10",
             report_finalized_ts="2025-01-01 10:20", ai_result_available_ts="2025-01-01 09:59"),
        # missing created: in too late, not in timing
        dict(exam_id="4", ai_solution="S", study_end_ts="2025-01-01 10:00", report_created_ts="",
             report_finalized_ts="2025-01-01 10:20", ai_result_available_ts="2025-01-01 10:25"),
        # unparseable AI timestamp
        dict(exam_id="5", ai_solution="S", study_end_ts="2025-01-01 10:00", report_created_ts="2025-01-01 10:10",
             report_finalized_ts="2025-01-01 10:20", ai_result_available_ts="garbage"),
    ])
    p, dq = prepare(df)
    assert _dq(dq, "missing_report_finalized_ts") == 1
    assert _dq(dq, "negative_report_interval_created_after_finalized") == 1
    assert _dq(dq, "negative_total_latency_ai_before_study_end") == 1
    assert _dq(dq, "missing_report_created_ts") == 1
    assert _dq(dq, "invalid_ai_result_available_ts") == 1
    assert _dq(dq, "eligible_too_late") == 2  # exams 3 and 4
    assert _dq(dq, "eligible_timing_categories") == 1  # exam 3
    s = summarize(p).iloc[0]
    assert s["n_too_late"] == 1  # exam 4
    assert s["n_latency_eligible"] == 3  # exams 1, 2 and 4; 3 negative, 5 invalid
    assert p.loc[p.exam_id == "2", "tat_min"].isna().all()


def test_duplicates_keep_earliest_ai():
    df = pd.DataFrame([
        dict(exam_id="1", ai_solution="S", report_finalized_ts="2025-01-01 10:05", ai_result_available_ts="2025-01-01 10:09"),
        dict(exam_id="1", ai_solution="S", report_finalized_ts="2025-01-01 10:05", ai_result_available_ts="2025-01-01 10:01"),
        dict(exam_id="1", ai_solution="T", report_finalized_ts="2025-01-01 10:05", ai_result_available_ts="2025-01-01 10:09"),
    ])
    p, dq = prepare(df)
    assert _dq(dq, "duplicate_exam_solution_rows_dropped") == 1
    assert len(p) == 2
    assert bool(p.loc[p.ai_solution == "S", "too_late"].iloc[0]) is False


def test_group_tables_and_quarter(basic_df):
    res = compute(basic_df)
    by_sol = res.tables["summary_by_ai_solution"].set_index("ai_solution")
    assert by_sol.loc["S2", "too_late_rate_pct"] == pytest.approx(50.0)
    assert set(res.tables["summary_by_quarter"]["quarter"]) == {"2025Q1", "2025Q2"}
    assert set(res.tables["summary_by_site"]["site"]) == {"A", "B"}


def test_missing_optional_modality_site():
    df = pd.DataFrame([dict(exam_id="1", ai_solution="S", report_finalized_ts="2025-01-01 10:05",
                            ai_result_available_ts="2025-01-01 10:09")])
    res = compute(df)
    assert list(res.tables["summary_by_modality"]["modality"]) == ["unspecified"]


def test_missing_required_column_message():
    df = pd.DataFrame([dict(exam_id="1", ai_solution="S", report_finalized_ts="2025-01-01 10:05")])
    with pytest.raises(ValueError, match="ai_result_available_ts"):
        prepare(df)


def test_column_mapping():
    df = pd.DataFrame([dict(Acc="1", Tool="S", Final="2025-01-01 10:05", Ready="2025-01-01 10:09")])
    cfg = Config(columns={"exam_id": "Acc", "ai_solution": "Tool", "report_finalized_ts": "Final",
                          "ai_result_available_ts": "Ready"})
    assert compute(df, cfg).overall["n_too_late"] == 1


def test_unknown_logical_column_rejected():
    with pytest.raises(ValueError, match="Unknown logical column"):
        Config(columns={"finalised": "x"})


def test_wilson_ci():
    lo, hi = wilson_ci(0, 10)
    assert lo == 0.0 and 0 < hi < 35
    lo, hi = wilson_ci(150, 2000)
    assert lo < 7.5 < hi
    assert all(math.isnan(x) for x in wilson_ci(0, 0))


def test_empty_input():
    df = pd.DataFrame(columns=["exam_id", "ai_solution", "report_finalized_ts", "ai_result_available_ts"])
    res = compute(df)
    assert res.overall["n_too_late_eligible"] == 0
    assert math.isnan(res.overall["too_late_rate_pct"])
    res.to_markdown()


def test_decomposition_from_inference_timestamps():
    df = pd.DataFrame([
        # total 10, processing 2 -> routing 8
        dict(exam_id="1", ai_solution="S", study_end_ts="2025-01-01 10:00", ai_inference_start_ts="2025-01-01 10:03",
             ai_inference_end_ts="2025-01-01 10:05", ai_result_available_ts="2025-01-01 10:10",
             report_finalized_ts="2025-01-01 10:30"),
        # total 20, processing 4 -> routing 16
        dict(exam_id="2", ai_solution="S", study_end_ts="2025-01-01 11:00", ai_inference_start_ts="2025-01-01 11:10",
             ai_inference_end_ts="2025-01-01 11:14", ai_result_available_ts="2025-01-01 11:20",
             report_finalized_ts="2025-01-01 11:30"),
        # processing longer than total latency: inconsistent, excluded from the decomposition only
        dict(exam_id="3", ai_solution="S", study_end_ts="2025-01-01 12:00", ai_inference_start_ts="2025-01-01 11:50",
             ai_inference_end_ts="2025-01-01 12:09", ai_result_available_ts="2025-01-01 12:05",
             report_finalized_ts="2025-01-01 12:30"),
    ])
    res = compute(df)
    o = res.overall
    assert o["n_split_eligible"] == 2
    assert o["n_latency_eligible"] == 3
    assert o["processing_median_min"] == pytest.approx(3.0)
    assert o["routing_median_min"] == pytest.approx(12.0)
    # ratio of means: mean routing 12 / mean total 15 = 80 %
    assert o["routing_share_pct"] == pytest.approx(80.0)
    assert _dq(res.data_quality, "negative_processing_or_routing_time") == 1
    assert o["n_routing_components_eligible"] == 0
    assert "Latency decomposition" in res.to_markdown()


def test_routing_share_is_ratio_of_means_not_mean_of_ratios():
    df = pd.DataFrame([
        dict(exam_id="1", ai_solution="S", study_end_ts="2025-01-01 10:00", ai_processing_seconds="60",
             ai_result_available_ts="2025-01-01 10:02", report_finalized_ts="2025-01-01 10:30"),
        dict(exam_id="2", ai_solution="S", study_end_ts="2025-01-01 11:00", ai_processing_seconds="60",
             ai_result_available_ts="2025-01-01 11:20", report_finalized_ts="2025-01-01 11:30"),
    ])
    o = compute(df).overall
    # routing 1 and 19 min, totals 2 and 20: ratio of means = 10/11, mean of ratios would be 72.5 %
    assert o["routing_share_pct"] == pytest.approx(100 * 10 / 11)


def test_processing_seconds_fallback_and_timestamps_preferred():
    df = pd.DataFrame([
        # timestamps present: 3 min processing, seconds column ignored
        dict(exam_id="1", ai_solution="S", study_end_ts="2025-01-01 10:00", ai_inference_start_ts="2025-01-01 10:01",
             ai_inference_end_ts="2025-01-01 10:04", ai_processing_seconds="30",
             ai_result_available_ts="2025-01-01 10:06", report_finalized_ts="2025-01-01 10:30"),
        # no timestamps: 120 s processing
        dict(exam_id="2", ai_solution="S", study_end_ts="2025-01-01 11:00", ai_processing_seconds="120",
             ai_result_available_ts="2025-01-01 11:06", report_finalized_ts="2025-01-01 11:30"),
        dict(exam_id="3", ai_solution="S", study_end_ts="2025-01-01 12:00", ai_processing_seconds="n/a",
             ai_result_available_ts="2025-01-01 12:06", report_finalized_ts="2025-01-01 12:30"),
    ])
    res = compute(df)
    p = res.prepared.set_index("exam_id")
    assert p.loc["1", "processing_min"] == pytest.approx(3.0)
    assert p.loc["2", "processing_min"] == pytest.approx(2.0)
    assert p.loc["2", "routing_min"] == pytest.approx(4.0)
    assert pd.isna(p.loc["3", "processing_min"])
    assert _dq(res.data_quality, "invalid_ai_processing_seconds") == 1


def test_routing_components_when_all_timestamps_present():
    df = pd.DataFrame([dict(
        exam_id="1", ai_solution="S", study_end_ts="2025-01-01 10:00", ai_fetched_ts="2025-01-01 10:02",
        ai_inference_start_ts="2025-01-01 10:03", ai_inference_end_ts="2025-01-01 10:07",
        ai_result_available_ts="2025-01-01 10:12", report_finalized_ts="2025-01-01 10:30")])
    res = compute(df)
    o = res.overall
    assert o["n_routing_components_eligible"] == 1
    assert (o["fetch_median_min"], o["upload_median_min"], o["download_median_min"]) == pytest.approx((2.0, 1.0, 5.0))
    assert o["fetch_median_min"] + o["upload_median_min"] + o["download_median_min"] == pytest.approx(o["routing_median_min"])
    assert "Routing components" in res.to_markdown()


def test_decomposition_absent_without_processing_inputs(basic_df):
    o = compute(basic_df).overall
    assert o["n_split_eligible"] == 0
    assert math.isnan(o["routing_share_pct"])
    assert math.isnan(o["processing_median_min"])
