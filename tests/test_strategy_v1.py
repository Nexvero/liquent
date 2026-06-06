"""Tests für MidBreakoutStrategyV1 (LQ-008 Phase 2).

Spec: LQ-008 Phase 1 (MidBreakoutStrategy v1).

Reine Strategie-Tests plus eine Runner-Integration im ``percent_risk``-Modus
(Risk-First End-to-End). Nur Standardbibliothek + bestehende Projektklassen.
KEINE CSV-Daten, kein Netzwerk, keine Exchange, keine Bewertung, keine
Optimierung. v0 (``MidBreakoutStrategy``) bleibt unverändert und dient als
Regressionsanker für ``breakout_threshold_pct == 0`` und ``cooldown_bars == 0``.
"""

import math
from datetime import datetime, timezone

from liquent.backtesting.runner import BacktestRunner, CostModel
from liquent.domain.models import Direction, MarketData, Signal
from liquent.risk.engine import RiskEngine, RiskLimits
from liquent.strategy import MidBreakoutStrategy, MidBreakoutStrategyV1


def _bars(mids: list[float]) -> list[MarketData]:
    """Baut Bars aus einer Mid-Liste (bid/ask symmetrisch -> _mid == m)."""
    return [
        MarketData(
            timestamp=datetime(2026, 6, 2, 0, i, tzinfo=timezone.utc),
            bid=m - 0.5,
            ask=m + 0.5,
            volume=1.0,
        )
        for i, m in enumerate(mids)
    ]


def _ts(i: int) -> datetime:
    return datetime(2026, 6, 2, 0, i, tzinfo=timezone.utc)


def _expect_value_error(fn) -> None:
    raised = False
    try:
        fn()
    except ValueError:
        raised = True
    assert raised, "erwartete ValueError wurde nicht ausgelöst"


# 1: Threshold verhindert Mikro-Breakout (über prev_high, aber < Schwelle).
def test_threshold_blocks_micro_breakout():
    # cur=100.5 ist > prev_high(100) [v0 würde auslösen], aber < 100*(1+0.01)=101.
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.01, cooldown_bars=0
    )
    assert strat.generate_signals(_bars([100.0, 100.0, 100.5, 100.0, 100.0])) == ()


# 2: Threshold erlaubt echten Long-Breakout (über der Schwelle).
def test_threshold_allows_real_long_breakout():
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.01, cooldown_bars=0
    )
    # i=2: window [100,100], prev_high 100, cur 102 > 101 -> LONG.
    signals = strat.generate_signals(_bars([100.0, 100.0, 102.0, 100.0, 100.0]))
    assert len(signals) == 1
    assert signals[0].direction == Direction.LONG
    assert signals[0].timestamp == _ts(2)


# 3: Threshold erlaubt echten Short-Breakout (unter der Schwelle).
def test_threshold_allows_real_short_breakout():
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.01,
        cooldown_bars=0, allow_short=True,
    )
    # i=2: window [100,100], prev_low 100, cur 98 < 100*0.99=99 -> SHORT.
    signals = strat.generate_signals(_bars([100.0, 100.0, 98.0, 100.0, 100.0]))
    assert len(signals) == 1
    assert signals[0].direction == Direction.SHORT
    assert signals[0].timestamp == _ts(2)


# 3b: allow_short=False unterdrückt den Short-Breakout.
def test_short_suppressed_when_disallowed():
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.01,
        cooldown_bars=0, allow_short=False,
    )
    assert strat.generate_signals(_bars([100.0, 100.0, 98.0, 100.0, 100.0])) == ()


# 4: Long-Signal hat stop_price < mid (und > 0).
def test_long_stop_below_mid():
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.01, cooldown_bars=0
    )
    sig = strat.generate_signals(_bars([100.0, 100.0, 102.0, 100.0, 100.0]))[0]
    assert sig.stop_price is not None
    assert 0.0 < sig.stop_price < 102.0
    assert math.isclose(sig.stop_price, 102.0 * (1 - 0.1), rel_tol=1e-9)


