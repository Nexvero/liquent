"""Strict, read-only pilot inspection of one frozen local CSV snapshot."""

from __future__ import annotations

import csv
import hashlib
import io
import math
from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import NamedTemporaryFile

from liquent.data.sources import HistoricalFileSource, _parse_timeframe
from liquent.research_pilot.contracts import DataInspection


_COLUMNS = ("timestamp", "open", "high", "low", "close", "volume")


def _check_pilot_rows(rows: list[list[str]]) -> None:
    """Supplement the loader, without correcting or normalizing its input."""
    if not rows:
        raise ValueError("CSV ist leer; Kopfzeile und Daten fehlen.")
    if len(rows[0]) != len(_COLUMNS) or set(rows[0]) != set(_COLUMNS):
        raise ValueError(
            "CSV-Kopfzeile muss timestamp, open, high, low, close und volume "
            "je genau einmal enthalten; zusätzliche oder mehrdeutige Spalten sind unzulässig."
        )
    if len(rows) == 1:
        raise ValueError("CSV enthält keine Datenzeilen.")
    for line, cells in enumerate(rows[1:], start=2):
        if len(cells) != len(_COLUMNS):
            raise ValueError(f"Zeile {line}: CSV-Spaltenanzahl stimmt nicht mit der Kopfzeile überein.")
        row = dict(zip(rows[0], cells))
        try:
            timestamp = datetime.fromisoformat(row["timestamp"].strip())
        except ValueError:
            raise ValueError(f"Zeile {line}: Zeitstempel fehlt oder ist kein gültiges ISO-8601-Datum.") from None
        if timestamp.utcoffset() != timedelta(0):
            raise ValueError(f"Zeile {line}: Zeitstempel benötigt eine explizite UTC-Zeitzone (Offset null).")
        for column in _COLUMNS[1:]:
            try:
                value = float(row[column])
            except ValueError:
                # Numeric syntax and negative values belong to the existing loader.
                continue
            if not math.isfinite(value):
                raise ValueError(f"Zeile {line}: {column} muss eine endliche Zahl sein.")
            if column != "volume" and value == 0:
                raise ValueError(f"Zeile {line}: Preise müssen strikt positiv sein ({column}).")


def _loader_reason(error: ValueError, snapshot_path: str) -> str:
    """Map only trusted loader prefixes; never return values or exception repr."""
    message = str(error).removeprefix(snapshot_path)
    if message.startswith(" (Zeile "):
        _, separator, message = message.partition("): ")
        if not separator:
            message = ""
    else:
        message = message.removeprefix(": ")
    for prefix, reason in (
        ("Spalte ", "OHLCV enthält einen fehlenden oder nicht numerischen Wert."),
        ("negativer Preis", "OHLCV enthält einen negativen Preis; Preise müssen strikt positiv sein."),
        ("negatives Volumen", "OHLCV enthält negatives Volumen."),
        ("high < low", "OHLCV-Preisspanne ist ungültig: high liegt unter low."),
        ("open außerhalb", "OHLCV ist ungültig: open liegt außerhalb der Preisspanne."),
        ("close außerhalb", "OHLCV ist ungültig: close liegt außerhalb der Preisspanne."),
        ("doppelter Zeitstempel", "Zeitreihe enthält einen doppelten Zeitstempel."),
        ("Daten nicht aufsteigend", "Zeitreihe ist nicht streng aufsteigend sortiert."),
    ):
        if message.startswith(prefix):
            return reason
    return "Die bestehende OHLCV-Validierung hat den Datensatz abgelehnt."


def inspect_dataset(path: Path, timeframe: str) -> DataInspection:
    """Return frozen validated bars and a JSON-compatible German quality report.

    ``rows`` counts parsed data records (zero if decoding/CSV parsing fails).
    Issues describe the first failure, not an exhaustive issue inventory.
    Unreadable files have no fingerprint; otherwise it hashes the original bytes.
    """
    report = {
        "status": "invalid",
        "dataset_fingerprint": None,
        "rows": 0,
        "period_start": None,
        "period_end": None,
        "timeframe": timeframe,
        "interval_seconds": 0,
        "issues": [],
        "gaps": [],
        "history": None,
        "warnings": [],
    }

    def invalid(reason: str) -> DataInspection:
        report["issues"] = [reason + " Prüfung beim ersten Fehler abgebrochen; weitere Fehler sind möglich."]
        return DataInspection(report=report, bars=())

    try:
        raw = path.read_bytes()
    except OSError:
        return invalid("Datensatz konnte nicht gelesen werden.")
    report["dataset_fingerprint"] = "sha256:" + hashlib.sha256(raw).hexdigest()
    try:
        interval = _parse_timeframe(timeframe)
    except (ValueError, TypeError):
        return invalid("Timeframe ist nicht unterstützt; erlaubt sind 1m, 5m, 15m und 1h.")
    if interval is None:
        return invalid("Ein expliziter Timeframe ist erforderlich.")
    report["interval_seconds"] = int(interval.total_seconds())
    try:
        rows = list(csv.reader(io.StringIO(raw.decode("utf-8"), newline=""), strict=True))
    except (UnicodeError, csv.Error):
        return invalid("CSV ist fehlerhaft oder nicht gültig UTF-8-kodiert.")
    report["rows"] = max(0, len(rows) - 1)
    try:
        _check_pilot_rows(rows)
    except ValueError as error:
        # Only our own fixed messages, never messages containing CSV cell values.
        return invalid(str(error))

    try:
        with NamedTemporaryFile(mode="wb", suffix=".csv") as snapshot:
            snapshot.write(raw)
            snapshot.flush()
            source = HistoricalFileSource(
                snapshot.name, timeframe=timeframe, gap_policy="flag", history_policy="flag"
            )
            try:
                bars = tuple(source.market_data())
            except ValueError as error:
                return invalid(_loader_reason(error, snapshot.name))
            report["gaps"] = [asdict(gap) for gap in source.gap_report()]
            history = source.history_report()
            report["history"] = asdict(history) if history is not None else None
    except OSError:
        return invalid("Der lokale Validierungs-Snapshot konnte nicht verarbeitet werden.")

    if history is not None and not history.meets_minimum:
        report["warnings"] = [
            "Historie unterschreitet die empfohlene Mindestlänge; "
            "kurze synthetische Testdaten bleiben zulässig, ihre Aussagekraft ist begrenzt."
        ]
    if report["gaps"]:
        return invalid("Zeitreihe enthält Lücken oder unregelmäßige Abstände zum konfigurierten Timeframe.")
    report["status"] = "valid"
    report["period_start"] = bars[0].timestamp.isoformat()
    report["period_end"] = bars[-1].timestamp.isoformat()
    return DataInspection(report=report, bars=bars)
