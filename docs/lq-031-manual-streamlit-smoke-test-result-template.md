# LQ-031 — Manual Streamlit Smoke-Test Result Template and Execution Gate

## Status

* Phase 2 implemented.
* Execution gate documented.
* Neutral result template documented.
* No code changes.
* No dependency changes.
* No Streamlit start.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Dieses Dokument definiert, wie ein späterer manueller Streamlit-Smoke-Test
  freigegeben werden darf.
* Es definiert ein neutrales Result Template.
* Es führt **keinen** UI-Test aus.
* Es installiert **keine** Dependencies.
* Es ist **keine** Trading-Anleitung.

## 2. Execution Gate

### Gate A — Do not execute yet

* Kein Streamlit-Start.
* Kein Installationsversuch.
* LQ-031 bleibt reine Doku.
* Weiterer Schritt: Pause oder separate Freigabe.

### Gate B — Check only

* Nur prüfen:
  * pytest
  * streamlit_available
  * app import
  * fallback
* Kein `pip install`.
* Kein `streamlit run`.

### Gate C — Install optional visual extra

Nur nach ausdrücklicher Freigabe:

```bash
pip install -e ".[visual]"
```

oder:

```bash
uv pip install -e ".[visual]"
```

Danach erneut prüfen:

```bash
python -m pytest
python - <<'PY'
import importlib.util
print("streamlit_available", importlib.util.find_spec("streamlit") is not None)
PY
python - <<'PY'
import tools.visual_preview.app as app
print("import ok", hasattr(app, "main"))
PY
python -m tools.visual_preview.app || true
```

### Gate D — Execute manual UI smoke-test

Nur wenn Streamlit verfügbar und Freigabe vorhanden:

```bash
streamlit run tools/visual_preview/app.py
```

Regeln:

* Keine Screenshots committen.
* Keine CSV-Dateien committen.
* Keine Reports committen.
* Keine Echtdaten verwenden.
* Keine API-/Exchange-/Live-/Paper-Funktion.

## 3. Neutral Result Template

```markdown
# Manual Streamlit Smoke-Test Result

Date:
Commit:
Tester:
Environment:
Streamlit available:
Streamlit installed during test:
Streamlit started:
Local URL shown:
Browser opened:
Synthetic datasets checked:
- micro_long:
- micro_short:
- stair_cooldown:

Strategy checks:
- v0:
- v1:
- v1 parameters visible:

Visual checks:
- Safety banner:
- Technical Summary:
- Mid Chart:
- Signal Table:
- Strategy Metadata:
- CSV format help:

CSV checks:
- Bid/Ask sample visible:
- OHLCV sample visible:
- Bid/Ask sample upload:
- OHLCV sample upload:
- Invalid timestamp handling:
- Invalid OHLCV range handling:

Safety checks:
- No live trading controls:
- No paper trading controls:
- No exchange controls:
- No API key prompts:
- No order controls:
- No equity/performance decision-basis display:
- No trading recommendation:

Artifacts:
- CSV files created in repo:
- Screenshots created:
- Reports created:

Pass/Fail:
Issues found:
Follow-up needed:
Notes:
```

Wichtig:

* Ergebnis neutral technisch.
* Keine Signalqualitätsbewertung.
* Keine Profitabilitätsbewertung.
* Keine Trading-Empfehlung.
* Keine Screenshots erforderlich.
* Kein Result-Dokument in Phase 2.
* Result-Dokument nur nach separater Freigabe.

## 4. Result Storage Decision

### Option A — No committed result

* Ergebnis bleibt im Chat/Terminal.
* Kein neues Dokument.
* Kein Artefaktrisiko.

Empfehlung für erste Ausführung, wenn kein Nachweis benötigt wird.

### Option B — Commit neutral markdown result

* Datei z.B.:
  * `docs/manual-streamlit-smoke-test-result.md`
* Nur neutraler Text.
* Keine Screenshots.
* Keine CSV.
* Keine Reports.
* Keine Echtdaten.
* Nur nach separater Freigabe.

### Option C — Keep result outside repo

* Ergebnis lokal oder extern notieren.
* Nicht committen.
* Sinnvoll, wenn Test nur informell ist.

Empfehlung:

* Erst Gate wählen.
* Für LQ-031 Phase 2 nur Doku/Template.
* Kein Ergebnisbericht committen.

## 5. Required Pre-Execution Checks

```bash
git status --short
git branch -vv
. .venv/bin/activate
python -m pytest
python - <<'PY'
import importlib.util
print("streamlit_available", importlib.util.find_spec("streamlit") is not None)
PY
python - <<'PY'
import tools.visual_preview.app as app
print("import ok", hasattr(app, "main"))
PY
python -m tools.visual_preview.app || true
git status --short | grep -i '\.csv' && echo "UNEXPECTED CSV FILE IN STATUS" || true
git status --short | grep -Ei '\.(png|jpg|jpeg|html|pdf)$' && echo "UNEXPECTED ARTEFACT IN STATUS" || true
```

Erwartung:

* Working Tree clean
* pytest grün
* app import ok
* fallback ohne Traceback
* keine CSV-/Screenshot-/Report-Artefakte

## 6. Required Post-Execution Checks

```bash
git status --short
git status --short | grep -i '\.csv' && echo "UNEXPECTED CSV FILE IN STATUS" || true
git status --short | grep -Ei '\.(png|jpg|jpeg|html|pdf)$' && echo "UNEXPECTED ARTEFACT IN STATUS" || true
find . -maxdepth 3 -type f \( -iname '*.csv' -o -iname '*.png' -o -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.html' -o -iname '*.pdf' \) | sort
```

Erwartung:

* keine unerwarteten Artefakte
* keine CSV-Dateien im Repo
* keine Screenshots im Repo
* keine Reports im Repo
* Working Tree clean, wenn kein Result-Dokument freigegeben wurde

## 7. Pass/Fail Interpretation

Pass bedeutet:

* UI ist technisch startbar.
* erwartete Elemente sind sichtbar.
* CSV-Samples funktionieren technisch.
* Safety-Hinweise sind sichtbar.
* keine Artefakte entstehen.

Fail bedeutet:

* technischer Fehler
* fehlender Safety-Hinweis
* UI startet nicht trotz verfügbarer Dependency
* CSV-Upload erzeugt Artefakte
* Live/Paper/Exchange/API/Order-Kontrollen erscheinen
* Profitabilitäts-/Trading-Empfehlung erscheint

Keine Interpretation:

* ob Signale gut sind
* ob Strategie geeignet ist
* ob Parameter sinnvoll sind
* ob Ergebnisse profitabel wären

## 8. Safety Boundaries

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

## 9. Phase 2 Implementation Status

* Execution gate finalized.
* Neutral result template finalized.
* Result storage decision documented.
* Required pre-execution checks documented.
* Required post-execution checks documented.
* Pass/fail interpretation documented.
* README link added.
* Visual Preview Index LQ-031 link added.
* Roadmap note added.
* Doku-tests added (`tests/test_visual_preview_smoke_result_template.py`).
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