# 5: Short-Signal hat stop_price > mid.
def test_short_stop_above_mid():
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.01,
        cooldown_bars=0, allow_short=True,
    )
    sig = strat.generate_signals(_bars([100.0, 100.0, 98.0, 100.0, 100.0]))[0]
    assert sig.stop_price is not None
    assert sig.stop_price > 98.0
    assert math.isclose(sig.stop_price, 98.0 * (1 + 0.1), rel_tol=1e-9)


# 6: cooldown_bars > 0 unterdrückt Folge-Signale.
def test_cooldown_suppresses_followups():
    # Streng steigende Mids -> jeder Bar wäre ein Breakout (threshold 0).
    mids = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.0, cooldown_bars=3
    )
    signals = strat.generate_signals(_bars(mids))
    # Signal bei i=2, danach i=3,4,5 (< 2+3+1=6) gesperrt -> genau 1 Signal.
    assert len(signals) == 1
    assert signals[0].timestamp == _ts(2)


# 7: cooldown_bars = 0 erlaubt unmittelbares Folge-Signal.
def test_cooldown_zero_allows_immediate_followup():
    mids = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.0, cooldown_bars=0
    )
    signals = strat.generate_signals(_bars(mids))
    # i in 2..5 -> 4 aufeinanderfolgende Long-Signale.
    assert len(signals) == 4
    assert [s.timestamp for s in signals] == [_ts(2), _ts(3), _ts(4), _ts(5)]


# 8: breakout_threshold_pct=0.0 reproduziert v0 (gleicher lookback/stop, cooldown=0).
def test_threshold_zero_reproduces_v0():
    mids = [10.0, 10.0, 11.0, 9.0, 12.0, 8.0, 13.0]
    v0 = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1)
    v1 = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.0, cooldown_bars=0
    )
    sig_v0 = v0.generate_signals(_bars(mids))
    sig_v1 = v1.generate_signals(_bars(mids))
    assert sig_v1 == sig_v0
    assert len(sig_v1) > 0  # Regressionsanker prüft tatsächlich Signale.


# 9: Kein Signal auf dem letzten Bar (kein Folge-Bar).
def test_no_signal_on_last_bar():
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.0, cooldown_bars=0
    )
    # Einziger potenzieller Breakout läge auf dem letzten Bar (i=3) -> verworfen.
    assert strat.generate_signals(_bars([10.0, 10.0, 10.0, 16.0])) == ()


# 10: Determinismus -> gleicher Input liefert identische Signale.
def test_deterministic_same_input_same_signals():
    mids = [10.0, 10.0, 11.0, 9.0, 12.0, 8.0, 13.0]

    def make() -> MidBreakoutStrategyV1:
        return MidBreakoutStrategyV1(
            lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.001,
            cooldown_bars=1,
        )

    res_a = make().generate_signals(_bars(mids))
    res_b = make().generate_signals(_bars(mids))
    assert res_a == res_b
    # Auch wiederholter Aufruf derselben Instanz ist deckungsgleich.
    strat = make()
    assert strat.generate_signals(_bars(mids)) == strat.generate_signals(_bars(mids))


# 11: Konstruktor-Validierung.
def test_constructor_validation():
    # invalid lookback
    _expect_value_error(lambda: MidBreakoutStrategyV1(lookback_bars=0))
    _expect_value_error(lambda: MidBreakoutStrategyV1(lookback_bars=-1))
    # invalid stop_distance_pct
    _expect_value_error(lambda: MidBreakoutStrategyV1(stop_distance_pct=0.0))
    _expect_value_error(lambda: MidBreakoutStrategyV1(stop_distance_pct=-0.1))
    _expect_value_error(lambda: MidBreakoutStrategyV1(stop_distance_pct=1.0))
    _expect_value_error(lambda: MidBreakoutStrategyV1(stop_distance_pct=1.5))
    # invalid breakout_threshold_pct ([0, 0.1))
    _expect_value_error(lambda: MidBreakoutStrategyV1(breakout_threshold_pct=-0.1))
    _expect_value_error(lambda: MidBreakoutStrategyV1(breakout_threshold_pct=0.1))
    _expect_value_error(lambda: MidBreakoutStrategyV1(breakout_threshold_pct=0.5))
    # invalid cooldown_bars (>= 0)
    _expect_value_error(lambda: MidBreakoutStrategyV1(cooldown_bars=-1))
    # invalid min_strength ([0, 1])
    _expect_value_error(lambda: MidBreakoutStrategyV1(min_strength=-0.1))
    _expect_value_error(lambda: MidBreakoutStrategyV1(min_strength=1.1))
    # invalid max_signals_per_day (None oder > 0)
    _expect_value_error(lambda: MidBreakoutStrategyV1(max_signals_per_day=0))
    _expect_value_error(lambda: MidBreakoutStrategyV1(max_signals_per_day=-5))


