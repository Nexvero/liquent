# LQ-019 — Visual Dashboard / Local Preview

> Status: **Phase 1 — Spezifikation / Dokumentation.** Keine Implementierung,
> keine Code-Änderung in `src/`, keine neuen Dependencies, keine Echtdaten.
> Plant eine **lokale, rein technische** visuelle Preview für Liquent.

## 1. Ausgangslage

- Liquent hat ein starkes CLI-/Backtesting-/Reporting-Fundament: Strategien
  v0/v1, synthetische Dataset-Builder, Reporting-Metadata (`strategy_metadata`/
  `cost_metadata`), CostModel-Parameter, strukturiertes Comparison-Reporting.
- **Aktuell sichtbar** sind nur: CLI-Ausgabe, README/Doku, Markdown-Reports,
  Comparison-Markdown (als String/Testausgabe).
- Es gibt **noch keine** interaktive visuelle Preview/App.
- **Visualisierung ist rein technische Darstellung** — keine Trading-
  Entscheidung, keine Profitabilitätsbewertung.

### Verifizierte Bestandsaufnahme (bindend)

- **Es existiert bereits** `src/liquent/ui/dashboard.py` (`class Dashboard`) —
  ein **reiner Anzeige-Platzhalter** ohne Rendering-Backend, ohne
  Ausführungslogik (liefert nur Dicts: `render_liquidity`, `render_signal`,
  `render_phase_status`). Er verweist auf `liquent/08_UI/Dashboard_MVP_Spec.md`.
  → **LQ-019 ändert ihn NICHT** (src/ ist tabu) und legt die neue Preview
  **außerhalb** der Kernbibliothek ab, um Doppeldeutigkeit zu vermeiden
  (siehe §5).
- **Keine** Viz-/Web-Dependencies vorhanden (`grep` ohne Treffer für
  `streamlit/plotly/matplotlib/fastapi/flask/jinja`).
- `pyproject.toml`: `dependencies = []` (keine Pflicht-Runtime-Deps),
  `[project.optional-dependencies]` vorhanden (`dev = ["pytest>=7.0"]`) → ein
  optionales Extra für Streamlit ist sauber ergänzbar (§10).

## 2. Ziel

Eine **lokale** visuelle Preview, die zunächst **nur** mit synthetischen (oder
explizit lokalen) Daten arbeitet. Mögliche erste Ansicht:
- Dataset-Auswahl, Strategieauswahl v0/v1,
- Parameterformular (gemeinsam + v1), Kostenparameterformular,
- technische Kennzahlen, Signaltabelle,
- Comparison-Report-Anzeige,
- optional einfacher Mid-Preis-Chart mit Signalmarkern.

**Keine** Live-Daten, **keine** API, **keine** Exchange-Anbindung, **keine**
Orderfunktion.

## 3. Nicht-Ziele

keine Echtdaten automatisch laden · kein Download · keine API-/Exchange-Anbindung ·
kein Paper-Trading · kein Live-Trading · keine Orderfunktion · keine Broker-
Anbindung · kein Login/Auth · kein Deployment · keine Cloud-App · keine
Optimierung/Parameter-Suche · keine Profitabilitätsbewertung · keine Trading-
Empfehlung · **keine** Speicherung von Reports als Artefakte in Phase 2 · keine
Änderung an Strategie-/Runner-Kernlogik.

## 4. Technologieoptionen

### Option A — Streamlit
- *Pro:* sehr schnell lokal sichtbar, wenig Boilerplate, Formulare/Tabellen/
  Markdown einfach, gut für interne Preview.
- *Contra:* zusätzliche Dependency, nicht ideal als spätere Produktiv-Webapp,
  UI-Design begrenzt.

### Option B — FastAPI + HTML/Jinja
- *Pro:* näher an Web-App-Architektur, kontrollierbarer, spätere API-/Frontend-
  Trennung.
- *Contra:* mehr Boilerplate, Charts/Formulare aufwändiger, langsamere erste
  Visualisierung.

### Option C — Static HTML Generator
- *Pro:* keine laufende App, report-artige lokale HTML-Vorschau, wenig Risiko.
- *Contra:* weniger interaktiv, Parameteränderungen nicht direkt erlebbar.

> **Empfehlung: Option A — Streamlit** für die erste lokale Preview. Begründung:
> schnellste sichtbare Umsetzung, passt zur internen technischen Exploration,
> erzwingt keine Backend-Architekturentscheidung; eine echte Web-App kann später
> separat geplant werden.
>
> Da Streamlit **nicht** in `pyproject` ist, plant Phase 2 entweder ein
> **optionales Extra** (`visual = ["streamlit"]`) **oder** zunächst nur ein
> App-Skeleton + testbare Logik. **Keine Installation in Phase 1.**

