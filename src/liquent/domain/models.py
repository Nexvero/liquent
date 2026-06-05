"""Domänen-Entitäten für Liquent.

Spec: liquent/04_Architecture/Domain_Model.md
Glossar: liquent/01_Strategy/Glossar_Liquidity.md

Nur Datenstrukturen und Typen — bewusst KEINE Logik. Die Felder folgen den
"Wichtigen Feldern" aus dem Domänenmodell. Invarianten aus dem Modell werden
hier dokumentiert, aber NICHT erzwungen (das ist Aufgabe der jeweiligen
Module, z. B. der Risk Engine).

Zeitstempel werden als timezone-aware ``datetime`` in UTC erwartet
(siehe Data_Source_Inventory: "Zeitstempel in einheitlicher Zeitzone (UTC)").
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class Direction(str, Enum):
    """Richtung eines Strategie-Signals."""

    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


class PositionStatus(str, Enum):
    """Lebenszyklus-Status einer Position."""

    OPEN = "open"
    CLOSED = "closed"


@dataclass(frozen=True)
class Instrument:
    """Handelbares Asset.

    Felder gemäß Domänenmodell: symbol, basis, quote.
    ``base`` entspricht dem im Modell genannten "basis" (Basiswährung/-asset).
    """

    symbol: str
    base: str
    quote: str


@dataclass(frozen=True)
class MarketData:
    """Marktzustand zu einem Zeitpunkt.

    Felder: timestamp, bid, ask, volume.
    """

    timestamp: datetime
    bid: float
    ask: float
    volume: float


@dataclass(frozen=True)
class OrderBookLevel:
    """Ein einzelnes Preisniveau im Orderbuch.

    Hilfsstruktur für ``OrderBookSnapshot.levels`` (Glossar: "Order Book",
    "Market Depth"). ``side`` unterscheidet Bid/Ask.

    # TODO(spec): Domain_Model nennt nur "levels[]" ohne Feldstruktur.
    #   Felder (price, size, side) sind hier als plausible Annahme gesetzt und
    #   bei Klärung in 03_Data / 04_Architecture zu bestätigen.
    """

    price: float
    size: float
    side: Direction = Direction.FLAT


@dataclass(frozen=True)
class OrderBookSnapshot:
    """Tiefe je Preisniveau zu einem Zeitpunkt.

    Felder: timestamp, levels[].
    """

    timestamp: datetime
    levels: list[OrderBookLevel] = field(default_factory=list)


@dataclass(frozen=True)
class LiquidityMetric:
    """Abgeleitete Liquiditätskennzahl.

    Felder: spread, depth, imbalance (Glossar: Spread, Market Depth, Imbalance).
    Wird aus MarketData und OrderBookSnapshot gespeist.
    """

    spread: float
    depth: float
    imbalance: float
    timestamp: datetime | None = None


@dataclass(frozen=True)
class Signal:
    """Strategie-Ausgabe.

    Felder: timestamp, direction, strength.
    Invariante (Modell): "Kein Signal ohne LiquidityMetric" — die Herkunft wird
    über ``metric`` referenzierbar gemacht, aber hier nicht erzwungen.

    ``stop_price`` (optional, Default ``None``): geplanter Stop-/Invalidations-
    Preis. Wird später (LQ-004 ``percent_risk``-Sizing) für die prozentuale
    Positionsgrößen-Berechnung herangezogen (risk_amount / Stop-Distanz). In
    dieser Phase rein additiv — keine automatische Stop-Berechnung, keine
    Validierung gegen den Entry-Preis, keine Engine-/Runner-Nutzung.

    # TODO(spec): Wertebereich/Skala von ``strength`` ist nicht definiert
    #   (z. B. 0.0–1.0 vs. beliebig). Bis zur Klärung als float belassen.
    """

    timestamp: datetime
    direction: Direction
    strength: float
    metric: LiquidityMetric | None = None
    stop_price: float | None = None


@dataclass(frozen=True)
class RiskDecision:
    """Ergebnis der Risikoprüfung.

    Felder: approved, size, reason.
    Invariante (Modell): "Keine Position ohne genehmigte RiskDecision".
    ``reason`` ist gemäß Risk_Engine_Spec bei jeder Ablehnung zu befüllen.

    Audit-Felder (optional, Default-Werte; LQ-004 vorbereitet): dokumentieren
    künftig die Sizing-Herleitung (``risk_amount``, ``stop_distance``,
    ``notional``) und welche Grenze die Größe gedeckelt hat
    (``capped_by_*``). In dieser Phase rein additiv — von der Engine noch nicht
    befüllt, brechen keine bestehenden Rückgaben.
    """

    approved: bool
    size: float
    reason: str
    risk_amount: float = 0.0
    stop_distance: float = 0.0
    notional: float = 0.0
    capped_by_max_position: bool = False
    capped_by_max_notional: bool = False
    capped_by_total_exposure: bool = False


@dataclass(frozen=True)
class Position:
    """Offene oder abgeschlossene Position.

    Felder: entry, size, status. Jede Position ist genau einem Instrument
    zugeordnet (Invariante des Modells).
    """

    instrument: Instrument
    entry: float
    size: float
    status: PositionStatus = PositionStatus.OPEN


@dataclass(frozen=True)
class Experiment:
    """Backtest-/Analyselauf.

    Felder: hypothese, parameter, metriken. Jeder Backtest-Lauf wird als
    Experiment dokumentiert (Backtesting-Spec, Vault-Ordner 12_Research/).
    """

    hypothese: str
    parameter: dict[str, Any] = field(default_factory=dict)
    metriken: dict[str, Any] = field(default_factory=dict)
