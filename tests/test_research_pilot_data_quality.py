"""Pilot rejects unsafe CSVs without changing source/engine semantics."""

import hashlib
import json
from pathlib import Path

import pytest

from liquent.data.sources import HistoricalFileSource
from liquent.research_pilot import data_quality
from liquent.research_pilot.data_quality import inspect_dataset


HEADER = "timestamp,open,high,low,close,volume\n"
FIRST = "2026-01-01T00:00:00+00:00,10,12,9,11,0\n"
SECOND = "2026-01-01T00:05:00Z,11,13,10,12,4\n"
VALID = HEADER + FIRST + SECOND


def dataset(tmp_path: Path, content: str | bytes) -> Path:
    path = tmp_path / "customer.csv"
    path.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    return path


def test_valid_report_and_short_history(tmp_path):
    result = inspect_dataset(dataset(tmp_path, VALID), "5m")
    assert result.valid
    assert isinstance(result.bars, tuple)
    assert [bar.bid for bar in result.bars] == [11, 12]
    assert all(bar.bid == bar.ask for bar in result.bars)
    assert result.report == {
        "status": "valid",
        "dataset_fingerprint": "sha256:" + hashlib.sha256(VALID.encode()).hexdigest(),
        "rows": 2,
        "period_start": "2026-01-01T00:00:00+00:00",
        "period_end": "2026-01-01T00:05:00+00:00",
        "timeframe": "5m",
        "interval_seconds": 300,
        "issues": [],
        "gaps": [],
        "history": {
            "timeframe": "5m", "actual_bars": 2, "required_bars": 8640,
            "required_days": 30, "meets_minimum": False, "policy": "flag",
        },
        "warnings": [
            "Historie unterschreitet die empfohlene Mindestlänge; "
            "kurze synthetische Testdaten bleiben zulässig, ihre Aussagekraft ist begrenzt."
        ],
    }
    json.dumps(result.report, allow_nan=False)


def test_snapshot_is_exact_and_original_is_never_reread(tmp_path, monkeypatch):
    raw = VALID.replace("\n", "\r\n").encode()
    original = dataset(tmp_path, raw)
    snapshots = []
    real_source = data_quality.HistoricalFileSource

    def source(path, **kwargs):
        assert kwargs == {"timeframe": "5m", "gap_policy": "flag", "history_policy": "flag"}
        snapshots.append(Path(path))
        assert Path(path).read_bytes() == raw
        original.write_bytes(b"changed while validating")
        return real_source(path, **kwargs)

    monkeypatch.setattr(data_quality, "HistoricalFileSource", source)
    result = inspect_dataset(original, "5m")
    assert result.valid
    assert len(result.bars) == 2
    assert result.report["dataset_fingerprint"] == "sha256:" + hashlib.sha256(raw).hexdigest()
    assert all(not path.exists() for path in snapshots)
    original.unlink()
    assert result.bars[-1].bid == 12


@pytest.mark.parametrize("numbers,reason", [
    ("-1,12,9,11,1", "negativen Preis"),
    ("10,12,9,11,-1", "negatives Volumen"),
    ("10,8,9,11,1", "high liegt unter low"),
    ("13,12,9,11,1", "open liegt außerhalb"),
    ("10,12,9,13,1", "close liegt außerhalb"),
    ("SECRET_CUSTOMER,12,9,11,1", "nicht numerischen"),
    ("10,12,9,,1", "nicht numerischen"),
])
def test_existing_ohlcv_validation_is_reused(tmp_path, numbers, reason):
    path = dataset(tmp_path, HEADER + "2026-01-01T00:00:00Z," + numbers + "\n")
    with pytest.raises(ValueError):
        HistoricalFileSource(str(path)).market_data()
    result = inspect_dataset(path, "5m")
    assert not result.valid
    assert result.bars == ()
    assert reason in result.report["issues"][0]
    rendered = json.dumps(result.report, ensure_ascii=False)
    assert "SECRET_CUSTOMER" not in rendered
    assert str(tmp_path) not in rendered
    assert "weitere Fehler sind möglich" in rendered


@pytest.mark.parametrize("column", range(1, 6))
@pytest.mark.parametrize("value", ["nan", "NaN", "inf", "-inf", "1e999"])
def test_nonfinite_values_in_every_numeric_column(tmp_path, column, value):
    cells = FIRST.strip().split(",")
    cells[column] = value
    result = inspect_dataset(dataset(tmp_path, HEADER + ",".join(cells) + "\n"), "5m")
    assert not result.valid
    assert result.bars == ()
    assert "endliche Zahl" in result.report["issues"][0]
    json.dumps(result.report, allow_nan=False)


@pytest.mark.parametrize("column", range(1, 5))
@pytest.mark.parametrize("zero", ["0", "-0.0"])
def test_zero_prices_are_rejected(tmp_path, column, zero):
    cells = FIRST.strip().split(",")
    cells[column] = zero
    result = inspect_dataset(dataset(tmp_path, HEADER + ",".join(cells) + "\n"), "5m")
    assert not result.valid
    assert result.bars == ()
    assert "strikt positiv" in result.report["issues"][0]


@pytest.mark.parametrize("timestamp", [
    "", "SECRET_CUSTOMER", "2026-01-01", "2026-01-01T00:00:00",
    "2026-01-01T00:00:00+01:00", "2026-01-01T00:00:00-05:00",
])
def test_missing_invalid_or_non_utc_timestamp(tmp_path, timestamp):
    raw = HEADER + timestamp + ",10,12,9,11,1\n"
    result = inspect_dataset(dataset(tmp_path, raw), "5m")
    assert not result.valid
    assert result.bars == ()
    assert "Zeitstempel" in result.report["issues"][0]
    assert "SECRET_CUSTOMER" not in json.dumps(result.report)


