"""LQ-046 — ergänzende Data-Source-/CSV-Loader-Behavior-Locks.

Diese Tests schreiben ausschließlich das BESTEHENDE Verhalten von
``src/liquent/data/sources.py`` (``HistoricalFileSource``) fest (Behavior-Lock):
zwei bisher nicht abgedeckte Validierungs-Negativfälle (nicht-leerer, unparse-
barer Timestamp; nicht-numerisches OHLCV-Feld) sowie der Reporter-Initialzustand
und der Gap-State-Reset bei erneutem ``market_data()``.

Negativfälle werden über ``tmp_path``-CSVs erzeugt (keine neuen committeten
Fixtures); bestehende Fixtures werden nur lesend genutzt. Keine echten
Marktdaten, keine Netzwerk-Calls, keine Artefakte. Keine Produktionslogik-
Änderung, keine Änderung bestehender Tests/Fixtures.
"""

from pathlib import Path

from liquent.data.sources import HistoricalFileSource

_FIXTURES = Path(__file__).parent / "fixtures"


def _fixture(name: str) -> str:
    return str(_FIXTURES / name)


def _write_csv(tmp_path, name: str, rows: str) -> str:
    """Schreibt eine kleine OHLCV-CSV in tmp_path (kein committetes Artefakt)."""
    path = tmp_path / name
    path.write_text(rows, encoding="utf-8")
    return str(path)


def _expect_value_error(fn) -> None:
    raised = False
    try:
        fn()
    except ValueError:
        raised = True
    assert raised, "erwartete ValueError wurde nicht ausgelöst"


# --------------------------------------------------------------------------- #
# Validierung: bisher nicht abgedeckte Negativfälle (über tmp_path)
# --------------------------------------------------------------------------- #
def test_malformed_timestamp_rejected(tmp_path):
    """Nicht-leerer, aber unparsebarer ISO-Timestamp -> ValueError."""
    path = _write_csv(
        tmp_path,
        "malformed_ts.csv",
        "timestamp,open,high,low,close,volume\n"
        "not-a-date,100,101,99,100,5\n",
    )
    _expect_value_error(HistoricalFileSource(path).market_data)


def test_non_numeric_ohlcv_field_rejected(tmp_path):
    """Nicht-numerisches OHLCV-Feld (open='abc') -> ValueError."""
    path = _write_csv(
        tmp_path,
        "non_numeric.csv",
        "timestamp,open,high,low,close,volume\n"
        "2026-01-01T00:00:00,abc,101,99,100,5\n",
    )
    _expect_value_error(HistoricalFileSource(path).market_data)


# --------------------------------------------------------------------------- #
# Reporter-Initialzustand vor dem ersten market_data()
# --------------------------------------------------------------------------- #
def test_reporters_initial_state_before_market_data():
    src = HistoricalFileSource(_fixture("ohlcv_valid.csv"), timeframe="5m")
    assert src.gap_report() == ()
    assert src.history_report() is None


# --------------------------------------------------------------------------- #
# Gap-State-Reset: erneuter market_data()-Aufruf akkumuliert keine Gaps
# --------------------------------------------------------------------------- #
def test_market_data_resets_gaps_on_rerun():
    src = HistoricalFileSource(
        _fixture("ohlcv_gap_5m.csv"), timeframe="5m", gap_policy="flag"
    )
    src.market_data()
    first = src.gap_report()
    assert len(first) >= 1  # die Gap-Fixture erzeugt mindestens eine Lücke
    src.market_data()
    second = src.gap_report()
    # Kein Akkumulieren: zweiter Lauf liefert dieselbe Lückenzahl (State-Reset).
    assert len(second) == len(first)
