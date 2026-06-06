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
import csv
from io import StringIO
from typing import Any, Mapping, Sequence

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


# --------------------------------------------------------------------------- #
# LQ-022: lokaler CSV-Textparser (rein, ohne Streamlit, ohne File-/Netzwerk-I/O)
# --------------------------------------------------------------------------- #

# Öffentliche CSV-Format-Konstanten (LQ-023). Keine .csv-Datei im Repo.
CSV_REQUIRED_COLUMNS: tuple[str, ...] = ("timestamp", "bid", "ask")
CSV_OPTIONAL_COLUMNS: tuple[str, ...] = ("volume",)
SAMPLE_CSV_TEMPLATE: str = (
    "timestamp,bid,ask,volume\n"
    "2026-01-01T00:00:00+00:00,100.0,100.5,1.0\n"
    "2026-01-01T00:05:00+00:00,100.2,100.7,1.0\n"
    "2026-01-01T00:10:00+00:00,100.4,100.9,1.0\n"
)

# LQ-024: zusätzliches OHLCV-Schema. open/high/low/close erforderlich; volume
# optional (Default 1.0); Mapping close -> bid = ask = close (⇒ mid = close).
_OHLCV_PRICE_COLUMNS: tuple[str, ...] = ("open", "high", "low", "close")
CSV_OHLCV_REQUIRED_COLUMNS: tuple[str, ...] = (
    "timestamp", "open", "high", "low", "close",
)
SAMPLE_OHLCV_CSV_TEMPLATE: str = (
    "timestamp,open,high,low,close,volume\n"
    "2026-01-01T00:00:00+00:00,100.0,100.6,99.8,100.4,1.0\n"
    "2026-01-01T00:05:00+00:00,100.4,100.9,100.2,100.7,1.0\n"
    "2026-01-01T00:10:00+00:00,100.7,101.2,100.5,101.0,1.0\n"
)


def _require_csv_columns(fieldnames: Sequence[str] | None) -> None:
    """Stellt sicher, dass die CSV-Pflichtspalten vorhanden sind (sonst ValueError)."""
    if not fieldnames:
        raise ValueError(
            "CSV is empty. Expected columns: " + ",".join(CSV_REQUIRED_COLUMNS) + "."
        )
    for column in CSV_REQUIRED_COLUMNS:
        if column not in fieldnames:
            raise ValueError(f"CSV is missing required column: {column}.")


def _parse_csv_timestamp(value: str | None, row: int) -> datetime:
    """Parst einen ISO-8601-Timestamp; verlangt timezone-aware (naiv -> ValueError).

    ``row`` ist die CSV-Zeilennummer inkl. Kopfzeile (Header = Zeile 1).
    """
    text = (value or "").strip()
    if not text:
        raise ValueError(f"CSV row {row}: timestamp is missing.")
    try:
        ts = datetime.fromisoformat(text)
    except ValueError:
        raise ValueError(
            f"CSV row {row}: timestamp is not a valid ISO-8601 datetime."
        ) from None
    if ts.tzinfo is None or ts.tzinfo.utcoffset(ts) is None:
        raise ValueError(
            f"CSV row {row}: timestamp must include timezone information, e.g. +00:00."
        ) from None
    return ts


def _parse_csv_positive(value: str | None, field: str, row: int) -> float:
    """Parst ein positives numerisches Feld (sonst ValueError mit Row-Hinweis)."""
    text = (value or "").strip()
    try:
        number = float(text)
    except (TypeError, ValueError):
        raise ValueError(f"CSV row {row}: {field} must be a positive number.") from None
    if number <= 0.0:
        raise ValueError(f"CSV row {row}: {field} must be a positive number.")
    return number


def _parse_csv_volume(value: str | None, row: int) -> float:
    """Parst die optionale Spalte ``volume`` (leer/fehlt -> Default ``1.0``)."""
    text = (value or "").strip()
    if not text:
        return 1.0
    try:
        return float(text)
    except (TypeError, ValueError):
        raise ValueError(
            f"CSV row {row}: volume must be numeric when provided."
        ) from None


def _detect_csv_schema(fieldnames: Sequence[str] | None) -> str:
    """Erkennt das CSV-Schema anhand der Kopfzeile: ``"bid_ask"`` oder ``"ohlcv"``.

    Reihenfolge: ``bid`` UND ``ask`` -> ``bid_ask`` (Default-Vorrang, auch bei
    Mischheader); sonst ``open/high/low/close`` vorhanden -> ``ohlcv``; sonst
    klarer Fehler. ``timestamp`` wird je Schema separat geprüft.
    """
    if not fieldnames:
        raise ValueError(
            "CSV is empty. Expected columns: " + ",".join(CSV_REQUIRED_COLUMNS) + "."
        )
    if "bid" in fieldnames and "ask" in fieldnames:
        return "bid_ask"
    if all(column in fieldnames for column in _OHLCV_PRICE_COLUMNS):
        return "ohlcv"
    # Teil-bid/ask-Header (nur bid ODER ask): als bid/ask behandeln, damit die
    # konkrete fehlende Pflichtspalte gemeldet wird (statt eines generischen
    # "not recognized").
    if "bid" in fieldnames or "ask" in fieldnames:
        return "bid_ask"
    raise ValueError(
        "CSV header not recognized. Expected either "
        "timestamp,bid,ask[,volume] or timestamp,open,high,low,close[,volume]."
    )


def _require_ohlcv_columns(fieldnames: Sequence[str]) -> None:
    """Stellt die OHLCV-Pflichtspalten sicher (timestamp + open/high/low/close)."""
    for column in CSV_OHLCV_REQUIRED_COLUMNS:
        if column not in fieldnames:
            raise ValueError(f"CSV is missing required column: {column}.")


