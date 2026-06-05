"""Domänen-Tests.

Spec: liquent/04_Architecture/Domain_Model.md
Prüft, dass die Kern-Entitäten importierbar und mit den Spec-Feldern
konstruierbar sind (Strukturen, keine Logik).
"""

from datetime import datetime, timezone

from liquent.domain.models import (
    Direction,
    Experiment,
    Instrument,
    LiquidityMetric,
    MarketData,
    OrderBookLevel,
    OrderBookSnapshot,
    Position,
    PositionStatus,
    RiskDecision,
    Signal,
)
from liquent.risk.engine import AccountState, RiskLimits


def _utc_now() -> datetime:
    return datetime(2026, 6, 2, tzinfo=timezone.utc)


def test_instrument_fields():
    inst = Instrument(symbol="BTC-EUR", base="BTC", quote="EUR")
    assert inst.symbol == "BTC-EUR"
    assert inst.base == "BTC"
    assert inst.quote == "EUR"


def test_market_data_and_order_book():
    md = MarketData(timestamp=_utc_now(), bid=100.0, ask=100.5, volume=12.0)
    assert md.ask >= md.bid

    book = OrderBookSnapshot(
        timestamp=_utc_now(),
        levels=[OrderBookLevel(price=100.0, size=2.0, side=Direction.LONG)],
    )
    assert len(book.levels) == 1
    assert book.levels[0].price == 100.0


def test_signal_carries_metric():
    metric = LiquidityMetric(spread=0.5, depth=1000.0, imbalance=0.1)
    signal = Signal(
        timestamp=_utc_now(),
        direction=Direction.LONG,
        strength=0.8,
        metric=metric,
    )
    assert signal.direction is Direction.LONG
    assert signal.metric is metric


def test_position_and_risk_decision():
    inst = Instrument(symbol="BTC-EUR", base="BTC", quote="EUR")
    pos = Position(instrument=inst, entry=100.0, size=1.0)
    assert pos.status is PositionStatus.OPEN
    assert pos.instrument is inst

    decision = RiskDecision(approved=False, size=0.0, reason="Test")
    assert decision.approved is False
    assert decision.reason


def test_experiment_defaults():
    exp = Experiment(hypothese="Liquidität korreliert mit Spread")
    assert exp.parameter == {}
    assert exp.metriken == {}


# --------------------------------------------------------------------------- #
# LQ-004 Phase 1: additive Risk-Sizing-Vorbereitung (keine Verhaltensänderung)
# --------------------------------------------------------------------------- #
# 1: Signal.stop_price ist standardmäßig None (rückwärtskompatibel).
def test_signal_stop_price_default_none():
    signal = Signal(timestamp=_utc_now(), direction=Direction.LONG, strength=1.0)
    assert signal.stop_price is None


# 2: Signal akzeptiert einen expliziten stop_price.
def test_signal_accepts_explicit_stop_price():
    signal = Signal(
        timestamp=_utc_now(),
        direction=Direction.LONG,
        strength=1.0,
        stop_price=95.0,
    )
    assert signal.stop_price == 95.0


# 3–7: RiskLimits-Defaults (additiv, fail-safe).
def test_risk_limits_new_defaults():
    limits = RiskLimits()
    assert limits.sizing_mode == "absolute"
    assert limits.risk_per_trade_pct == 0.0
    assert limits.max_position_notional == 0.0
    assert limits.max_daily_loss == 0.0
    assert limits.max_losing_streak == 0
    # Bestehendes Feld bleibt unverändert vorhanden.
    assert limits.risk_per_trade == 0.0


# 8–11: RiskDecision-Audit-Felder (Defaults).
def test_risk_decision_audit_field_defaults():
    decision = RiskDecision(approved=True, size=1.0, reason="ok")
    assert decision.risk_amount == 0.0
    assert decision.stop_distance == 0.0
    assert decision.notional == 0.0
    assert decision.capped_by_max_position is False
    assert decision.capped_by_max_notional is False
    assert decision.capped_by_total_exposure is False


# Zusatz: AccountState-Erweiterung ist additiv mit Default.
def test_account_state_day_realized_loss_default():
    state = AccountState()
    assert state.day_realized_loss == 0.0
