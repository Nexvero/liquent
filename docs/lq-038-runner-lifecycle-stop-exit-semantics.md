# LQ-038 — Runner Lifecycle Decision and Stop-Exit Semantics

## Status

* Phase 2 implemented.
* Runner lifecycle decision finalized.
* Current decision documented: keep Close-to-Close lifecycle and stop_price
  sizing-only.
* Stop-exit remains out of scope.
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

* Dieses Dokument ist der Entscheidungspunkt nach LQ-037.
* Es klärt, ob `stop_price` weiterhin sizing-only bleibt oder später eine
  Stop-Exit-Semantik erhält.
* Es dokumentiert die aktuelle Empfehlung.
* Es ist **keine** Trading-Anleitung.
* Es bewertet **keine** Strategie.

## 2. Verified Current Lifecycle

Verifiziert durch read-only Codelesung (`runner.py`, `metrics.py`,
`engine.py`, `domain/models.py`) und die LQ-037-Regressionstests.

> **Hinweis zu Feldnamen (Transparenz):** Das `Signal`-Objekt trägt **kein**
> `side`- und **kein** `price`-Feld. Die Richtung liegt in `direction`
> (`Direction` LONG/SHORT/FLAT); ein „side"-String existiert nur auf
> `TradeResult`.

### Signal

* Strategie erzeugt `Signal` über `generate_signals(market_data)`.
* Verifizierte `Signal`-Felder (`domain/models.py`):
  * `timestamp`,
  * `direction`,
  * `strength`,
  * `metric`,
  * `stop_price`.
* **Kein** `Signal`-`side`-Feld.
* **Kein** `Signal`-`price`-Feld.
* `side` wird später auf `TradeResult` abgebildet (aus `direction.value`).

### Risk Check

* `RiskEngine.evaluate(...)` bewertet das `Signal`.
* `RiskDecision.approved` ist `True`/`False`.
* Ablehnung über `approved=False` + `reason`.
* **Kein** separates `rejected`-Feld.
* `stop_price` wird für `percent_risk`-Sizing genutzt (`stop_distance`).

### Entry

* Ein approved `Signal` kann zu einem `TradeResult` führen.
* Entry-Felder nach realem Code:
  * `entry_time`,
  * `entry_price`,
  * `quantity`,
  * `side`.

### Exit

* Aktuell **Close-to-Close**.
* `exit_time` vorhanden.
* `exit_price` vorhanden.
* **Kein** `exit_reason`.
* **Kein** Stop-Exit.
* `stop_price` beeinflusst **nicht** den Exit-Preis.
* LQ-037 testet explizit sizing-only / kein Stop-Exit.

### Result

* `BacktestResult` enthält technische Ergebnisfelder (`trades`, `metrics`,
  `ending_equity`, `equity_curve`, `approved_signals`, `rejected_signals`,
  `experiment_id`, `parameters`).
* `BacktestResult` enthält **keine** Reporting-Metadaten wie
  `strategy_metadata`/`cost_metadata`.
* Reporting-Metadaten liegen im Reporting-Layer (`BacktestExperimentSummary`).

## 3. Decision Options

### Option A — Keep current Close-to-Close lifecycle

* `stop_price` bleibt sizing-only.
* keine Stop-Exit-Semantik.
* die bestehenden LQ-037-Regressionstests bleiben Referenz.
* niedrigstes Risiko.

### Option B — Document sizing-only permanently

* `stop_price` ist dauerhaft nur für RiskEngine-Sizing.
* keine Stop-Exit-Simulation im Runner.
* eine spätere Stop-Exit-Einführung braucht einen eigenen neuen Track.

### Option C — Introduce Stop-Exit later without changing TradeResult shape

* der Runner prüft später das Stop-Level.
* der Exit würde über die bestehenden Felder laufen.
* **kein** `exit_reason`.
* Risiko: implizite, schwerer nachvollziehbare Semantik.

### Option D — Introduce explicit exit_reason later

* `TradeResult` würde um `exit_reason` erweitert.
* mögliche Werte:
  * `close_to_close`,
  * `stop_exit`,
  * `end_of_data`.
