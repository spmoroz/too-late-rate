"""too-late-rate: timing metrics for deployed radiology AI from HL7/RIS timestamps."""

__version__ = "1.0.0"

from .api import Result, compute  # noqa: E402
from .config import Config, StabilityThresholds  # noqa: E402
from .io import parse_timestamps, read_table  # noqa: E402
from .metrics import classify_pattern, cv_pct, prepare, stability_table, summarize  # noqa: E402

__all__ = [
    "__version__",
    "Config",
    "StabilityThresholds",
    "Result",
    "compute",
    "prepare",
    "summarize",
    "stability_table",
    "classify_pattern",
    "cv_pct",
    "parse_timestamps",
    "read_table",
]
