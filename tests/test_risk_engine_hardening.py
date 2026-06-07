"""LQ-041 — ergänzende RiskEngine-Regressionstests.

Diese Tests schreiben ausschließlich das BESTEHENDE Verhalten von
``src/liquent/risk/engine.py`` fest (Behavior-Lock). Keine Produktionslogik-
Änderung, keine neuen Features, keine Änderung an ``tests/test_risk.py``.

Abgedeckt werden bisher nicht explizit gesicherte Verhaltensgrenzen
(siehe ``docs/lq-041-risk-engine-hardening.md``, Test Plan):
absolute-Sizing-Bindung, Exposure-Deckelung, Grenzwert-Semantik, FLAT-Reject,
percent_risk Wert-Rejects + Config-Rejects, Mehrfach-Caps und die Invariante
"genau eine RiskDecision".
"""

from datetime import datetime, timezone

from liquent.domain.models import Direction, Signal
from liquent.risk.engine import AccountState, RiskEngine, RiskLimits


# --------------------------------------------------------------------------- #
# Helfer (bewusst lokal — keine Kopplung an tests/test_risk.py)
# --------------------------------------------------------------------------- #
_TS = datetime(2026, 6, 2, tzinfo=timezone.utc)


def _signal(strength: float = 0.8, direction: Direction = Direction.LONG) -> Signal:
    return Signal(timestamp=_TS, direction=direction, strength=strength)


def _abs_limits(**overrides) -> RiskLimits:
    base = dict(
        max_position_size=10.0,
        max_total_exposure=100.0,
        risk_per_trade=5.0,
        max_daily_drawdown=20.0,
    )
    base.update(overrides)
    return RiskLimits(**base)


def _pct_limits(**overrides) -> RiskLimits:
    base = dict(
        max_position_size=1000.0,
        max_total_exposure=1_000_000.0,
        risk_per_trade=0.0,
        max_daily_drawdown=1000.0,
        risk_per_trade_pct=0.01,
        max_position_notional=0.0,
        max_daily_loss=0.0,
        max_losing_streak=0,
        sizing_mode="percent_risk",
    )
    base.update(overrides)
    return RiskLimits(**base)


def _long(stop_price: float = 95.0) -> Signal:
    return Signal(timestamp=_TS, direction=Direction.LONG, strength=1.0, stop_price=stop_price)


# --------------------------------------------------------------------------- #
# Absolute-Modus
# --------------------------------------------------------------------------- #
def test_absolute_size_bound_by_risk_per_trade():
    """proposed = min(risk_per_trade, max_position_size); hier bindet risk_per_trade."""
    engine = RiskEngine(_abs_limits(risk_per_trade=5.0, max_position_size=10.0))
    decision = engine.evaluate(_signal(), AccountState(equity=1000.0))
    assert decision.approved is True
    assert decision.size == 5.0


def test_absolute_size_bound_by_max_position_size():
    """proposed = min(risk_per_trade, max_position_size); hier bindet max_position_size."""
    engine = RiskEngine(_abs_limits(risk_per_trade=5.0, max_position_size=3.0))
    decision = engine.evaluate(_signal(), AccountState(equity=1000.0))
    assert decision.approved is True
    assert decision.size == 3.0


def test_absolute_remaining_exposure_caps_size():
    """size = min(proposed, max_total_exposure - current_exposure)."""
    engine = RiskEngine(_abs_limits(risk_per_trade=5.0, max_position_size=10.0, max_total_exposure=100.0))
    decision = engine.evaluate(_signal(), AccountState(equity=1000.0, current_exposure=98.0))
    assert decision.approved is True
    assert decision.size == 2.0


def test_absolute_day_drawdown_equal_limit_rejects():
    """Grenzwert: day_drawdown == max_daily_drawdown loest den Stopp aus (>=)."""
    engine = RiskEngine(_abs_limits(max_daily_drawdown=20.0))
    decision = engine.evaluate(_signal(), AccountState(equity=1000.0, day_drawdown=20.0))
    assert decision.approved is False
    assert decision.size == 0.0
    assert decision.reason


