"""Synthetischer v0/v1-Vergleichslauf (LQ-010 Phase 1).

Vergleicht ``MidBreakoutStrategy`` (v0) und ``MidBreakoutStrategyV1`` (v1) rein
**technisch** auf vollständig **deterministischen, synthetischen** Mid-Serien —
KEINE Echtdaten, KEINE Dateien, KEIN Netzwerk, KEINE Reports, kein Zufall. Es
wird ausschließlich technisches Verhalten geprüft (Signalzahlen, Richtungen,
Threshold-/Cooldown-Wirkung, Risk-First-Gate-Zählungen). **Keine
Profitabilitätsbewertung, keine Trading-Empfehlung.**

Abgedeckte Marktphasen (über die Serien hinweg):
1. Seitwärtsphase mit Mikro-Ausbruch (Threshold-Wirkung),
2. klarer Long-Breakout,
3. Folge-Bars / Treppe (Cooldown-Wirkung),
4. klarer Short-Breakout,
5. ausreichend Historie für ``lookback_bars = 12``.

Mechanische Backtest-Felder (z. B. ``ending_equity``) werden NICHT interpretiert.
"""

from datetime import datetime, timezone

from liquent.backtesting.runner import BacktestRunner, CostModel
from liquent.domain.models import Direction, MarketData
from liquent.risk.engine import RiskEngine, RiskLimits
from liquent.strategy import MidBreakoutStrategy, MidBreakoutStrategyV1

# Gemeinsame, deterministische Parameter für einen fairen Vergleich.
_LOOKBACK = 12
_STOP_PCT = 0.01
_THRESHOLD = 0.001  # 0,1 %

# Synthetische Mid-Serien (deterministisch; 12 flache Bars Historie voran).
# Mikro-Ausbruch 100.05 = +0.05 % (< 0.1 % Threshold), echter Breakout 102 = +2 %.
_MICRO_LONG = [100.0] * 12 + [100.05, 100.0, 100.0, 102.0, 100.0]
_MICRO_SHORT = [100.0] * 12 + [99.95, 100.0, 100.0, 98.0, 100.0]
# Treppe: jeder Bar ein echter Breakout (+1 ≈ +1 %), für den Cooldown-Vergleich.
_STAIR = [100.0] * 12 + [101.0, 102.0, 103.0, 104.0, 105.0, 106.0]

_STARTING_EQUITY = 10_000.0


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


class _MidSource:
    """In-Memory-DataSource aus einer Mid-Liste (keine Datei, kein Netzwerk)."""

    def __init__(self, mids: list[float]) -> None:
        self._bars = _bars(mids)

    def market_data(self):
        return list(self._bars)

    def order_book_snapshots(self):
        return []


