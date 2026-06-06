"""MidBreakoutStrategyV1 — dichte-kontrollierte Mid-Breakout-Strategie (LQ-008).

Spec: LQ-008 Phase 1 (MidBreakoutStrategy v1).
ADR: liquent/10_Decisions/ADR-002_Risk_First_Execution.md (Risk-First)

Diese Klasse ist eine **additive** Weiterentwicklung von ``MidBreakoutStrategy``
(v0, ``mid_breakout.py`` — bleibt unverändert). Sie adressiert die im
30-Tage-Echtdatenlauf beobachtete hohe Signaldichte über zwei zusätzliche,
deterministische Stellschrauben:

- ``breakout_threshold_pct``: eine relative Mindestbewegung über/unter dem
  Rückblick-Hoch/Tief filtert Mikro-/Noise-Ausbrüche heraus. ``0.0`` reproduziert
  exakt das v0-Verhalten (strikter ``>``/``<``-Vergleich).
- ``cooldown_bars``: nach einem erzeugten Signal werden die folgenden
  ``cooldown_bars`` Bars übersprungen, um Trade-Cluster aufzubrechen.

Wie v0 arbeitet die Strategie rein und deterministisch auf dem Mittelkurs
``mid = (bid + ask) / 2`` (Domänenmodell führt bid/ask, kein OHLC; der CSV-Lader
bildet ``close -> bid = ask = close`` ab, also ``mid == close``). Es ist ein
Mid-/Close-Breakout-Proxy: kein echtes Intrabar-High/Low, kein ATR, kein
Orderbook, keine Indikator-Bibliotheken. Keine I/O, keine Netzwerk-Calls, keine
Wall-Clock-Zeit, kein Zufall. KEINE Optimierung, KEINE Profitabilitätsaussage,
KEINE Handlungsempfehlung.

Risk-First-Invariante: jedes Signal trägt einen richtungskonsistenten,
positiven ``stop_price`` (Voraussetzung des ``percent_risk``-Modus der
RiskEngine). ``strength`` ist ausschließlich Signalqualität/Filter — die
RiskEngine skaliert die Positionsgröße NICHT über ``strength`` (sie prüft nur
``> 0``). Das Sizing erfolgt allein in der RiskEngine.
"""

from __future__ import annotations

from typing import Sequence

from ..domain.models import Direction, MarketData, Signal


def _mid(bar: MarketData) -> float:
    """Referenzpreis eines Bars = Mittelkurs zwischen bid und ask."""
    return (bar.bid + bar.ask) / 2.0