## 5. Vorgeschlagener Ablageort

- Option A: `apps/visual_preview/`
- Option B: `src/liquent/ui/`
- Option C: `tools/visual_preview/`

> **Empfehlung: `tools/visual_preview/`.** Begründung: klar als lokales
> Entwickler-/Analysewerkzeug abgegrenzt, **nicht** Teil der Kernbibliothek, kein
> Produktiv-UI-Versprechen, kein Import-Durcheinander in `src/`. **Wichtig:** Das
> bestehende `src/liquent/ui/Dashboard` (Anzeige-Platzhalter) bleibt unberührt;
> die neue Preview ist davon getrennt (vermeidet Verwechslung Kernlib vs.
> Werkzeug).

Geplante Datei: `tools/visual_preview/app.py`; Start später:
`streamlit run tools/visual_preview/app.py`.

## 6. Datenquellen für Preview

Phase 2 nur **synthetische** Builder (`tests/helpers/synthetic_data.py`):
- `build_sideways_with_micro_long_breakout`,
- `build_sideways_with_micro_short_breakout`,
- `build_stair_breakout_for_cooldown`.

> Hinweis: Die Builder liegen aktuell unter `tests/helpers/`. Wenn die Preview
> sie produktiv nutzt, ist in Phase 2 zu entscheiden, ob ein kleiner
> synthetischer Daten-Helfer nach `tools/visual_preview/` dupliziert oder die
> Builder bereitgestellt werden (kein `src/`-Eingriff). Empfehlung: in
> `tools/visual_preview/` eigenständig, ohne `tests/`-Import.

Optional **später** (nicht Phase 2): lokaler CSV-Upload/-Pfad — nur lokale Datei,
**keine** API/Netzwerkpfade, **keine** Pfade ins Repo committen, **kein**
Download.

> **Empfehlung Phase 2:** nur synthetische Builder; CSV-Upload erst spätere Phase.

## 7. Funktionsumfang MVP

### Sidebar / Parameter
- Dataset: micro long / micro short / stair (cooldown).
- Strategy: v0 / v1.
- Gemeinsam: `lookback_bars`, `stop_distance_pct`, `allow_short`, `min_strength`.
- v1: `breakout_threshold_pct`, `cooldown_bars`, `max_signals_per_day`.
- CostModel: `fee_rate`, `spread`, `slippage`.

### Main View
- Titel: „Liquent — understand liquidity".
- **Safety-Banner:** „Synthetic/local preview only", „No live trading",
  „No trading recommendation".
- Technische KPIs: `signals_total` (und — falls Runner genutzt —
  `trades_total`, `approved_signals`, `rejected_signals`).
- Strategy-Metadata, Cost-Metadata.
- Signaltabelle: `timestamp`, `side`, `price/mid`, `stop_price`, `strength`.
- Comparison-Markdown: `render_comparison_markdown` optional anzeigen.

### Chart (optional)
- Einfacher Mid-Preis-Chart mit Long/Short-Signalmarkern.
- **Kein** Equity-Chart im MVP; `ending_equity` **nicht** prominent.

## 8. Backend-/Code-Nutzung

Geplante Nutzung vorhandener Bausteine: `MidBreakoutStrategy`,
`MidBreakoutStrategyV1`, synthetische Builder, `comparison_reporting`, optional
`BacktestRunner` + `RiskEngine`.

> **Empfehlung Phase 2:** für die erste Preview **nur `generate_signals`** —
> kein Runner. Weniger Risiko, keine Ergebnis-/Equity-Darstellung. Ziel ist,
> Signaldichte und Parameterauswirkung sichtbar zu machen, **nicht** Backtest-
> Ergebnisse zu interpretieren. Runner-Integration später separat.

## 9. Tests für Phase 2

UI-nahe Logik in **testbare Helfer** auslagern (z. B.
`tools/visual_preview/preview_logic.py`), ohne Streamlit-E2E:

1. Synthetic-Dataset-Mapping enthält drei Datasets.
2. Strategy-Factory erzeugt v0.
3. Strategy-Factory erzeugt v1.
4. v1-Parameter werden korrekt übernommen.
5. `max_signals_per_day` None/1/2 wirkt sichtbar auf die Signalzahl.
6. Preview-Summary enthält **keine** Profitabilitätsfelder.
7. Safety-Notes enthalten: „Synthetic/local preview only", „No live trading",
   „No trading recommendation".
8. **Kein** Netzwerk-/Download-/API-/Exchange-/Paper-/Live-Pfad (statischer Scan).
9. Bestehende Tests bleiben grün.

> Falls die Streamlit-App selbst in Phase 2 entsteht: **kein** Browser-Test;
> App importierbar halten; kritische Logik separat (in `preview_logic`) testbar.

## 10. Dependency-Frage

