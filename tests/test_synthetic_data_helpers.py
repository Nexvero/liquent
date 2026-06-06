"""Tests für die testinternen synthetischen Dataset-Builder (LQ-014 Phase 2).

Rein deterministisch, keine Echtdaten, keine Dateien, kein Netzwerk.
"""

from datetime import datetime, timezone

from liquent.domain.models import MarketData

from helpers.synthetic_data import (
    InMemoryMarketDataSource,
    SyntheticDataset,
    build_sideways_with_micro_long_breakout,
    build_sideways_with_micro_short_breakout,
    build_stair_breakout_for_cooldown,
    make_mid_series_dataset,
)


def _expect_value_error(fn) -> None:
    raised = False
    try:
        fn()
    except ValueError:
        raised = True
    assert raised, "erwartete ValueError wurde nicht ausgelöst"


# 1: deterministische UTC-Zeitstempel (start + i * interval_minutes).
def test_timestamps_are_deterministic():
    start = datetime(2026, 6, 2, 0, 0, tzinfo=timezone.utc)
    ds = make_mid_series_dataset("x", [100.0, 101.0, 102.0], start=start, interval_minutes=5)
    ts = [bar.timestamp for bar in ds.market_data]
    assert ts == [
        datetime(2026, 6, 2, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 6, 2, 0, 5, tzinfo=timezone.utc),
        datetime(2026, 6, 2, 0, 10, tzinfo=timezone.utc),
    ]
    # Default-Start ist deterministisch (2026-01-01 UTC).
    assert make_mid_series_dataset("x", [100.0]).market_data[0].timestamp == datetime(
        2026, 1, 1, tzinfo=timezone.utc
    )


# 2: half_spread=0 -> bid == ask == mid.
def test_half_spread_zero_bid_equals_ask_equals_mid():
    ds = make_mid_series_dataset("x", [100.0, 105.0], half_spread=0.0)
    for bar, mid in zip(ds.market_data, ds.mids):
        assert bar.bid == bar.ask == mid
        assert (bar.bid + bar.ask) / 2.0 == mid


# 3: half_spread > 0 setzt bid/ask korrekt, mid bleibt das Mittel.
def test_half_spread_sets_bid_ask():
    ds = make_mid_series_dataset("x", [100.0], half_spread=0.5)
    bar = ds.market_data[0]
    assert bar.bid == 99.5
    assert bar.ask == 100.5
    assert (bar.bid + bar.ask) / 2.0 == 100.0


# 4: Anzahl MarketData == Anzahl mids.
def test_length_matches_mids():
    ds = make_mid_series_dataset("x", [1.0, 2.0, 3.0, 4.0])
    assert len(ds.market_data) == 4 == len(ds.mids)
    assert all(isinstance(bar, MarketData) for bar in ds.market_data)
    assert isinstance(ds, SyntheticDataset)


# 5: leere mids -> ValueError.
def test_empty_mids_rejected():
    _expect_value_error(lambda: make_mid_series_dataset("x", []))


# 6: interval_minutes <= 0 -> ValueError.
def test_invalid_interval_rejected():
    _expect_value_error(lambda: make_mid_series_dataset("x", [100.0], interval_minutes=0))
    _expect_value_error(lambda: make_mid_series_dataset("x", [100.0], interval_minutes=-5))


# 7: half_spread < 0 -> ValueError.
def test_negative_half_spread_rejected():
    _expect_value_error(lambda: make_mid_series_dataset("x", [100.0], half_spread=-0.1))


# 8: bid <= 0 -> ValueError.
def test_nonpositive_bid_rejected():
    # mid=0.5, half_spread=0.5 -> bid=0.0 -> abgelehnt.
    _expect_value_error(lambda: make_mid_series_dataset("x", [0.5], half_spread=0.5))


# 9: InMemoryMarketDataSource.market_data() gibt stabile Daten zurück.
def test_in_memory_source_market_data_stable():
    ds = make_mid_series_dataset("x", [100.0, 101.0], half_spread=0.5)
    src = InMemoryMarketDataSource(ds.market_data)
    first = src.market_data()
    second = src.market_data()
    assert tuple(first) == tuple(second) == ds.market_data
    # Mutation der Rückgabe beeinflusst die Quelle nicht (eigene Kopie/Tuple).
    assert isinstance(first, tuple)


# 10: order_book_snapshots() gibt leeres tuple.
def test_in_memory_source_order_book_empty():
    src = InMemoryMarketDataSource(())
    assert src.order_book_snapshots() == ()


# 10b: ohne metadata/history_report bleibt der Runner-defensive Pfad neutral.
def test_in_memory_source_has_no_metadata_attr_by_default():
    src = InMemoryMarketDataSource(())
    assert getattr(src, "metadata", None) is None
    assert getattr(src, "history_report", None) is None


# 11: Builder long-breakout hat erwartete Länge/Muster.
def test_micro_long_builder_shape():
    ds = build_sideways_with_micro_long_breakout()
    assert len(ds.mids) == 17  # 12 flach + 5
    assert ds.mids[12] == 100.05  # Mikro-Ausbruch
    assert ds.mids[15] == 102.0   # echter Breakout
    assert ds.mids[:12] == (100.0,) * 12
    # short-Builder spiegelbildlich.
    short = build_sideways_with_micro_short_breakout()
    assert short.mids[12] == 99.95
    assert short.mids[15] == 98.0


# 12: Builder stair hat aufeinanderfolgende Breakouts (streng steigender Schwanz).
def test_stair_builder_has_consecutive_breakouts():
    ds = build_stair_breakout_for_cooldown()
    assert len(ds.mids) == 18  # 12 flach + 6
    tail = ds.mids[12:]
    assert tail == (101.0, 102.0, 103.0, 104.0, 105.0, 106.0)
    assert all(b > a for a, b in zip(tail, tail[1:]))


# 13: Statischer Scan -> Helper-Modul ohne Netzwerk-/Live-/Paper-/Download-/API-Pfade.
def test_helper_module_has_no_forbidden_paths():
    import inspect

    from helpers import synthetic_data as module

    source_code = inspect.getsource(module).lower()
    forbidden = [
        "li" + "ve",
        "pa" + "per",
        "exch" + "ange",
        "down" + "load",
        "soc" + "ket",
        "req" + "uests",
        "ht" + "tp://",
        "ht" + "tps://",
        "api_" + "key",
    ]
    for token in forbidden:
        assert token not in source_code, f"Helper-Modul darf {token!r} nicht enthalten"
