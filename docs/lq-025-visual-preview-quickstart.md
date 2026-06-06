# LQ-025 — Visual Preview Quickstart and First-Run Checklist

## Status

- Phase 2 implemented.
- Visual Preview is optional and local.
- Streamlit is an optional extra.
- No live trading.
- No trading recommendation.
- No profitability assessment.

## 1. Purpose

- Diese Doku zeigt, wie man die lokale Visual Preview startet.
- Sie nutzt synthetische oder lokal hochgeladene CSV-Daten.
- Sie ist ein technisches Signal-Inspektionswerkzeug.
- Keine Trading-Entscheidung, keine Ergebnisinterpretation.

## 2. Requirements

- Projektverzeichnis: `/opt/mcp-nexvero/liquent/`.
- Python-Umgebung / lokale `.venv`.
- Tests grün (`python -m pytest`).
- Optionales `visual`-Extra für Streamlit (nur nötig, wenn die UI gestartet
  wird; `dependencies = []` bleibt unverändert).

## 3. Quickstart

1. Projekt öffnen:

   ```bash
   cd /opt/mcp-nexvero/liquent/
   ```

2. Virtuelle Umgebung aktivieren:

   ```bash
   . .venv/bin/activate
   ```

3. Tests ausführen:

   ```bash
   python -m pytest
   ```

4. Fallback ohne Streamlit prüfen:

   ```bash
   python -m tools.visual_preview.app
   ```

   Erwartung: klare Meldung, dass Streamlit optional installiert werden muss —
   **kein Traceback**.

5. Optionales Visual-Extra installieren:

   ```bash
   pip install -e ".[visual]"
   # alternativ:
   uv pip install -e ".[visual]"
   ```

   Wichtig: **nicht** automatisch durch Liquent — nur manuell, wenn die lokale UI
   gestartet werden soll.

6. Visual Preview starten:

   ```bash
   streamlit run tools/visual_preview/app.py
   ```

7. Lokale Browser-App öffnet sich.

## 4. First-Run Checklist

- [ ] Working Tree clean
- [ ] `.venv` aktiv
- [ ] `python -m pytest` grün
- [ ] `python -m tools.visual_preview.app` zeigt Fallback ohne Traceback, falls
      Streamlit fehlt
- [ ] optionales Extra installiert, falls UI gestartet werden soll
- [ ] `streamlit run tools/visual_preview/app.py` gestartet
- [ ] Safety-Banner sichtbar
- [ ] synthetisches Dataset auswählbar
- [ ] Strategie v0/v1 auswählbar
- [ ] Technical Summary sichtbar
- [ ] Mid Chart sichtbar
- [ ] Signal Table sichtbar
- [ ] CSV-Modus zeigt Format-Hinweise und Sample
- [ ] CSV-Upload speichert keine Datei

## 5. UI Guide

### Dataset Mode
- Synthetic dataset
- Local CSV upload

### Synthetic datasets
- `micro_long`
- `micro_short`
- `stair_cooldown`

### Strategy
- v0 als Regressionsbasis
- v1 mit Threshold, Cooldown und `max_signals_per_day`

### Technical Summary
- `dataset`
- `strategy`
- `bars`
- `signals_total`
- first timestamp
- last timestamp

### Mid Chart
- zeigt den Mid-Preis
- zeigt technische Signalmarker, falls vorhanden
- **kein** Equity-Chart
- **keine** Performance-Darstellung

### Signal Table
- `timestamp`
- `side`
- `price`
- `stop_price`
- `strength`

### Safety Notes
- Synthetic/local preview only
- No live trading
- No trading recommendation
- No profitability assessment

## 6. CSV Quickstart

### Bid/Ask CSV

Required: `timestamp`, `bid`, `ask` · Optional: `volume`.

```csv
timestamp,bid,ask,volume
2026-01-01T00:00:00+00:00,100.0,100.5,1.0
2026-01-01T00:05:00+00:00,100.2,100.7,1.0
```

### OHLCV CSV

Required: `timestamp`, `open`, `high`, `low`, `close` · Optional: `volume`.

Mapping: `close -> bid`, `close -> ask`, `mid = close`.

```csv
timestamp,open,high,low,close,volume
2026-01-01T00:00:00+00:00,100.0,101.0,99.5,100.5,1.0
2026-01-01T00:05:00+00:00,100.5,101.2,100.1,100.8,1.0
```

Regeln:
- `timestamp` muss ISO-8601 mit Zeitzone sein.
- naive Timestamps werden abgelehnt.
- bid/ask- bzw. OHLCV-Werte müssen gültig sein.
- Upload bleibt local/in-memory.
- Liquent speichert hochgeladene CSVs nicht.
- Keine CSV-Beispieldatei wird im Repo benötigt.

## 7. Troubleshooting

### Streamlit is not installed

Symptom: `python -m tools.visual_preview.app` zeigt eine Meldung, dass Streamlit
nicht installiert ist.

Lösung:

```bash
pip install -e ".[visual]"
# oder:
uv pip install -e ".[visual]"
```

### CSV is missing required column
Lösung: Spaltennamen prüfen.

### timestamp must include timezone information
Lösung: `+00:00` ergänzen.

### ask must be greater than or equal to bid
Lösung: bid/ask-Werte prüfen.

### OHLCV validation error
Lösung:
- `high >= low`
- `low <= open <= high`
- `low <= close <= high`
- `close > 0`

> Wichtig: keine Markt-/Trading-Interpretation.

## 8. Safety Boundaries

- No API keys.
- No exchange credentials.
- No network calls by Liquent.
- No external data download by Liquent.
- No live data source.
- No orders.
- No paper-trading connection.
- Uploaded CSV files are not saved by Liquent.
- No real CSV files are committed.
- No report files.
- No profitability assessment.
- No trading recommendation.
- No equity/performance display as decision basis.

## 9. Phase 2 Implementation Status

- README compact quickstart added.
- Detailed quickstart docs added (this file).
- First-run checklist added.
- Bid/Ask and OHLCV CSV quickstart added.
- Troubleshooting added.
- Safety boundaries documented.
- No code changes.
- No tools changes.
- No src changes.
- No dependency installation.
- pytest: alle Tests grün (siehe README-Teststand).

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
