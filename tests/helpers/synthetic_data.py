"""Wiederverwendbare, testinterne synthetische Dataset-Builder (LQ-014).

Spec: docs/lq-014-synthetic-dataset-builders.md

Konsolidiert die zuvor mehrfach duplizierten Helfer (``_bars`` / ``_MidSource``)
zu einem kleinen, deterministischen Baukasten für synthetische ``MarketData``.
Rein testintern — KEIN Produktivcode, KEINE Runtime-API. Vollständig
deterministisch: keine Zufallswerte, keine I/O, keine Zeit aus der Wanduhr.

Verifizierte Fakten:
- ``MarketData`` hat die Felder ``timestamp, bid, ask, volume`` (kein OHLC); der
  Referenzpreis ist ``mid = (bid + ask) / 2``.
- Das ``DataSource``-Protocol verlangt ``market_data()`` UND
  ``order_book_snapshots()`` — daher stellt die In-Memory-Quelle beide bereit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping, Sequence

from liquent.domain.models import MarketData

# Deterministischer Default-Start (UTC) für neue Datasets.
_DEFAULT_START = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class SyntheticDataset:
    """Immutables, synthetisches Dataset (Mid-Serie + abgeleitete MarketData)."""

    name: str
    description: str
    mids: tuple[float, ...]
    market_data: tuple[MarketData, ...]


def make_mid_series_dataset(
    name: str,
    mids: Sequence[float],
    *,
    start: datetime | None = None,
    interval_minutes: int = 5,
    description: str = "",
    half_spread: float = 0.0,
    volume: float = 1.0,
) -> SyntheticDataset:
    """Baut ein deterministisches Dataset aus einer Mid-Serie.

    Regeln:
        - ``timestamp[i] = start + i * interval_minutes`` (UTC, ohne Wanduhr),
        - ``bid = mid - half_spread``, ``ask = mid + half_spread`` -> ``mid`` ist
          stets das arithmetische Mittel; ``half_spread = 0`` ergibt ``bid == ask``,
        - ``volume`` konstant.

    Validierung (fail-safe, ValueError): ``interval_minutes > 0``,
    ``half_spread >= 0``, ``mids`` nicht leer, resultierender ``bid > 0``.
    """
    if interval_minutes <= 0:
        raise ValueError(f"interval_minutes muss > 0 sein (war {interval_minutes})")
    if half_spread < 0.0:
        raise ValueError(f"half_spread muss >= 0 sein (war {half_spread})")

    mid_values = [float(m) for m in mids]
    if not mid_values:
        raise ValueError("mids darf nicht leer sein")

    base = start if start is not None else _DEFAULT_START
    bars: list[MarketData] = []
    for i, mid in enumerate(mid_values):
        bid = mid - half_spread
        ask = mid + half_spread
        if bid <= 0.0:
            raise ValueError(
                f"bid <= 0 (mid={mid}, half_spread={half_spread}) — ungültiger Bar"
            )
        bars.append(
            MarketData(
                timestamp=base + timedelta(minutes=i * interval_minutes),
                bid=bid,
                ask=ask,
                volume=float(volume),
            )
        )

    return SyntheticDataset(
        name=name,
        description=description,
        mids=tuple(mid_values),
        market_data=tuple(bars),
    )


class InMemoryMarketDataSource:
    """In-Memory-``DataSource`` aus einer ``MarketData``-Sequenz (testintern).

    Erfüllt das ``DataSource``-Protocol strukturell: ``market_data()`` und
    ``order_book_snapshots()``. Keine Datei, kein Netzwerk. ``metadata`` und
    ``history_report`` werden nur als Attribute gesetzt, wenn explizit übergeben
    (sonst gar nicht), damit der ``BacktestRunner`` sie defensiv via ``getattr``
    überspringt — identisch zum bisherigen Verhalten ohne Metadaten.
    """

    def __init__(
        self,
        data: Sequence[MarketData],
        *,
        metadata: Mapping[str, Any] | None = None,
        history_report: Any | None = None,
    ) -> None:
        self._data: tuple[MarketData, ...] = tuple(data)
        if metadata is not None:
            self.metadata = metadata
        if history_report is not None:
            self.history_report = history_report

    def market_data(self) -> tuple[MarketData, ...]:
        return tuple(self._data)

    def order_book_snapshots(self) -> tuple[Any, ...]:
        return ()


# --------------------------------------------------------------------------- #
# Deterministische Muster-Builder (kapseln die LQ-010-Serien)
# --------------------------------------------------------------------------- #
# 12 flache Bars Historie voran (ausreichend für lookback_bars=12).

_MICRO_LONG_MIDS = [100.0] * 12 + [100.05, 100.0, 100.0, 102.0, 100.0]
_MICRO_SHORT_MIDS = [100.0] * 12 + [99.95, 100.0, 100.0, 98.0, 100.0]
_STAIR_MIDS = [100.0] * 12 + [101.0, 102.0, 103.0, 104.0, 105.0, 106.0]


def build_sideways_with_micro_long_breakout() -> SyntheticDataset:
    """Seitwärts + Mikro-Long (< Threshold) + echter Long-Breakout (+2 %)."""
    return make_mid_series_dataset(
        "sideways_with_micro_long_breakout",
        _MICRO_LONG_MIDS,
        description="Sideways phase, micro long breakout, real long breakout",
        half_spread=0.5,
    )


def build_sideways_with_micro_short_breakout() -> SyntheticDataset:
    """Seitwärts + Mikro-Short (< Threshold) + echter Short-Breakout (-2 %)."""
    return make_mid_series_dataset(
        "sideways_with_micro_short_breakout",
        _MICRO_SHORT_MIDS,
        description="Sideways phase, micro short breakout, real short breakout",
        half_spread=0.5,
    )


def build_stair_breakout_for_cooldown() -> SyntheticDataset:
    """Treppe: aufeinanderfolgende echte Breakouts (für den Cooldown-Vergleich)."""
    return make_mid_series_dataset(
        "stair_breakout_for_cooldown",
        _STAIR_MIDS,
        description="Stepwise consecutive breakouts for cooldown comparison",
        half_spread=0.5,
    )
