"""Tests für die chartfreundliche Preview-Logik (LQ-021 Phase 2).

Rein deterministisch, ohne Streamlit, ohne I/O, ohne Echtdaten. Prüft
``build_price_rows`` / ``build_signal_rows`` / ``build_chart_rows`` sowie die
additiv erweiterte ``generate_preview_summary``.
"""

from tools.visual_preview.preview_logic import (
    build_chart_rows,
    build_preview_datasets,
    build_price_rows,
    build_signal_rows,
    build_strategy,
    generate_preview_summary,
)


def _signals(dataset_key: str, **params):
    dataset = build_preview_datasets()[dataset_key]
    strat = build_strategy("v1", **params)
    return dataset, tuple(strat.generate_signals(dataset.market_data))


# 1: build_price_rows liefert je Bar timestamp/mid/bid/ask/volume.
def test_price_rows_fields():
    ds = build_preview_datasets()["micro_long"]
    rows = build_price_rows(ds)
    assert len(rows) == len(ds.market_data)
    for row in rows:
        assert set(row.keys()) == {"timestamp", "mid", "bid", "ask", "volume"}


# 2: build_price_rows berechnet mid = (bid+ask)/2.
def test_price_rows_mid_is_correct():
    ds = build_preview_datasets()["stair_cooldown"]
    rows = build_price_rows(ds)
    for row, mid in zip(rows, ds.mids):
        assert row["mid"] == (row["bid"] + row["ask"]) / 2.0 == mid


# 3: build_signal_rows liefert timestamp/side/price/stop_price/strength.
def test_signal_rows_fields():
    ds, sigs = _signals(
        "micro_long", breakout_threshold_pct=0.0, cooldown_bars=0
    )
    mid_by_ts = {b.timestamp: (b.bid + b.ask) / 2.0 for b in ds.market_data}
    rows = build_signal_rows(sigs, mid_by_ts=mid_by_ts)
    assert len(rows) == len(sigs)
    for row in rows:
        assert set(row.keys()) == {"timestamp", "side", "price", "stop_price", "strength"}
    # price entspricht dem Mid am Signal-Bar.
    assert all(r["price"] is not None for r in rows)


# 4: build_chart_rows liefert timestamp/mid/long_signal_price/short_signal_price.
def test_chart_rows_fields():
    ds, sigs = _signals("micro_long", breakout_threshold_pct=0.0, cooldown_bars=0)
    rows = build_chart_rows(ds, sigs)
    assert len(rows) == len(ds.market_data)
    for row in rows:
        assert set(row.keys()) == {
            "timestamp", "mid", "long_signal_price", "short_signal_price"
        }


# 5: Long-Signale werden korrekt markiert (long_signal_price gesetzt, short None).
def test_chart_rows_marks_long_signals():
    ds, sigs = _signals("micro_long", breakout_threshold_pct=0.0, cooldown_bars=0)
    rows = build_chart_rows(ds, sigs)
    long_marked = [r for r in rows if r["long_signal_price"] is not None]
    assert len(long_marked) == len(sigs) > 0
    for r in long_marked:
        assert r["long_signal_price"] == r["mid"]
        assert r["short_signal_price"] is None


# 6: Short-Signale werden korrekt markiert.
def test_chart_rows_marks_short_signals():
    ds, sigs = _signals("micro_short", breakout_threshold_pct=0.0, cooldown_bars=0)
    rows = build_chart_rows(ds, sigs)
    short_marked = [r for r in rows if r["short_signal_price"] is not None]
    assert len(short_marked) == len(sigs) > 0
    for r in short_marked:
        assert r["short_signal_price"] == r["mid"]
        assert r["long_signal_price"] is None


# 7: generate_preview_summary enthält price_rows/chart_rows/technical_summary.
def test_summary_contains_chart_structures():
    summary = generate_preview_summary("stair_cooldown", "v1", {})
    assert isinstance(summary["price_rows"], list) and summary["price_rows"]
    assert isinstance(summary["chart_rows"], list) and summary["chart_rows"]
    tech = summary["technical_summary"]
    assert set(tech.keys()) == {
        "dataset_name", "strategy_key", "bars", "signals_total",
        "first_timestamp", "last_timestamp",
    }
    assert tech["dataset_name"] == "stair_cooldown"
    assert tech["bars"] == 18


# 8: keine Profitabilitäts-/Bewertungsfelder in den Chart-/Preis-Strukturen.
def test_no_profitability_fields_in_chart_structures():
    summary = generate_preview_summary("stair_cooldown", "v1", {})
    blob = str(
        {k: summary[k] for k in ("price_rows", "chart_rows", "signals", "technical_summary")}
    ).lower()
    for token in ("ending_equity", "performance", "profit", "pnl", "winner", "better", "worse"):
        assert token not in blob, f"Chart-Strukturen dürfen {token!r} nicht enthalten"


# 9: max_signals_per_day bleibt sichtbar (stair: None→5, 1→1, 2→2).
def test_max_signals_per_day_still_visible():
    base = {"lookback_bars": 12, "stop_distance_pct": 0.01,
            "breakout_threshold_pct": 0.0, "cooldown_bars": 0}

    def total(msd):
        return generate_preview_summary(
            "stair_cooldown", "v1", {**base, "max_signals_per_day": msd}
        )["signals_total"]

    assert (total(None), total(1), total(2)) == (5, 1, 2)