def _parse_ohlcv_price(value: str | None, field: str, row: int) -> float:
    """Parst einen nicht-negativen OHLC-Preis (sonst ValueError mit Row-Hinweis)."""
    text = (value or "").strip()
    try:
        number = float(text)
    except (TypeError, ValueError):
        raise ValueError(
            f"CSV row {row}: {field} must be a non-negative number."
        ) from None
    if number < 0.0:
        raise ValueError(f"CSV row {row}: {field} must be a non-negative number.")
    return number


def _parse_bid_ask_rows(reader: "csv.DictReader") -> list[tuple[datetime, float, float, float]]:
    """Liest bid/ask-Datenzeilen (unverändert zum bisherigen Verhalten)."""
    parsed: list[tuple[datetime, float, float, float]] = []
    for row_number, row in enumerate(reader, start=2):
        ts = _parse_csv_timestamp(row.get("timestamp"), row_number)
        bid = _parse_csv_positive(row.get("bid"), "bid", row_number)
        ask = _parse_csv_positive(row.get("ask"), "ask", row_number)
        volume = _parse_csv_volume(row.get("volume"), row_number)
        if ask < bid:
            raise ValueError(
                f"CSV row {row_number}: ask must be greater than or equal to bid."
            )
        parsed.append((ts, bid, ask, volume))
    return parsed


def _parse_ohlcv_rows(reader: "csv.DictReader") -> list[tuple[datetime, float, float, float]]:
    """Liest OHLCV-Datenzeilen und mappt ``close -> bid = ask = close``.

    Validierung je Zeile (row-nummeriert, englisch, kein Traceback):
    timestamp tz-aware; open/high/low/close nicht-negativ; ``high >= low``;
    ``low <= open <= high`` und ``low <= close <= high``; ``close > 0``.
    """
    parsed: list[tuple[datetime, float, float, float]] = []
    for row_number, row in enumerate(reader, start=2):
        ts = _parse_csv_timestamp(row.get("timestamp"), row_number)
        open_ = _parse_ohlcv_price(row.get("open"), "open", row_number)
        high = _parse_ohlcv_price(row.get("high"), "high", row_number)
        low = _parse_ohlcv_price(row.get("low"), "low", row_number)
        close = _parse_ohlcv_price(row.get("close"), "close", row_number)
        volume = _parse_csv_volume(row.get("volume"), row_number)
        if high < low:
            raise ValueError(
                f"CSV row {row_number}: high must be greater than or equal to low."
            )
        if not (low <= open_ <= high):
            raise ValueError(f"CSV row {row_number}: open must be within [low, high].")
        if not (low <= close <= high):
            raise ValueError(f"CSV row {row_number}: close must be within [low, high].")
        if close <= 0.0:
            raise ValueError(f"CSV row {row_number}: close must be a positive number.")
        # Mapping: close als Referenzpreis (bid = ask = close => mid = close).
        parsed.append((ts, close, close, volume))
    return parsed


def build_dataset_from_csv_text(name: str, csv_text: str) -> PreviewDataset:
    """Baut ein ``PreviewDataset`` aus lokalem CSV-Text (stdlib ``csv``, kein I/O).

    Unterstützt zwei Schemata (Auto-Erkennung per Header, LQ-024):
    - **bid/ask** (Default): ``timestamp,bid,ask[,volume]`` -> ``mid=(bid+ask)/2``.
    - **OHLCV**: ``timestamp,open,high,low,close[,volume]`` ->
      ``bid = ask = close`` (⇒ ``mid = close``), konsistent zur Kernbibliothek.

    ``volume`` ist in beiden Schemata optional (Default ``1.0``). Fehler tragen
    die CSV-Zeilennummer (Header = Zeile 1, erste Datenzeile = Zeile 2) und sind
    englisch/neutral (kein Traceback). Stabile Sortierung nach ``timestamp``.
    KEINE pandas-, Datei- oder Netzwerk-Abhängigkeit.
    """
    reader = csv.DictReader(StringIO(csv_text))
    schema = _detect_csv_schema(reader.fieldnames)
    if schema == "bid_ask":
        _require_csv_columns(reader.fieldnames)
        parsed = _parse_bid_ask_rows(reader)
    else:
        _require_ohlcv_columns(reader.fieldnames)
        parsed = _parse_ohlcv_rows(reader)

    if not parsed:
        raise ValueError("CSV contains no data rows.")

    parsed.sort(key=lambda r: r[0])  # stabil (Timsort) nach timestamp
    bars = tuple(
        MarketData(timestamp=ts, bid=bid, ask=ask, volume=vol)
        for ts, bid, ask, vol in parsed
    )
    mids = tuple((bar.bid + bar.ask) / 2.0 for bar in bars)
    return PreviewDataset(
        name=name or "local_csv",
        description="Local CSV preview dataset",
        mids=mids,
        market_data=bars,
    )


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
    dataset: "str | PreviewDataset",
    strategy_key: str,
    params: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Erzeugt eine rein technische Preview-Zusammenfassung (kein Runner, kein I/O).

    ``dataset`` ist entweder ein synthetischer Dataset-Key (``str``) ODER ein
    fertiges ``PreviewDataset`` (z. B. aus ``build_dataset_from_csv_text``).

    Enthält: Dataset-Metadaten, Strategie-Metadaten, ``signals_total``, eine
    Signaltabelle (timestamp/side/price/stop_price/strength) und die
    Sicherheitshinweise. KEIN ``ending_equity``, KEINE Bewertungsfelder.
    """
    if isinstance(dataset, PreviewDataset):
        dataset = dataset
    else:
        datasets = build_preview_datasets()
        if dataset not in datasets:
            raise ValueError(f"unbekanntes dataset_key: {dataset!r}")
        dataset = datasets[dataset]

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
