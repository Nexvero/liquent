"""Customer-facing readiness check; never starts research or creates an order."""
from __future__ import annotations

import os
from pathlib import Path
from tempfile import TemporaryDirectory

from .data_quality import inspect_dataset


_ALLOWED_TIMEFRAMES = {"1m", "5m", "15m", "1h"}


def check_customer_data(raw: bytes, timeframe: str, max_dataset_bytes: int = 5 * 1024 * 1024) -> dict:
    """Inspect unchanged CSV bytes privately and return the existing validator facts.

    ``short_history`` is null when the validator could not assess history.
    Readiness is technical suitability, not a strategy or order approval.
    """
    if type(max_dataset_bytes) is not int or max_dataset_bytes <= 0:
        raise ValueError("Ungültige Dateigrößengrenze.")
    if type(raw) is not bytes or not raw or len(raw) > max_dataset_bytes:
        raise ValueError("CSV muss als nicht leere Datei innerhalb der Dateigrößengrenze vorliegen.")
    if type(timeframe) is not str or timeframe not in _ALLOWED_TIMEFRAMES:
        raise ValueError("Bitte ein unterstütztes Zeitintervall wählen: 1m, 5m, 15m oder 1h.")
    try:
        with TemporaryDirectory(prefix="liquent-data-check-") as scratch:
            directory = Path(scratch)
            os.chmod(directory, 0o700)
            path = directory / "dataset.csv"
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, "wb") as stream:
                stream.write(raw)
            inspection = inspect_dataset(path, timeframe)
    except OSError:
        raise ValueError("Die lokale Datenprüfung konnte nicht abgeschlossen werden.") from None
    quality = inspection.report
    history = quality["history"]
    short_history = not history["meets_minimum"] if history is not None else None
    status = "blocked" if not inspection.valid else ("limited" if short_history else "usable")
    if status == "blocked":
        headline = "Diese Datei kann derzeit nicht verwendet werden."
        meaning = " ".join(quality["issues"])
        next_steps = ["Prüfen Sie den genannten Fehler; es erfolgt keine automatische Reparatur.",
                      "Exportieren Sie eine korrigierte UTF-8-CSV mit den sechs OHLCV-Spalten, "
                      "gültigen UTC-Zeitstempeln und festen Abständen im gewählten Intervall.",
                      "Prüfen Sie, ob Ihre Daten ohne Kalenderlücken oder Handelspausen vorliegen können. "
                      "Das Modell passt nicht automatisch zu Handelskalenderpausen und weist alle Zeitlücken ab.",
                      "Prüfen Sie die neue Datei erneut."]
    elif status == "limited":
        headline = "Die Datei ist lesbar, die Historie ist noch kurz."
        meaning = ("Die technische Datenprüfung ist bestanden. Die vorhandene Historie "
                   "unterschreitet jedoch die Empfehlung des Datenprüfers für dieses Intervall. "
                   "Das begrenzt die Aussagekraft; daraus folgt keine Strategieaussage.")
        next_steps = ["Ergänzen Sie nach Möglichkeit eine längere, lückenlose Historie und prüfen Sie sie erneut.",
                      "Prüfen Sie vor einem Research-Auftrag, ob Zeitraum und Daten für Ihre Fragestellung geeignet sind."]
    else:
        headline = "Die technische Datenbasis ist geeignet."
        meaning = ("Format, Werte und Zeitabstände erfüllen die Datenprüfung; die empfohlene "
                   "Mindesthistorie ist vorhanden. Dies bestätigt keine Strategie, Rendite, "
                   "Datenrechte oder reale Handelsausführung.")
        next_steps = ["Sie können diese technische Datenbasis für eine Research-Anfrage verwenden.",
                      "Untersuchungsumfang, unterstützte Konfigurationen, Nutzungsrechte und "
                      "Auftragsfreigaben müssen vor einer Simulation separat geprüft werden."]
    return {"schema": "liquent.data-readiness.v1", "status": status,
            "simulation_started": False, "headline": headline, "meaning": meaning,
            "next_steps": next_steps, "data_quality": quality,
            "facts": {"rows": quality["rows"], "period_start": quality["period_start"],
                      "period_end": quality["period_end"], "timeframe": quality["timeframe"],
                      "short_history": short_history, "gap_count": len(quality["gaps"])}}