def test_absolute_flat_signal_rejected():
    """FLAT-Signal wird abgelehnt (keine Ausfuehrung erforderlich)."""
    engine = RiskEngine(_abs_limits())
    decision = engine.evaluate(_signal(direction=Direction.FLAT), AccountState(equity=1000.0))
    assert decision.approved is False
    assert decision.size == 0.0
    assert decision.reason


# --------------------------------------------------------------------------- #
# Percent-Risk-Modus: Wert-Rejects (nicht None)
# --------------------------------------------------------------------------- #
def test_percent_risk_non_positive_reference_price_rejected():
    """reference_price <= 0 (Wert, nicht None) -> Ablehnung."""
    engine = RiskEngine(_pct_limits())
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=0.0)
    assert decision.approved is False
    assert decision.size == 0.0


def test_percent_risk_non_positive_stop_price_rejected():
    """stop_price <= 0 (Wert, nicht None) -> Ablehnung."""
    engine = RiskEngine(_pct_limits())
    decision = engine.evaluate(_long(stop_price=0.0), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is False
    assert decision.size == 0.0


# --------------------------------------------------------------------------- #
# Percent-Risk-Modus: Config-Rejects (fail-safe)
# --------------------------------------------------------------------------- #
def test_percent_risk_non_positive_max_daily_drawdown_rejected():
    engine = RiskEngine(_pct_limits(max_daily_drawdown=0.0))
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is False


def test_percent_risk_non_positive_max_position_size_rejected():
    engine = RiskEngine(_pct_limits(max_position_size=0.0))
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is False


def test_percent_risk_non_positive_max_total_exposure_rejected():
    engine = RiskEngine(_pct_limits(max_total_exposure=0.0))
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is False


# --------------------------------------------------------------------------- #
# Percent-Risk-Modus: Mehrfach-Caps + Cap-Reihenfolge
# --------------------------------------------------------------------------- #
def test_percent_risk_multiple_caps_apply_in_order():
    """raw size 20 -> max_position_size(10) -> notional(500/100=5) -> exposure(300/100=3)."""
    engine = RiskEngine(
        _pct_limits(max_position_size=10.0, max_position_notional=500.0, max_total_exposure=300.0)
    )
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is True
    assert decision.size == 3.0
    assert decision.capped_by_max_position is True
    assert decision.capped_by_max_notional is True
    assert decision.capped_by_total_exposure is True


# --------------------------------------------------------------------------- #
# Invarianten
# --------------------------------------------------------------------------- #
def test_percent_risk_size_independent_of_losing_streak():
    """Kein Martingale: ohne aktives Streak-Limit ist size unabhaengig von Verlusten."""
    engine = RiskEngine(_pct_limits(max_losing_streak=0))
    no_losses = engine.evaluate(
        _long(), AccountState(equity=10_000.0, consecutive_losses=0), reference_price=100.0
    )
    with_losses = engine.evaluate(
        _long(), AccountState(equity=10_000.0, consecutive_losses=5), reference_price=100.0
    )
    assert no_losses.approved is True
    assert with_losses.approved is True
    assert no_losses.size == with_losses.size == 20.0


def test_every_evaluated_path_yields_exactly_one_decision():
    """Akzeptanzkriterium: jeder Pfad liefert genau eine wohlgeformte RiskDecision."""
    abs_engine = RiskEngine(_abs_limits())
    pct_engine = RiskEngine(_pct_limits())
    cases = [
        # (engine, signal, account_state, reference_price)
        (abs_engine, _signal(), AccountState(equity=1000.0), None),            # approve
        (abs_engine, _signal(direction=Direction.FLAT), AccountState(), None),  # reject FLAT
        (abs_engine, _signal(strength=0.0), AccountState(), None),              # reject strength
        (pct_engine, _long(), AccountState(equity=10_000.0), 100.0),           # approve
        (pct_engine, _long(), AccountState(equity=0.0), 100.0),                # reject equity
        (pct_engine, _long(), AccountState(equity=10_000.0), 0.0),             # reject ref<=0
    ]
    for engine, signal, account_state, reference_price in cases:
        decision = engine.evaluate(signal, account_state, reference_price=reference_price)
        assert decision is not None
        assert isinstance(decision.approved, bool)
        assert isinstance(decision.size, float)
        assert isinstance(decision.reason, str)
        if decision.approved is False:
            assert decision.size == 0.0
            assert decision.reason != ""
