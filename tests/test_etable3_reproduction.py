"""Reproduction of the paper: stability pattern rules checked against the published aggregate values of
eTable 3 (quarterly median total latency per AI solution, minutes) of:
Morozov S, et al. J Am Coll Radiol 2026. doi:10.1016/j.jacr.2026.09.026.

Only the published quarterly medians are used; quarters shown as n/a are omitted.
Solutions are labelled by the anonymous row descriptions of the published table.
"""

import numpy as np
import pandas as pd
import pytest

from too_late_rate import StabilityThresholds, classify_pattern, compute, cv_pct
from too_late_rate.metrics import CONVERGENCE, DRIFT, INCIDENT, INSUFFICIENT, STEADY, VARIABLE

# (published medians, published CV %, published pattern)
ETABLE3 = {
    "Chest XR": ([2.58, 2.57, 2.57], 0.4, STEADY),
    "Mammography": ([3.55, 3.55, 3.53, 3.09], 6.7, STEADY),
    "Aorta CT": ([7.57, 7.78, 7.61, 8.93, 8.91], 8.6, STEADY),
    "Multiple sclerosis MRI": ([14.46, 12.19, 11.29, 13.65, 14.00, 14.76, 13.84, 11.73, 11.96], 9.9, STEADY),
    "Knee MRI": ([2.72, 2.81, 2.75, 3.00, 3.47, 3.59, 3.57, 3.70, 3.85], 13.8, DRIFT),
    "Trauma XR": ([1.73, 1.74, 1.73, 1.73, 1.76, 1.78, 2.57, 2.08, 2.05], 14.7, STEADY),
    "Brain volumetry MRI": ([8.54, 7.39, 8.80, 10.12, 10.82, 10.60, 12.45, 11.08, 10.59], 15.3, DRIFT),
    "Chest CT lung nodules": ([20.43, 14.77, 14.62, 10.77], 26.3, CONVERGENCE),
    "MSK measurements XR": ([1.89, 1.94, 3.09, 3.07, 1.36], 33.9, INCIDENT),
}


@pytest.mark.parametrize("name", list(ETABLE3))
def test_etable3_patterns_reproduced(name):
    medians, _, pattern = ETABLE3[name]
    got, detail = classify_pattern(medians)
    assert got == pattern, f"{name}: {got} ({detail})"


@pytest.mark.parametrize("name", list(ETABLE3))
def test_etable3_cv_close(name):
    medians, published_cv, _ = ETABLE3[name]
    # Published CVs were computed on unrounded medians; allow rounding error.
    assert cv_pct(medians) == pytest.approx(published_cv, abs=0.5)


