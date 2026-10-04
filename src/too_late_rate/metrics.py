"""Core metrics: Too Late rate, timing categories, latency and quarterly stability."""

from __future__ import annotations

import math
from typing import Iterable, Sequence

import numpy as np
import pandas as pd

from .config import REQUIRED_COLUMNS, TIMESTAMP_COLUMNS, Config, StabilityThresholds
from .io import parse_timestamps

BEFORE = "before_report_creation"
DURING = "during_dictation"
AFTER = "after_finalization"
TIMING_CATEGORIES = (BEFORE, DURING, AFTER)

STEADY = "steady_state"
DRIFT = "progressive_drift"
CONVERGENCE = "post_deployment_convergence"
INCIDENT = "transient_incident"
VARIABLE = "variable_unclassified"
INSUFFICIENT = "insufficient_data"

UNSPECIFIED = "unspecified"

_TS_SHORT = {
    "report_created_ts": "t_created",
    "report_finalized_ts": "t_finalized",
    "ai_result_available_ts": "t_ai_available",
    "study_end_ts": "t_study_end",
    "ai_inference_start_ts": "t_inf_start",
    "ai_inference_end_ts": "t_inf_end",
    "ai_fetched_ts": "t_fetched",
}

# --------------------------------------------------------------------------- #
# Preparation
# --------------------------------------------------------------------------- #


