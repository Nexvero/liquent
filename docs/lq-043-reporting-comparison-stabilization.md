# LQ-043 — Reporting/Comparison Stabilization Docs + Regression Coverage

## Status

* Phase 2 implemented / finalized.
* Reporting / Comparison contract documented; regression coverage added.
* 10 ergänzende Regressionstests (`tests/test_reporting_comparison_hardening.py`).
* Bestehende Reporting-/Comparison-Tests unverändert.
* Reine Dokumentations-/Regressionsphase.
* Beschreibt den **aktuellen** Reporting-/Comparison-Code, kein Wunschdesign.
* No reporting.py changes.
* No comparison_reporting.py changes.
* No new report fields / sections / order.
* No new comparison logic.
* No ranking / evaluation / recommendation logic.
* No exit_reason.
* No Stop-Exit.
* No Runner-Lifecycle change.
* No new strategy.
* No Streamlit start.
* No dependency install.
* No file writing.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Den bestehenden Reporting-/Comparison-Contract aus dem Code dokumentieren
  (`src/liquent/backtesting/reporting.py`,
  `src/liquent/backtesting/comparison_reporting.py`).
* Ergänzende Regressionstests vorbereiten, die **bestehendes** Verhalten
  festschreiben (`tests/test_reporting_comparison_hardening.py`).
* Keine Produktionslogik ändern.
* Diese Doku ist rein deskriptiv: **keine** Bewertung, **kein** Ranking,
  **keine** Empfehlung, **keine** Profitabilitätsaussage.

## 2. Verified Current Model

Verifiziert lesend gegen den echten Code (ohne Änderung).

### Reporting Contract

`reporting.py` überführt ein `BacktestResult` in eine stabile, serialisierbare,
rein deskriptive Zusammenfassung. Alle Funktionen sind rein/deterministisch
(keine I/O, keine Wall-Clock-Zeit, kein Zufall, nur Standardbibliothek). Es
werden **keine** Dateien geschrieben (Vault-/Obsidian-Export = spätere Phase).

### BacktestExperimentSummary Contract

Quelle: `@dataclass(frozen=True) class BacktestExperimentSummary`. Pflichtfelder:
`experiment_id`, `title`, `strategy_name`, `starting_equity`, `ending_equity`,
`number_of_trades`, `approved_signals`, `rejected_signals`, `metrics`,
`parameters`, `risk_notes`, `safety_flags`. Optionale, additive Felder mit
Default `None`: `strategy_metadata`, `cost_metadata`. Immutable (`frozen=True`).

### summarize_backtest_result Contract

Reine Funktion. Verhalten:

* `strategy_name = str(parameters.get("strategy", "unknown"))` —
  Fallback `"unknown"`, wenn der Parameter fehlt.
