"""LQ-042 — ergänzende CostModel-/Metrics-Regressionstests.

Diese Tests schreiben ausschließlich das BESTEHENDE Verhalten von
``src/liquent/backtesting/metrics.py`` (reine Funktionen) und der
``CostModel``-Konvention fest (Behavior-Lock). Keine Produktionslogik-Änderung,
keine neuen Features, keine Änderung an ``tests/test_backtesting.py``.

Abgedeckt werden bisher nicht explizit gesicherte Konventionen/Grenzwerte
(siehe ``docs/lq-042-cost-metrics-hardening.md``, Test Plan): Kosten-Komponenten
isoliert, per-Einheit-Spread vs. notional-basierte fee/slippage, abs()-Symmetrie,
additive Zerlegung sowie Metrik-Grenzwerte rund um ``net_pnl == 0`` und
``exposure_time > 1.0``.
"""

import math

from liquent.backtesting.metrics import (
    TradeResult,
    best_trade,
    calculate_trade_costs,
    exposure_time,
    max_drawdown,
    profit_factor,
    win_rate,
    worst_losing_streak,
    worst_trade,
)
from liquent.backtesting.runner import CostModel


def _trade(net_pnl: float, *, bars: int = 1) -> TradeResult:
    return TradeResult(
        entry_price=100.0,
        exit_price=100.0 + net_pnl,
        quantity=1.0,
        side="long",
        gross_pnl=net_pnl,
        costs=0.0,
        net_pnl=net_pnl,
        r_multiple=0.0,
        duration_bars=bars,
    )


# --------------------------------------------------------------------------- #
# CostModel / calculate_trade_costs
# --------------------------------------------------------------------------- #
def test_fee_only_is_notional_based():
    """fee skaliert mit Notional (Preis * Menge)."""
    cm = CostModel(fee_rate=0.001)
    base = calculate_trade_costs(100.0, 2.0, cm)
    assert math.isclose(base, 0.2, rel_tol=1e-9)  # 200 * 0.001
    # doppelter Preis -> doppelte Gebühr; doppelte Menge -> doppelte Gebühr.
    assert math.isclose(calculate_trade_costs(200.0, 2.0, cm), 0.4, rel_tol=1e-9)
    assert math.isclose(calculate_trade_costs(100.0, 4.0, cm), 0.4, rel_tol=1e-9)


def test_spread_only_is_per_unit_and_price_independent():
    """spread haengt nur an der Menge, nicht am Preis."""
    cm = CostModel(spread=0.05)
    at_100 = calculate_trade_costs(100.0, 2.0, cm)
    at_999 = calculate_trade_costs(999.0, 2.0, cm)
    assert math.isclose(at_100, 0.1, rel_tol=1e-9)  # 2 * 0.05
    assert at_100 == at_999  # preisunabhaengig
    # doppelte Menge -> doppelter Spread.
    assert math.isclose(calculate_trade_costs(100.0, 4.0, cm), 0.2, rel_tol=1e-9)


def test_slippage_only_is_notional_based():
    cm = CostModel(slippage=0.0005)
    assert math.isclose(calculate_trade_costs(100.0, 2.0, cm), 0.1, rel_tol=1e-9)  # 200 * 0.0005
    assert math.isclose(calculate_trade_costs(200.0, 2.0, cm), 0.2, rel_tol=1e-9)


def test_zero_quantity_yields_zero_cost():
    cm = CostModel(fee_rate=0.001, spread=0.05, slippage=0.0005)
    assert calculate_trade_costs(100.0, 0.0, cm) == 0.0


def test_negative_quantity_symmetric_non_negative():
    cm = CostModel(fee_rate=0.001, spread=0.05, slippage=0.0005)
    pos = calculate_trade_costs(100.0, 2.0, cm)
    neg = calculate_trade_costs(100.0, -2.0, cm)
    assert pos == neg
    assert neg >= 0.0


# Hinweis: Eine negative `price`-Symmetrie wird BEWUSST NICHT getestet. Ein
# negativer Preis ist kein realistischer Marktwert; ein solcher Test koennte als
# fachliche Marktannahme missverstanden werden. Die `abs()`-Symmetrie ist bereits
# ueber `test_negative_quantity_symmetric_non_negative` als reiner Code-Contract
# abgedeckt (siehe docs/lq-042 Deferred Topics).


def test_total_cost_is_sum_of_components():
    """total == fee_only + spread_only + slippage_only fuer gleiche Eingaben."""
    price, qty = 100.0, 2.0
    full = calculate_trade_costs(price, qty, CostModel(fee_rate=0.001, spread=0.05, slippage=0.0005))
    fee = calculate_trade_costs(price, qty, CostModel(fee_rate=0.001))
    spread = calculate_trade_costs(price, qty, CostModel(spread=0.05))
    slippage = calculate_trade_costs(price, qty, CostModel(slippage=0.0005))
    assert math.isclose(full, fee + spread + slippage, rel_tol=1e-9)


# --------------------------------------------------------------------------- #
# Metrics-Grenzwerte
# --------------------------------------------------------------------------- #
def test_win_rate_zero_pnl_not_counted_as_win():
    assert math.isclose(win_rate([_trade(1.0), _trade(0.0)]), 0.5)
    assert win_rate([_trade(0.0)]) == 0.0


def test_worst_losing_streak_zero_pnl_breaks_streak():
    seq = [_trade(-1.0), _trade(0.0), _trade(-1.0), _trade(-1.0)]
    # 0.0 unterbricht -> laengste Serie ist die letzte (2), nicht 3.
    assert worst_losing_streak(seq) == 2


def test_max_drawdown_recovers_then_deeper_trough():
    # Peak 100 -> 80 (DD 20) -> neues Peak 120 -> 70 (DD 50). max = 50.
    assert math.isclose(max_drawdown([100.0, 80.0, 120.0, 70.0]), 50.0)


def test_exposure_time_can_exceed_one():
    trades = [_trade(1.0, bars=3), _trade(-1.0, bars=5)]  # Summe 8 bars
    assert math.isclose(exposure_time(trades, total_bars=4), 2.0)


def test_best_and_worst_trade_all_negative_list():
    trades = [_trade(-5.0), _trade(-2.0), _trade(-9.0)]
    assert math.isclose(best_trade(trades), -2.0)  # kleinster Verlustbetrag
    assert math.isclose(worst_trade(trades), -9.0)


def test_profit_factor_ignores_zero_pnl_trades():
    with_zero = profit_factor([_trade(4.0), _trade(-2.0), _trade(0.0)])
    without_zero = profit_factor([_trade(4.0), _trade(-2.0)])
    assert math.isclose(with_zero, 2.0)
    assert with_zero == without_zero
