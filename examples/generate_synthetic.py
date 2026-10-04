"""Generate the simulated example dataset in examples/synthetic_exams.csv.

All values are simulated (SYNTHETIC DATA). The dataset contains five anonymous
AI solutions (AI solution A to E) over eight calendar quarters, each built to show one
stability pattern, plus injected data-quality anomalies (missing, inverted
and unparseable timestamps, duplicates).

Usage:
    python examples/generate_synthetic.py [--n 6000] [--seed 42]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from too_late_rate.synthetic import generate_synthetic


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--n", type=int, default=6000)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", type=Path, default=Path(__file__).with_name("synthetic_exams.csv"))
    args = ap.parse_args()
    df = generate_synthetic(n=args.n, seed=args.seed)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} rows to {args.out}")


if __name__ == "__main__":
    main()
