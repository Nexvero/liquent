# LQ-036 — BacktestRunner Regression Test Plan

## Status

* Phase 2 implemented.
* BacktestRunner regression test plan finalized.
* Existing Runner/RiskEngine/CostModel/Metrics/Reporting behavior documented.
* Regression test groups documented.
* No runner regression tests implemented in Phase 2.
* No code changes.
* No runner changes.
* No RiskEngine changes.
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

* Dieses Dokument definiert den Regressionstest-Plan für den bestehenden
  `BacktestRunner`-Stack.
* Es folgt auf LQ-035
  (`docs/lq-035-backtest-runner-trade-lifecycle-integration.md`).
* Es plant Tests, ohne sie in Phase 2 umzusetzen.
* Es schützt den bestehenden Vertrag (Runner/Risk/Cost/Metrics/Reporting) vor
  unbeabsichtigten Änderungen.
* Es ist **keine** Trading-Anleitung und bewertet **keine** Strategie.

## 2. Verified Current State

Verifiziert durch read-only Codelesung (LQ-036 Phase 1, in Phase 2 erneut
geprüft). Feld-/Methodennamen sind exakt nach Quelltext benannt.

> **Hinweis zu abweichenden Namen (Transparenz):** Die Task-Vorlage nannte
> einige Feldnamen, die im Code so **nicht** existieren. Diese Doku dokumentiert
> ausschließlich die tatsächlich vorhandenen Felder und markiert die
> Abweichungen ausdrücklich, damit spätere Regressionstests keine falschen
> Annahmen prüfen.

### BacktestRunner

* Pfad: `src/liquent/backtesting/runner.py`.
* Klasse: `BacktestRunner`.
* Methode: `run(self) -> BacktestResult`.
* nutzt `source.market_data()` (Bars; defensiv zusätzlich `metadata` und
  `history_report`, falls die Quelle sie trägt).
* nutzt `strategy.generate_signals(...)`; die Rückgabe wird über
  `_resolve_signals(...)` fail-safe validiert und Entry-Bars zugeordnet.
* gibt `BacktestResult` zurück.
* **Risk-First (verifiziert):** jedes ausführbare Signal MUSS durch
  `risk_engine.evaluate(signal, account_state, reference_price=entry_price)`.
* **Close-to-Close (verifiziert):** pro ausführbarem Signal genau ein Trade;
  Entry = Mid des Signal-Bars, Exit = Mid des Folge-Bars (`duration_bars=1`).
* **kein** separates Order-Modell; `Position` (in `domain/models.py`) wird im
  Runner **nicht** als zentrales Lifecycle-Objekt genutzt.

### BacktestResult

Exakt vorhandene Felder (frozen dataclass, alle Pflicht):

* `experiment_id: str` (deterministischer SHA-256 über skalare Parameter; keine
  Wall-Clock, kein Zufall).
* `number_of_trades: int`.
* `approved_signals: int`.
* `rejected_signals: int`.
* `starting_equity: float`.
* `ending_equity: float`.
* `equity_curve: tuple[float, ...]` (beginnt mit `starting_equity`).
* `metrics: dict[str, float]`.
* `trades: tuple[TradeResult, ...]`.
* `parameters: dict[str, str | int | float | bool]` (nur skalare Werte).

Wichtig:

* **Kein** `generated_at` auf `BacktestResult`.
* **Kein** `strategy_metadata` auf `BacktestResult`.
* **Kein** `cost_metadata` auf `BacktestResult`.
* Diese Reporting-Metadaten liegen im **Reporting-Layer** auf
  `BacktestExperimentSummary` (`reporting.py`), nicht auf `BacktestResult`.

### TradeResult

Exakt vorhandene Felder (frozen dataclass, `metrics.py`):

* `entry_price: float`.
* `exit_price: float`.
* `quantity: float` (>= 0; der Runner übergibt `decision.size` als `quantity`).
* `side: str` (`"long"` | `"short"`; validiert in `__post_init__`).
* `gross_pnl: float`.
* `costs: float`.
* `net_pnl: float` (maßgeblich für Metriken).
* `r_multiple: float` (Proxy `net_pnl/size`).
* `duration_bars: int` (im Runner stets `1`).
* `entry_time: str | None` (ISO-8601-UTC, aus `timestamp.isoformat()`).
* `exit_time: str | None` (ISO-8601-UTC).

Wichtig:

* **Kein** `exit_reason` auf `TradeResult`.
* **Kein** `opened_at`/`closed_at`; die realen Namen sind
  `entry_time`/`exit_time`.

### RiskEngine

* `RiskLimits` (frozen): `max_position_size`, `max_total_exposure`,
  `risk_per_trade`, `max_daily_drawdown`, `risk_per_trade_pct`,
  `max_position_notional`, `max_daily_loss`, `max_losing_streak`,
  `sizing_mode` (`"absolute"` | `"percent_risk"`).