@pytest.mark.parametrize("header", [
    "timestamp,open,high,low,close,close",
    "timestamp,open,high,low,close,volume,SECRET_CUSTOMER",
    "timestamp,open,high,low,close",
    "timestamp,open,high,low,close, Volume",
    "Timestamp,open,high,low,close,volume",
    "timestamp,open,high,low,close,volume,volume",
])
def test_missing_extra_duplicate_or_ambiguous_headers(tmp_path, header):
    result = inspect_dataset(dataset(tmp_path, header + "\n" + FIRST), "5m")
    assert not result.valid
    assert result.bars == ()
    assert "Kopfzeile" in result.report["issues"][0]
    assert "SECRET_CUSTOMER" not in json.dumps(result.report)


def test_exact_reordered_header_is_allowed(tmp_path):
    result = inspect_dataset(dataset(tmp_path,
        "volume,close,low,high,open,timestamp\n0,11,9,12,10,2026-01-01T00:00:00Z\n"
    ), "5m")
    assert result.valid
    assert result.bars[0].bid == 11


@pytest.mark.parametrize("raw", [
    "", HEADER, "\n", HEADER + "\n", HEADER + FIRST.rstrip() + ",SECRET_CUSTOMER\n",
    HEADER + "2026-01-01T00:00:00Z,10,12,9,11\n",
    HEADER + '"unterminated\n', HEADER + '"2026-01-01T00:00:00Z"oops,10,12,9,11,1\n',
    b"\xff\xfe", HEADER + FIRST + "\n" + SECOND,
])
def test_empty_and_malformed_csv(tmp_path, raw):
    result = inspect_dataset(dataset(tmp_path, raw), "5m")
    assert not result.valid
    assert result.bars == ()
    assert result.report["issues"]
    assert "SECRET_CUSTOMER" not in json.dumps(result.report)


@pytest.mark.parametrize("second,reason", [
    (FIRST, "doppelten Zeitstempel"),
    (FIRST.replace("2026-01-01", "2025-12-31"), "sortiert"),
])
def test_duplicate_or_unsorted_timestamps(tmp_path, second, reason):
    result = inspect_dataset(dataset(tmp_path, HEADER + FIRST + second), "5m")
    assert not result.valid
    assert result.bars == ()
    assert reason in result.report["issues"][0]


@pytest.mark.parametrize("time,actual,missing", [
    ("00:10:00", 600, 1), ("00:07:00", 420, 0), ("00:04:00", 240, 0),
    ("00:05:00.500000", 300, 0),
])
def test_gaps_and_irregular_spacing_keep_source_gap_details(tmp_path, time, actual, missing):
    path = dataset(tmp_path, HEADER + FIRST + SECOND.replace("00:05:00", time))
    result = inspect_dataset(path, "5m")
    assert not result.valid
    assert result.bars == ()
    assert result.report["gaps"] == [{
        "previous_timestamp": "2026-01-01T00:00:00+00:00",
        "current_timestamp": f"2026-01-01T{time}+00:00",
        "expected_delta_seconds": 300, "actual_delta_seconds": actual, "missing_bars": missing,
    }]
    assert result.report["history"]["actual_bars"] == 2
    assert "unregelmäßige" in result.report["issues"][0]


@pytest.mark.parametrize("raw", [VALID, HEADER + FIRST + FIRST, HEADER + "bad\n"])
def test_reports_are_deterministic_and_path_independent(tmp_path, raw):
    first = inspect_dataset(dataset(tmp_path, raw), "5m")
    second_path = tmp_path / "other.csv"
    second_path.write_text(raw, encoding="utf-8")
    second = inspect_dataset(second_path, "5m")
    assert first == second
    assert json.dumps(first.report, sort_keys=True, allow_nan=False) == json.dumps(
        second.report, sort_keys=True, allow_nan=False
    )


@pytest.mark.parametrize("timeframe,seconds", [("1m", 60), ("5m", 300), ("15m", 900), ("1h", 3600)])
def test_supported_timeframes(tmp_path, timeframe, seconds):
    result = inspect_dataset(dataset(tmp_path, HEADER + FIRST), timeframe)
    assert result.valid
    assert result.report["interval_seconds"] == seconds


def test_unknown_timeframe_and_missing_file_are_safe(tmp_path):
    result = inspect_dataset(dataset(tmp_path, VALID), "SECRET_CUSTOMER")
    assert not result.valid
    assert result.bars == ()
    assert "SECRET_CUSTOMER" not in result.report["issues"][0]
    missing = inspect_dataset(tmp_path / "SECRET_CUSTOMER.csv", "5m")
    assert not missing.valid
    assert missing.report["dataset_fingerprint"] is None
    assert "SECRET_CUSTOMER" not in json.dumps(missing.report)
    assert str(tmp_path) not in json.dumps(missing.report)


def test_snapshot_cleanup_on_loader_failure(tmp_path, monkeypatch):
    snapshots = []
    real_source = data_quality.HistoricalFileSource

    def source(path, **kwargs):
        snapshots.append(Path(path))
        return real_source(path, **kwargs)

    monkeypatch.setattr(data_quality, "HistoricalFileSource", source)
    result = inspect_dataset(dataset(tmp_path, HEADER + FIRST + FIRST), "5m")
    assert not result.valid
    assert len(snapshots) == 1
    assert not snapshots[0].exists()
    assert str(snapshots[0]) not in json.dumps(result.report)