* Safety-Flags `live_execution`, `network_calls`, `paper_trading`: aus
  `parameters` übernommen; fehlend → `False` **plus** Audit-Note
  („… were missing in parameters and defaulted to False.").
* `risk_notes` abhängig vom `sizing_mode`:
  * `percent_risk` → fünf percent_risk-spezifische Hinweise,
  * `absolute` → drei absolute-Hinweise,
  * fehlend/unbekannt → defensive Audit-Note.
* In **jedem** Modus wird zuletzt die deskriptive Note
  „Descriptive summary only; this is not investment advice." angehängt.
* `metrics`/`parameters` werden defensiv kopiert (`dict(...)`); ein nachträg-
  liches Mutieren des `BacktestResult` ändert die Summary nicht.
* `strategy_metadata`/`cost_metadata` werden über die Normalizer in feste Form
  gebracht (siehe Normalization Contract).

### summary_to_markdown Contract

Reine Funktion, deterministisch. Abschnittsreihenfolge (technischer
Output-Contract, **keine** Wertung):

1. `# Liquent Backtest Experiment`
2. `## Experiment`
3. `## Strategy` — nur falls `strategy_metadata` gesetzt (inkl.
   `### Strategy Parameters`).
4. `## Cost Model` — nur falls `cost_metadata` gesetzt.
5. `## Metrics`
6. `## Parameters`
7. `## Risk Notes`
8. `## Safety Flags`

`_format_value` formatiert `bool` als `"True"`/`"False"` (bool wird **vor** int
geprüft, da bool eine int-Subklasse ist) — nicht als `"1"`/`"0"`.

### summary_to_dict Contract

Reine Funktion. Tupel werden zu Listen, Dicts werden kopiert (JSON-/YAML-
geeignet, kein I/O). Die Schlüssel `"strategy"` bzw. `"cost_model"` erscheinen
**nur**, wenn die jeweiligen Metadaten gesetzt sind (sonst nicht enthalten).

### Comparison Reporting Contract

`comparison_reporting.py` stellt mehrere synthetische Varianten **nebeneinander**
dar — rein deskriptiv: **kein** Ranking, **keine** Bewertung, **keine**
Empfehlung, **kein** `ending_equity`. Rein/deterministisch, kein I/O.

### Normalization Contract

* `normalize_comparison` erzwingt die Top-Level-Form
  `{title, dataset, variants, notes}` und feste Feldreihenfolgen.
* `variants`: ist der Wert keine Sequenz **oder** ein `str`/`bytes`, wird er als
  „keine Varianten" (`[]`) behandelt.
* `notes`: eine echte Sequenz (kein `str`/`bytes`) wird elementweise zu `str`
  übernommen und **überschreibt** die Default-Notes; andernfalls greifen die
  Default-Notes (`Synthetic data only.`, `No profitability assessment.`,
  `No trading recommendation.`).
* `dataset`-Felder: `name` (Default `"unknown"`), `type` (Default
  `"synthetic"`), `bars` (Default `0`), `description` (Default `""`).
* je Variante: `label` (Default `variant_{index}`), `strategy`
  (`family/key/name/params`; `params` kein Mapping → `{}`), `cost_model`
  (`fee_rate/spread/slippage`, fehlend → `0.0`), `technical_results`
  (`signals_total/trades_total/approved_signals/rejected_signals`, fehlend → `0`).

### Output Contract

`render_comparison_markdown` erzeugt deterministisch die Abschnitte
`# <title>` → `## Dataset` → `## Variants` (Übersichtstabelle) →
`## Variant Parameters` (Strategy + Cost Model je Variante) → `## Notes`.
Reihenfolge und Spalten sind ein technischer Output-Contract.

### Descriptive-only Invariants

* Reihenfolge, Sortierung und Label-Konvention sind **technische**
  Output-Contracts — daraus wird **kein** Ranking, **keine** Bewertung, **keine**
  Empfehlung und **keine** Gewinn-/Verlust-Wertung abgeleitet.
* Der Vergleichsreport enthält bewusst kein `ending_equity` und keine
  Rangwertung.
* Ausdrücklich: keine Ranking-Logik, keine Bewertungslogik und keine
  Trading-Empfehlung; jede Reihenfolge ist nur ein technischer Output-Contract.

## 3. Edge-Case Table

| Funktion | Eingang | Ergebnis (aktuell) |
|---|---|---|
| `summarize_backtest_result` | `parameters` ohne `"strategy"` | `strategy_name == "unknown"` |
| `summarize_backtest_result` | fehlende Safety-Flags | `False` + Audit-Note |
| `summarize_backtest_result` | jeder `sizing_mode` | enthält „… not investment advice." |
| `summarize_backtest_result` | `strategy_metadata.params` kein Dict | `params` → `{}` |
| `summarize_backtest_result` | nachträgliche Result-Mutation | Summary unverändert (defensive Kopie) |
| `summary_to_markdown` | `bool`-Parameter | `"True"`/`"False"` (nicht `"1"`/`"0"`) |
| `summary_to_dict` | Metadaten `None` | keine `"strategy"`/`"cost_model"`-Keys |
| `normalize_comparison` | `variants` als `str`/`bytes`/Nicht-Sequenz | `[]` |
| `normalize_comparison` | `notes` als echte Sequenz | überschreibt Default-Notes |
| `normalize_comparison` | `notes` als Nicht-Sequenz/`str` | Default-Notes |
| `normalize_comparison` | `strategy.params` kein Mapping | `{}` |
| `normalize_comparison` | fehlendes `label` | `variant_{index}` |

## 4. Regression Invariants

* Reporting und Comparison sind rein/deterministisch (kein I/O, keine
  Wall-Clock-Zeit, kein Zufall).
* Additive Metadaten-Abschnitte erscheinen nur bei vorhandenen Metadaten;
  ohne Metadaten bleibt der Output backward-compatible.
* Feste Abschnitts-/Feldreihenfolgen sind stabil.
* Rein deskriptiv: keine Bewertung, kein Ranking, keine Empfehlung, keine
  Profitabilitätsaussage.
* Robuste Defaults/Guards für fehlende oder ungültige Eingaben.

## 5. Safety Boundaries

* No API keys.
* No exchange credentials.
* No network calls by Liquent.
* No external data download by Liquent.
* No live data source.
* No orders.
* No paper-trading connection.
* No file writing in this track.
* No real CSV files committed.
* No screenshots committed.
* No report files generated.
* No profitability assessment.
* No trading recommendation.
* No ranking / evaluation language.

## 6. README/Roadmap Impact

README:

* LQ-043-Link in Phase 2 ergänzt,
* Teststand aktualisiert.

Roadmap:

* LQ-043 als Reporting-/Comparison-Stabilization-/Regression-Track ergänzt
  (Phase 2).
* Status:
  * Reporting / Comparison contract documented,
  * additional regression coverage added,
  * no production logic changes,
  * no ranking / evaluation / recommendation logic,
  * Runner Lifecycle bleibt gemäß LQ-040 pausiert.

Visual Preview Index:

* nicht erweitern,
* LQ-043 ist kein Visual-Preview-Track.

## 7. Phase Plan

* **Phase 1** (abgeschlossen): Doku-Entwurf + Lückenabgleich gegen die
  bestehenden Reporting-/Comparison-Tests; Entwurf von
  `tests/test_reporting_comparison_hardening.py`. Kein Commit.
* **Phase 2** (diese): Doku finalisiert, Tests finalisiert, Doku-/Link-Test
  (`tests/test_reporting_comparison_hardening_doc.py`), README/Roadmap minimal
  verlinkt, Teststand aktualisiert. Kein Commit.
* **Phase 3**: Commit der erwarteten Dateien. Kein Push ohne separate Freigabe.

## 7a. Implementation Status (Phase 2)

* Reporting / Comparison contract documented (Verified Current Model, Output
  Contract, Normalization Contract, Descriptive-only Invariants, Edge-Case
  Table, Regression Invariants).
* 10 ergänzende Regressionstests hinzugefügt
  (`tests/test_reporting_comparison_hardening.py`) — Behavior-Lock, keine neuen
  Features.
* Bestehende Reporting-/Comparison-Tests unverändert.
* `src/liquent/backtesting/reporting.py` unverändert (keine Produktionslogik).
* `src/liquent/backtesting/comparison_reporting.py` unverändert.
* Reporting bleibt rein deskriptiv; Comparison bleibt rein deskriptiv.
* Reihenfolge ist ausschließlich technischer Output-Contract — keine Ranking-,
  Bewertungs- oder Empfehlungslogik.
* Verifiziert: `strategy_name`-Fallback `"unknown"`,
  „not investment advice"-Note in allen `risk_notes`-Modi, defensive Kopien,
  robuste Defaults/Guards in `comparison_reporting`.
* README-Link + Teststand aktualisiert.
* Roadmap-Link + Status aktualisiert.
* Doku-/Link-Test hinzugefügt: 11 Tests
  (`tests/test_reporting_comparison_hardening_doc.py`).
* Visual Preview Index unverändert.
* No exit_reason, no Stop-Exit, no new strategy, no new report fields/sections,
  no changed section order, no new comparison logic.
* No dependency installed, no Streamlit start, no real data, no artefacts.
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).

