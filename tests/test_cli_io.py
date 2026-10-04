import pandas as pd
import pytest

from too_late_rate import Config, compute
from too_late_rate.cli import main
from too_late_rate.synthetic import generate_synthetic

EXPECTED = {
    "report.md",
    "data_quality.csv",
    "summary_overall.csv",
    "summary_by_ai_solution.csv",
    "summary_by_modality.csv",
    "summary_by_site.csv",
    "summary_by_quarter.csv",
    "summary_by_ai_solution_modality.csv",
    "quarterly_by_ai_solution.csv",
    "stability_by_ai_solution.csv",
}


def test_synth_and_compute_cli(tmp_path, capsys):
    data = tmp_path / "s.csv"
    assert main(["synth", "--out", str(data), "--n", "3000", "--seed", "1"]) == 0
    out = tmp_path / "rep"
    assert main(["compute", str(data), "--out", str(out), "--timezone", "Europe/Zurich", "--exam-level"]) == 0
    files = {p.name for p in out.iterdir()}
    assert EXPECTED | {"exam_level.csv"} <= files
    assert "Too Late rate:" in capsys.readouterr().out
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "## Quarterly latency stability by AI solution" in md
    assert chr(0x2014) not in md  # no em dash


def test_synthetic_patterns_recovered():
    res = compute(generate_synthetic(n=6000, seed=42), Config(timezone="Europe/Zurich"))
    st = res.tables["stability_by_ai_solution"].set_index("ai_solution")["pattern"].to_dict()
    assert st == {
        "AI solution A": "steady_state",
        "AI solution B": "progressive_drift",
        "AI solution C": "post_deployment_convergence",
        "AI solution D": "transient_incident",
        "AI solution E": "steady_state",
    }
    dq = res.data_quality.set_index("check")["n"]
    assert dq["duplicate_exam_solution_rows_dropped"] > 0
    assert dq["negative_report_interval_created_after_finalized"] > 0


def test_cli_yaml_and_col_override(tmp_path):
    df = pd.DataFrame([dict(Acc="1", Tool="S", Final="2025-01-01 10:05", Ready="2025-01-01 10:09")])
    src = tmp_path / "in.csv"
    df.to_csv(src, index=False)
    cfg = tmp_path / "c.yaml"
    cfg.write_text("timezone: Europe/Zurich\ncolumns:\n  exam_id: Acc\n  ai_solution: Tool\n  report_finalized_ts: WRONG\n")
    out = tmp_path / "o"
    rc = main(["compute", str(src), "--config", str(cfg), "--col", "report_finalized_ts=Final",
               "--col", "ai_result_available_ts=Ready", "--out", str(out)])
    assert rc == 0
    s = pd.read_csv(out / "summary_overall.csv")
    assert s.loc[0, "n_too_late"] == 1


def test_cli_error_on_missing_column(tmp_path, capsys):
    src = tmp_path / "in.csv"
    pd.DataFrame([dict(exam_id="1")]).to_csv(src, index=False)
    assert main(["compute", str(src), "--out", str(tmp_path / "o")]) == 2
    assert "Missing required column" in capsys.readouterr().err


def test_bad_config_key():
    with pytest.raises(ValueError, match="Unknown config key"):
        Config.from_dict({"colums": {}})


def test_parquet_roundtrip(tmp_path, basic_df):
    pytest.importorskip("pyarrow")
    path = tmp_path / "x.parquet"
    basic_df.to_parquet(path)
    assert compute(path).overall["n_too_late"] == 1


def test_tsv_input(tmp_path, basic_df):
    path = tmp_path / "x.tsv"
    basic_df.to_csv(path, sep="\t", index=False)
    assert compute(path).overall["n_too_late"] == 1
