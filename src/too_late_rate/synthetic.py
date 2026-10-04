"""Synthetic example data. Entirely simulated; contains no real examination data.

AI solution labels (AI solution A to E), exam ids (SYN000001...) and site labels
(Synthetic site 1...) are invented and do not refer to any product, vendor or site.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

QUARTERS = pd.period_range("2024Q1", "2025Q4", freq="Q")

# (label, modality, baseline median latency in minutes, quarterly multipliers)
_SOLUTIONS = [
    ("AI solution A", "XR", 1.8, [1.0] * 8),  # steady-state
    ("AI solution B", "MR", 3.0, [1.0, 1.04, 1.1, 1.18, 1.25, 1.33, 1.4, 1.48]),  # progressive drift
    ("AI solution C", "CT", 9.0, [2.0, 1.6, 1.3, 1.1, 1.0, 1.0, 1.0, 1.0]),  # post-deployment convergence
    ("AI solution D", "XR", 1.9, [1.0, 1.0, 1.0, 1.0, 1.7, 1.65, 1.0, 1.0]),  # transient incident
    ("AI solution E", "MG", 3.5, [1.0, 1.03, 0.98, 1.02, 0.97, 1.01, 1.0, 0.99]),  # steady-state
]

# Mean minutes from study end to report creation, and from creation to finalization.
_READ_DELAY = {"XR": 12.0, "MG": 25.0, "CT": 30.0, "MR": 35.0}
_DICTATION = {"XR": 3.0, "MG": 5.0, "CT": 10.0, "MR": 12.0}


def generate_synthetic(n: int = 6000, seed: int = 42, timezone: str = "Europe/Zurich", anomalies: bool = True) -> pd.DataFrame:
    """Generate a synthetic exam-level table in the default input format.

    Timestamps are written as naive local times (interpret them with
    ``timezone``). With ``anomalies=True`` a small share of rows gets missing
    timestamps, inverted report timestamps, AI results before study end,
    unparseable text and duplicated rows, to exercise the data-quality counts.
    """
    rng = np.random.default_rng(seed)
    sol_idx = rng.integers(0, len(_SOLUTIONS), n)
    q_idx = rng.integers(0, len(QUARTERS), n)
    sites = np.array([f"Synthetic site {i}" for i in range(1, 6)])
    rows = []
    for i in range(n):
        label, modality, base, mult = _SOLUTIONS[sol_idx[i]]
        q = QUARTERS[q_idx[i]]
        start = q.start_time
        day = start + pd.Timedelta(days=int(rng.integers(0, 88)))
        study_end = day + pd.Timedelta(hours=float(rng.uniform(7.5, 18.5)))
        latency = base * mult[q_idx[i]] * float(rng.lognormal(0.0, 0.25))
        # total latency = fetching + upload + processing + download
        parts = rng.dirichlet([3.0, 2.0, 4.0, 1.0]) * latency
        fetched = study_end + pd.Timedelta(minutes=float(parts[0]))
        inf_start = fetched + pd.Timedelta(minutes=float(parts[1]))
        inf_end = inf_start + pd.Timedelta(minutes=float(parts[2]))
        ai = study_end + pd.Timedelta(minutes=latency)
        created = study_end + pd.Timedelta(minutes=float(rng.exponential(_READ_DELAY[modality])) + 0.5)
        finalized = created + pd.Timedelta(minutes=float(rng.exponential(_DICTATION[modality])) + 0.3)
        rows.append(
            {
                "exam_id": f"SYN{i + 1:06d}",
                "ai_solution": label,
                "modality": modality,
                "site": sites[rng.integers(0, len(sites))],
                "study_end_ts": study_end,
                "ai_fetched_ts": fetched,
                "ai_inference_start_ts": inf_start,
                "ai_inference_end_ts": inf_end,
                "ai_result_available_ts": ai,
                "report_created_ts": created,
                "report_finalized_ts": finalized,
            }
        )
    df = pd.DataFrame(rows)
    ts_cols = ["study_end_ts", "ai_fetched_ts", "ai_inference_start_ts", "ai_inference_end_ts", "ai_result_available_ts", "report_created_ts", "report_finalized_ts"]
    for c in ts_cols:
        df[c] = df[c].dt.round("s").dt.strftime("%Y-%m-%d %H:%M:%S").astype(object)

    if anomalies:
        m = len(df)
        pick = lambda frac: rng.choice(m, size=max(1, int(frac * m)), replace=False)  # noqa: E731
        df.loc[pick(0.01), "report_created_ts"] = None
        df.loc[pick(0.005), "report_finalized_ts"] = None
        df.loc[pick(0.005), "ai_result_available_ts"] = None
        df.loc[pick(0.003), "study_end_ts"] = "not recorded"
        inv = pick(0.003)
        df.loc[inv, ["report_created_ts", "report_finalized_ts"]] = df.loc[inv, ["report_finalized_ts", "report_created_ts"]].to_numpy()
        early = pick(0.002)
        df.loc[early, "ai_result_available_ts"] = (
            pd.to_datetime(df.loc[early, "study_end_ts"], errors="coerce") - pd.Timedelta(minutes=1)
        ).dt.strftime("%Y-%m-%d %H:%M:%S").to_numpy()
        dups = df.iloc[pick(0.002)]
        df = pd.concat([df, dups], ignore_index=True)
    return df
