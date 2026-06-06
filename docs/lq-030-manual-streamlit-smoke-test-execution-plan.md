# LQ-030 — Manual Streamlit Smoke-Test Execution Plan

## Status

* Phase 2 implemented.
* Manual Streamlit smoke-test execution plan documented.
* No code changes.
* No dependency changes.
* No Streamlit start.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Dieses Dokument beschreibt, wie die bestehende lokale Visual Preview manuell
  geprüft werden kann.
* Es ist ein Ausführungsplan für einen späteren manuellen Smoke-Test.
* Es ist **keine** Implementierung.
* Es startet Streamlit **nicht**.
* Es ist **keine** Trading-Anleitung.

## 2. Preconditions

* Working Tree clean
* `main` synchron mit `origin/main`
* `.venv` aktiv
* pytest grün
* App importierbar ohne Streamlit
* Fallback ohne Streamlit stabil
* keine CSV-/Screenshot-/Report-Artefakte im Status
* Streamlit-Verfügbarkeit nur prüfen, nicht automatisch ändern

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
git status --short | grep -i '\.csv' && echo "UNEXPECTED CSV FILE IN STATUS" || true
git status --short | grep -Ei '\.(png|jpg|jpeg|html|pdf)$' && echo "UNEXPECTED ARTEFACT IN STATUS" || true
```

## 3. Streamlit Availability Decision

```bash
python - <<'PY'
import importlib.util
print("streamlit_available", importlib.util.find_spec("streamlit") is not None)
PY
```

Wenn `False`:

* Kein Fehler.
* UI-Smoke-Test kann nicht ausgeführt werden, bis die optionale
  Visual-Dependency installiert ist.
* Fallback-Pfad bleibt gültig.
* Installation bleibt separater Freigabepunkt.

Wenn `True`:

* UI-Smoke-Test darf lokal gestartet werden.
* Kein Commit von Artefakten.
* Keine Screenshots.
* Keine echten Daten.

## 4. Optional Manual Installation Gate

Installation ist nur nach separater Freigabe erlaubt.

Mögliche Befehle:

```bash
pip install -e ".[visual]"
```

oder:

```bash
uv pip install -e ".[visual]"
```

Regeln:

* nicht automatisch in LQ-030 Phase 2
* nur manuell und separat freigegeben
* keine neue Pflichtdependency
* keine Änderung an `pyproject.toml`
* Installation nur lokal in `.venv`
* nach Installation erneut pytest/import/fallback prüfen

## 5. Manual App Start Plan

Wenn Streamlit verfügbar ist:

```bash
streamlit run tools/visual_preview/app.py
```

Manuelle Erwartungen:

* lokale URL erscheint
* Browser öffnet UI oder URL kann manuell geöffnet werden
* kein Login
* keine API-Keys
* keine Exchange-Verbindung
* keine Live-Datenquelle
* keine Orders

## 6. UI Smoke-Test Matrix

| Area         | Check                           | Expected result                                                                                       |
| ------------ | ------------------------------- | ----------------------------------------------------------------------------------------------------- |
| Header       | App title visible               | Liquent — understand liquidity                                                                        |
| Safety       | Safety notes visible            | Synthetic/local preview only, No live trading, No trading recommendation, No profitability assessment |
| Dataset Mode | Synthetic dataset selectable    | micro_long, micro_short, stair_cooldown                                                               |
| Dataset Mode | Local CSV upload selectable     | CSV help and samples visible                                                                          |
| Strategy     | v0 selectable                   | Strategy metadata visible                                                                             |
| Strategy     | v1 selectable                   | v1 params visible                                                                                     |
| Summary      | Technical Summary visible       | dataset/strategy/bars/signals_total/first/last timestamp                                              |
| Chart        | Mid Chart visible               | mid line + signal marker series                                                                       |
| Table        | Signal Table visible            | timestamp/side/price/stop_price/strength                                                              |
| CSV          | Bid/Ask sample visible          | codeblock/sample text                                                                                 |
| CSV          | OHLCV sample visible            | codeblock/sample text                                                                                 |
| Safety       | No equity/performance UI        | no decision-basis performance display                                                                 |
| Safety       | No live/paper/exchange controls | none visible                                                                                          |

## 7. Synthetic Dataset Test Cases

### Case S1 — micro_long + v0

* Dataset: micro_long
* Strategy: v0
* Expected:
  * Summary appears
  * Chart appears
  * Signal Table appears or stays empty without error
  * No tracebacks

### Case S2 — micro_long + v1

* Dataset: micro_long
* Strategy: v1
* Parameters visible:
  * breakout_threshold_pct
  * cooldown_bars
  * max_signals_per_day
* Expected:
  * UI reacts to parameter changes
  * signals_total updates technically
  * no signal-quality assessment

### Case S3 — micro_short + v1

* Dataset: micro_short
* Expected:
  * Short signals are visible if parameters generate signals
  * no signal-quality assessment

### Case S4 — stair_cooldown + v1

* Dataset: stair_cooldown
* Parameters:
  * cooldown_bars
  * max_signals_per_day
* Expected:
  * signals_total changes technically
  * no profitability statement

## 8. CSV Test Cases Without Persisted Files

### Case C1 — Bid/Ask sample

* Copy sample from UI code block.
* If upload file is needed:
  * create it temporarily outside the repository
  * do not commit it
  * delete it after the test
* Upload through `file_uploader`.
* Expected:
  * dataset loads
  * Summary/Chart/Table update
  * no file appears in the repository

### Case C2 — OHLCV sample

* Copy sample from UI code block.
* Upload as above.
* Expected:
  * close -> bid
  * close -> ask
  * mid = close
  * no file appears in the repository

### Case C3 — invalid timestamp

* Test CSV with naive timestamp.
* Expected:
  * understandable error message
  * no traceback
  * no file saved

### Case C4 — invalid OHLCV range

* Test CSV with close outside low/high.
* Expected:
  * understandable error message
  * no traceback
  * no file saved

## 9. Post-Test Cleanup

```bash
git status --short
git status --short | grep -i '\.csv' && echo "UNEXPECTED CSV FILE IN STATUS" || true
git status --short | grep -Ei '\.(png|jpg|jpeg|html|pdf)$' && echo "UNEXPECTED ARTEFACT IN STATUS" || true
find . -maxdepth 3 -type f \( -iname '*.csv' -o -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.html' -o -iname '*.pdf' \) | sort
```

Expected:

* no unexpected artifacts
* no CSV
* no screenshots
* no reports
* Working Tree still clean, if no documentation was changed

## 10. Result Logging Template

```markdown
# Manual Streamlit Smoke-Test Result

Date:
Commit:
Tester:
Streamlit available:
Streamlit started:
Synthetic datasets checked:
CSV Bid/Ask checked:
CSV OHLCV checked:
Invalid CSV handling checked:
Artifacts created:
Issues found:
Notes:
```

Wichtig:

* Ergebnis nur neutral technisch.
* Keine Trading-/Profitabilitätsbewertung.
* Keine Screenshots erforderlich.
* Kein Report-Artefakt in Phase 2.

## 11. Pass/Fail Criteria

Pass:

* pytest grün
* App startet lokal, falls Streamlit verfügbar/installiert
* Safety Notes sichtbar
* Synthetic Dataset Mode funktioniert
* CSV-Modus zeigt Bid/Ask und OHLCV-Samples
* CSV-Upload funktioniert mit Sample-Daten
* Invalid CSV zeigt verständliche Fehlermeldung
* keine Artefakte im Repo
* keine API-/Exchange-/Live-/Paper-Funktion sichtbar

Fail:

* Import bricht
* Fallback bricht
* Streamlit-App startet trotz verfügbarer Dependency nicht
* Safety Notes fehlen
* CSV-Upload schreibt Dateien ins Repo
* echte CSV-/Screenshot-/Report-Artefakte entstehen
* API-/Exchange-/Live-/Paper-Funktion sichtbar
* Profitabilitäts-/Trading-Empfehlung sichtbar

## 12. Safety Boundaries

* No API keys.
* No exchange credentials.
* No network calls by Liquent.
* No external data download by Liquent.
* No live data source.
* No orders.
* No paper-trading connection.
* Uploaded CSV files are not saved by Liquent.
* No real CSV files committed.
* No screenshots committed.
* No report files generated by the preview.
* No profitability assessment.
* No trading recommendation.
* No equity/performance display as decision basis.

## 13. Phase 2 Implementation Status

* Execution plan finalized (this file).
* README link added.
* Visual Preview Index LQ-030 link added.
* Roadmap note added.
* Doku-tests added
  (`tests/test_visual_preview_manual_smoke_execution_plan.py`).
* No code changes.
* No tools changes.
* No src changes.
* No pyproject changes.
* No dependency installed.
* No Streamlit start.
* No real data.
* No CSV files.
* No screenshots.
* No reports.
* pytest: all tests green (see README test status).

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
