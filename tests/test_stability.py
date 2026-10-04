"""Stability pattern rules on synthetic quarterly median series.

All series below are invented for testing. Each one is built to show one of the
pattern definitions used in the paper (steady state, progressive drift,
post-deployment convergence, transient incident). No study data are used.
"""

import numpy as np
import pandas as pd
import pytest

from too_late_rate import StabilityThresholds, classify_pattern, compute, cv_pct
from too_late_rate.metrics import CONVERGENCE, DRIFT, INCIDENT, INSUFFICIENT, STEADY, VARIABLE

# (synthetic quarterly medians in minutes, expected pattern)
SYNTHETIC_SERIES = {
    "flat, 3 quarters": ([2.0, 2.01, 1.99], STEADY),
    "flat with small dip": ([4.0, 4.0, 3.95, 3.6], STEADY),
    "noisy flat, 9 quarters": ([10.0, 8.6, 8.0, 9.5, 9.8, 10.2, 9.6, 8.2, 8.4], STEADY),
    "slow step, 5 quarters": ([6.0, 6.2, 6.1, 7.0, 7.0], STEADY),
    "gradual rise": ([3.0, 3.1, 3.05, 3.3, 3.8, 3.9, 3.9, 4.0, 4.2], DRIFT),
    "noisy rise": ([6.0, 5.2, 6.2, 7.1, 7.6, 7.4, 8.7, 7.8, 7.4], DRIFT),
    "falling after go-live": ([15.0, 11.0, 10.8, 8.0], CONVERGENCE),
    "two-quarter spike": ([2.0, 2.05, 3.2, 3.2, 1.5], INCIDENT),
}


@pytest.mark.parametrize("name", list(SYNTHETIC_SERIES))
def test_synthetic_patterns(name):
    medians, pattern = SYNTHETIC_SERIES[name]
    got, detail = classify_pattern(medians)
    assert got == pattern, f"{name}: {got} ({detail})"


def test_cv_sample_sd():
    # sample SD of [1, 2, 3] is 1, mean 2 -> 50 %
    assert cv_pct([1.0, 2.0, 3.0]) == pytest.approx(50.0)
    assert np.isnan(cv_pct([1.0]))


def test_insufficient_quarters():
    assert classify_pattern([2.0, 2.1])[0] == INSUFFICIENT
    assert classify_pattern([])[0] == INSUFFICIENT


def test_variable_unclassified():
    assert classify_pattern([2.0, 3.5, 2.0, 3.5, 2.0, 3.5])[0] == VARIABLE


def test_incident_needs_recovery():
    # elevation that never comes back is not a transient incident
    assert classify_pattern([2.0, 2.0, 2.0, 3.0, 3.0, 3.0])[0] != INCIDENT
    assert classify_pattern([2.0, 2.0, 2.0, 3.0, 2.0, 2.0])[0] == INCIDENT


def test_incident_max_quarters_configurable():
    series = [2.0, 2.0, 3.0, 3.0, 3.0, 2.0]
    assert classify_pattern(series)[0] != INCIDENT
    assert classify_pattern(series, StabilityThresholds(incident_max_quarters=3))[0] == INCIDENT


def test_stability_table_from_exams():
    """Build exam-level data whose quarterly medians follow a drift; check end to end."""
    rows = []
    quarters = pd.period_range("2024Q1", "2025Q2", freq="Q")
    for qi, q in enumerate(quarters):
        for j in range(25):
            end = q.start_time + pd.Timedelta(days=10, hours=j % 8 + 8)
            lat = 2.0 * (1 + 0.1 * qi) + 0.01 * (j - 12)
            ai = end + pd.Timedelta(minutes=lat)
            rows.append(dict(exam_id=f"{qi}-{j}", ai_solution="S", study_end_ts=end.isoformat() + "Z",
                             ai_result_available_ts=ai.isoformat() + "Z",
                             report_finalized_ts=(end + pd.Timedelta(minutes=30)).isoformat() + "Z"))
    # a sparse quarter that must be ignored (n < 20)
    for j in range(5):
        end = pd.Timestamp("2025-08-01 10:00") + pd.Timedelta(hours=j)
        rows.append(dict(exam_id=f"x{j}", ai_solution="S", study_end_ts=end.isoformat() + "Z",
                         ai_result_available_ts=(end + pd.Timedelta(minutes=50)).isoformat() + "Z",
                         report_finalized_ts=(end + pd.Timedelta(minutes=60)).isoformat() + "Z"))
    res = compute(pd.DataFrame(rows))
    st = res.tables["stability_by_ai_solution"].iloc[0]
    assert st["n_quarters"] == 6
    assert st["pattern"] == DRIFT
    assert st["median_min_2024Q1"] == pytest.approx(2.0, abs=0.01)
    q = res.tables["quarterly_by_ai_solution"]
    assert not q.loc[q.quarter == "2025Q3", "used_for_stability"].iloc[0]
    assert np.isfinite(st["cv_pct"])
