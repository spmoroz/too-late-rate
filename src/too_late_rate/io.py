"""Input reading and timezone-safe timestamp parsing."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

# ISO 8601 with an explicit offset or Z after a time component, for example
# "2025-03-01T08:15:00+01:00", "2025-03-01 08:15:00Z", "2025-03-01T08:15+0100".
_ISO_AWARE = r"\d{2}:\d{2}(?::\d{2}(?:[.,]\d+)?)?\s*(?:[Zz]|[+-]\d{2}:?\d{2})$"
# HL7 v2 TS/DTM: YYYYMMDD[HH[MM[SS[.S+]]]][+/-ZZZZ]
_HL7 = r"^(\d{8}(?:\d{2}){0,3})(\.\d{1,6})?([+-]\d{4})?$"


def read_table(path: str | Path) -> pd.DataFrame:
    """Read a CSV, TSV or Parquet file. All columns are read as text for CSV/TSV."""
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix in {".parquet", ".pq"}:
        try:
            return pd.read_parquet(path)
        except ImportError as exc:  # pragma: no cover - depends on env
            raise ImportError("Reading Parquet needs pyarrow: pip install 'too-late-rate[parquet]'") from exc
    sep = "\t" if suffix in {".tsv", ".tab"} else ","
    return pd.read_csv(path, sep=sep, dtype=str, keep_default_na=True)


def _localize(naive: pd.Series, tz: str, ambiguous: str) -> pd.Series:
    """Attach ``tz`` to naive datetimes and convert to UTC."""
    if ambiguous == "NaT":
        amb: object = "NaT"
    elif ambiguous == "earliest":
        amb = np.ones(len(naive), dtype=bool)
    else:
        amb = np.zeros(len(naive), dtype=bool)
    return naive.dt.tz_localize(tz, ambiguous=amb, nonexistent="NaT").dt.tz_convert("UTC")


def _empty_utc(index: pd.Index) -> pd.Series:
    return pd.Series(pd.NaT, index=index, dtype="datetime64[ns, UTC]")


def _parse_hl7(raw: pd.Series, tz: str, ambiguous: str) -> pd.Series:
    parts = raw.str.extract(_HL7)
    digits = parts[0].str.ljust(14, "0")
    base = pd.to_datetime(digits, format="%Y%m%d%H%M%S", errors="coerce")
    frac = pd.to_numeric(parts[1].fillna("0"), errors="coerce").fillna(0.0)
    base = base + pd.to_timedelta(frac, unit="s")
    out = _empty_utc(raw.index)
    has_off = parts[2].notna()
    if has_off.any():
        off = parts[2][has_off]
        sign = np.where(off.str[0] == "-", -1, 1)
        minutes = sign * (off.str[1:3].astype(int) * 60 + off.str[3:5].astype(int))
        utc = (base[has_off] - pd.to_timedelta(minutes, unit="m")).dt.tz_localize("UTC")
        out.loc[has_off] = utc
    if (~has_off).any():
        out.loc[~has_off] = _localize(base[~has_off], tz, ambiguous)
    return out


def parse_timestamps(values: pd.Series, tz: str = "UTC", ambiguous: str = "NaT") -> tuple[pd.Series, int]:
    """Parse a column of timestamps to timezone-aware UTC.

    Accepted inputs, which may be mixed within one column:

    * ISO 8601 strings with an offset or ``Z``: converted to UTC exactly.
    * ISO 8601 or other pandas-parsable strings without an offset: interpreted
      as local time in ``tz``, then converted to UTC.
    * HL7 v2 TS/DTM strings (``YYYYMMDDHHMMSS[.S][+ZZZZ]``): offset honoured
      if present, otherwise interpreted in ``tz``.
    * Already-parsed pandas datetimes (naive: interpreted in ``tz``).

    Local times that do not exist (spring-forward gap) become NaT. Local times
    that occur twice (fall-back) follow ``ambiguous``.

    Returns
    -------
    (parsed, n_invalid)
        ``parsed`` is a ``datetime64[ns, UTC]`` Series. ``n_invalid`` counts
        non-empty inputs that could not be turned into a valid instant.
    """
    if isinstance(values.dtype, pd.DatetimeTZDtype):
        return values.dt.tz_convert("UTC").astype("datetime64[ns, UTC]"), 0
    if pd.api.types.is_datetime64_dtype(values):
        out = _localize(values, tz, ambiguous).astype("datetime64[ns, UTC]")
        return out, int((values.notna() & out.isna()).sum())

    raw = values.astype("string").str.strip()
    raw = raw.mask(raw == "")
    raw = raw.mask(raw.str.lower().isin(["nan", "nat", "none", "null"]))
    present = raw.notna()
    out = _empty_utc(values.index)

    hl7 = present & raw.str.match(_HL7).fillna(False).astype(bool)
    aware = present & ~hl7 & raw.str.contains(_ISO_AWARE, regex=True).fillna(False).astype(bool)
    naive = present & ~hl7 & ~aware

    if hl7.any():
        out.loc[hl7] = _parse_hl7(raw[hl7], tz, ambiguous)
    if aware.any():
        out.loc[aware] = pd.to_datetime(raw[aware], utc=True, errors="coerce", format="mixed")
    if naive.any():
        parsed = pd.to_datetime(raw[naive], errors="coerce", format="mixed")
        if isinstance(parsed.dtype, pd.DatetimeTZDtype):  # pragma: no cover - defensive
            parsed = parsed.dt.tz_convert("UTC")
            out.loc[naive] = parsed
        else:
            out.loc[naive] = _localize(parsed, tz, ambiguous)

    out = out.astype("datetime64[ns, UTC]")
    n_invalid = int((present & out.isna()).sum())
    return out, n_invalid
