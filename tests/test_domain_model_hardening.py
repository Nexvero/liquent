"""LQ-047 — ergänzende Domain-Model-Behavior-Locks.

Diese Tests schreiben ausschließlich das BESTEHENDE Verhalten von
``src/liquent/domain/models.py`` fest (Behavior-Lock): Enum-Werte/str-Verhalten,
frozen-Immutability, default_factory-Unabhängigkeit, optionale Feld-Defaults
sowie Equality/Hashing. Rein in-memory — keine Daten, keine Fixtures, keine
Artefakte. Keine Produktionslogik-Änderung, keine neuen Felder, keine Änderung
bestehender Tests.
"""

from dataclasses import FrozenInstanceError
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

_TS = datetime(2026, 6, 2, tzinfo=timezone.utc)


def _expect(exc_type, fn) -> None:
    raised = False
    try:
        fn()
    except exc_type:
        raised = True
    assert raised, f"erwartete {exc_type.__name__} wurde nicht ausgelöst"


# --------------------------------------------------------------------------- #
# Enum Contract
# --------------------------------------------------------------------------- #
def test_direction_enum_values_and_str():
    assert Direction.LONG == "long"
    assert Direction.SHORT == "short"
    assert Direction.FLAT == "flat"
    assert {d.value for d in Direction} == {"long", "short", "flat"}


def test_position_status_enum_values_and_str():
    assert PositionStatus.OPEN == "open"
    assert PositionStatus.CLOSED == "closed"
    assert {s.value for s in PositionStatus} == {"open", "closed"}


# --------------------------------------------------------------------------- #
# Frozen / Immutability
# --------------------------------------------------------------------------- #
def test_frozen_dataclasses_raise_on_mutation():
    inst = Instrument(symbol="B", base="b", quote="q")
    md = MarketData(timestamp=_TS, bid=1.0, ask=2.0, volume=1.0)
    sig = Signal(timestamp=_TS, direction=Direction.LONG, strength=1.0)
    dec = RiskDecision(approved=True, size=1.0, reason="ok")
    pos = Position(instrument=inst, entry=100.0, size=1.0)

    _expect(FrozenInstanceError, lambda: setattr(inst, "symbol", "X"))
    _expect(FrozenInstanceError, lambda: setattr(md, "bid", 0.0))
    _expect(FrozenInstanceError, lambda: setattr(sig, "strength", 0.0))
    _expect(FrozenInstanceError, lambda: setattr(dec, "size", 0.0))
    _expect(FrozenInstanceError, lambda: setattr(pos, "size", 0.0))


# --------------------------------------------------------------------------- #
# Default / default_factory
# --------------------------------------------------------------------------- #
def test_default_factory_fields_are_independent():
    e1, e2 = Experiment(hypothese="h"), Experiment(hypothese="h")
    e1.parameter["x"] = 1
    e1.metriken["y"] = 2
    assert e2.parameter == {}
    assert e2.metriken == {}

    s1 = OrderBookSnapshot(timestamp=_TS)
    s2 = OrderBookSnapshot(timestamp=_TS)
    s1.levels.append(OrderBookLevel(price=1.0, size=1.0))
    assert s2.levels == []


# --------------------------------------------------------------------------- #
# Optional-Field Defaults (bisher nicht abgedeckt)
# --------------------------------------------------------------------------- #
def test_optional_field_defaults():
    assert OrderBookLevel(price=1.0, size=1.0).side == Direction.FLAT
    assert LiquidityMetric(spread=0.0, depth=0.0, imbalance=0.0).timestamp is None
    assert OrderBookSnapshot(timestamp=_TS).levels == []


# --------------------------------------------------------------------------- #
# Equality / Hashing
# --------------------------------------------------------------------------- #
def test_equality_and_hashing():
    a = Instrument(symbol="BTC-EUR", base="BTC", quote="EUR")
    b = Instrument(symbol="BTC-EUR", base="BTC", quote="EUR")
    assert a == b
    assert hash(a) == hash(b)
    assert len({a, b}) == 1  # wertgleich -> ein Set-Element
    assert {a: "x"}[b] == "x"  # als Dict-Key nutzbar


def test_dict_list_dataclasses_are_unhashable():
    # Experiment (dict-Felder) und OrderBookSnapshot (list-Feld) sind unhashbar.
    _expect(TypeError, lambda: hash(Experiment(hypothese="h")))
    _expect(TypeError, lambda: hash(OrderBookSnapshot(timestamp=_TS)))