* Datenmodelländerung, aber bessere Testbarkeit.

### Option E — Introduce Position lifecycle later

* neues oder aktiv genutztes `Position`-Modell.
* separate Entry-/Exit-Events.
* größter Scope.

## 4. Recommended Decision

Aktuelle Empfehlung:

* **Option A** beibehalten.
* Current decision:
  * Close-to-Close bleibt aktueller Contract.
  * `stop_price` bleibt sizing-only.
  * kein Stop-Exit ohne separate Spezifikation.
* Wenn Stop-Exit später gewünscht wird:
  * zuerst **Option D** separat spezifizieren,
  * explizites `exit_reason` einführen,
  * Tests vor Code,
  * keine UI-Integration,
  * keine Profitabilitätsbewertung.

Begründung:

* der aktuelle Runner ist durch LQ-037 stabil abgesichert,
* ein Stop-Exit wäre neue Semantik,
* neue Semantik sollte **nicht** implizit eingeführt werden,
* ein explizites `exit_reason` wäre sauberer als eine versteckte
  Exit-Preis-Änderung.

## 5. Impact Analysis

Mögliche Auswirkungen einer späteren Stop-Exit-Einführung.

### Runner

* die Exit-Logik müsste erweitert werden,
* die Bar-Reihenfolge müsste exakt definiert werden,
* die Same-bar-/next-bar-Regel müsste festgelegt werden,
* Long-/Short-Stop-Hit-Regeln müssten getrennt getestet werden.

### Data Model

* `TradeResult` könnte unverändert bleiben oder `exit_reason` erhalten,
* Empfehlung für später: **nicht** implizit ohne `exit_reason`.

### RiskEngine

* die RiskEngine bleibt Approval-/Sizing-Schicht,
* die Stop-Ausführung wäre Runner-Verantwortung.

### Metrics / Reporting

* technische Ergebnisse können sich ändern,
* Exit-Gründe müssten neutral dargestellt werden, falls eingeführt,
* keine Bewertungssprache.

### CLI

* keine automatische Erweiterung,
* spätere Flags nur separat spezifizieren.

### Visual Preview

* bleibt frozen,
* keine Integration in diesem Track.

## 6. Test Plan for Later Implementation

Wenn Option A/B bleibt:

* bestehende LQ-037 sizing-only Tests beibehalten,
* Close-to-Close-Verhalten stabil halten,
* `stop_price` erzeugt keinen Stop-Exit,
* kein `exit_reason` erwarten.

Wenn Option D später kommt:

* `TradeResult` hat `exit_reason`,
* `close_to_close` wird korrekt gesetzt,
* `stop_exit` wird korrekt gesetzt,
* `end_of_data` wird korrekt gesetzt,
* Long-Stop-Hit testen,
* Short-Stop-Hit testen,
* Same-bar-/next-bar-Regel testen,
* CostModel bleibt konsistent,
* Metrics bleiben deterministisch,
* keine Report-Artefakte.

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

* der LQ-038-Link wird ergänzt.

Roadmap (`docs/technical-status-and-roadmap.md`):

* LQ-038 wird unter „BacktestRunner / Trade-Lifecycle" ergänzt.
* Status:
  * lifecycle decision finalized,
  * current decision: keep Close-to-Close and `stop_price` sizing-only,
  * no Stop-Exit without separate spec.

Visual Preview Index:

* bleibt unverändert,
* LQ-038 ist **kein** Visual-Preview-Track.

## 9. Phase 2 Implementation Status

* Runner lifecycle decision finalized (this file).
* Current lifecycle documented (real identifiers only).
* Decision options A–E documented.
* Recommended decision documented.
* Impact analysis documented.
* Later-implementation test plan documented.
* Roadmap link added.
* README link added.
* Doku-tests added (`tests/test_runner_lifecycle_stop_exit_semantics_doc.py`).
* Visual Preview Index unchanged.
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
* pytest: all tests green (see README test status).

---

*Research-/Backtesting-Kontext. Keine Live-/Paper-Trading-Funktion, keine
Exchange-Anbindung, keine Profitabilitätsaussage, keine Handelsempfehlung.*
