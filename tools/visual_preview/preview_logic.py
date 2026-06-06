"""Testbare, reine Logik für die lokale Visual Preview (LQ-019 Phase 2).

Lokales Entwickler-/Analysewerkzeug — KEIN Produktivcode, KEIN Streamlit-Import
hier. Vollständig deterministisch: keine Zufallswerte, keine I/O, keine Zeit aus
der Wanduhr, keine Netzwerk-, Börsen- oder Orderpfade. Nutzt ausschließlich die
bestehenden Strategieklassen aus ``liquent`` und eigene, minimale synthetische
Dataset-Builder (bewusst KEINE Abhängigkeit auf ``tests/helpers``).

Zweck: Signaldichte und Parameterauswirkung sichtbar machen — rein technisch,
KEINE Profitabilitätsbewertung, KEINE Handelsempfehlung.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Mapping

from liquent.domain.models import MarketData
from liquent.strategy import MidBreakoutStrategy, MidBreakoutStrategyV1

# Deskriptive Sicherheitshinweise (nur Anzeige; keine Empfehlung).
SAFETY_NOTES: tuple[str, ...] = (
    "Synthetic/local preview only.",
    "No live trading.",
    "No trading recommendation.",
    "No profitability assessment.",
)

_STRATEGIES = ("v0", "v1")
_V0_DEFAULTS = {"lookback_bars": 3, "stop_distance_pct": 0.05}
_V1_DEFAULTS = {
    "lookback_bars": 12,
    "stop_distance_pct": 0.01,
    "breakout_threshold_pct": 0.001,
    "cooldown_bars": 3,
}

_DEFAULT_START = datetime(2026, 1, 1, tzinfo=timezone.utc)


@dataclass(frozen=True)
class PreviewDataset:
    """Immutables, synthetisches Dataset (Mid-Serie + abgeleitete MarketData)."""

    name: str
    description: str
    mids: tuple[float, ...]
    market_data: tuple[MarketData, ...]


def _make_dataset(name: str, description: str, mids: list[float]) -> PreviewDataset:
    """Baut ein deterministisches Dataset (5-Min-Raster UTC, bid/ask = mid ∓ 0.5)."""
    bars = tuple(
        MarketData(
            timestamp=_DEFAULT_START + timedelta(minutes=5 * i),
            bid=m - 0.5,
            ask=m + 0.5,
            volume=1.0,
        )
        for i, m in enumerate(mids)
    )
    return PreviewDataset(
        name=name, description=description, mids=tuple(float(m) for m in mids),
        market_data=bars,
    )


def build_preview_datasets() -> dict[str, PreviewDataset]:
    """Liefert die synthetischen Preview-Datasets (deterministisch, gleicher UTC-Tag)."""
    return {
        "micro_long": _make_dataset(
            "micro_long",
            "Sideways phase, micro long breakout, real long breakout",
            [100.0] * 12 + [100.05, 100.0, 100.0, 102.0, 100.0],
        ),
        "micro_short": _make_dataset(
            "micro_short",
            "Sideways phase, micro short breakout, real short breakout",
            [100.0] * 12 + [99.95, 100.0, 100.0, 98.0, 100.0],
        ),
        "stair_cooldown": _make_dataset(
            "stair_cooldown",
            "Stepwise consecutive breakouts for cooldown / daily-limit preview",
            [100.0] * 12 + [101.0, 102.0, 103.0, 104.0, 105.0, 106.0],
        ),
    }


def build_strategy(
    strategy_key: str,
    *,
    lookback_bars: int | None = None,
    stop_distance_pct: float | None = None,
    breakout_threshold_pct: float | None = None,
    cooldown_bars: int | None = None,
    allow_short: bool = True,
    min_strength: float = 0.0,
    max_signals_per_day: int | None = None,
):
    """Erzeugt eine Strategie-Instanz analog zur CLI-Auflösung.

    - ``"v0"`` -> ``MidBreakoutStrategy`` (Defaults lookback 3, stop 0.05),
    - ``"v1"`` -> ``MidBreakoutStrategyV1`` (Defaults 12 / 0.01 / 0.001 / 3).

    v1-only Parameter (``breakout_threshold_pct``, ``cooldown_bars``,
    ``max_signals_per_day``) bei ``v0`` werden — konsistent zum CLI-Gating — mit
    ``ValueError`` abgelehnt. Ungültiger ``strategy_key`` ebenfalls.
    """
    if strategy_key not in _STRATEGIES:
        raise ValueError(f"strategy_key muss v0 oder v1 sein (war {strategy_key!r})")

    if strategy_key == "v0":
        if breakout_threshold_pct is not None:
            raise ValueError("breakout_threshold_pct ist nur mit strategy v1 erlaubt")
        if cooldown_bars is not None:
            raise ValueError("cooldown_bars ist nur mit strategy v1 erlaubt")
        if max_signals_per_day is not None:
            raise ValueError("max_signals_per_day ist nur mit strategy v1 erlaubt")
        return MidBreakoutStrategy(
            lookback_bars=lookback_bars if lookback_bars is not None
            else _V0_DEFAULTS["lookback_bars"],
            stop_distance_pct=stop_distance_pct if stop_distance_pct is not None
            else _V0_DEFAULTS["stop_distance_pct"],
            min_strength=min_strength,
            allow_short=allow_short,
        )

    return MidBreakoutStrategyV1(
        lookback_bars=lookback_bars if lookback_bars is not None
        else _V1_DEFAULTS["lookback_bars"],
        stop_distance_pct=stop_distance_pct if stop_distance_pct is not None
        else _V1_DEFAULTS["stop_distance_pct"],
        breakout_threshold_pct=breakout_threshold_pct if breakout_threshold_pct is not None
        else _V1_DEFAULTS["breakout_threshold_pct"],
        cooldown_bars=cooldown_bars if cooldown_bars is not None
        else _V1_DEFAULTS["cooldown_bars"],
        allow_short=allow_short,
        min_strength=min_strength,
        max_signals_per_day=max_signals_per_day,
    )


def _strategy_metadata(strategy_key: str, strategy) -> dict[str, Any]:
    """Liest die effektiven Parameter von der Instanz (deterministische Reihenfolge)."""
    if strategy_key == "v1":
        params: dict[str, Any] = {
            "lookback_bars": strategy.lookback_bars,
            "stop_distance_pct": strategy.stop_distance_pct,
            "breakout_threshold_pct": strategy.breakout_threshold_pct,
            "cooldown_bars": strategy.cooldown_bars,
            "allow_short": strategy.allow_short,
            "min_strength": strategy.min_strength,
            "max_signals_per_day": strategy.max_signals_per_day,
        }
    else:
        params = {
            "lookback_bars": strategy.lookback_bars,
            "stop_distance_pct": strategy.stop_distance_pct,
            "allow_short": strategy.allow_short,
            "min_strength": strategy.min_strength,
        }
    return {
        "family": "mid_breakout",
        "key": strategy_key,
        "name": type(strategy).__name__,
        "params": params,
    }


def build_price_rows(dataset: PreviewDataset) -> list[dict[str, Any]]:
    """Chartfreundliche Preis-Rows je Bar (rein, deterministisch, keine I/O)."""
    rows: list[dict[str, Any]] = []
    for bar in dataset.market_data:
        rows.append(
            {
                "timestamp": bar.timestamp.isoformat(),
                "mid": (bar.bid + bar.ask) / 2.0,
                "bid": bar.bid,
                "ask": bar.ask,
                "volume": bar.volume,
            }
        )
    return rows


def build_signal_rows(signals, *, mid_by_ts: Mapping[Any, float] | None = None) -> list[dict[str, Any]]:
    """Signal-Rows (timestamp/side/price/stop_price/strength).

    ``mid_by_ts`` ordnet jedem Bar-Timestamp seinen Mid-Preis zu; ohne Angabe
    bleibt ``price`` ``None`` (das Signal selbst trägt keinen Preis). Keine
    Profit-/Performance-Felder.
    """
    mid_lookup = dict(mid_by_ts or {})
    rows: list[dict[str, Any]] = []
    for sig in signals:
        rows.append(
            {
                "timestamp": sig.timestamp.isoformat(),
                "side": sig.direction.value,
                "price": mid_lookup.get(sig.timestamp),
                "stop_price": sig.stop_price,
                "strength": sig.strength,
            }
        )
    return rows


def build_chart_rows(dataset: PreviewDataset, signals) -> list[dict[str, Any]]:
    """Chart-Rows je Bar: Mid-Serie + optionale Long/Short-Marker am Signal-Bar.

    ``long_signal_price`` / ``short_signal_price`` sind nur am jeweiligen
    Signal-Bar gesetzt (= Mid dort), sonst ``None`` — so kann eine Chart-Funktion
    Marker als separate Serien zeichnen. Pro Bar höchstens ein Signal (Modell).
    """
    side_by_ts = {sig.timestamp: sig.direction.value for sig in signals}
    rows: list[dict[str, Any]] = []
    for bar in dataset.market_data:
        mid = (bar.bid + bar.ask) / 2.0
        side = side_by_ts.get(bar.timestamp)
        rows.append(
            {
                "timestamp": bar.timestamp.isoformat(),
                "mid": mid,
                "long_signal_price": mid if side == "long" else None,
                "short_signal_price": mid if side == "short" else None,
            }
        )
    return rows


def generate_preview_summary(
    dataset_key: str, strategy_key: str, params: Mapping[str, Any] | None = None
) -> dict[str, Any]:
    """Erzeugt eine rein technische Preview-Zusammenfassung (kein Runner, kein I/O).

    Enthält: Dataset-Metadaten, Strategie-Metadaten, ``signals_total``, eine
    Signaltabelle (timestamp/side/price/stop_price/strength) und die
    Sicherheitshinweise. KEIN ``ending_equity``, KEINE Bewertungsfelder.
    """
    datasets = build_preview_datasets()
    if dataset_key not in datasets:
        raise ValueError(f"unbekanntes dataset_key: {dataset_key!r}")
    dataset = datasets[dataset_key]

    p = dict(params or {})
    strategy = build_strategy(
        strategy_key,
        lookback_bars=p.get("lookback_bars"),
        stop_distance_pct=p.get("stop_distance_pct"),
        breakout_threshold_pct=p.get("breakout_threshold_pct"),
        cooldown_bars=p.get("cooldown_bars"),
        allow_short=p.get("allow_short", True),
        min_strength=p.get("min_strength", 0.0),
        max_signals_per_day=p.get("max_signals_per_day"),
    )

    signals = tuple(strategy.generate_signals(dataset.market_data))
    mid_by_ts = {bar.timestamp: (bar.bid + bar.ask) / 2.0 for bar in dataset.market_data}
    signal_rows = build_signal_rows(signals, mid_by_ts=mid_by_ts)
    bars = dataset.market_data

    technical_summary = {
        "dataset_name": dataset.name,
        "strategy_key": strategy_key,
        "bars": len(bars),
        "signals_total": len(signals),
        "first_timestamp": bars[0].timestamp.isoformat() if bars else None,
        "last_timestamp": bars[-1].timestamp.isoformat() if bars else None,
    }

    return {
        "dataset": {
            "name": dataset.name,
            "type": "synthetic",
            "bars": len(bars),
            "description": dataset.description,
        },
        "strategy": _strategy_metadata(strategy_key, strategy),
        "signals_total": len(signals),
        "signals": signal_rows,
        # LQ-021: additive, chartfreundliche Strukturen (rückwärtskompatibel).
        "price_rows": build_price_rows(dataset),
        "chart_rows": build_chart_rows(dataset, signals),
        "technical_summary": technical_summary,
        "safety_notes": list(SAFETY_NOTES),
    }
