"""Configuration: column mapping, timezone handling and stability thresholds."""

from __future__ import annotations

from dataclasses import dataclass, field, fields
from pathlib import Path
from typing import Any, Mapping

#: Logical column names used internally, mapped to the input column names.
DEFAULT_COLUMNS: dict[str, str] = {
    "exam_id": "exam_id",
    "ai_solution": "ai_solution",
    "modality": "modality",
    "site": "site",
    "report_created_ts": "report_created_ts",
    "report_finalized_ts": "report_finalized_ts",
    "ai_result_available_ts": "ai_result_available_ts",
    "study_end_ts": "study_end_ts",
    "ai_inference_start_ts": "ai_inference_start_ts",
    "ai_inference_end_ts": "ai_inference_end_ts",
    "ai_processing_seconds": "ai_processing_seconds",
    "ai_fetched_ts": "ai_fetched_ts",
}

#: Columns that must be present in the input.
REQUIRED_COLUMNS: tuple[str, ...] = (
    "exam_id",
    "ai_solution",
    "report_finalized_ts",
    "ai_result_available_ts",
)

#: Logical columns that hold timestamps.
TIMESTAMP_COLUMNS: tuple[str, ...] = (
    "report_created_ts",
    "report_finalized_ts",
    "ai_result_available_ts",
    "study_end_ts",
    "ai_inference_start_ts",
    "ai_inference_end_ts",
    "ai_fetched_ts",
)

AMBIGUOUS_CHOICES = ("NaT", "earliest", "latest")


@dataclass
class StabilityThresholds:
    """Thresholds for the quarterly stability pattern flag.

    The defaults were calibrated so that they reproduce the pattern labels
    reported in eTable 3 of the JACR paper. They are a transparent heuristic,
    not a statistical test.
    """

    #: Minimum number of quarters with data before any pattern is assigned.
    min_quarters: int = 3
    #: Minimum exams with a valid total latency for a quarter to be used.
    min_quarter_n: int = 20
    #: Steady-state requires a coefficient of variation below this value (%).
    steady_cv_max_pct: float = 15.0
    #: Absolute Spearman rho (quarter index vs median) that counts as a trend.
    trend_rho: float = 0.6
    #: Ratio of the mean of the last k vs first k quarterly medians that
    #: counts as a material change (drift if >= ratio, convergence if <= 1/ratio).
    trend_ratio: float = 1.25
    #: Number of quarters averaged at each end for the end/start ratio.
    edge_quarters: int = 2
    #: A quarter is "elevated" if its median is >= this factor x baseline.
    incident_factor: float = 1.3
    #: Longest run of adjacent elevated quarters still called transient.
    incident_max_quarters: int = 2
    #: Recovery means every later quarter is <= this factor x baseline.
    recovery_factor: float = 1.15


@dataclass
class Config:
    """Run configuration.

    Parameters
    ----------
    columns:
        Mapping from logical column name to the column name in the input.
        Missing keys fall back to :data:`DEFAULT_COLUMNS`.
    timezone:
        IANA timezone used to interpret timestamps that carry no UTC offset,
        and to assign calendar quarters. Default ``"UTC"``.
    ambiguous:
        How to resolve local times that occur twice at the end of daylight
        saving time: ``"NaT"`` (treat as invalid, default), ``"earliest"``
        (first occurrence, summer time) or ``"latest"`` (second occurrence).
    stability:
        Thresholds for the quarterly stability table.
    """

    columns: dict[str, str] = field(default_factory=lambda: dict(DEFAULT_COLUMNS))
    timezone: str = "UTC"
    ambiguous: str = "NaT"
    stability: StabilityThresholds = field(default_factory=StabilityThresholds)

    def __post_init__(self) -> None:
        merged = dict(DEFAULT_COLUMNS)
        unknown = set(self.columns) - set(DEFAULT_COLUMNS)
        if unknown:
            raise ValueError(
                f"Unknown logical column(s) in mapping: {sorted(unknown)}. "
                f"Valid names: {sorted(DEFAULT_COLUMNS)}"
            )
        merged.update(self.columns)
        self.columns = merged
        if self.ambiguous not in AMBIGUOUS_CHOICES:
            raise ValueError(f"ambiguous must be one of {AMBIGUOUS_CHOICES}, got {self.ambiguous!r}")
        _check_timezone(self.timezone)

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "Config":
        data = dict(data or {})
        allowed = {"columns", "timezone", "ambiguous", "stability"}
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"Unknown config key(s): {sorted(unknown)}. Allowed: {sorted(allowed)}")
        stab = data.pop("stability", None) or {}
        valid = {f.name for f in fields(StabilityThresholds)}
        bad = set(stab) - valid
        if bad:
            raise ValueError(f"Unknown stability key(s): {sorted(bad)}. Allowed: {sorted(valid)}")
        return cls(
            columns=dict(data.get("columns") or {}),
            timezone=data.get("timezone", "UTC"),
            ambiguous=str(data.get("ambiguous", "NaT")),
            stability=StabilityThresholds(**stab),
        )

    @classmethod
    def from_yaml(cls, path: str | Path) -> "Config":
        import yaml

        with open(path, encoding="utf-8") as fh:
            return cls.from_dict(yaml.safe_load(fh) or {})


def _check_timezone(name: str) -> None:
    try:
        from zoneinfo import ZoneInfo

        ZoneInfo(name)
    except Exception as exc:  # pragma: no cover - message path
        raise ValueError(f"Unknown timezone {name!r}: use an IANA name such as 'Europe/Zurich'") from exc
