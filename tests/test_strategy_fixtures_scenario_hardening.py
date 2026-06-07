"""LQ-045 — ergänzende Strategy-/Fixture-/Scenario-Behavior-Locks.

Diese Tests schreiben ausschließlich das BESTEHENDE Verhalten fest
(Behavior-Lock): Strategie-Signale tragen ``metric is None``, und die
synthetischen Muster-Builder aus ``tests/helpers/synthetic_data.py`` sind
deterministisch und verdrahten ``half_spread`` korrekt in die ``MarketData``.

Nur synthetische/lokale Daten (Mid-Serien via ``make_mid_series_dataset`` bzw.
die Muster-Builder). Keine echten Marktdaten, keine Netzwerk-Calls, keine neuen
Artefakte. Keine Produktionslogik-Änderung, keine Änderung bestehender Tests.
"""

from helpers.synthetic_data import (
    build_sideways_with_micro_long_breakout,
    build_sideways_with_micro_short_breakout,
    build_stair_breakout_for_cooldown,
    make_mid_series_dataset,
)
from liquent.domain.models import Direction
from liquent.strategy import MidBreakoutStrategy, MidBreakoutStrategyV1


def _bars(mids):
    """Synthetische MarketData-Sequenz aus einer Mid-Serie (mid == (bid+ask)/2)."""
    return make_mid_series_dataset("lq045", mids, half_spread=0.5).market_data


# --------------------------------------------------------------------------- #
# Strategie-Signal-Contract: metric bleibt None
# --------------------------------------------------------------------------- #
def test_v0_signal_metric_is_none():
    strat = MidBreakoutStrategy(lookback_bars=2, stop_distance_pct=0.1)
    signals = strat.generate_signals(_bars([10.0, 10.0, 11.0, 10.0, 10.0]))
    assert len(signals) == 1
    assert signals[0].direction == Direction.LONG
    assert signals[0].strength == 1.0
    assert signals[0].metric is None


def test_v1_signal_metric_is_none():
    strat = MidBreakoutStrategyV1(
        lookback_bars=2, stop_distance_pct=0.1, breakout_threshold_pct=0.0, cooldown_bars=0
    )
    signals = strat.generate_signals(_bars([100.0, 100.0, 102.0, 100.0, 100.0]))
    assert len(signals) == 1
    assert signals[0].direction == Direction.LONG
    assert signals[0].metric is None


# --------------------------------------------------------------------------- #
# Synthetic-Builder: Determinismus + half_spread-Verdrahtung
# --------------------------------------------------------------------------- #
def test_pattern_builders_are_deterministic():
    for build in (
        build_sideways_with_micro_long_breakout,
        build_sideways_with_micro_short_breakout,
        build_stair_breakout_for_cooldown,
    ):
        a = build()
        b = build()
        assert a.mids == b.mids
        assert a.market_data == b.market_data


def test_builder_market_data_reflects_half_spread():
    ds = build_sideways_with_micro_long_breakout()
    assert len(ds.market_data) == len(ds.mids)
    first = ds.market_data[0]
    assert first.bid == ds.mids[0] - 0.5
    assert first.ask == ds.mids[0] + 0.5
    # mid bleibt das arithmetische Mittel von bid/ask.
    assert (first.bid + first.ask) / 2.0 == ds.mids[0]
