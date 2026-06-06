# LQ-033 — Optional Streamlit Install Execution Plan

## Status

* Phase 2 implemented.
* Optional Streamlit install execution plan documented.
* Installation still requires separate approval.
* No code changes.
* No dependency changes.
* No dependency installed.
* No Streamlit start.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Dieses Dokument beschreibt, wie eine spätere optionale Streamlit-Installation
  sicher vorbereitet und gegated werden kann.
* Es führt **keine** Installation aus.
* Es startet Streamlit **nicht**.
* Es ändert **keine** Dependencies.
* Es ist **keine** Trading-Anleitung.

## 2. Ausgangslage

* LQ-032 hat den No-Execution-Checkpoint dokumentiert.
* Aktuelle Empfehlung aus LQ-032: No-Execution beibehalten, solange keine
  separate Installationsfreigabe vorliegt.
* Streamlit ist optionales Extra `visual`.
* Streamlit war zuletzt nicht verfügbar (`streamlit_available = False`).
* Es wurde bisher keine Dependency installiert.
* Es wurde bisher kein Streamlit-Start durchgeführt.
* Es wurde bisher kein UI-Smoke-Test durchgeführt.
* Es wurden keine CSV-/Screenshot-/Report-Artefakte committed.

## 3. Installation Gate

Eine Installation darf nur erfolgen, wenn explizit entschieden wurde:

### Gate A — Do not install

* Keine Installation.
* Kein Streamlit-Start.
* No-Execution bleibt bestehen.
* Sicherster Standard.

### Gate B — Prepare install only

* Nur Voraussetzungen und Befehle prüfen.
* Keine Installation ausführen.
* Kein Streamlit-Start.
* Weiterhin No-Execution.

### Gate C — Install optional visual extra

Nur nach separater Freigabe:

```bash
pip install -e ".[visual]"
```

oder:

```bash
uv pip install -e ".[visual]"
```

Regeln:

* Installation nur lokal in `.venv`.
* Keine Änderung an `pyproject.toml`.
* Keine neue Pflichtdependency.
* Kein Commit von Dependency-Artefakten.
* Danach zwingend Post-Install-Checks.

### Gate D — Install and then prepare UI start

* Erst Gate C vollständig ausführen.
* Erst danach prüfen, ob UI-Start separat freigegeben wird.
* Kein automatischer `streamlit run`.

## 4. Pre-Install Checks

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

Erwartung vor Installation:

* Working Tree clean
* `main` synchron mit `origin/main`
* pytest grün
* app import ok
* fallback ohne Traceback
* keine CSV-/Screenshot-/Report-Artefakte
* `streamlit_available` kann False sein
* kein Streamlit-Start

## 5. Install Command Options

### Option 1 — pip

```bash
pip install -e ".[visual]"
```

### Option 2 — uv

```bash
uv pip install -e ".[visual]"
```

Regeln:

* Nur eine Option verwenden.
* Nicht beide ohne Grund ausführen.
* Installation ist lokaler Umgebungsschritt.
* Kein Commit von Umgebung/Cache/Lock-Artefakten.
* Kein Ändern von `pyproject.toml`.

## 6. Post-Install Checks

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
git status --short
git status --short | grep -i '\.csv' && echo "UNEXPECTED CSV FILE IN STATUS" || true
git status --short | grep -Ei '\.(png|jpg|jpeg|html|pdf)$' && echo "UNEXPECTED ARTEFACT IN STATUS" || true
```

Erwartung nach Installation:

* pytest grün
* `streamlit_available` True
* app import ok
* fallback-Verhalten kontrolliert
* keine CSV-/Screenshot-/Report-Artefakte
* Working Tree clean oder nur erwartete Doku-Änderungen, falls dokumentiert

## 7. UI Start Is Separate

Auch nach erfolgreicher Installation gilt:

* Kein automatischer UI-Start.
* `streamlit run tools/visual_preview/app.py` nur nach separater Freigabe.
* Für UI-Start LQ-030 verwenden.
* Für Ergebnisdokumentation LQ-031 verwenden.
* Keine Screenshots committen.
* Keine CSV-Dateien committen.
* Keine Reports committen.

## 8. Rollback / Cleanup Considerations

Wenn Installation Probleme macht:

* keine Code-Dateien ändern
* keine Dependency-Dateien committen
* ggf. virtuelle Umgebung neu erstellen
* ggf. Paket lokal deinstallieren
* danach erneut:
  * pytest
  * import app
  * fallback
  * git status
* keine Artefakte committen

Wichtig:

* Kein automatischer Rollback in dieser Phase.
* Nur dokumentierte manuelle Hinweise.

## 9. Safety Boundaries

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

## 10. README/Index/Roadmap-Auswirkung

README:

* optional kurzer Link auf LQ-033 Optional Streamlit Install Execution Plan

Visual Preview Index (`docs/visual-preview-index.md`):

* LQ-033 ergänzen:
  * Optional Streamlit install execution plan

Roadmap (`docs/technical-status-and-roadmap.md`):

* optionaler Hinweis:
  * optional Streamlit install plan documented; installation still requires
    separate approval

## 11. Tests für Phase 2

Geplante Doku-Tests:

1. LQ-033-Doku existiert.
2. Doku enthält Installation Gate.
3. Doku enthält Gate A.
4. Doku enthält Gate B.
5. Doku enthält Gate C.
6. Doku enthält Gate D.
7. Doku enthält Pre-Install Checks.
8. Doku enthält Install Command Options.
9. Doku enthält Post-Install Checks.
10. Doku enthält UI Start Is Separate.
11. Doku enthält Rollback / Cleanup Considerations.
12. README enthält LQ-033-Link, falls ergänzt.
13. Visual Preview Index enthält LQ-033-Link.
14. Roadmap enthält LQ-033-Link oder Install-Plan-Hinweis.
15. Keine verbotene Wertungssprache (der Doku-Test scannt fragment-gebaute
    Tokens, damit die Testdatei sich nicht selbst matcht):
    - Profitabilitäts-Wertung
    - „Sieger"-Sprache
    - Garantieversprechen
    - Strategie-Superlative
    - direkte Handelsaufforderungen
16. Keine echten CSV-/Screenshot-/Report-Artefakte.
17. Bestehende Tests bleiben grün.

## 12. Kompatibilität

* reine Doku-/Install-Plan-Ergänzung.
* keine Codeänderung.
* keine tools-Änderung.
* keine pyproject-Änderung.
* keine src-Änderung.
* bestehende Visual Preview bleibt unverändert.
* bestehende Tests bleiben grün.
* kein Streamlit-Start.
* keine Installation.

## 13. Offene Entscheidungspunkte

1. Soll Gate A beibehalten werden?
2. Soll Gate C wirklich freigegeben werden?
3. Soll pip oder uv verwendet werden?
4. Soll danach ein UI-Start erfolgen?
5. Soll ein Result-Dokument erstellt werden?
6. Soll die Visual Preview danach pausieren oder erweitert werden?

## 14. Phase 2 Implementation Status

* Optional install execution plan finalized (this file).
* Installation gate A-D documented.
* Pre-install checks documented.
* Install command options documented.
* Post-install checks documented.
* UI start kept separate.
* Rollback / cleanup considerations documented.
* README link added.
* Visual Preview Index LQ-033 link added.
* Roadmap note added.
* Doku-tests added (`tests/test_visual_preview_optional_install_plan.py`).
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