## 8. Test Plan

Ergänzende Regressionstests in `tests/test_reporting_comparison_hardening.py` —
sie schreiben ausschließlich **bestehendes** Verhalten fest (keine neuen
Features, keine Änderung bestehender Tests).

Adoptierte Lücken (echtes, bisher nicht explizit gesichertes Verhalten):

* **reporting** — `strategy_name`-Fallback `"unknown"` bei fehlendem Parameter.
* **reporting** — „… not investment advice."-Note in allen `sizing_mode`-Modi.
* **reporting** — `strategy_metadata.params` kein Dict → `{}`.
* **reporting** — vollständige Markdown-Abschnittsreihenfolge (Experiment →
  Strategy → Cost Model → Metrics → Parameters → Risk Notes → Safety Flags).
* **reporting** — defensive Kopie: Result-Mutation nach `summarize` ändert die
  Summary nicht.
* **reporting** — `_format_value` rendert `bool` als `"True"`/`"False"` im
  Markdown (nicht `"1"`/`"0"`).
* **comparison** — `variants` als `str`/Nicht-Sequenz → `[]`.
* **comparison** — benutzerdefinierte `notes` überschreiben Default-Notes.
* **comparison** — `notes` als Nicht-Sequenz/`str` → Default-Notes.
* **comparison** — `strategy.params` kein Mapping → `{}`.

