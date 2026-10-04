"""Markdown report."""

from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import TYPE_CHECKING

import pandas as pd

from . import __version__

if TYPE_CHECKING:  # pragma: no cover
    from .api import Result


def _f(x, nd: int = 1) -> str:
    if x is None or (isinstance(x, float) and math.isnan(x)):
        return "n/a"
    return f"{x:.{nd}f}"


def _md_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No data._\n"
    cols = list(df.columns)
    lines = ["| " + " | ".join(cols) + " |", "|" + "|".join("---" for _ in cols) + "|"]
    for _, r in df.iterrows():
        lines.append("| " + " | ".join(str(r[c]) for c in cols) + " |")
    return "\n".join(lines) + "\n"


def _group_rows(t: pd.DataFrame, key: str) -> pd.DataFrame:
    rows = []
    for _, r in t.iterrows():
        rows.append(
            {
                key: r[key],
                "Too Late n/N": f"{int(r['n_too_late'])}/{int(r['n_too_late_eligible'])}",
                "Too Late %": _f(r["too_late_rate_pct"]),
                "95% CI": f"{_f(r['too_late_ci95_low_pct'])}-{_f(r['too_late_ci95_high_pct'])}",
                "Before creation %": _f(r["pct_before_report_creation"]),
                "During dictation %": _f(r["pct_during_dictation"]),
                "After finalization %": _f(r["pct_after_finalization"]),
                "Latency median [IQR], min": f"{_f(r['total_latency_median_min'], 2)} "
                f"[{_f(r['total_latency_q1_min'], 2)}-{_f(r['total_latency_q3_min'], 2)}]",
                "Processing median, min": _f(r["processing_median_min"], 2),
                "Routing share %": _f(r["routing_share_pct"]),
            }
        )
    return pd.DataFrame(rows)


def render_markdown(result: "Result", title: str = "Too Late rate report") -> str:
    t = result.tables
    o = result.overall
    out = [f"# {title}\n"]
    out.append(
        f"Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} with too-late-rate "
        f"{__version__}. Local timezone for naive timestamps and quarters: `{result.config.timezone}`.\n"
    )
    out.append("## Headline\n")
    out.append(
        f"- **Too Late rate:** {_f(o['too_late_rate_pct'])}% "
        f"({int(o['n_too_late'])}/{int(o['n_too_late_eligible'])}; 95% CI "
        f"{_f(o['too_late_ci95_low_pct'])}-{_f(o['too_late_ci95_high_pct'])}%). "
        "Report finalized strictly before the AI result was available; no threshold."
    )
    if o["n_timing_eligible"]:
        out.append(
            f"- **Timing categories** (N={int(o['n_timing_eligible'])} with report creation time): "
            f"before report creation {_f(o['pct_before_report_creation'])}%, "
            f"during dictation {_f(o['pct_during_dictation'])}%, "
            f"after finalization {_f(o['pct_after_finalization'])}%."
        )
    if o["n_latency_eligible"]:
        out.append(
            f"- **Total latency** (AI result available minus study end, N={int(o['n_latency_eligible'])}): "
            f"median {_f(o['total_latency_median_min'], 2)} min "
            f"[IQR {_f(o['total_latency_q1_min'], 2)}-{_f(o['total_latency_q3_min'], 2)}]."
        )
    if o["n_split_eligible"]:
        out.append(
            f"- **Latency decomposition** (N={int(o['n_split_eligible'])} with AI processing time): "
            f"AI processing median {_f(o['processing_median_min'], 2)} min "
            f"[IQR {_f(o['processing_q1_min'], 2)}-{_f(o['processing_q3_min'], 2)}]; "
            f"routing time median {_f(o['routing_median_min'], 2)} min; "
            f"routing share (ratio of means) {_f(o['routing_share_pct'])}%."
        )
    if o["n_routing_components_eligible"]:
        out.append(
            f"- **Routing components** (N={int(o['n_routing_components_eligible'])}): median fetching "
            f"{_f(o['fetch_median_min'], 2)} min, upload {_f(o['upload_median_min'], 2)} min, "
            f"download {_f(o['download_median_min'], 2)} min."
        )
    if o["n_tat_eligible"]:
        out.append(
            f"- **Report TAT** (finalized minus created, N={int(o['n_tat_eligible'])}): "
            f"median {_f(o['tat_median_min'], 2)} min "
            f"[IQR {_f(o['tat_q1_min'], 2)}-{_f(o['tat_q3_min'], 2)}]."
        )

    out.append("")
    for name, key, heading in (
        ("summary_by_ai_solution", "ai_solution", "By AI solution"),
        ("summary_by_modality", "modality", "By modality"),
        ("summary_by_site", "site", "By site"),
        ("summary_by_quarter", "quarter", "By calendar quarter"),
    ):
        out.append(f"## {heading}\n")
        out.append(_md_table(_group_rows(t[name], key)))

    out.append("\n## Quarterly latency stability by AI solution\n")
    st = t["stability_by_ai_solution"]
    if st.empty:
        out.append("_No quarterly latency data (study end timestamp absent or too few exams per quarter)._\n")
    else:
        view = pd.DataFrame(
            {
                "AI solution": st["ai_solution"],
                "Quarters": st["n_quarters"],
                "Window": st["first_quarter"].astype(str) + " to " + st["last_quarter"].astype(str),
                "CV %": st["cv_pct"].map(_f),
                "Pattern": st["pattern"],
                "Why": st["pattern_detail"],
            }
        )
        out.append(_md_table(view))
        out.append(
            f"\nQuarters with fewer than {result.config.stability.min_quarter_n} latency-eligible exams are "
            "not used. CV is the sample standard deviation of quarterly medians over their mean; it depends "
            "on the number of quarters and is not comparable between solutions with different windows. The "
            "pattern flag is a screening heuristic: inspect the quarterly table before acting on it.\n"
        )

    out.append("\n## Data quality\n")
    out.append(_md_table(result.data_quality))
    out.append(
        "\n## Definitions and caveats\n"
        "- Unit of analysis: one (exam_id, ai_solution) pair. Duplicate pairs keep the earliest AI result.\n"
        "- Too Late: `report_finalized_ts < ai_result_available_ts`. Equal timestamps are not Too Late.\n"
        "- Before report creation: `ai_result_available_ts <= report_created_ts`. During dictation: "
        "`report_created_ts < ai_result_available_ts <= report_finalized_ts`. After finalization equals Too Late.\n"
        "- Exams with report created after report finalized are excluded from the Too Late rate, the timing "
        "categories and TAT. Exams with AI result before study end are excluded from total latency.\n"
        "- Total latency (AI result available minus study end) = routing time (fetching + upload + download) "
        "+ inference time (AI processing). Processing = inference end minus inference start, or "
        "`ai_processing_seconds`; routing = total latency minus processing. Routing share = mean routing time / "
        "mean total latency (ratio of means), on exams with both values.\n"
        "- The Too Late rate measures infrastructure-imposed temporal loss. It is a ceiling on lost "
        "opportunity for AI to inform the report, not a measure of clinical harm or of radiologist engagement.\n"
        "- Results depend on synchronized clocks between the RIS, the AI platform and the modality. Check "
        "clock drift before comparing sites.\n"
    )
    return "\n".join(out)
