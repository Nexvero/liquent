"""Datenquellen-Schnittstellen für Liquent.

Spec: liquent/03_Data/Data_Source_Inventory.md

Definiert die Abstraktion über mögliche Quellen (Exchange Public API,
historische OHLCV-Dumps, Order-Book-Snapshots, Referenzkurse). In dieser
Skeleton-Phase gibt es ausschließlich Schnittstellen und Platzhalter:

- KEINE echten Netzwerk-Calls zu Börsen.
- KEINE Zugangsdaten im Code (siehe .env.example / Sicherheitshinweis der Spec).

Anforderungen aus der Spec, die jede konkrete Quelle erfüllen muss:
- Zeitstempel in UTC.
- Lücken/Ausreißer dokumentiert.
- Reproduzierbare Snapshots für Backtests.
- Trennung roh / bereinigt.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable, Protocol, runtime_checkable

from ..domain.models import MarketData, OrderBookSnapshot


@runtime_checkable
class DataSource(Protocol):
    """Abstraktion über eine Liquent-Datenquelle (nur lesend).

    Konkrete Implementierungen werden in eigenen Tasks ergänzt; das Skeleton
    legt nur die Schnittstelle fest.
    """

    def market_data(self) -> Iterable[MarketData]:
        """Liefert MarketData-Punkte in aufsteigender UTC-Zeit."""
        ...

    def order_book_snapshots(self) -> Iterable[OrderBookSnapshot]:
        """Liefert Orderbuch-Snapshots in aufsteigender UTC-Zeit."""
        ...


# Pflichtspalten des CSV-Schemas (LQ-005 Phase 3).
_REQUIRED_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")
# Preisspalten, die nicht-negativ sein müssen.
_PRICE_COLUMNS = ("open", "high", "low", "close")

# LQ-003 Phase 2: unterstützte Timeframes (v1) und Gap-Policies.
_TIMEFRAME_SECONDS = {
    "1m": 60,
    "5m": 300,
    "15m": 900,
    "1h": 3600,
}
_GAP_POLICIES = ("reject", "flag", "tolerate")


@dataclass(frozen=True)
class Gap:
    """Erkannte Lücke zwischen zwei aufeinanderfolgenden Bars (immutable).

    Zeitstempel als ISO-8601-Strings (konsistent zur String-Darstellung im
    Report); Deltas in ganzen Sekunden. ``missing_bars`` zählt die fehlenden
    vollständigen Intervalle konservativ als ``actual // expected - 1`` (für
    exakte Vielfache exakt; bei Nicht-Vielfachen abgerundet, mind. 0).
    """

    previous_timestamp: str
    current_timestamp: str
    expected_delta_seconds: int
    actual_delta_seconds: int
    missing_bars: int


def _parse_timeframe(timeframe: str | None) -> timedelta | None:
    """Mappt einen v1-Timeframe-String auf ein ``timedelta`` (fail-safe).

    ``None`` -> ``None`` (keine Gap-Erkennung). Unbekannte Werte -> ``ValueError``.
    """
    if timeframe is None:
        return None
    if timeframe not in _TIMEFRAME_SECONDS:
        raise ValueError(
            f"unbekannter timeframe {timeframe!r}; unterstützt: "
            f"{', '.join(_TIMEFRAME_SECONDS)}"
        )
    return timedelta(seconds=_TIMEFRAME_SECONDS[timeframe])


class HistoricalFileSource:
    """Datei-basierte historische Quelle für lokale OHLCV-CSV-Dumps.

    LQ-005 Phase 3. Liest reproduzierbare Backtest-Daten aus einer lokalen
    Datei (Data_Source_Inventory: "Historische OHLCV-Dumps"). Bewusst KEIN
    Netzwerk, KEINE Exchange-Anbindung, KEINE Zugangsdaten — nur Lesen einer
    bereits vorliegenden, vertrauenswürdigen Datei mit der Standardbibliothek.

    Erwartetes CSV-Schema (Kopfzeile Pflicht, Reihenfolge der Spalten egal)::

        timestamp,open,high,low,close,volume

    Validierung (fail-safe — bei Verletzung wird ``ValueError`` mit Zeilen-
    bezug geworfen, statt fehlerhafte Daten in den Backtest zu lassen):
        - alle Pflichtspalten vorhanden,
        - ``timestamp`` nicht leer und ISO-8601-parsebar (``fromisoformat``),
        - ``open/high/low/close/volume`` als ``float`` parsebar,
        - Preise (open/high/low/close) und ``volume`` nicht negativ,
        - ``high >= low``,
        - ``low <= open <= high`` und ``low <= close <= high``,
        - Zeitstempel streng aufsteigend (Duplikate und unsortierte Daten
          werden abgelehnt).

    Leere Daten (Designentscheidung): Eine Datei nur mit Kopfzeile — oder eine
    vollständig leere Datei ohne Kopfzeile — liefert eine **leere Liste**
    (kein Fehler). Der ``BacktestRunner`` behandelt leere Bars bereits stabil
    (Phase 2). Eine vorhandene Kopfzeile, der eine Pflichtspalte fehlt, ist
    hingegen ein Fehler (``ValueError``).

    Abbildung auf das Domänenmodell: ``MarketData`` führt ``bid``/``ask``
    (kein OHLC). Da der Backtest Close-to-Close rechnet, wird der validierte
    ``close`` als Referenzpreis übernommen (``bid = ask = close`` ⇒
    ``mid = close``). ``open/high/low`` werden validiert, aber nicht
    gespeichert; ``volume`` wird übernommen. Bewusst keine neue, inkompatible
    Datenstruktur (LQ-005 Phase 3, minimal-invasiv).

    Gap-Erkennung (LQ-003 Phase 2, optional, additiv): Wird ein ``timeframe``
    (z. B. ``"5m"``, ``"1h"``) gesetzt, prüft der Loader den Abstand
    aufeinanderfolgender Zeitstempel gegen das erwartete Raster. ``gap_policy``
    steuert die Reaktion: ``"reject"`` (Default) wirft bei der ersten Lücke,
    ``"flag"`` lädt und stellt die Lücken über ``gap_report()`` bereit,
    ``"tolerate"`` lädt, solange die Anzahl Lücken ``max_gaps`` nicht
    überschreitet. ``timeframe=None`` deaktiviert die Gap-Erkennung
    (bisheriges Verhalten, vollständig rückwärtskompatibel). Jede Lücke ist
    deterministisch (rein aus den Zeitstempeln berechnet).

    # TODO(spec): Instrument-/Quellen-Metadaten bleiben offen (LQ-003 Phase 3).
    """

    def __init__(
        self,
        path: str,
        timeframe: str | None = None,
        gap_policy: str = "reject",
        max_gaps: int = 0,
    ) -> None:
        self.path = path
        # Fail-safe: ungültige Konfiguration sofort bei Konstruktion ablehnen.
        self.timeframe = timeframe
        self._expected_delta = _parse_timeframe(timeframe)
        if gap_policy not in _GAP_POLICIES:
            raise ValueError(
                f"unbekannte gap_policy {gap_policy!r}; unterstützt: "
                f"{', '.join(_GAP_POLICIES)}"
            )
        self.gap_policy = gap_policy
        self.max_gaps = max_gaps
        self.gaps: tuple[Gap, ...] = ()

    def market_data(self) -> list[MarketData]:
        """Liest und validiert die CSV vollständig und gibt eine Liste zurück.

        Eager (kein Generator): Validierungsfehler treten sofort beim Aufruf
        auf, nicht erst bei verzögerter Iteration. Ergebnis ist in aufsteigender
        Zeit sortiert (per Validierung erzwungen) und damit reproduzierbar.
        Bei gesetztem ``timeframe`` werden Lücken gemäß ``gap_policy`` behandelt
        und in ``self.gaps`` festgehalten.
        """
        bars: list[MarketData] = []
        found_gaps: list[Gap] = []
        self.gaps = ()
        with open(self.path, newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)

            # Vollständig leere Datei (keine Kopfzeile) -> leere Liste, keine Gaps.
            if reader.fieldnames is None:
                return bars

            missing = [c for c in _REQUIRED_COLUMNS if c not in reader.fieldnames]
            if missing:
                raise ValueError(
                    f"{self.path}: fehlende Pflichtspalte(n): {', '.join(missing)}"
                )

            previous_ts: datetime | None = None
            for line_no, row in enumerate(reader, start=2):  # Zeile 1 = Kopfzeile
                ts = self._parse_timestamp(row.get("timestamp"), line_no)
                values = self._parse_numbers(row, line_no)
                self._validate_ohlcv(values, line_no)

                if previous_ts is not None:
                    if ts == previous_ts:
                        raise ValueError(
                            f"{self.path} (Zeile {line_no}): doppelter Zeitstempel "
                            f"{ts.isoformat()}"
                        )
                    if ts < previous_ts:
                        raise ValueError(
                            f"{self.path} (Zeile {line_no}): Daten nicht aufsteigend "
                            f"sortiert ({ts.isoformat()} < {previous_ts.isoformat()})"
                        )
                    # Gap-Erkennung nur bei gesetztem Timeframe (deterministisch).
                    if self._expected_delta is not None and ts - previous_ts != self._expected_delta:
                        gap = self._build_gap(previous_ts, ts)
                        if self.gap_policy == "reject":
                            raise ValueError(
                                f"{self.path} (Zeile {line_no}): Lücke erkannt — "
                                f"previous={gap.previous_timestamp}, "
                                f"current={gap.current_timestamp}, "
                                f"expected_delta={gap.expected_delta_seconds}s, "
                                f"actual_delta={gap.actual_delta_seconds}s"
                            )
                        found_gaps.append(gap)
                previous_ts = ts

                # Close-to-Close: close als Referenzpreis (bid = ask = close).
                bars.append(
                    MarketData(
                        timestamp=ts,
                        bid=values["close"],
                        ask=values["close"],
                        volume=values["volume"],
                    )
                )

        # tolerate: zu viele Lücken -> fail-safe ablehnen.
        if self.gap_policy == "tolerate" and len(found_gaps) > self.max_gaps:
            raise ValueError(
                f"{self.path}: {len(found_gaps)} Lücke(n) > max_gaps="
                f"{self.max_gaps} (gap_policy=tolerate)"
            )
        self.gaps = tuple(found_gaps)
        return bars

    def gap_report(self) -> tuple[Gap, ...]:
        """Liefert die beim letzten ``market_data()`` erkannten Lücken."""
        return self.gaps

    def _build_gap(self, previous_ts: datetime, current_ts: datetime) -> Gap:
        """Erzeugt ein ``Gap`` aus zwei Zeitstempeln (deterministisch)."""
        expected_s = int(self._expected_delta.total_seconds())  # type: ignore[union-attr]
        actual_s = int((current_ts - previous_ts).total_seconds())
        missing_bars = max(0, actual_s // expected_s - 1) if expected_s > 0 else 0
        return Gap(
            previous_timestamp=previous_ts.isoformat(),
            current_timestamp=current_ts.isoformat(),
            expected_delta_seconds=expected_s,
            actual_delta_seconds=actual_s,
            missing_bars=missing_bars,
        )

    def order_book_snapshots(self) -> Iterable[OrderBookSnapshot]:
        # Orderbuch-Snapshots gehören nicht zum OHLCV-CSV-Scope (Phase 3).
        raise NotImplementedError(
            "HistoricalFileSource.order_book_snapshots: OHLCV-CSV deckt nur "
            "MarketData ab (LQ-005 Phase 3); Orderbuch-Quellen folgen separat."
        )

    # ----------------------------- Hilfen ------------------------------- #
    def _parse_timestamp(self, raw: str | None, line_no: int) -> datetime:
        """Parst einen nicht-leeren ISO-8601-Zeitstempel (keine TZ-Konvertierung)."""
        value = (raw or "").strip()
        if not value:
            raise ValueError(f"{self.path} (Zeile {line_no}): leerer Zeitstempel")
        try:
            return datetime.fromisoformat(value)
        except ValueError as exc:
            raise ValueError(
                f"{self.path} (Zeile {line_no}): ungültiger ISO-8601-Zeitstempel "
                f"{value!r}"
            ) from exc

    def _parse_numbers(self, row: dict[str, str], line_no: int) -> dict[str, float]:
        """Wandelt die numerischen Pflichtfelder in float (fail-safe)."""
        values: dict[str, float] = {}
        for column in ("open", "high", "low", "close", "volume"):
            raw = (row.get(column) or "").strip()
            try:
                values[column] = float(raw)
            except ValueError as exc:
                raise ValueError(
                    f"{self.path} (Zeile {line_no}): Spalte {column!r} ist nicht "
                    f"numerisch ({raw!r})"
                ) from exc
        return values

    def _validate_ohlcv(self, values: dict[str, float], line_no: int) -> None:
        """Erzwingt die OHLCV-Invarianten (Vorzeichen, Spannen-Konsistenz)."""
        for column in _PRICE_COLUMNS:
            if values[column] < 0:
                raise ValueError(
                    f"{self.path} (Zeile {line_no}): negativer Preis in {column!r} "
                    f"({values[column]})"
                )
        if values["volume"] < 0:
            raise ValueError(
                f"{self.path} (Zeile {line_no}): negatives Volumen "
                f"({values['volume']})"
            )
        high, low = values["high"], values["low"]
        if high < low:
            raise ValueError(
                f"{self.path} (Zeile {line_no}): high < low ({high} < {low})"
            )
        if not (low <= values["open"] <= high):
            raise ValueError(
                f"{self.path} (Zeile {line_no}): open außerhalb [low, high] "
                f"({values['open']} nicht in [{low}, {high}])"
            )
        if not (low <= values["close"] <= high):
            raise ValueError(
                f"{self.path} (Zeile {line_no}): close außerhalb [low, high] "
                f"({values['close']} nicht in [{low}, {high}])"
            )
