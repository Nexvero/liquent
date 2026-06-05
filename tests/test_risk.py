"""Risk-Engine-Tests.

Spec: liquent/05_Risk/Risk_Engine_Spec.md
ADR: liquent/10_Decisions/ADR-002_Risk_First_Execution.md

Deckt die zentralen Invarianten ab:
- Jedes Signal erzeugt genau eine RiskDecision.
- Fehlendes/leeres Signal -> Ablehnung (fail-safe).
- Fehlkonfigurierte Limits -> Ablehnung (fail-safe statt fail-open).
- Verlustserien führen nie zu größerem Risiko.
"""

from datetime import datetime, timezone

from liquent.domain.models import Direction, Signal
from liquent.risk.engine import AccountState, RiskEngine, RiskLimits


def _signal(strength: float = 0.8, direction: Direction = Direction.LONG) -> Signal:
    return Signal(
        timestamp=datetime(2026, 6, 2, tzinfo=timezone.utc),
        direction=direction,
        strength=strength,
    )


def _valid_limits() -> RiskLimits:
    return RiskLimits(
        max_position_size=10.0,
        max_total_exposure=100.0,
        risk_per_trade=5.0,
        max_daily_drawdown=20.0,
    )


def test_empty_signal_is_rejected():
    """Fehlendes Signal -> Ablehnung mit Begründung."""
    engine = RiskEngine(_valid_limits())
    decision = engine.evaluate(None, AccountState())  # type: ignore[arg-type]
    assert decision.approved is False
    assert decision.size == 0.0
    assert decision.reason


def test_zero_strength_signal_is_rejected():
    engine = RiskEngine(_valid_limits())
    decision = engine.evaluate(_signal(strength=0.0), AccountState())
    assert decision.approved is False


def test_unconfigured_limits_fail_safe():
    """Default-Limits (alle 0) lehnen ab — fail-safe statt fail-open."""
    engine = RiskEngine()  # keine Limits -> Defaults
    decision = engine.evaluate(_signal(), AccountState())
    assert decision.approved is False
    assert "Limits" in decision.reason or "fail-safe" in decision.reason


def test_valid_signal_within_limits_is_approved():
    engine = RiskEngine(_valid_limits())
    decision = engine.evaluate(_signal(), AccountState(equity=1000.0))
    assert decision.approved is True
    assert 0.0 < decision.size <= 10.0


def test_no_risk_increase_after_losing_streak():
    """Invariante: nach Verlustserie wird das Risiko NIE erhöht."""
    engine = RiskEngine(_valid_limits())
    baseline = engine.evaluate(_signal(), AccountState(consecutive_losses=0))
    after_losses = engine.evaluate(_signal(), AccountState(consecutive_losses=5))
    if after_losses.approved:
        assert after_losses.size <= baseline.size


def test_drawdown_stop_pauses_trading():
    engine = RiskEngine(_valid_limits())
    decision = engine.evaluate(_signal(), AccountState(day_drawdown=25.0))
    assert decision.approved is False


def test_exposure_limit_blocks_new_risk():
    engine = RiskEngine(_valid_limits())
    decision = engine.evaluate(_signal(), AccountState(current_exposure=100.0))
    assert decision.approved is False


def test_every_signal_yields_exactly_one_decision():
    """Akzeptanzkriterium: genau eine RiskDecision je Signal."""
    engine = RiskEngine(_valid_limits())
    decision = engine.evaluate(_signal(), AccountState())
    assert decision is not None
    assert hasattr(decision, "approved")


# --------------------------------------------------------------------------- #
# LQ-004 Phase 2: percent_risk Sizing (absolute bleibt Default & unverändert)
# --------------------------------------------------------------------------- #
def _pct_limits(**overrides) -> RiskLimits:
    """Valide percent_risk-Limits; großzügig, damit keine Cap-Tests stören."""
    base = dict(
        max_position_size=1000.0,
        max_total_exposure=1_000_000.0,
        risk_per_trade=0.0,  # im percent_risk-Modus irrelevant
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
    return Signal(
        timestamp=datetime(2026, 6, 2, tzinfo=timezone.utc),
        direction=Direction.LONG,
        strength=1.0,
        stop_price=stop_price,
    )


def _short(stop_price: float = 105.0) -> Signal:
    return Signal(
        timestamp=datetime(2026, 6, 2, tzinfo=timezone.utc),
        direction=Direction.SHORT,
        strength=1.0,
        stop_price=stop_price,
    )


# 1: absolute-Default bleibt bisheriges Verhalten (reference_price ignoriert).
def test_absolute_mode_unchanged_and_default():
    limits = _valid_limits()
    assert limits.sizing_mode == "absolute"
    engine = RiskEngine(limits)
    decision = engine.evaluate(_signal(), AccountState(equity=1000.0), reference_price=100.0)
    assert decision.approved is True
    assert 0.0 < decision.size <= 10.0
    # Audit-Felder bleiben im absoluten Modus auf Default.
    assert decision.risk_amount == 0.0
    assert decision.notional == 0.0


# 2: percent_risk Long-Sizing.
def test_percent_risk_long_sizing():
    engine = RiskEngine(_pct_limits())
    decision = engine.evaluate(
        _long(stop_price=95.0), AccountState(equity=10_000.0), reference_price=100.0
    )
    assert decision.approved is True
    assert decision.risk_amount == 100.0
    assert decision.stop_distance == 5.0
    assert decision.size == 20.0
    assert decision.notional == 2000.0


# 3: percent_risk Short-Sizing.
def test_percent_risk_short_sizing():
    engine = RiskEngine(_pct_limits())
    decision = engine.evaluate(
        _short(stop_price=105.0), AccountState(equity=10_000.0), reference_price=100.0
    )
    assert decision.approved is True
    assert decision.stop_distance == 5.0
    assert decision.size == 20.0


# 4: fehlender reference_price -> Ablehnung.
def test_percent_risk_missing_reference_price_rejected():
    engine = RiskEngine(_pct_limits())
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0))
    assert decision.approved is False
    assert decision.reason


