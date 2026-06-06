# LQ-032 — Streamlit Optional Install Decision and No-Execution Checkpoint

## Status

* Phase 2 implemented.
* No-execution checkpoint documented.
* Recommended decision: keep no-execution state.
* No code changes.
* No dependency changes.
* No Streamlit start.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Dieses Dokument markiert den Entscheidungspunkt vor einer optionalen
  Streamlit-Installation.
* Es dokumentiert, dass ohne separate Freigabe keine Installation und kein
  UI-Start erfolgt.
* Es schützt den stabilen Stand vor unbeabsichtigten Dependency- oder
  Artefaktänderungen.
* Es ist **keine** Trading-Anleitung.

## 2. Current No-Execution State

* Tests zuletzt: 488 passed
* `main` synchron mit `origin/main`
* Working Tree clean zum Zeitpunkt des Phase-1-Starts
* `streamlit_available` zuletzt False
* app import ohne Streamlit funktioniert
* `python -m tools.visual_preview.app` zeigt Fallback ohne Traceback
* keine Dependency installiert
* kein Streamlit-Start
* kein UI-Test
* kein Result-Dokument
* keine CSV-/Screenshot-/Report-Artefakte

## 3. Decision Options

### Option A — Keep No-Execution State

* Keine Installation.
* Kein Streamlit-Start.
* Visual Preview bleibt dokumentiert, aber nicht visuell ausgeführt.
* Weiter nur Doku-/Review-Arbeit.

Vorteile:

* geringstes Risiko
* keine Dependency-Änderung
* keine lokalen Artefakte
* keine UI-Ausführungsunsicherheit

Nachteile:

* UI bleibt nicht visuell bestätigt

### Option B — Prepare Installation, but do not install yet

* Nur Installationsplan prüfen.
* Keine Befehle ausführen.
* Voraussetzungen dokumentieren.
* Separate Freigabe für Installation erforderlich.

Vorteile:

* nächste Ausführung wird vorbereitet
* weiterhin kein Dependency-Risiko

Nachteile:

* UI bleibt weiterhin nicht sichtbar geprüft

### Option C — Install optional visual extra later

Nur nach separater Freigabe:

```bash
pip install -e ".[visual]"
```

oder:

```bash
uv pip install -e ".[visual]"
```

Danach erneute Checks:

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

Vorteile:

* UI-Smoke-Test wird möglich

Risiken:

* Download/Installation in lokaler Umgebung
* Dependency-Zustand verändert sich
* mögliche lokale Fehler durch Streamlit-Umgebung

### Option D — Execute Streamlit UI later

Nur wenn Streamlit verfügbar und separat freigegeben:

```bash
streamlit run tools/visual_preview/app.py
```

Danach LQ-031 Result Template nutzen.

Vorteile:

* echte UI-Sichtprüfung

Risiken:

* lokale UI-Ausführung
* mögliche Artefakte, wenn nicht sauber kontrolliert
* Result-Dokument-Entscheidung nötig

## 4. Recommended Decision

Empfehlung für aktuellen Stand:

* **Option A — Keep No-Execution State**

Begründung:

* Die Visual Preview ist bereits dokumentiert und stabilisiert.
* Es gibt keine ausdrückliche Freigabe zur Installation.
* Streamlit ist optional und aktuell nicht verfügbar.
* Kein Grund, die lokale Umgebung ohne separate Entscheidung zu verändern.

Alternative:

* Wenn eine echte Sichtprüfung gewünscht ist, zuerst Option C separat freigeben.
* Danach LQ-033 Phase 1 — Optional Streamlit install execution plan.

Wichtig:

* Empfehlung betrifft nur Entwicklungs-/Ausführungsprozess.
* Keine Trading-Empfehlung.

## 5. Required Checks for No-Execution Checkpoint

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
* `streamlit_available` kann False sein
* app import ok
* fallback ohne Traceback
* keine CSV-/Screenshot-/Report-Artefakte
* kein Streamlit-Start

## 6. If Installation Is Later Approved

1. Vorher:
   * Working Tree clean
   * pytest grün
   * aktuelle Doku gepusht
2. Installation nur lokal:
   * `pip install -e ".[visual]"`
   * oder `uv pip install -e ".[visual]"`
3. Danach:
   * pytest erneut
   * streamlit_available erneut
   * app import erneut
   * fallback erneut
4. Erst danach:
   * separate Entscheidung für `streamlit run`
5. Keine Artefakte committen.

## 7. If UI Execution Is Later Approved

1. Streamlit verfügbar bestätigen.
2. Working Tree clean.
3. `streamlit run tools/visual_preview/app.py`
4. LQ-030 Smoke-Test-Plan durchführen.
5. LQ-031 Result Template nutzen.
6. Keine Screenshots committen.
7. Keine CSV-Dateien committen.
8. Keine Reports committen.
9. Post-Execution Checks ausführen.
10. Separat entscheiden, ob ein neutrales Result-Dokument committed wird.

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

* No-execution checkpoint finalized.
* Recommended decision documented: keep no-execution state.
* Decision options A-D documented.
* Required checks documented.
* Later installation sequence documented.
* Later UI execution sequence documented.
* README link added.
* Visual Preview Index LQ-032 link added.
* Roadmap note added.
* Doku-tests added (`tests/test_visual_preview_no_execution_checkpoint.py`).
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
