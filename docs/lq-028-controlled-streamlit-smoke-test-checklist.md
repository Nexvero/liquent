# LQ-028 — Controlled Local Streamlit Smoke-Test Checklist

> Status: **Phase 1 — Spezifikation only.** Keine Implementierung, keine
> Codeänderung, keine Dependency-Installation, kein Streamlit-Start, keine
> Echtdaten, keine Artefakte. Research-/Backtesting-Kontext.
> **Keine** Profitabilitätsbewertung. **Keine** Handelsempfehlung.

## 1. Ausgangslage

- LQ-019 bis LQ-027 haben die Visual Preview aufgebaut, dokumentiert und als
  lokalen Checkpoint stabilisiert (siehe `docs/visual-preview-index.md` und
  `docs/lq-027-visual-preview-stabilization-checkpoint.md`).
- Die App ist **ohne Streamlit importierbar** — der Streamlit-Import erfolgt
  ausschließlich innerhalb von `main()` (try/except in
  `tools/visual_preview/app.py`).
- Streamlit ist ein **optionales Extra** `visual` (`pyproject.toml`:
  `visual = ["streamlit>=1.0"]`), keine Pflicht-Dependency.
- Es gibt einen klaren **Fallback**, wenn Streamlit nicht installiert ist:
  `python -m tools.visual_preview.app` gibt eine verständliche Meldung aus
  (kein Traceback).
- Der nächste sinnvolle Schritt ist **kein neues Feature**, sondern ein
  kontrollierter manueller Smoke-Test der lokalen UI.
- Dieser Smoke-Test darf **keine** Echtdaten, **keine** API, **keine**
  Exchange-Anbindung und **keine** Live-/Paper-Trading-Pfade nutzen.

## 2. Ziel

Eine klare, sichere Smoke-Test-Checkliste für den lokalen Streamlit-Start:

- Umgebung prüfen
- Tests ausführen
- Streamlit-Verfügbarkeit prüfen
- optionales Visual-Extra **nur manuell** installieren, falls ausdrücklich
  gewünscht
- App lokal starten
- UI-Elemente prüfen
- synthetische Datasets prüfen
- CSV-Samples prüfen
- Sicherheitsgrenzen prüfen
- keine Artefakte committen

## 3. Nicht-Ziele

- keine Implementierung
- keine Codeänderung
- keine Tooländerung
- keine automatische Installation
- keine verpflichtende Dependency
- keine Echtdaten
- keine echten CSV-Dateien
- keine Screenshots
- keine Reports
- kein Download
- keine API-Anbindung
- keine Exchange-Anbindung
- kein Broker
- kein Paper-Trading
- kein Live-Trading
- keine Orders
- kein Deployment
- keine Optimierung
- keine Parameter-Suche
- keine Profitabilitätsbewertung
- keine Trading-Empfehlung

## 4. Preconditions

Voraussetzungen vor dem Smoke-Test:

- Working Tree clean
- Branch `main` synchron mit `origin/main`
- `.venv` aktiv
- `python -m pytest` grün
- App importierbar ohne Streamlit
- Fallback ohne Streamlit stabil
- Keine CSV-/Report-/Screenshot-Artefakte im Status
- Streamlit nur optional

Befehle:

```bash
cd /opt/mcp-nexvero/liquent/
git status --short
git branch -vv
. .venv/bin/activate
python -m pytest
python - <<'PY'
import tools.visual_preview.app as app
print("import ok", hasattr(app, "main"))
PY
python -m tools.visual_preview.app || true
```

Erwartung:

- Working Tree clean
- pytest grün
- `import ok True`
- Fallback ohne Streamlit gibt klare Meldung aus, kein Traceback

## 5. Streamlit Availability Check

```bash
python - <<'PY'
import importlib.util
print("streamlit_available", importlib.util.find_spec("streamlit") is not None)
PY
```

Wenn `False`:

- kein Fehler
- erwarteter Zustand möglich (Streamlit ist optional)
- App-Fallback bleibt gültig
- lokale UI kann erst nach optionaler **manueller** Installation gestartet werden

Wenn `True`:

- Smoke-Test kann direkt mit `streamlit run ...` starten

## 6. Optional Manual Installation