Bewusst **nicht** übernommen (bereits abgedeckt):

* `summary_to_dict` ohne Metadaten ohne `"strategy"`/`"cost_model"`-Keys
  (test_no_metadata_is_backward_compatible / test_no_cost_metadata_…).
* Markdown-Teilreihenfolge Strategy < Cost Model < Metrics
  (test_strategy_and_cost_metadata_together) — LQ-043 erweitert auf die
  **vollständige** Reihenfolge.
* Metadaten-Feldreihenfolge, Determinismus, forbidden-words, fehlende
  Cost-/Result-Felder default `0.0`/`0`, `label`-Fallback `variant_{index}`,
  Default-Notes vorhanden, leere/teilweise Comparison stabil.

## 9. Non-Goals

* keine Änderung an `src/liquent/backtesting/reporting.py` (Produktionslogik),
* keine Änderung an `src/liquent/backtesting/comparison_reporting.py`,
* keine Änderung an bestehenden Reporting-/Comparison-Tests,
* keine neuen Report-Felder/-Abschnitte, keine geänderte Abschnittsreihenfolge,
* keine neue Comparison-Logik, keine Ranking-/Bewertungslogik,
* kein Schreiben echter Report-/Vault-Dateien,
* kein `exit_reason`, keine Stop-Exit-Logik, keine Runner-Lifecycle-Änderung,
* keine RiskEngine-/CostModel-/Metrics-/Strategie-/Visual-Preview-Änderung,
* keine Echtdaten, keine CSV-/Screenshot-/Report-Artefakte,
* keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 10. Deferred Topics

1. Vault-/Obsidian-Dateiexport (Schreiben echter Dateien) bleibt eine spätere
   Phase außerhalb dieses Tracks.
2. Erweiterte Serialisierung (JSON-/YAML-Datei-Ausgabe) bleibt offen.
3. Ob `ending_equity` jemals im Vergleichsreport erscheinen soll, ist bewusst
   verschoben (aktuell ausgeschlossen, rein deskriptiver Stand).
4. Fachliche Erweiterung der Report-Inhalte (zusätzliche deskriptive Felder)
   bleibt separater, ausdrücklich freizugebender Track.