# 5: fehlender stop_price -> Ablehnung.
def test_percent_risk_missing_stop_rejected():
    engine = RiskEngine(_pct_limits())
    signal = Signal(
        timestamp=datetime(2026, 6, 2, tzinfo=timezone.utc),
        direction=Direction.LONG,
        strength=1.0,
    )  # stop_price = None
    decision = engine.evaluate(signal, AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is False


# 6: Long mit Stop >= Entry -> Ablehnung.
def test_percent_risk_long_stop_not_below_entry_rejected():
    engine = RiskEngine(_pct_limits())
    over = engine.evaluate(_long(stop_price=105.0), AccountState(equity=10_000.0), reference_price=100.0)
    equal = engine.evaluate(_long(stop_price=100.0), AccountState(equity=10_000.0), reference_price=100.0)
    assert over.approved is False
    assert equal.approved is False


# 7: Short mit Stop <= Entry -> Ablehnung.
def test_percent_risk_short_stop_not_above_entry_rejected():
    engine = RiskEngine(_pct_limits())
    under = engine.evaluate(_short(stop_price=95.0), AccountState(equity=10_000.0), reference_price=100.0)
    equal = engine.evaluate(_short(stop_price=100.0), AccountState(equity=10_000.0), reference_price=100.0)
    assert under.approved is False
    assert equal.approved is False


# 8: risk_per_trade_pct <= 0 -> Ablehnung.
def test_percent_risk_pct_non_positive_rejected():
    engine = RiskEngine(_pct_limits(risk_per_trade_pct=0.0))
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is False


# 9: risk_per_trade_pct > 1.0 -> Ablehnung.
def test_percent_risk_pct_above_one_rejected():
    engine = RiskEngine(_pct_limits(risk_per_trade_pct=1.5))
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is False


# 10: equity <= 0 -> Ablehnung.
def test_percent_risk_non_positive_equity_rejected():
    engine = RiskEngine(_pct_limits())
    decision = engine.evaluate(_long(), AccountState(equity=0.0), reference_price=100.0)
    assert decision.approved is False


# 11: max_position_size kappt size.
def test_percent_risk_capped_by_max_position_size():
    engine = RiskEngine(_pct_limits(max_position_size=10.0))
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is True
    assert decision.size == 10.0
    assert decision.capped_by_max_position is True


# 12: max_position_notional kappt size.
def test_percent_risk_capped_by_max_notional():
    engine = RiskEngine(_pct_limits(max_position_notional=500.0))
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is True
    assert decision.size == 5.0  # 500 / 100
    assert decision.capped_by_max_notional is True


# 13: verbleibendes max_total_exposure kappt size.
def test_percent_risk_capped_by_total_exposure():
    engine = RiskEngine(_pct_limits(max_total_exposure=300.0))
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is True
    assert decision.size == 3.0  # 300 / 100
    assert decision.capped_by_total_exposure is True


# 14: max_daily_drawdown blockiert.
def test_percent_risk_drawdown_blocks():
    engine = RiskEngine(_pct_limits(max_daily_drawdown=1000.0))
    decision = engine.evaluate(
        _long(), AccountState(equity=10_000.0, day_drawdown=1000.0), reference_price=100.0
    )
    assert decision.approved is False


# 15: max_daily_loss blockiert.
def test_percent_risk_daily_loss_blocks():
    engine = RiskEngine(_pct_limits(max_daily_loss=500.0))
    decision = engine.evaluate(
        _long(), AccountState(equity=10_000.0, day_realized_loss=500.0), reference_price=100.0
    )
    assert decision.approved is False


# 16: max_losing_streak blockiert.
def test_percent_risk_losing_streak_blocks():
    engine = RiskEngine(_pct_limits(max_losing_streak=3))
    decision = engine.evaluate(
        _long(), AccountState(equity=10_000.0, consecutive_losses=3), reference_price=100.0
    )
    assert decision.approved is False


# 17: unbekannter sizing_mode -> Ablehnung.
def test_unknown_sizing_mode_rejected():
    engine = RiskEngine(_pct_limits(sizing_mode="martingale"))
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is False
    assert decision.size == 0.0


# 18: Audit-Felder bei Approval korrekt gesetzt.
def test_percent_risk_audit_fields_on_approval():
    engine = RiskEngine(_pct_limits())
    decision = engine.evaluate(_long(), AccountState(equity=10_000.0), reference_price=100.0)
    assert decision.approved is True
    assert decision.risk_amount == 100.0
    assert decision.stop_distance == 5.0
    assert decision.notional == 2000.0
    assert decision.capped_by_max_position is False
    assert decision.capped_by_max_notional is False
    assert decision.capped_by_total_exposure is False