def prepare(df: pd.DataFrame, config: Config | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Map columns, parse timestamps, derive per-exam flags and metrics.

    Returns
    -------
    (prepared, data_quality)
        ``prepared`` has one row per unique (exam_id, ai_solution) pair with
        UTC timestamps (``t_*``), eligibility flags, ``too_late``,
        ``timing_category``, ``total_latency_min``, ``processing_min``,
        ``routing_min`` (and ``fetch_min``, ``upload_min``, ``download_min``
        when available), ``tat_min`` and ``quarter``.
        ``data_quality`` is a two-column table (check, n) with the counts of
        every exclusion and anomaly.
    """
    config = config or Config()
    cmap = config.columns
    missing = [f"{logical} (expected column '{cmap[logical]}')" for logical in REQUIRED_COLUMNS if cmap[logical] not in df.columns]
    if missing:
        raise ValueError("Missing required column(s): " + "; ".join(missing))

    dq: dict[str, int] = {"input_rows": int(len(df))}
    work = pd.DataFrame(index=df.index)

    for logical in ("exam_id", "ai_solution", "modality", "site"):
        actual = cmap[logical]
        if actual in df.columns:
            col = df[actual].astype("string").str.strip()
            col = col.mask(col == "")
        else:
            col = pd.Series(pd.NA, index=df.index, dtype="string")
        if logical == "exam_id":
            dq["missing_exam_id"] = int(col.isna().sum())
            work[logical] = col
        else:
            if logical in ("modality", "site") and actual not in df.columns:
                dq[f"column_absent_{logical}"] = 1
            dq[f"missing_{logical}"] = int(col.isna().sum()) if actual in df.columns else 0
            work[logical] = col.fillna(UNSPECIFIED)

    present_ts = {}
    for logical in TIMESTAMP_COLUMNS:
        actual = cmap[logical]
        short = _TS_SHORT[logical]
        present_ts[logical] = actual in df.columns
        if present_ts[logical]:
            parsed, n_bad = parse_timestamps(df[actual], config.timezone, config.ambiguous)
            dq[f"invalid_{logical}"] = n_bad
        else:
            parsed = pd.Series(pd.NaT, index=df.index, dtype="datetime64[ns, UTC]")
            dq[f"column_absent_{logical}"] = 1
        work[short] = parsed

    proc_col = cmap["ai_processing_seconds"]
    present_proc_sec = proc_col in df.columns
    if present_proc_sec:
        raw_sec = df[proc_col].astype("string").str.strip()
        raw_sec = raw_sec.mask(raw_sec == "")
        sec = pd.to_numeric(raw_sec, errors="coerce")
        dq["invalid_ai_processing_seconds"] = int((raw_sec.notna() & sec.isna()).sum())
        work["ai_processing_seconds"] = sec.astype(float)
    else:
        dq["column_absent_ai_processing_seconds"] = 1
        work["ai_processing_seconds"] = np.nan

    # Duplicate (exam_id, ai_solution) pairs: keep the earliest AI result.
    work = work.sort_values("t_ai_available", kind="stable", na_position="last")
    keyed = work["exam_id"].notna()
    dup = keyed & work.duplicated(subset=["exam_id", "ai_solution"], keep="first")
    dq["duplicate_exam_solution_rows_dropped"] = int(dup.sum())
    work = work.loc[~dup].sort_index()

    t_c, t_f, t_a, t_s = work["t_created"], work["t_finalized"], work["t_ai_available"], work["t_study_end"]

    dq["missing_report_finalized_ts"] = int(t_f.isna().sum())
    dq["missing_ai_result_available_ts"] = int(t_a.isna().sum())
    dq["missing_report_created_ts"] = int(t_c.isna().sum()) if present_ts["report_created_ts"] else 0
    dq["missing_study_end_ts"] = int(t_s.isna().sum()) if present_ts["study_end_ts"] else 0

    neg_report = t_c.notna() & t_f.notna() & (t_c > t_f)
    dq["negative_report_interval_created_after_finalized"] = int(neg_report.sum())

    pair = t_f.notna() & t_a.notna()
    work["too_late_eligible"] = pair & ~neg_report
    too_late = pd.Series(pd.NA, index=work.index, dtype="boolean")
    el = work["too_late_eligible"]
    too_late.loc[el] = (t_f[el] < t_a[el]).to_numpy()
    work["too_late"] = too_late

    work["timing_eligible"] = el & t_c.notna()
    cat = pd.Series(pd.NA, index=work.index, dtype="string")
    te = work["timing_eligible"]
    cat.loc[te & (t_a <= t_c)] = BEFORE
    cat.loc[te & (t_a > t_c) & (t_a <= t_f)] = DURING
    cat.loc[te & (t_a > t_f)] = AFTER
    work["timing_category"] = cat

    lat = (t_a - t_s).dt.total_seconds() / 60.0
    neg_lat = lat < 0
    dq["negative_total_latency_ai_before_study_end"] = int(neg_lat.sum())
    work["latency_eligible"] = lat.notna() & ~neg_lat
    work["total_latency_min"] = lat.where(work["latency_eligible"])

    # Decomposition of total latency, following the paper: total latency =
    # routing time (fetching + upload + download) + inference time (AI processing).
    # Processing comes from inference end minus inference start, or, where those
    # are missing, from ai_processing_seconds. Routing = total - processing.
    t_is, t_ie, t_fe = work["t_inf_start"], work["t_inf_end"], work["t_fetched"]
    proc_ts = (t_ie - t_is).dt.total_seconds() / 60.0
    proc_num = work["ai_processing_seconds"] / 60.0
    processing = proc_ts.where(proc_ts.notna(), proc_num)
    routing = lat - processing
    has_proc = work["latency_eligible"] & processing.notna()
    bad_split = has_proc & ((processing < 0) | (routing < 0))
    dq["negative_processing_or_routing_time"] = int(bad_split.sum())
    split_ok = has_proc & ~bad_split
    work["split_eligible"] = split_ok
    work["processing_min"] = processing.where(split_ok)
    work["routing_min"] = routing.where(split_ok)

    # Optional routing components when every timestamp is present.
    fetch = (t_fe - t_s).dt.total_seconds() / 60.0
    upload = (t_is - t_fe).dt.total_seconds() / 60.0
    download = (t_a - t_ie).dt.total_seconds() / 60.0
    comp_all = split_ok & fetch.notna() & upload.notna() & download.notna()
    bad_comp = comp_all & ((fetch < 0) | (upload < 0) | (download < 0))
    dq["negative_routing_component"] = int(bad_comp.sum())
    comp_ok = comp_all & ~bad_comp
    work["fetch_min"] = fetch.where(comp_ok)
    work["upload_min"] = upload.where(comp_ok)
    work["download_min"] = download.where(comp_ok)

    tat = (t_f - t_c).dt.total_seconds() / 60.0
    work["tat_min"] = tat.where(tat.notna() & ~neg_report)

    dq["info_report_finalized_before_study_end"] = int((t_f.notna() & t_s.notna() & (t_f < t_s)).sum())

    ref = t_s.where(t_s.notna(), t_a)
    local = ref.dt.tz_convert(config.timezone).dt.tz_localize(None)
    q = local.dt.to_period("Q").astype("string")
    work["quarter"] = q.where(ref.notna(), "unknown").fillna("unknown")

    dq["rows_after_deduplication"] = int(len(work))
    dq["eligible_too_late"] = int(el.sum())
    dq["eligible_timing_categories"] = int(te.sum())
    dq["eligible_total_latency"] = int(work["latency_eligible"].sum())

    dq_table = pd.DataFrame({"check": list(dq), "n": list(dq.values())})
    return work, dq_table


# --------------------------------------------------------------------------- #
# Summaries
# --------------------------------------------------------------------------- #


def wilson_ci(k: int, n: int, z: float = 1.959963984540054) -> tuple[float, float]:
    """Wilson score interval for a proportion, in percent."""
    if n == 0:
        return (math.nan, math.nan)
    p = k / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (100 * max(0.0, centre - half), 100 * min(1.0, centre + half))


def _pct(k: int, n: int) -> float:
    return 100.0 * k / n if n else math.nan


def _quantiles(x: pd.Series) -> tuple[float, float, float]:
    x = x.dropna()
    if x.empty:
        return (math.nan, math.nan, math.nan)
    q = x.quantile([0.25, 0.5, 0.75]).to_numpy()
    return (float(q[1]), float(q[0]), float(q[2]))


def _summarize_group(g: pd.DataFrame) -> dict:
    el = g[g["too_late_eligible"]]
    n = int(len(el))
    k = int(el["too_late"].sum()) if n else 0
    lo, hi = wilson_ci(k, n)
    tim = g["timing_category"][g["timing_eligible"]]
    nt = int(len(tim))
    counts = {c: int((tim == c).sum()) for c in TIMING_CATEGORIES}
    lat_med, lat_q1, lat_q3 = _quantiles(g["total_latency_min"])
    tat_med, tat_q1, tat_q3 = _quantiles(g["tat_min"])
    rt_med, rt_q1, rt_q3 = _quantiles(g["routing_min"])
    pr_med, pr_q1, pr_q3 = _quantiles(g["processing_min"])
    sp = g[g["split_eligible"]]
    n_split = int(len(sp))
    mean_total = float(sp["total_latency_min"].mean()) if n_split else math.nan
    mean_routing = float(sp["routing_min"].mean()) if n_split else math.nan
    share = 100.0 * mean_routing / mean_total if n_split and mean_total > 0 else math.nan
    return {
        "n_exams": int(len(g)),
        "n_too_late_eligible": n,
        "n_too_late": k,
        "too_late_rate_pct": _pct(k, n),
        "too_late_ci95_low_pct": lo,
        "too_late_ci95_high_pct": hi,
        "n_timing_eligible": nt,
        "n_before_report_creation": counts[BEFORE],
        "pct_before_report_creation": _pct(counts[BEFORE], nt),
        "n_during_dictation": counts[DURING],
        "pct_during_dictation": _pct(counts[DURING], nt),
        "n_after_finalization": counts[AFTER],
        "pct_after_finalization": _pct(counts[AFTER], nt),
        "n_latency_eligible": int(g["total_latency_min"].notna().sum()),
        "total_latency_median_min": lat_med,
        "total_latency_q1_min": lat_q1,
        "total_latency_q3_min": lat_q3,
        "n_split_eligible": n_split,
        "processing_median_min": pr_med,
        "processing_q1_min": pr_q1,
        "processing_q3_min": pr_q3,
        "routing_median_min": rt_med,
        "routing_q1_min": rt_q1,
        "routing_q3_min": rt_q3,
        "routing_mean_min": mean_routing,
        "total_latency_mean_split_min": mean_total,
        "routing_share_pct": share,
        "n_routing_components_eligible": int(g["fetch_min"].notna().sum()),
        "fetch_median_min": _quantiles(g["fetch_min"])[0],
        "upload_median_min": _quantiles(g["upload_min"])[0],
        "download_median_min": _quantiles(g["download_min"])[0],
        "n_tat_eligible": int(g["tat_min"].notna().sum()),
        "tat_median_min": tat_med,
        "tat_q1_min": tat_q1,
        "tat_q3_min": tat_q3,
    }


def summarize(prepared: pd.DataFrame, by: Sequence[str] | None = None) -> pd.DataFrame:
    """Too Late rate, timing categories, total latency (with routing/processing decomposition) and TAT, optionally by group."""
    by = list(by or [])
    if not by:
        return pd.DataFrame([{"group": "overall", **_summarize_group(prepared)}])
    rows = []
    for key, g in prepared.groupby(by, sort=True, dropna=False):
        key = key if isinstance(key, tuple) else (key,)
        rows.append({**dict(zip(by, key)), **_summarize_group(g)})
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Quarterly stability
# --------------------------------------------------------------------------- #


def cv_pct(values: Iterable[float]) -> float:
    """Coefficient of variation (%), sample standard deviation (ddof=1)."""
    v = np.asarray(list(values), dtype=float)
    if len(v) < 2 or np.mean(v) == 0:
        return math.nan
    return float(np.std(v, ddof=1) / np.mean(v) * 100)


def spearman_rho(values: Sequence[float]) -> float:
    """Spearman correlation between position (quarter order) and value."""
    v = pd.Series(list(values), dtype=float)
    if len(v) < 3 or v.nunique() < 2:
        return 0.0
    r_x = pd.Series(np.arange(len(v)), dtype=float)
    r_y = v.rank(method="average")
    return float(np.corrcoef(r_x, r_y)[0, 1])


def classify_pattern(medians: Sequence[float], th: StabilityThresholds | None = None) -> tuple[str, str]:
    """Assign a quarterly latency pattern to a time-ordered series of medians.

    Definitions follow the eTable 3 footnote of the JACR paper:

    * steady-state: CV < 15% and no sustained directional trend;
    * progressive drift: gradual monotonic increase;
    * post-deployment convergence: initial elevated latency converging down;
    * transient incident: transient elevation in adjacent quarters with full
      subsequent recovery.

    Operational rules (checked in this order):

    1. fewer than ``min_quarters`` values: ``insufficient_data``;
    2. transient incident: a run of 1 to ``incident_max_quarters`` adjacent
       quarters, preceded by at least one quarter, each >= ``incident_factor``
       x the median of the preceding quarters (baseline), followed by at least
       one quarter, with every later quarter <= ``recovery_factor`` x baseline
       and the quarter just before the run not elevated;
    3. progressive drift: Spearman rho >= ``trend_rho`` and mean of last k
       quarters / mean of first k quarters >= ``trend_ratio``;
    4. post-deployment convergence: rho <= -``trend_rho`` and that ratio
       <= 1 / ``trend_ratio``;
    5. steady-state: CV < ``steady_cv_max_pct``;
    6. otherwise ``variable_unclassified``.

    Returns ``(pattern, detail)`` where detail is a short human-readable reason.
    """
    th = th or StabilityThresholds()
    v = [float(x) for x in medians if x is not None and not (isinstance(x, float) and math.isnan(x))]
    n = len(v)
    if n < th.min_quarters:
        return INSUFFICIENT, f"{n} quarter(s) with data; need >= {th.min_quarters}"

    for start in range(1, n - 1):
        baseline = float(np.median(v[:start]))
        # the quarter before the run must itself be at baseline level
        if baseline <= 0 or v[start - 1] >= th.incident_factor * baseline:
            continue
        for length in range(1, th.incident_max_quarters + 1):
            end = start + length
            if end >= n:
                break
            window = v[start:end]
            after = v[end:]
            if all(x >= th.incident_factor * baseline for x in window) and all(
                x <= th.recovery_factor * baseline for x in after
            ):
                return INCIDENT, (
                    f"quarters {start + 1}-{end} elevated (max {max(window) / baseline:.2f}x baseline "
                    f"{baseline:.2f}), recovered in {len(after)} later quarter(s)"
                )

    rho = spearman_rho(v)
    k = max(1, min(th.edge_quarters, n // 2))
    first, last = float(np.mean(v[:k])), float(np.mean(v[-k:]))
    ratio = last / first if first > 0 else math.nan
    cv = cv_pct(v)
    if rho >= th.trend_rho and ratio >= th.trend_ratio:
        return DRIFT, f"rho {rho:.2f}, last/first {ratio:.2f}"
    if rho <= -th.trend_rho and ratio <= 1 / th.trend_ratio:
        return CONVERGENCE, f"rho {rho:.2f}, last/first {ratio:.2f}"
    if cv < th.steady_cv_max_pct:
        return STEADY, f"CV {cv:.1f}%, rho {rho:.2f}, last/first {ratio:.2f}"
    return VARIABLE, f"CV {cv:.1f}% without a classifiable trend or incident"


def quarterly_long(prepared: pd.DataFrame, th: StabilityThresholds | None = None) -> pd.DataFrame:
    """Per ai_solution x quarter: n, median [IQR] total latency, median processing time, routing share and Too Late rate."""
    th = th or StabilityThresholds()
    p = prepared[prepared["quarter"] != "unknown"]
    out = summarize(p, ["ai_solution", "quarter"])
    if out.empty:
        return out
    keep = [
        "ai_solution",
        "quarter",
        "n_latency_eligible",
        "total_latency_median_min",
        "total_latency_q1_min",
        "total_latency_q3_min",
        "n_split_eligible",
        "processing_median_min",
        "routing_share_pct",
        "n_too_late_eligible",
        "n_too_late",
        "too_late_rate_pct",
    ]
    out = out[keep].copy()
    out["used_for_stability"] = out["n_latency_eligible"] >= th.min_quarter_n
    return out.sort_values(["ai_solution", "quarter"]).reset_index(drop=True)


def stability_table(prepared: pd.DataFrame, th: StabilityThresholds | None = None) -> pd.DataFrame:
    """One row per ai_solution: quarterly medians (wide), CV, trend statistics and pattern."""
    th = th or StabilityThresholds()
    long = quarterly_long(prepared, th)
    cols_fixed = ["ai_solution", "n_quarters", "first_quarter", "last_quarter", "cv_pct", "spearman_rho", "last_first_ratio", "pattern", "pattern_detail"]
    if long.empty:
        return pd.DataFrame(columns=cols_fixed)
    used = long[long["used_for_stability"]]
    quarters = sorted(used["quarter"].unique())
    rows = []
    for sol in sorted(long.loc[long["n_latency_eligible"] > 0, "ai_solution"].unique()):
        s = used[used["ai_solution"] == sol].sort_values("quarter")
        med = s["total_latency_median_min"].tolist()
        pattern, detail = classify_pattern(med, th)
        k = max(1, min(th.edge_quarters, len(med) // 2)) if med else 1
        row = {
            "ai_solution": sol,
            "n_quarters": len(med),
            "first_quarter": s["quarter"].iloc[0] if len(s) else None,
            "last_quarter": s["quarter"].iloc[-1] if len(s) else None,
            "cv_pct": cv_pct(med),
            "spearman_rho": spearman_rho(med) if len(med) >= 3 else math.nan,
            "last_first_ratio": (np.mean(med[-k:]) / np.mean(med[:k])) if len(med) >= 2 else math.nan,
            "pattern": pattern,
            "pattern_detail": detail,
        }
        for qtr in quarters:
            hit = s.loc[s["quarter"] == qtr, "total_latency_median_min"]
            row[f"median_min_{qtr}"] = float(hit.iloc[0]) if len(hit) else math.nan
        rows.append(row)
    if not rows:
        return pd.DataFrame(columns=cols_fixed)
    return pd.DataFrame(rows).sort_values(["cv_pct", "ai_solution"], na_position="last").reset_index(drop=True)
