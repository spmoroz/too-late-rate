"""High-level Python API."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from . import __version__
from .config import Config
from .io import read_table
from .metrics import prepare, quarterly_long, stability_table, summarize

GROUPINGS: dict[str, list[str]] = {
    "summary_overall": [],
    "summary_by_ai_solution": ["ai_solution"],
    "summary_by_modality": ["modality"],
    "summary_by_site": ["site"],
    "summary_by_quarter": ["quarter"],
    "summary_by_ai_solution_modality": ["ai_solution", "modality"],
}


@dataclass
class Result:
    """All outputs of one run. ``tables`` maps a table name to a DataFrame."""

    prepared: pd.DataFrame
    data_quality: pd.DataFrame
    tables: dict[str, pd.DataFrame] = field(default_factory=dict)
    config: Config = field(default_factory=Config)

    @property
    def overall(self) -> pd.Series:
        return self.tables["summary_overall"].iloc[0]

    def to_markdown(self, title: str = "Too Late rate report") -> str:
        from .report import render_markdown

        return render_markdown(self, title=title)

    def write(self, out_dir: str | Path, write_exam_level: bool = False) -> list[Path]:
        """Write every table as CSV plus ``report.md``. Returns the written paths."""
        out = Path(out_dir)
        out.mkdir(parents=True, exist_ok=True)
        written = []
        for name, table in {"data_quality": self.data_quality, **self.tables}.items():
            path = out / f"{name}.csv"
            table.to_csv(path, index=False, float_format="%.4f")
            written.append(path)
        if write_exam_level:
            path = out / "exam_level.csv"
            self.prepared.to_csv(path, index=False, float_format="%.4f")
            written.append(path)
        path = out / "report.md"
        path.write_text(self.to_markdown(), encoding="utf-8")
        written.append(path)
        return written


def compute(data: pd.DataFrame | str | Path, config: Config | None = None) -> Result:
    """Compute every metric from a DataFrame or a CSV/TSV/Parquet path.

    Examples
    --------
    >>> from too_late_rate import compute, Config
    >>> res = compute("exams.csv", Config(timezone="Europe/Zurich"))  # doctest: +SKIP
    >>> res.overall["too_late_rate_pct"]  # doctest: +SKIP
    """
    config = config or Config()
    df = data if isinstance(data, pd.DataFrame) else read_table(data)
    prepared, dq = prepare(df, config)
    tables = {name: summarize(prepared, by) for name, by in GROUPINGS.items()}
    tables["quarterly_by_ai_solution"] = quarterly_long(prepared, config.stability)
    tables["stability_by_ai_solution"] = stability_table(prepared, config.stability)
    return Result(prepared=prepared, data_quality=dq, tables=tables, config=config)


__all__ = ["compute", "Result", "GROUPINGS", "__version__"]