* `AccountState` (frozen): `equity`, `current_exposure`, `consecutive_losses`,
  `day_drawdown`, `day_realized_loss`.
* `RiskDecision` (frozen, `domain/models.py`): `approved`, `size`, `reason`,
  plus Audit-Felder `risk_amount`, `stop_distance`, `notional`,
  `capped_by_max_position`, `capped_by_max_notional`,
  `capped_by_total_exposure`.
* `evaluate(self, signal, account_state, reference_price=None) -> RiskDecision`
  dispatcht nach `sizing_mode`.
* **Ablehnung über `approved=False` + `reason`** (size `0.0`). Es gibt **kein**
  separates `rejected`-Feld.
* **percent_risk / stop_price:** im `percent_risk`-Modus sind
  `reference_price` und `signal.stop_price` Pflicht; Sizing =
  `equity*risk_per_trade_pct / stop_distance`, danach ausschließlich gekappt.
* **`stop_price` ist sizing-only** — der Runner führt **keinen** Stop-Exit aus
  (Exit bleibt der Folge-Bar-Mid).

### CostModel / Metrics / Reporting

* **CostModel** (frozen, `runner.py`): `fee_rate`, `spread`, `slippage`
  (Defaults `0.0` = frictionless).
* **Kostenformel** `calculate_trade_costs(price, quantity, cost_model)`
  (`metrics.py`):
  `notional = abs(price*quantity)`;
  `fee_cost = notional*fee_rate`;
  `spread_cost = abs(quantity)*spread`;
  `slippage_cost = notional*slippage`;
  `total = fee_cost + spread_cost + slippage_cost` (>= 0). Der Runner ruft dies
  getrennt für Entry- und Exit-Leg auf; `net_pnl = gross_pnl - costs`.
* **Metrics-Funktionen** (`metrics.py`, rein): `number_of_trades`, `win_rate`,
  `profit_factor`, `max_drawdown`, `average_r_multiple`, `expectancy`,
  `exposure_time`, `worst_losing_streak`, `best_trade`, `worst_trade`.
* **Reporting** (`reporting.py`): `summarize_backtest_result(result, title, *,
  strategy_metadata=None, cost_metadata=None) -> BacktestExperimentSummary`,
  `summary_to_markdown`, `summary_to_dict`.
* **`BacktestExperimentSummary`** trägt die optionalen, additiven Felder
  `strategy_metadata` (`family`/`key`/`name`/`params`) und `cost_metadata`
  (`fee_rate`/`spread`/`slippage`) — **separat** von `BacktestResult` (Default
  `None` -> byte-identischer Output).
* **Comparison-Reporting** (`comparison_reporting.py`): technische
  Vergleichsfelder (`signals_total`/`trades_total`/`approved_signals`/
  `rejected_signals`); **kein** `ending_equity` im Comparison-Report.

## 3. Regression Test Groups

Geplante Testgruppen (Spezifikation; in Phase 2 **nicht** implementiert).

### Group A — Runner Contract Tests

* `BacktestRunner.run` returns `BacktestResult`.
* `source.market_data()` wird genutzt.
* `strategy.generate_signals(...)` wird genutzt.
* leere Signal-Liste erzeugt deterministisches Ergebnis
  (`number_of_trades == 0`, `equity_curve == (starting_equity,)`).
* `BacktestResult` enthält exakt die erwarteten Felder (§2).
* **keine** Reporting-Metadaten auf `BacktestResult` erwarten (kein
  `generated_at`/`strategy_metadata`/`cost_metadata`).

### Group B — Risk Decision Tests

* `RiskDecision.approved=True` wird technisch zu genau einem `TradeResult`
  verarbeitet.
* `RiskDecision.approved=False` erzeugt **keinen** `TradeResult`
  (nur `rejected_signals` erhöht sich).
* `reason` bleibt nachvollziehbar (über die RiskEngine-Rückgabe).
* `stop_price` wird bei `percent_risk`-Sizing genutzt (`stop_distance`).
* `stop_price` löst **keinen** Stop-Exit aus.

### Group C — TradeResult Determinism Tests

* `entry_time` deterministisch.
* `exit_time` deterministisch.
* `quantity` deterministisch (`== decision.size`).
* `side`/`entry_price`/`exit_price` entsprechen dem synthetischen Setup.
* **kein** `exit_reason` erwarten.
* **kein** separates Order-Objekt erwarten.
* **kein** Position-Lifecycle erwarten.

### Group D — CostModel Regression Tests

* `fee_rate` wirkt technisch auf `costs`/`net_pnl` (nicht auf `gross_pnl`).
* `spread` wirkt technisch auf die Kosten (`abs(quantity)*spread`).
* `slippage` wirkt technisch auf die Kosten (Notional-Anteil).
* Kosten beeinflussen die Nettofelder; frictionless -> `costs == 0.0`.
* Kosten ändern **nicht** die Strategy-Signale.
* negative Kostenparameter: dokumentierter Ist-Zustand ist, dass `CostModel`
  aktuell **keine** Validierung erzwingt — Tests prüfen den Ist-Zustand, ohne
  neue Validierung einzuführen.