- Streamlit ist **nicht** in `pyproject` (verifiziert).
- Optionen:
  - **A:** `pyproject` um optionales Extra ergänzen, z. B.
    `visual = ["streamlit"]` unter `[project.optional-dependencies]`.
  - **B:** noch keine Dependency — nur App-Skeleton + testbare Logik.
- **Empfehlung:** für Phase 2 **keine neue Pflicht-Dependency**
  (`dependencies = []` bleibt). Falls Streamlit genutzt wird, als **optionales
  Extra** dokumentieren. **Keine Installation/Download** in dieser Phase.

## 11. README/Doku-Auswirkung

Nach **Phase-2-Implementierung** (nicht jetzt) README um einen kurzen Abschnitt
„Visual Preview" ergänzen:
- lokaler Entwickler-/Analysemodus, nur synthetische/lokale Daten,
- kein Live-Trading, keine Trading-Empfehlung,
- Startbefehl: `streamlit run tools/visual_preview/app.py`.

In Phase 1: **nur Spezifikation.**

## 12. Sicherheitsgrenzen für Visual Preview

keine API-Keys · keine Exchange-Credentials · keine Netzwerk-Calls · kein
Download · keine Live-Daten · keine Orders · keine Paper-Trading-Verbindung ·
keine Speicherung von Nutzerdaten · keine Report-Artefakte automatisch im Repo ·
keine Profitabilitätsbewertung · keine Empfehlungssprache.

## 13. Offene Entscheidungspunkte

1. **Streamlit oder static HTML?** → *Empfehlung: Streamlit.*
2. **Nur `generate_signals` oder Runner?** → *Empfehlung: zuerst
   `generate_signals`.*
3. **Chart direkt in Phase 2?** → *Empfehlung: einfacher Mid-Chart optional*,
   falls ohne neue komplexe Dependency möglich (Streamlit `line_chart` reicht).
4. **Streamlit Pflicht- oder optionale Dependency?** → *Empfehlung: optionales
   Extra.*
5. **CSV-Upload in Phase 2?** → *Empfehlung: nein, erst synthetische Daten.*
6. **Später echte Web-App?** → *Empfehlung: separate spätere Roadmap.*
7. **(Verifiziert) Verhältnis zum bestehenden `src/liquent/ui/Dashboard`?** →
   *Empfehlung: getrennt halten* — die neue Preview liegt in
   `tools/visual_preview/`; der Kern-Platzhalter bleibt unverändert.
8. **(Verifiziert) Builder-Quelle:** synthetische Builder liegen in
   `tests/helpers/` → in Phase 2 eigenständig in `tools/visual_preview/` halten
   (kein `tests/`-Import aus einem Werkzeug).

---

## Phase 2 Implementation Status

Umgesetzt (Empfehlung Option A/Streamlit, Ablageort `tools/visual_preview/`):

- **`tools/visual_preview/` angelegt** (`__init__.py`, `preview_logic.py`,
  `app.py`) + `tools/__init__.py` (Paket-Import). **Keine `src/`-Änderung.**
- **`preview_logic.py`** (Streamlit-frei, testbar): eigene minimale synthetische
  Builder (`build_preview_datasets` → `micro_long`/`micro_short`/`stair_cooldown`;
  **keine** `tests/helpers`-Abhängigkeit), `build_strategy` (v0/v1 mit
  CLI-konsistentem v1-only-Gating via `ValueError`), `generate_preview_summary`
  (Dataset-/Strategy-Metadaten, `signals_total`, Signaltabelle, `SAFETY_NOTES`).
  **Nur `generate_signals`, kein Runner; kein `ending_equity`.**
- **`app.py`**: optionales Streamlit-Skeleton; Streamlit-Import **nur** in
  `main()` (try/except) → bei fehlender Installation klare Meldung „Streamlit is
  not installed…", kein Traceback, keine Netzwerk-Calls, keine Dateien.
- **Keine neue Pflicht-Dependency** (`pyproject` unverändert; `dependencies = []`
  bleibt). Streamlit nur als optionaler, separat zu installierender Extra
  dokumentiert.
- **Tests:** `tests/test_visual_preview_logic.py` (11): Dataset-Mapping,
  determ. MarketData, v0/v1-Factory, v1-Parameter, v0-Gating, Summary-Struktur,
  keine Profitabilitätsfelder, `max_signals_per_day` sichtbar (None/1/2 → 5/1/2),
  **`app.py` importierbar ohne Streamlit**, statischer Pfad-Scan.
- **README** um „Visual Preview" ergänzt (lokal/optional, „Requires optional
  Streamlit installation", kein Live-Trading/keine Empfehlung).
- **pytest: 364 passed** (lokale `.venv`).

`src/`, CLI, Runner, RiskEngine, Strategien unverändert. Kein Push.

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
