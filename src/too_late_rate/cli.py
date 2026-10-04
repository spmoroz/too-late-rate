"""Command-line interface: ``too-late-rate compute`` and ``too-late-rate synth``."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import AMBIGUOUS_CHOICES, DEFAULT_COLUMNS, Config


def _parse_col(values: list[str] | None) -> dict[str, str]:
    mapping: dict[str, str] = {}
    for item in values or []:
        if "=" not in item:
            raise SystemExit(f"--col expects LOGICAL=INPUT_COLUMN, got {item!r}")
        k, v = item.split("=", 1)
        k = k.strip()
        if k not in DEFAULT_COLUMNS:
            raise SystemExit(f"Unknown logical column {k!r}. Valid: {', '.join(DEFAULT_COLUMNS)}")
        mapping[k] = v.strip()
    return mapping


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="too-late-rate",
        description="Too Late rate and timing metrics for deployed radiology AI from HL7/RIS timestamps.",
    )
    p.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    c = sub.add_parser("compute", help="Compute metrics from a CSV/TSV/Parquet file.")
    c.add_argument("input", type=Path, help="Input file (.csv, .tsv, .parquet).")
    c.add_argument("--out", type=Path, default=Path("report"), help="Output directory (default: report/).")
    c.add_argument("--config", type=Path, help="YAML config (columns, timezone, ambiguous, stability).")
    c.add_argument(
        "--col",
        action="append",
        metavar="LOGICAL=INPUT",
        help="Column mapping, repeatable, e.g. --col report_finalized_ts=HL7_Validated. Overrides the config file.",
    )
    c.add_argument("--timezone", help="IANA timezone for timestamps without offset and for quarters (default UTC).")
    c.add_argument("--ambiguous", choices=AMBIGUOUS_CHOICES, help="Resolution of repeated local times at DST end.")
    c.add_argument("--min-quarter-n", type=int, help="Minimum exams per quarter for the stability table (default 20).")
    c.add_argument("--exam-level", action="store_true", help="Also write exam_level.csv (per-exam flags).")
    c.add_argument("--title", default="Too Late rate report", help="Title of report.md.")

    s = sub.add_parser("synth", help="Write a synthetic example dataset (no real data).")
    s.add_argument("--out", type=Path, default=Path("synthetic_exams.csv"))
    s.add_argument("--n", type=int, default=6000)
    s.add_argument("--seed", type=int, default=42)
    return p


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "synth":
        from .synthetic import generate_synthetic

        df = generate_synthetic(n=args.n, seed=args.seed)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        df.to_csv(args.out, index=False)
        print(f"Wrote {len(df)} synthetic rows to {args.out}")
        return 0

    from .api import compute

    cfg_dict: dict = {}
    if args.config:
        import yaml

        cfg_dict = yaml.safe_load(args.config.read_text(encoding="utf-8")) or {}
    cols = dict(cfg_dict.get("columns") or {})
    cols.update(_parse_col(args.col))
    cfg_dict["columns"] = cols
    if args.timezone:
        cfg_dict["timezone"] = args.timezone
    if args.ambiguous:
        cfg_dict["ambiguous"] = args.ambiguous
    if args.min_quarter_n is not None:
        cfg_dict.setdefault("stability", {})
        cfg_dict["stability"] = dict(cfg_dict["stability"] or {}, min_quarter_n=args.min_quarter_n)

    try:
        config = Config.from_dict(cfg_dict)
        result = compute(args.input, config)
    except (ValueError, FileNotFoundError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result.write(args.out, write_exam_level=args.exam_level)
    o = result.overall
    print(
        f"Too Late rate: {o['too_late_rate_pct']:.1f}% ({int(o['n_too_late'])}/{int(o['n_too_late_eligible'])}). "
        f"Tables and report.md written to {args.out}/"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