class MidBreakoutStrategyV1:
    """Mid-Breakout-Strategie v1 mit Breakout-Threshold und Cooldown.

    Signalregeln je Entry-Bar ``i`` (mit ``lookback_bars <= i <= n - 2``):
        LONG, wenn ``mid[i] > prev_high * (1 + breakout_threshold_pct)``.
        SHORT, wenn ``mid[i] < prev_low * (1 - breakout_threshold_pct)`` und
        ``allow_short`` gesetzt ist.
    Dabei ist ``prev_high = max(mids[i-lookback_bars : i])`` und
    ``prev_low = min(...)``. Auf dem letzten Bar entstehen bewusst keine Signale
    (kein Folge-Bar für den Close-to-Close-Exit des Runners).

    Cooldown: Nach einem erzeugten Signal auf Bar ``i`` werden die nächsten
    ``cooldown_bars`` Bars (``i+1 … i+cooldown_bars``) für neue Signale
    übersprungen. ``cooldown_bars = 0`` erlaubt ein unmittelbares Folgesignal.

    Stop-Regeln (kompatibel zur strikten ``percent_risk``-Prüfung der Engine):
        LONG:  ``stop_price = mid[i] * (1 - stop_distance_pct)`` (< mid, > 0).
        SHORT: ``stop_price = mid[i] * (1 + stop_distance_pct)`` (> mid).

    Strength:
        ``breakout_threshold_pct == 0`` -> ``strength = 1.0``.
        sonst ``strength = min(1.0, breakout_distance_pct / breakout_threshold_pct)``
        mit ``breakout_distance_pct = abs(mid[i] - breakout_level) / breakout_level``
        und ``breakout_level = prev_high`` (LONG) bzw. ``prev_low`` (SHORT).
        Da ein Signal nur jenseits der Schwelle entsteht, ist ``strength`` bei
        ``threshold > 0`` praktisch gesättigt (== 1.0); der Wert bleibt rein
        informativ. ``min_strength`` wirkt ausschließlich als Signalfilter.

    ``max_signals_per_day`` ist als optionales Feld vorhanden (Default ``None``),
    wird in dieser Phase aber NICHT erzwungen (vorbereitet für v1.1).
    """

    def __init__(
        self,
        lookback_bars: int = 12,
        stop_distance_pct: float = 0.01,
        breakout_threshold_pct: float = 0.001,
        cooldown_bars: int = 3,
        allow_short: bool = True,
        min_strength: float = 0.0,
        max_signals_per_day: int | None = None,
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
        if breakout_threshold_pct < 0.0 or breakout_threshold_pct >= 0.1:
            raise ValueError(
                "breakout_threshold_pct muss in [0, 0.1) liegen "
                f"(war {breakout_threshold_pct})"
            )
        if cooldown_bars < 0:
            raise ValueError(f"cooldown_bars muss >= 0 sein (war {cooldown_bars})")
        if min_strength < 0.0 or min_strength > 1.0:
            raise ValueError(
                f"min_strength muss in [0, 1] liegen (war {min_strength})"
            )
        if max_signals_per_day is not None and max_signals_per_day <= 0:
            raise ValueError(
                "max_signals_per_day muss None oder > 0 sein "
                f"(war {max_signals_per_day})"
            )

        self.lookback_bars = lookback_bars
        self.stop_distance_pct = stop_distance_pct
        self.breakout_threshold_pct = breakout_threshold_pct
        self.cooldown_bars = cooldown_bars
        self.allow_short = allow_short
        self.min_strength = min_strength
        self.max_signals_per_day = max_signals_per_day

    def generate_signals(self, market_data: Sequence[MarketData]) -> tuple[Signal, ...]:
        """Erzeugt thresholded Breakout-Signale mit Cooldown (rein, deterministisch).

        Entry-Indizes: ``lookback_bars <= i <= len(market_data) - 2`` — es muss
        genügend Historie für das Rückblickfenster UND ein Folge-Bar für den
        Close-to-Close-Exit existieren. Pro Bar höchstens ein Signal (LONG und
        SHORT schließen sich aus), daher keine doppelten Zeitstempel.
        """
        bars = list(market_data)
        n = len(bars)

        # Letzter ausführbarer Entry-Index (braucht Folge-Bar bei i+1).
        last_entry = n - 2
        if last_entry < self.lookback_bars:
            return ()

        mids = [_mid(bar) for bar in bars]

        signals: list[Signal] = []
        # Cooldown-Gate: vor diesem Index ist kein neues Signal erlaubt.
        next_allowed = self.lookback_bars
        long_threshold = 1.0 + self.breakout_threshold_pct
        short_threshold = 1.0 - self.breakout_threshold_pct

        for i in range(self.lookback_bars, last_entry + 1):
            if i < next_allowed:
                continue

            window = mids[i - self.lookback_bars : i]
            prev_high = max(window)
            prev_low = min(window)
            cur = mids[i]

            if cur > prev_high * long_threshold:
                direction = Direction.LONG
                breakout_level = prev_high
                stop_price = cur * (1.0 - self.stop_distance_pct)
            elif self.allow_short and cur < prev_low * short_threshold:
                direction = Direction.SHORT
                breakout_level = prev_low
                stop_price = cur * (1.0 + self.stop_distance_pct)
            else:
                continue

            # Fail-safe: kein Signal mit nicht-positivem Stop (kann bei
            # 0 < stop_distance_pct < 1 und mid > 0 nicht auftreten).
            if stop_price <= 0.0:
                continue

            # Strength rein als Signalqualität/Filter (kein Sizing-Hebel).
            if self.breakout_threshold_pct == 0.0:
                strength = 1.0
            else:
                breakout_distance_pct = abs(cur - breakout_level) / breakout_level
                strength = min(
                    1.0, breakout_distance_pct / self.breakout_threshold_pct
                )
            if strength < self.min_strength:
                continue

            signals.append(
                Signal(
                    timestamp=bars[i].timestamp,
                    direction=direction,
                    strength=strength,
                    stop_price=stop_price,
                )
            )
            # Cooldown: nächste cooldown_bars Bars überspringen.
            next_allowed = i + self.cooldown_bars + 1

        return tuple(signals)
