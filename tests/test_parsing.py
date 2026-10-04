import pandas as pd
import pytest

from too_late_rate import parse_timestamps


def ts(s):
    return pd.Timestamp(s)


def test_aware_iso_converted_exactly():
    out, bad = parse_timestamps(pd.Series(["2025-03-01T08:15:00+01:00", "2025-03-01T07:15:00Z"]), tz="America/New_York")
    assert bad == 0
    assert out.iloc[0] == out.iloc[1] == ts("2025-03-01T07:15:00Z")


def test_naive_interpreted_in_timezone():
    out, _ = parse_timestamps(pd.Series(["2025-07-01 10:00:00"]), tz="Europe/Zurich")
    assert out.iloc[0] == ts("2025-07-01T08:00:00Z")  # CEST = UTC+2
    out, _ = parse_timestamps(pd.Series(["2025-01-01 10:00:00"]), tz="Europe/Zurich")
    assert out.iloc[0] == ts("2025-01-01T09:00:00Z")  # CET = UTC+1


def test_mixed_formats_in_one_column():
    s = pd.Series(["2025-01-01 10:00:00", "2025-01-01T10:00:00+01:00", "20250101100000", "20250101100000+0100", None, ""])
    out, bad = parse_timestamps(s, tz="Europe/Zurich")
    assert bad == 0
    assert out.iloc[:4].nunique() == 1
    assert out.iloc[0] == ts("2025-01-01T09:00:00Z")
    assert out.iloc[4:].isna().all()


def test_hl7_precision_variants():
    s = pd.Series(["202501011000", "2025010110", "20250101", "20250101100000.5-0500"])
    out, bad = parse_timestamps(s, tz="UTC")
    assert bad == 0
    assert out.iloc[0] == ts("2025-01-01T10:00:00Z")
    assert out.iloc[1] == ts("2025-01-01T10:00:00Z")
    assert out.iloc[2] == ts("2025-01-01T00:00:00Z")
    assert out.iloc[3] == ts("2025-01-01T15:00:00.5Z")


def test_date_only_iso_not_mistaken_for_offset():
    out, bad = parse_timestamps(pd.Series(["2025-01-01"]), tz="Europe/Zurich")
    assert bad == 0
    assert out.iloc[0] == ts("2024-12-31T23:00:00Z")


def test_invalid_counted():
    out, bad = parse_timestamps(pd.Series(["not a date", "2025-13-40 10:00", "2025-01-01 10:00"]), tz="UTC")
    assert bad == 2
    assert out.isna().sum() == 2


def test_dst_gap_nonexistent_is_invalid():
    # 2025-03-30 02:30 does not exist in Europe/Zurich
    out, bad = parse_timestamps(pd.Series(["2025-03-30 02:30:00"]), tz="Europe/Zurich")
    assert bad == 1 and out.isna().all()


@pytest.mark.parametrize(
    "mode,expected",
    [("NaT", None), ("earliest", "2025-10-26T00:30:00Z"), ("latest", "2025-10-26T01:30:00Z")],
)
def test_dst_fallback_ambiguous(mode, expected):
    # 2025-10-26 02:30 occurs twice in Europe/Zurich
    out, bad = parse_timestamps(pd.Series(["2025-10-26 02:30:00"]), tz="Europe/Zurich", ambiguous=mode)
    if expected is None:
        assert bad == 1 and out.isna().all()
    else:
        assert bad == 0 and out.iloc[0] == ts(expected)


def test_datetime_dtypes():
    naive = pd.Series(pd.to_datetime(["2025-01-01 10:00"]))
    out, _ = parse_timestamps(naive, tz="Europe/Zurich")
    assert out.iloc[0] == ts("2025-01-01T09:00:00Z")
    aware = naive.dt.tz_localize("Asia/Tokyo")
    out, _ = parse_timestamps(aware, tz="Europe/Zurich")
    assert out.iloc[0] == ts("2025-01-01T01:00:00Z")


def test_too_late_across_offsets():
    """Finalized in local time with offset, AI in UTC: comparison must use instants."""
    from too_late_rate import prepare

    df = pd.DataFrame([dict(exam_id="1", ai_solution="S",
                            report_finalized_ts="2025-01-01T10:05:00+01:00",  # 09:05Z
                            ai_result_available_ts="2025-01-01T09:30:00Z")])
    p, _ = prepare(df)
    assert bool(p["too_late"].iloc[0]) is True