Nur als **manuelle Option** dokumentiert — diese Spezifikation führt nichts aus:

```bash
pip install -e ".[visual]"
```

oder:

```bash
uv pip install -e ".[visual]"
```

Wichtig:

- Diese Spezifikation führt **keine** Installation aus.
- Installation ist **nicht** Teil automatischer Tests.
- Streamlit bleibt optional.
- Kein externer Download durch Liquent.
- Keine neue Pflichtdependency.

## 7. Local App Start

Wenn Streamlit verfügbar ist:

```bash
streamlit run tools/visual_preview/app.py
```

Erwartung:

- lokale Streamlit-App startet
- Browser öffnet lokale URL
- keine API-Keys erforderlich
- keine Login-/Auth-Anforderung
- keine Exchange-Verbindung
- keine Live-Datenquelle

## 8. Manual UI Smoke-Test Checklist

- [ ] App startet lokal
- [ ] Header "Liquent — understand liquidity" sichtbar
- [ ] Safety Banner sichtbar
- [ ] "Synthetic/local preview only" sichtbar
- [ ] "No live trading" sichtbar
- [ ] "No trading recommendation" sichtbar
- [ ] "No profitability assessment" sichtbar
- [ ] Dataset Mode auswählbar
- [ ] Synthetic dataset auswählbar
- [ ] Local CSV upload auswählbar
- [ ] micro_long auswählbar
- [ ] micro_short auswählbar
- [ ] stair_cooldown auswählbar
- [ ] Strategy v0 auswählbar
- [ ] Strategy v1 auswählbar
- [ ] v1-Parameter sichtbar (`breakout_threshold_pct`, `cooldown_bars`,
      optional `max_signals_per_day`)
- [ ] Technical Summary sichtbar
- [ ] Mid Chart sichtbar
- [ ] Signal Table sichtbar
- [ ] Strategy Metadata sichtbar
- [ ] CSV-Modus zeigt Bid/Ask-Sample
- [ ] CSV-Modus zeigt OHLCV-Sample
- [ ] CSV-Upload speichert keine Datei
- [ ] Keine Equity-/Performance-Darstellung als Entscheidungsbasis sichtbar
- [ ] Keine API-/Exchange-/Live-/Paper-Trading-Funktion sichtbar

## 9. Synthetic Dataset Smoke Tests

Nur technische Sichtprüfung — **keine** Bewertung, ob Signale gut/schlecht sind.

### micro_long

- Dataset auswählen
- Strategie v1 auswählen
- Technical Summary erscheint
- Mid Chart erscheint
- Signal Table erscheint

### micro_short

- Dataset auswählen
- `allow_short` aktiv lassen
- Signal Table zeigt Short-Signale, falls die Strategieparameter Signale
  erzeugen

### stair_cooldown

- Dataset auswählen
- v1 auswählen
- `cooldown_bars` ändern
- `max_signals_per_day` ändern
- `signals_total` verändert sich technisch sichtbar

Wichtig:

- Keine Bewertung, ob Signale gut/schlecht sind.
- Nur technische Sichtprüfung.

## 10. CSV Smoke Tests Without Persisted Files

- CSV-Samples aus UI-Codeblock kopieren (Bid/Ask und OHLCV).
- In temporäre lokale Datei **außerhalb** des Repos speichern, falls manuell nötig.
- **Nicht** ins Repo kopieren.
- **Nicht** committen.
- Upload über den Streamlit `file_uploader`.
- Prüfen:
  - Bid/Ask CSV lädt (`timestamp,bid,ask[,volume]`)
  - OHLCV CSV lädt (`timestamp,open,high,low,close[,volume]`)
  - Fehlerhinweise bei ungültigem Timestamp verständlich sind

Wichtig:

- Keine Beispiel-CSV-Datei im Repo.
- Keine echten Daten.
- Keine hochgeladenen CSVs speichern (Upload ist in-memory only).
- Keine Reportdateien.

## 11. Post-Test Cleanup

```bash
git status --short
git status --short | grep -i '\.csv' && echo "UNEXPECTED CSV FILE IN STATUS" || true
find . -maxdepth 3 -type f \( -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.csv' -o -iname '*.html' \) | sort
```

Erwartung:

- keine unerwarteten Artefakte
- keine CSV
- keine Screenshots
- keine Reports

Optional:

- Browser schließen
- Streamlit-Prozess stoppen mit `Ctrl+C`

## 12. Pass/Fail-Kriterien

Pass:

- pytest grün
- App startet lokal, falls Streamlit verfügbar/installiert
- Safety Banner sichtbar
- Synthetic Dataset Mode funktioniert
- CSV-Modus zeigt Samples
- Bid/Ask- und OHLCV-Upload funktionieren mit Sample-Daten
- Keine Artefakte im Repo
- Keine API-/Exchange-/Live-/Paper-Funktion sichtbar

Fail:

- Traceback beim Import
- Fallback ohne Streamlit bricht hart ab
- Streamlit-App startet nicht trotz installierter Dependency
- Safety-Hinweise fehlen
- CSV-Upload schreibt Dateien
- echte CSV-/Screenshot-/Report-Artefakte entstehen im Repo
- API-/Exchange-/Live-/Paper-Funktion sichtbar
- Profitabilitäts-/Trading-Empfehlung sichtbar

## 13. README/Roadmap-Auswirkung

README:

- kurzer Link:
  - Controlled Streamlit smoke-test checklist:
    `docs/lq-028-controlled-streamlit-smoke-test-checklist.md`

Visual Preview Index (`docs/visual-preview-index.md`):

- LQ-028 ergänzen:
  - Controlled local Streamlit smoke-test checklist

Roadmap (`docs/technical-status-and-roadmap.md`):

- optional kurzer Hinweis:
  - LQ-028 documents manual smoke-test procedure
  - no automation, no deployment

## 14. Tests für Phase 2

Geplante Doku-Tests:

1. LQ-028-Doku existiert.
2. Doku enthält Preconditions.
3. Doku enthält Streamlit Availability Check.
4. Doku enthält Local App Start.
5. Doku enthält Manual UI Smoke-Test Checklist.
6. Doku enthält Synthetic Dataset Smoke Tests.
7. Doku enthält CSV Smoke Tests Without Persisted Files.
8. Doku enthält Post-Test Cleanup.
9. Doku enthält Pass/Fail-Kriterien.
10. README enthält Link auf LQ-028.
11. Visual Preview Index enthält Link auf LQ-028.
12. Keine verbotene Wertungssprache (der Doku-Test scannt fragment-gebaute
    Tokens, damit die Testdatei sich nicht selbst matcht):
    - Profitabilitäts-Wertung
    - „Sieger"-Sprache
    - Garantieversprechen
    - Strategie-Superlative
    - direkte Handelsaufforderungen
    Siehe `tests/test_visual_preview_smoke_test_checklist.py`.
13. Keine echten CSV-Dateien.
14. Bestehende Tests bleiben grün.

## 15. Sicherheitsgrenzen

- No API keys.
- No exchange credentials.
- No network calls by Liquent.
- No external data download by Liquent.
- No live data source.
- No orders.
- No paper-trading connection.
- Uploaded CSV files are not saved by Liquent.
- No real CSV files committed.
- No screenshots committed.
- No report files generated by the preview.
- No profitability assessment.
- No trading recommendation.
- No equity/performance display as decision basis.

## 16. Kompatibilität

- reine Doku-/Checklist-Ergänzung.
- keine Codeänderung.
- keine tools-Änderung.
- keine pyproject-Änderung.
- keine src-Änderung.
- bestehende Visual Preview bleibt unverändert.
- bestehende Tests bleiben grün.

## 17. Offene Entscheidungspunkte

1. Soll Streamlit im Rahmen der Entwicklung wirklich installiert werden?
   **Empfehlung:** nur manuell und nach separater Freigabe.
2. Soll ein Screenshot als Nachweis erstellt werden?
   **Empfehlung:** nein, keine Artefakte committen.
3. Soll der Smoke-Test automatisiert werden?
   **Empfehlung:** nein, kein Browser-/Streamlit-E2E in dieser Phase.
4. Soll ein Release-Tag gesetzt werden?
   **Empfehlung:** nein, separate Freigabe.
5. Soll danach Runner/CostModel in der UI diskutiert werden?
   **Empfehlung:** nur mit neuer Spezifikation.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