# 11b: gültige Grenzwerte werden akzeptiert (kein Fehler).
def test_constructor_accepts_valid_bounds():
    MidBreakoutStrategyV1(
        lookback_bars=1, stop_distance_pct=0.999, breakout_threshold_pct=0.0,
        cooldown_bars=0, min_strength=0.0, max_signals_per_day=None,
    )
    MidBreakoutStrategyV1(
        breakout_threshold_pct=0.0999, min_strength=1.0, max_signals_per_day=1
    )


# 11c: max_signals_per_day wird in Phase 2 NICHT erzwungen.
def test_max_signals_per_day_not_enforced_in_phase2():
    mids = [10.0, 11.0, 12.0, 13.0, 14.0, 15.0, 16.0]
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.0,
        cooldown_bars=0, max_signals_per_day=1,
    )
    # Trotz max_signals_per_day=1 entstehen mehrere Signale am selben Tag.
    assert len(strat.generate_signals(_bars(mids))) == 4


# --------------------------------------------------------------------------- #
# Runner-Integration mit percent_risk (Risk-First End-to-End, in-memory)
# --------------------------------------------------------------------------- #


class _MidSource:
    """In-Memory-DataSource aus einer Mid-Liste (bid/ask symmetrisch)."""

    def __init__(self, mids: list[float]) -> None:
        self._bars = _bars(mids)

    def market_data(self):
        return list(self._bars)

    def order_book_snapshots(self):
        return []


def _pct_risk_limits(**overrides) -> RiskLimits:
    base = dict(
        max_position_size=100.0,
        max_total_exposure=100_000.0,
        risk_per_trade=1.0,
        max_daily_drawdown=10_000.0,
        sizing_mode="percent_risk",
        risk_per_trade_pct=0.01,
        max_position_notional=100_000.0,
        max_daily_loss=0.0,
        max_losing_streak=0,
    )
    base.update(overrides)
    return RiskLimits(**base)


_LONG_MIDS = [100.0, 101.0, 102.0, 106.0, 108.0]
_STARTING_EQUITY = 10_000.0


# 12: Runner-Integration mit percent_risk bleibt grün (ein Long-Trade).
def test_integration_percent_risk_long_trade():
    res = BacktestRunner(
        _MidSource(_LONG_MIDS),
        RiskEngine(_pct_risk_limits()),
        CostModel(fee_rate=0.0, spread=0.0, slippage=0.0),
        strategy=MidBreakoutStrategyV1(
            lookback_bars=3, stop_distance_pct=0.05, breakout_threshold_pct=0.001,
            cooldown_bars=3,
        ),
        initial_equity=_STARTING_EQUITY,
    ).run()
    assert res.number_of_trades == 1
    assert res.trades[0].side == "long"
    # Risk-First-Konsistenz.
    assert res.approved_signals == res.number_of_trades == 1
    assert res.rejected_signals == 0
    assert res.parameters["signals_total"] == 1
    assert res.parameters["strategy"] == "MidBreakoutStrategyV1"
    assert res.parameters["sizing_mode"] == "percent_risk"


# 13: Statischer Scan -> keine Netzwerk-/Live-/Paper-Trading-Pfade.
def test_module_has_no_network_live_or_paper_paths():
    import inspect

    from liquent.strategy import mid_breakout_v1 as module

    source_code = inspect.getsource(module)
    forbidden = (
        "socket", "urllib", "requests", "http://", "https://",
        "websocket", "ccxt", "live_order", "place_order",
        "paper_trading", "api_key", "secret",
    )
    for token in forbidden:
        assert token not in source_code, f"Modul darf {token!r} nicht referenzieren"
