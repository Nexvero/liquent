# LQ-040 — Runner Lifecycle Implementation Decision / Pause Checkpoint

## Status

* Phase 2 implemented.
* Runner lifecycle implementation decision finalized.
* Current decision documented: pause Runner Lifecycle implementation.
* Current Runner contract remains Close-to-Close and stop_price sizing-only.
* LQ-039 remains a future specification, not an implementation trigger.
* No code changes.
* No runner changes.
* No RiskEngine changes.
* No TradeResult changes.
* No CostModel changes.
* No Metrics changes.
* No CLI changes.
* No strategy changes.
* No Visual Preview changes.
* No Streamlit start.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Dieses Dokument folgt auf LQ-039
  (`docs/lq-039-explicit-exit-reason-stop-exit-spec.md`).
* Es entscheidet bewusst, ob jetzt implementiert oder pausiert wird.
* Es schließt den aktuellen Runner-Lifecycle-Spezifikationsblock ab.
* Es ist **keine** Trading-Anleitung.
* Es bewertet **keine** Strategie.

## 2. Current Runner Lifecycle Contract

Verifiziert lesend gegen den echten Code (ohne Änderung):
`src/liquent/backtesting/runner.py`, `src/liquent/backtesting/metrics.py`,
`src/liquent/domain/models.py`.

* Der `BacktestRunner` (`BacktestRunner.run`) bleibt unverändert.
* Close-to-Close bleibt der aktuelle Contract.
* `stop_price` bleibt sizing-only.
* Stop-Exit bleibt außerhalb des aktuellen Runner-Contracts.
* `TradeResult` hat kein `exit_reason`.
* Die LQ-037-Regressionstests schützen diesen Contract
  (`tests/test_backtest_runner_regressions.py`).
* LQ-039 beschreibt nur einen möglichen Future Track.
* Visual Preview bleibt eingefroren
  (`docs/lq-034-visual-preview-documentation-freeze.md`).

## 3. Decision Options

### Option A — Pause Runner Lifecycle Track

* Kein `exit_reason`.
* Kein Stop-Exit.
* Aktueller Contract bleibt.
* Nächsten Track außerhalb des Runner-Lifecycle wählen.

Vorteile:

* Stabilität,
* keine Scope-Ausweitung,
* keine Performance-Deutung,
* bestehende Tests bleiben Referenz.

Risiken:

* Stop-Exit bleibt nur vorbereitet, nicht umgesetzt.

### Option B — Start exit_reason implementation planning

* Noch keine Implementierung.
* Separate spätere Spezifikation:
  * Data model change,
  * tests first,
  * `close_to_close` default,
  * no `stop_exit` yet.

Vorteile:

* kontrollierter Weg zu sauberer Exit-Semantik.

Risiken:

* `TradeResult`-Contract ändert sich später,
* Folgetests/Reporting/CLI betroffen.

### Option C — Implement exit_reason immediately

* Nicht empfohlen.
* Würde direkt Code ändern.

Risiken:

* zu großer Sprung,
* mögliche Regressionen,
* vorzeitige Semantikänderung.

### Option D — Implement Stop-Exit immediately

* Nicht empfohlen.
* Würde Code und Semantik ändern.

Risiken:

* größter Scope,
* Gefahr impliziter Performance-Deutung,
* Exit-Regeln noch nicht final entschieden.

## 4. Recommended Decision

Aktuelle Empfehlung:

* Option A.
* Runner Lifecycle Track pausieren.
* Aktueller Contract bleibt:
  * Close-to-Close,
  * `stop_price` sizing-only,
  * kein Stop-Exit,
  * kein `exit_reason`.
* LQ-039 bleibt als Future Spec bestehen.
* Keine Implementierung ohne neue ausdrückliche Freigabe.

Begründung:

* Die Regressionstests sichern den aktuellen Contract.
* LQ-039 bereitet die spätere Erweiterung ausreichend vor.
* Eine sofortige Implementierung hätte mehr Scope als aktuell nötig.
* Andere Tracks können jetzt fachlich wertvoller sein.

## 5. Possible Next Tracks

### Track A — RiskEngine regression hardening

* `RiskLimits` / `AccountState` / `RiskDecision` tiefer testen.
* Keine Runner-Semantik ändern.

### Track B — CostModel / Metrics hardening

* Kostenformel und Metrics stabilisieren.
* Keine Bewertungssprache.

### Track C — CLI output polish

* technische Ausgabe lesbarer machen,
* keine Reportdateien ohne bestehendes Verhalten,
* keine Empfehlung.

### Track D — Reporting / Comparison stabilization

* `BacktestExperimentSummary` / `comparison_reporting` absichern,
* `strategy_metadata` / `cost_metadata` sauber halten.

### Track E — Strategy fixtures and scenario coverage

* synthetische Fixtures erweitern,
* keine Echtdaten,
* keine Optimierung.

## 6. Conditions Before Any exit_reason Implementation

* separate Implementierungsspezifikation,
* Tests zuerst,
* `TradeResult`-Contract bewusst ändern,
* LQ-037-Regressionstests bewusst anpassen,
* Reporting-/CLI-Auswirkungen prüfen,
* Stop-Exit nicht gleichzeitig mit `exit_reason` einführen,
* Visual Preview ausgeschlossen halten,
* keine Profitabilitätsbewertung.

## 7. Safety Boundaries

* No API keys.
* No exchange credentials.
* No network calls by Liquent.
* No external data download by Liquent.
* No live data source.
* No orders.
* No paper-trading connection.
* No real CSV files committed.
* No screenshots committed.
* No report files generated in Phase 2.
* No profitability assessment.
* No trading recommendation.
* No equity/performance display as decision basis.

## 8. README/Roadmap Impact

README:

* LQ-040-Link wird ergänzt.

Roadmap:

* LQ-040 als pause/decision checkpoint ergänzt.
* Status:
  * recommended decision: pause Runner lifecycle implementation,
  * current contract remains Close-to-Close and stop_price sizing-only.

Visual Preview Index:

* bleibt unverändert,
* LQ-040 ist kein Visual-Preview-Track.

## 9. Phase 2 Implementation Status

* Runner lifecycle implementation decision finalized.
* Current Runner contract documented.
* Decision options A-D documented.
* Recommended decision documented.
* Possible next tracks documented.
* Conditions before exit_reason implementation documented.
* README link added.
* Roadmap link added.
* Doku-tests added.
* Visual Preview Index unchanged.
* No exit_reason implemented.
* No stop-exit tests implemented.
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
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).
