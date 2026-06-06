"""Tests für die lokale Visual-Preview-Logik (LQ-019 Phase 2).

Rein deterministisch, keine Echtdaten, keine Datei, kein Netzwerk, KEIN
Streamlit nötig. ``app.py`` muss ohne Streamlit importierbar bleiben.
"""

from datetime import timezone

from tools.visual_preview.preview_logic import (
    PreviewDataset,
    build_preview_datasets,
    build_strategy,
    generate_preview_summary,
)
from liquent.strategy import MidBreakoutStrategy, MidBreakoutStrategyV1


def _expect_value_error(fn) -> None:
    raised = False
    try:
        fn()
    except ValueError:
        raised = True
    assert raised, "erwartete ValueError wurde nicht ausgelöst"


# 1: build_preview_datasets enthält drei stabile Datasets.
def test_datasets_mapping():
    ds = build_preview_datasets()
    assert set(ds.keys()) == {"micro_long", "micro_short", "stair_cooldown"}
    assert all(isinstance(v, PreviewDataset) for v in ds.values())


# 2: MarketData ist deterministisch (UTC-aware, bid/ask, nicht leer).
def test_market_data_is_deterministic():
    ds = build_preview_datasets()["stair_cooldown"]
    assert len(ds.market_data) == 18 == len(ds.mids)
    for bar in ds.market_data:
        assert bar.timestamp.tzinfo == timezone.utc
        assert bar.ask > bar.bid
    # mid = (bid+ask)/2 entspricht der Mid-Serie.
    assert (ds.market_data[12].bid + ds.market_data[12].ask) / 2.0 == ds.mids[12]


# 3: build_strategy("v0") -> MidBreakoutStrategy.
def test_build_strategy_v0():
    strat = build_strategy("v0")
    assert isinstance(strat, MidBreakoutStrategy)
    assert strat.lookback_bars == 3
    assert strat.stop_distance_pct == 0.05


# 4: build_strategy("v1") -> MidBreakoutStrategyV1.
def test_build_strategy_v1():
    strat = build_strategy("v1")
    assert isinstance(strat, MidBreakoutStrategyV1)
    assert strat.lookback_bars == 12
    assert strat.stop_distance_pct == 0.01
    assert strat.breakout_threshold_pct == 0.001
    assert strat.cooldown_bars == 3


# 5: v1-Parameter werden übernommen.
def test_v1_params_applied():
    strat = build_strategy(
        "v1", breakout_threshold_pct=0.0, cooldown_bars=0, max_signals_per_day=2
    )
    assert strat.breakout_threshold_pct == 0.0
    assert strat.cooldown_bars == 0
    assert strat.max_signals_per_day == 2


# 6: v1-only Parameter bei v0 werden abgelehnt; ungültiger key ebenfalls.
def test_v0_rejects_v1_only_params():
    _expect_value_error(lambda: build_strategy("v0", breakout_threshold_pct=0.001))
    _expect_value_error(lambda: build_strategy("v0", cooldown_bars=3))
    _expect_value_error(lambda: build_strategy("v0", max_signals_per_day=2))
    _expect_value_error(lambda: build_strategy("v2"))


# 7: generate_preview_summary liefert die erwarteten Felder.
def test_summary_structure():
    summary = generate_preview_summary("micro_long", "v1", {})
    assert set(summary.keys()) == {
        "dataset", "strategy", "signals_total", "signals", "safety_notes",
    }
    assert summary["dataset"]["type"] == "synthetic"
    assert summary["strategy"]["key"] == "v1"
    assert isinstance(summary["signals_total"], int)
    for note in (
        "Synthetic/local preview only.", "No live trading.",
        "No trading recommendation.", "No profitability assessment.",
    ):
        assert note in summary["safety_notes"]
    # Signalzeilen tragen die erwarteten Spalten (falls vorhanden).
    for row in summary["signals"]:
        assert set(row.keys()) == {"timestamp", "side", "price", "stop_price", "strength"}


# 8: keine Profitabilitäts-/Bewertungsfelder in den Daten (Notes ausgenommen).
def test_summary_has_no_profitability_fields():
    summary = generate_preview_summary("stair_cooldown", "v1", {})
    data = {k: v for k, v in summary.items() if k != "safety_notes"}
    blob = str(data).lower()
    for token in ("ending_equity", "performance", "profit", "winner", "better", "worse"):
        assert token not in blob, f"Summary-Daten dürfen {token!r} nicht enthalten"


# 9: max_signals_per_day wirkt sichtbar auf die Signalzahl (stair-Dataset).
def test_max_signals_per_day_changes_count():
    base = {"lookback_bars": 12, "stop_distance_pct": 0.01,
            "breakout_threshold_pct": 0.0, "cooldown_bars": 0}

    def total(msd):
        return generate_preview_summary(
            "stair_cooldown", "v1", {**base, "max_signals_per_day": msd}
        )["signals_total"]

    n_none, n_one, n_two = total(None), total(1), total(2)
    assert n_none > n_one
    assert n_one == 1
    assert n_two >= n_one
    assert n_two == 2


# 10: app.py ist importierbar OHNE Streamlit.
def test_app_importable_without_streamlit():
    import importlib

    module = importlib.import_module("tools.visual_preview.app")
    assert hasattr(module, "main")


# 11: Statischer Scan -> keine Netzwerk-/Download-/API-/Exchange-/Order-Pfade.
#     (Disclaimer-Wörter wie "live"/"profitability" sind bewusst NICHT in der
#      Liste; geprüft werden konkrete Code-/Pfad-Token.)
def test_tools_have_no_forbidden_paths():
    import inspect

    from tools.visual_preview import app as app_module
    from tools.visual_preview import preview_logic as logic_module

    source = (inspect.getsource(app_module) + inspect.getsource(logic_module)).lower()
    forbidden = [
        "soc" + "ket",
        "url" + "lib",
        "req" + "uests",
        "ht" + "tp://",
        "ht" + "tps://",
        "cc" + "xt",
        "api_" + "key",
        "live_" + "order",
        "place_" + "order",
        "paper_" + "trading",
        "down" + "load(",
    ]
    for token in forbidden:
        assert token not in source, f"Visual-Preview darf {token!r} nicht enthalten"
