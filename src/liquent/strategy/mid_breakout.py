"""MidBreakoutStrategy — erste regelbasierte v0-Strategie (LQ-006 Phase 1).

Spec: Strategie-v0-Spezifikation (Mid-Breakout, OHLCV-Proxy).
ADR: liquent/10_Decisions/ADR-002_Risk_First_Execution.md (Risk-First)

Zweck: eine bewusst einfache, deterministische Strategie, die die bestehende
Pipeline validiert (Daten -> Signal mit ``stop_price`` -> RiskEngine
``percent_risk`` -> Runner). KEINE echte Handelslogik im Sinne von
Orderflow/Orderbook, KEINE Optimierung, KEINE Profitabilitätsaussage und KEINE
Handlungsempfehlung.

Datengrundlage (wichtig): ``MarketData`` führt ``bid``/``ask``/``volume`` und
KEIN OHLC. Der Referenzpreis ist der Mittelkurs ``mid = (bid + ask) / 2`` —
identisch zur Referenz im Runner. Da der CSV-Lader ``close -> bid = ask =
close`` abbildet, gilt auf CSV-Daten ``mid == close``. Diese Strategie ist damit
ein **Mid-/Close-Breakout-Proxy**, kein echtes Intrabar-High/Low-Breakout
(kein ATR, kein Orderbook, keine Indikator-Bibliotheken).

Die Strategie ist rein und deterministisch: keine I/O, keine Netzwerk-Calls,
keine Wall-Clock-Zeit, kein Zufall. Sie erfüllt die ``Strategy``-Schnittstelle
des Runners strukturell (``generate_signals(market_data) -> Sequence[Signal]``)
ohne Abhängigkeit auf das Backtesting-Modul.
"""

from __future__ import annotations

from typing import Sequence

from ..domain.models import Direction, MarketData, Signal


def _mid(bar: MarketData) -> float:
    """Referenzpreis eines Bars = Mittelkurs zwischen bid und ask."""
    return (bar.bid + bar.ask) / 2.0


class MidBreakoutStrategy:
    """Regelbasierte Mid-Breakout-Strategie (v0, Proxy auf Mid/Close).

    Signalregeln je Entry-Bar ``i`` (mit ausreichend Historie und Folge-Bar):
        LONG, wenn ``mid[i] > max(mid[i-lookback_bars : i])`` (strikt).
        SHORT, wenn ``mid[i] < min(mid[i-lookback_bars : i])`` (strikt) und
        ``allow_short`` gesetzt ist.

    Stop-Regeln (kompatibel zur strikten ``percent_risk``-Prüfung der Engine):
        LONG:  ``stop_price = mid[i] * (1 - stop_distance_pct)`` (< mid, > 0).
        SHORT: ``stop_price = mid[i] * (1 + stop_distance_pct)`` (> mid).

    Strength: in v0 fix ``1.0``. Die RiskEngine prüft ``strength`` aktuell nur
    auf ``> 0`` und skaliert die Positionsgröße NICHT damit; das Sizing erfolgt
    ausschließlich in der RiskEngine. Eine proportionale Stärke hätte in v0
    daher keine Verhaltenswirkung und wird bewusst nicht eingeführt.
    ``min_strength`` bleibt als (vorwärtskompatibler) Filterparameter erhalten.

    Hinweis zu ``Signal.metric``: Das Domänenfeld erwartet ein
    ``LiquidityMetric | None`` — KEINEN String. Da diese Proxy-Strategie keine
    Liquiditätskennzahl berechnet, bleibt ``metric`` bewusst ``None`` (statt
    einen Herkunfts-String in ein typisiertes Feld zu schreiben).
    """

    def __init__(
        self,
        lookback_bars: int,
        stop_distance_pct: float,
        min_strength: float = 0.0,
        allow_short: bool = True,
    ) -> None:
        # Fail-safe: ungültige Konfiguration sofort bei Konstruktion ablehnen.
        if lookback_bars <= 0:
            raise ValueError(f"lookback_bars muss > 0 sein (war {lookback_bars})")
        if stop_distance_pct <= 0.0:
            raise ValueError(
                f"stop_distance_pct muss > 0 sein (war {stop_distance_pct})"
            )
        if stop_distance_pct >= 1.0:
            # Obergrenze garantiert zugleich einen positiven Long-Stop (> 0).
            raise ValueError(
                f"stop_distance_pct muss < 1.0 sein (war {stop_distance_pct})"
            )
        if min_strength < 0.0 or min_strength > 1.0:
            raise ValueError(
                f"min_strength muss in [0, 1] liegen (war {min_strength})"
            )

        self.lookback_bars = lookback_bars
        self.stop_distance_pct = stop_distance_pct
        self.min_strength = min_strength
        self.allow_short = allow_short

    def generate_signals(self, market_data: Sequence[MarketData]) -> tuple[Signal, ...]:
        """Erzeugt Breakout-Signale (rein, deterministisch).

        Entry-Indizes: ``lookback_bars <= i <= len(market_data) - 2`` — es muss
        genügend Historie für das Rückblickfenster UND ein Folge-Bar für den
        Close-to-Close-Exit des Runners existieren. Auf dem letzten Bar werden
        bewusst keine Signale erzeugt. Pro Bar entsteht höchstens ein Signal
        (LONG und SHORT schließen sich aus), daher keine doppelten Zeitstempel.
        """
        bars = list(market_data)
        n = len(bars)

        # Letzter ausführbarer Entry-Index (braucht Folge-Bar bei i+1).
        last_entry = n - 2
        if last_entry < self.lookback_bars:
            return ()

        mids = [_mid(bar) for bar in bars]
        # Fixe Stärke (siehe Klassendoku); Filter bleibt vorwärtskompatibel.
        strength = 1.0
        if strength < self.min_strength:
            return ()

        signals: list[Signal] = []
        for i in range(self.lookback_bars, last_entry + 1):
            window = mids[i - self.lookback_bars : i]
            prev_high = max(window)
            prev_low = min(window)
            cur = mids[i]

            if cur > prev_high:
                direction = Direction.LONG
                stop_price = cur * (1.0 - self.stop_distance_pct)
            elif self.allow_short and cur < prev_low:
                direction = Direction.SHORT
                stop_price = cur * (1.0 + self.stop_distance_pct)
            else:
                continue

            # Fail-safe: kein Signal mit nicht-positivem Stop (kann bei
            # 0 < stop_distance_pct < 1 und mid > 0 nicht auftreten).
            if stop_price <= 0.0:
                continue

            signals.append(
                Signal(
                    timestamp=bars[i].timestamp,
                    direction=direction,
                    strength=strength,
                    stop_price=stop_price,
                )
            )

        return tuple(signals)