def _pct_risk_limits() -> RiskLimits:
    return RiskLimits(
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


def _v0() -> MidBreakoutStrategy:
    return MidBreakoutStrategy(lookback_bars=_LOOKBACK, stop_distance_pct=_STOP_PCT)


def _v1(cooldown_bars: int = 3) -> MidBreakoutStrategyV1:
    return MidBreakoutStrategyV1(
        lookback_bars=_LOOKBACK,
        stop_distance_pct=_STOP_PCT,
        breakout_threshold_pct=_THRESHOLD,
        cooldown_bars=cooldown_bars,
    )


# --------------------------------------------------------------------------- #
# Reine Signal-Ebene (Threshold- und Cooldown-Wirkung)
# --------------------------------------------------------------------------- #


# 1: v0 erzeugt beim Mikro-Ausbruch ein (zusätzliches) Long-Signal.
def test_v0_signals_on_micro_long_breakout():
    signals = _v0().generate_signals(_bars(_MICRO_LONG))
    directions = [s.direction for s in signals]
    timestamps = [s.timestamp for s in signals]
    assert len(signals) == 2
    assert directions == [Direction.LONG, Direction.LONG]
    # Das Mikro-Signal bei i=12 ist enthalten (v0 hat keinen Threshold).
    assert _ts(12) in timestamps
    assert _ts(15) in timestamps


# 2: v1 blockt den Mikro-Ausbruch (Threshold), behält aber den echten Breakout.
def test_v1_blocks_micro_long_keeps_real():
    signals = _v1().generate_signals(_bars(_MICRO_LONG))
    assert len(signals) == 1
    assert signals[0].direction == Direction.LONG
    assert signals[0].timestamp == _ts(15)  # nur der echte Breakout, nicht i=12


# 3: v1 erzeugt beim echten Long-Breakout ein Long-Signal mit stop < mid.
def test_v1_real_long_signal_has_consistent_stop():
    sig = _v1().generate_signals(_bars(_MICRO_LONG))[0]
    assert sig.direction == Direction.LONG
    assert sig.stop_price is not None and 0.0 < sig.stop_price < 102.0


# 4: v1 erzeugt beim echten Short-Breakout ein Short-Signal; Mikro-Short geblockt.
def test_v1_real_short_signal_micro_blocked():
    v0_signals = _v0().generate_signals(_bars(_MICRO_SHORT))
    v1_signals = _v1().generate_signals(_bars(_MICRO_SHORT))
    # v0: Mikro-Short (i=12) + echter Short (i=15).
    assert len(v0_signals) == 2
    assert all(s.direction == Direction.SHORT for s in v0_signals)
    # v1: nur der echte Short bei i=15.
    assert len(v1_signals) == 1
    assert v1_signals[0].direction == Direction.SHORT
    assert v1_signals[0].timestamp == _ts(15)
    assert v1_signals[0].stop_price is not None and v1_signals[0].stop_price > 98.0


# 5: v1-Cooldown reduziert Folge-Signale gegenüber cooldown_bars=0.
def test_v1_cooldown_reduces_followup_signals():
    n_cd0 = len(_v1(cooldown_bars=0).generate_signals(_bars(_STAIR)))
    n_cd3 = len(_v1(cooldown_bars=3).generate_signals(_bars(_STAIR)))
    assert n_cd0 == 5  # jeder Bar ein echter Breakout
    assert n_cd3 == 2  # Signal bei i=12, dann i=13..15 gesperrt, wieder i=16
    assert n_cd3 < n_cd0


# 5b: ohne Threshold/Cooldown verhalten sich v0 und v1 deckungsgleich (Treppe).
def test_v0_and_v1_threshold_zero_cooldown_zero_match_on_stair():
    v1_eq = MidBreakoutStrategyV1(
        lookback_bars=_LOOKBACK, stop_distance_pct=_STOP_PCT,
        breakout_threshold_pct=0.0, cooldown_bars=0,
    )
    assert _v0().generate_signals(_bars(_STAIR)) == v1_eq.generate_signals(_bars(_STAIR))


# --------------------------------------------------------------------------- #
# Runner-/Risk-Integration (Risk-First End-to-End, beide Strategien)
# --------------------------------------------------------------------------- #


def _run(strategy) -> "object":
    return BacktestRunner(
        _MidSource(_MICRO_LONG),
        RiskEngine(_pct_risk_limits()),
        CostModel(fee_rate=0.0, spread=0.0, slippage=0.0),
        strategy=strategy,
        initial_equity=_STARTING_EQUITY,
    ).run()


# 6: Beide Strategien laufen durch dieselbe Backtest-/Risk-Strecke.
def test_runner_integration_both_strategies():
    res_v0 = _run(_v0())
    res_v1 = _run(_v1())

    # v0: Mikro + echter Breakout = 2 Trades; v1: nur echter Breakout = 1 Trade.
    assert res_v0.parameters["signals_total"] == 2
    assert res_v0.approved_signals == 2
    assert res_v0.rejected_signals == 0
    assert res_v0.number_of_trades == 2
    assert res_v0.parameters["strategy"] == "MidBreakoutStrategy"

    assert res_v1.parameters["signals_total"] == 1
    assert res_v1.approved_signals == 1
    assert res_v1.rejected_signals == 0
    assert res_v1.number_of_trades == 1
    assert res_v1.parameters["strategy"] == "MidBreakoutStrategyV1"

    # Risk-First-Invariante für beide: approved + rejected == signals_total.
    for res in (res_v0, res_v1):
        assert res.approved_signals + res.rejected_signals == res.parameters["signals_total"]
        assert res.approved_signals == res.number_of_trades
        # sizing_mode bleibt percent_risk; Sicherheits-Flags konstant.
        assert res.parameters["sizing_mode"] == "percent_risk"
        assert res.parameters["live_execution"] is False
        assert res.parameters["network_calls"] is False
        assert res.parameters["paper_trading"] is False


# 7: Determinismus — gleicher synthetischer Input liefert identische Gate-Zählungen.
def test_runner_comparison_is_deterministic():
    a = _run(_v1())
    b = _run(_v1())
    assert (a.parameters["signals_total"], a.approved_signals, a.rejected_signals,
            a.number_of_trades) == (
        b.parameters["signals_total"], b.approved_signals, b.rejected_signals,
        b.number_of_trades)