### Group E — Metrics / Equity Tests

* `ending_equity` deterministisch.
* `equity_curve` deterministisch.
* `metrics` enthält die bestehenden Felder (§2).
* technische Werte werden geprüft, nicht bewertet.
* keine Ranking-/Recommendation-Aussage.

### Group F — Metadata / Reporting Tests

* `strategy_metadata` bleibt im Reporting-Layer erhalten (falls übergeben).
* `cost_metadata` bleibt im Reporting-Layer erhalten (falls übergeben).
* `BacktestExperimentSummary` enthält die erwarteten Metadaten (verifiziert).
* `BacktestResult` wird **nicht** fälschlich um Reporting-Metadaten erweitert.

### Group G — CLI Regression Tests

* CLI v0/v1 Auswahl unverändert (`--strategy v0|v1`, Default v0).
* v1-only Gating unverändert (`--breakout-threshold-pct`, `--cooldown-bars`,
  `--max-signals-per-day`).
* Cost-Flags unverändert (`--fee-rate`/`--spread`/`--slippage`).
* CLI nutzt den bestehenden Runner-/Reporting-Pfad.
* keine neue Reportdatei außerhalb des bestehenden Verhaltens.
* keine Visual-Preview-Änderung.

### Group H — Safety / Boundary Tests

* keine API-/Exchange-/Live-/Paper-/Order-Pfade.
* keine echten CSV-Dateien.
* keine Screenshots.
* keine Reports.
* keine verbotene Wertungssprache (Fragment-gebauter Token-Scan).
* Visual Preview Index (`docs/visual-preview-index.md`) bleibt unverändert.

## 4. Synthetic Fixture Strategy

* nur synthetische In-Memory-Daten (z. B. `tests/helpers/synthetic_data.py`,
  `InMemoryMarketDataSource`).
* keine echten CSVs.
* keine Downloads.
* kleine `MarketData`-Sequenzen.
* deterministische Timestamps.
* UTC-aware Timestamps.
* minimale Fixtures:
  * no signals,
  * one approved signal,
  * one rejected signal,
  * non-zero CostModel,
  * deterministic equity_curve,
  * percent_risk with stop_price.
* keine Performance-Interpretation.

## 5. Recommended Phase 3 / Later Scope

Empfohlene nächste Implementierung nach Phase 2:

* neue Testdatei: `tests/test_backtest_runner_regressions.py`.
* reine Regressionstests gegen den bestehenden Code.
* **keine** Codeänderung erwartet.
* wenn ein Test fehlschlägt:
  * zuerst prüfen, ob Test oder Spezifikation den Ist-Zustand falsch annimmt,
  * **nicht** sofort Code umbauen (Spec-First).
* keine Stop-Exit-Implementierung.
* keine neue Position-Lifecycle-Semantik.
* keine UI-Integration.
* keine CLI-Erweiterung.

Empfohlene erste Testreihenfolge:

1. `BacktestRunner` returns `BacktestResult`.
2. Empty signals deterministic.
3. Rejected signals do not create trades.
4. Approved signal creates deterministic `TradeResult` (so, wie der aktuelle
   Runner es tut).
5. CostModel deterministic.
6. `ending_equity`/`equity_curve` deterministic.
7. Reporting-Layer metadata preserved.
8. `stop_price` sizing-only behavior.

## 6. Out of Scope for Later Regression-Test Phase

* Stop-Exit-Implementierung.
* neues Position-Lifecycle-Modell.
* neue Trade-/Order-Klassen.
* Runner-Neudesign.
* Visual Preview Integration.
* Streamlit.
* echte Daten.
* Reports.
* CLI-Feature-Erweiterung.
* Optimierung.
* Profitabilitätsbewertung.
* Trading-Empfehlung.

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

* LQ-036-Link wird ergänzt (technische nächste Schritte).

Roadmap (`docs/technical-status-and-roadmap.md`):

* LQ-036 wird unter „BacktestRunner / Trade-Lifecycle" ergänzt.
* Status:
  * regression test plan finalized,
  * next suggested action: add regression tests only,
  * no implementation unless failing tests reveal a documented mismatch.

Visual Preview Index:

* bleibt unverändert.
* LQ-036 ist **kein** Visual-Preview-Track.

## 9. Phase 2 Implementation Status

* Regression test plan finalized (this file).
* Verified current state preserved (real identifiers only).
* Regression groups A–H documented.
* Synthetic fixture strategy documented.
* Recommended later scope documented.
* Roadmap link added.
* README link added.
* Doku-tests added (`tests/test_backtest_runner_regression_plan.py`).
* Visual Preview Index unchanged.
* No runner regression tests implemented.
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
