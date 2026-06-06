# LQ-035 — BacktestRunner / Trade-Lifecycle Integration Specification

## Status

* Phase 2 implemented.
* BacktestRunner / trade-lifecycle integration specification finalized.
* Existing Runner/RiskEngine/CostModel/Reporting state documented.
* No code changes.
* No runner changes.
* No RiskEngine changes.
* No strategy changes.
* No Visual Preview changes.
* No Streamlit start.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Dieses Dokument startet einen neuen technischen Track nach dem
  Visual-Preview-Freeze (LQ-034).
* Es beschreibt den aktuellen Backtesting-/Risk-/Cost-/Reporting-Stand.
* Es dokumentiert mögliche nächste Integrationsschritte.
* Es ist **keine** Trading-Anleitung.
* Es bewertet **keine** Strategie.

## 2. Verified Current State

Verifiziert durch Codelesung (read-only).

### Strategy Layer

* `MidBreakoutStrategy` (v0) existiert.
* `MidBreakoutStrategyV1` (v1) existiert.
* Signale werden über
  `generate_signals(self, market_data: Sequence[MarketData]) -> tuple[Signal, ...]`
  erzeugt.
* `Signal`-Felder (`domain/models.py`):
  * `timestamp`
  * `direction` (`Direction`: LONG/SHORT/FLAT)
  * `strength`
  * `stop_price` (`float | None`)
  * `metric` (`LiquidityMetric | None`)
* v1-Parameter: `lookback_bars=12`, `stop_distance_pct=0.01`,
  `breakout_threshold_pct=0.001`, `cooldown_bars=3`, `allow_short=True`,
  `min_strength=0.0`, `max_signals_per_day=None`.
* v1-Validierungen: `lookback_bars>0`, `stop_distance_pct∈(0,1)`,
  `breakout_threshold_pct∈[0,0.1)`, `cooldown_bars>=0`, `min_strength∈[0,1]`,
  `max_signals_per_day` None oder >0.

### Runner Layer

* `BacktestRunner` existiert (`backtesting/runner.py`).
* `BacktestRunner.run(self) -> BacktestResult` existiert.
* `DataSource.market_data()` wird genutzt.
* `BacktestResult` (frozen) existiert mit Feldern: `experiment_id`,
  `number_of_trades`, `approved_signals`, `rejected_signals`,
  `starting_equity`, `ending_equity`, `equity_curve` (`tuple[float, ...]`),
  `metrics` (`dict[str, float]`), `trades` (`tuple[TradeResult, ...]`),
  `parameters`.
* Der Runner ist bereits mit der CLI verdrahtet
  (`cli/backtest_mid_breakout.py`).
* Trades werden aktuell als `TradeResult` modelliert.
* Kein separates `Order`-Modell.
* Kein separates Trade-Lifecycle-Objekt über `TradeResult` hinaus.
* `Position` existiert in `domain/models.py`, wird aber im Runner **nicht** als
  zentrales Lifecycle-Objekt genutzt.

### RiskEngine Layer

* `RiskEngine` existiert (`risk/engine.py`).
* `RiskLimits` (frozen) existiert: `max_position_size`, `max_total_exposure`,
  `risk_per_trade`, `max_daily_drawdown`, `risk_per_trade_pct`,
  `max_position_notional`, `max_daily_loss`, `max_losing_streak`,
  `sizing_mode` (`"absolute"` | `"percent_risk"`).
* `AccountState` (frozen) existiert: `equity`, `current_exposure`,
  `consecutive_losses`, `day_drawdown`, `day_realized_loss`.
* `RiskEngine.evaluate(signal, account_state, reference_price=None) ->
  RiskDecision`.
* `RiskDecision`-Felder: `approved` (bool), `size`, `reason`, `risk_amount`,
  `stop_distance`, `notional`, `capped_by_max_position`,
  `capped_by_max_notional`, `capped_by_total_exposure`.
* `stop_price` wird für `percent_risk`-Sizing verwendet, aber **nicht** als
  Stop-Exit im Runner ausgeführt.

### CostModel / Metrics / Reporting

* `CostModel` (frozen, `runner.py`) existiert: `fee_rate`, `spread`,
  `slippage`.
* `calculate_trade_costs(price, quantity, cost_model)` in `metrics.py`.
* `TradeResult` (frozen, `metrics.py`): `entry_price`, `exit_price`,
  `quantity`, `side`, `gross_pnl`, `costs`, `net_pnl`, `r_multiple`,
  `duration_bars`, `entry_time`, `exit_time`.
* Metrics-Funktionen: `number_of_trades`, `win_rate`, `profit_factor`,
  `max_drawdown`, `average_r_multiple`, `expectancy`, `exposure_time`,
  `worst_losing_streak`, `best_trade`, `worst_trade`.
* Reporting (`reporting.py`): `summarize_backtest_result`,
  `summary_to_markdown`, `summary_to_dict`; `strategy_metadata`
  (`family`/`key`/`name`/`params`), `cost_metadata`
  (`fee_rate`/`spread`/`slippage`), `safety_flags`
  (`live_execution`/`network_calls`/`paper_trading`).
* `comparison_reporting.py`: `normalize_comparison`,
  `render_comparison_markdown`, `technical_results`
  (`signals_total`/`trades_total`/`approved_signals`/`rejected_signals`).
* `ending_equity`/`equity_curve` existieren bereits.
* Diese Felder sind technische Outputs und **keine** Strategieempfehlung.

### Visual Preview

* Visual Preview ist signal-only.
* Keine Runner-Integration in Visual Preview.
* LQ-034 hat die Visual-Preview-Doku eingefroren.
* LQ-035 verändert Visual Preview **nicht**.

## 3. Integration Gap

* Runner existiert bereits.
* RiskEngine existiert bereits.
* CostModel existiert bereits.
* `TradeResult` existiert bereits.
* Es fehlt **nicht** der komplette Runner.
* Offene Lücke ist eher:
  * Lifecycle-Semantik sauberer dokumentieren/testen
  * Stop-Exit-Verhalten klären (derzeit kein Stop-Exit)
  * Position-Objekt-Nutzung klären
  * `approved`/`rejected`-Zählung neutral absichern
  * Kostenanwendung regressionssicher testen
  * Reporting-Sprache neutral halten
  * Visual Preview bewusst nicht erweitern

## 4. Target Integration Model

1. DataSource liefert `MarketData`.
2. Strategie erzeugt technische Signale.
3. Runner verarbeitet Signale gegen MarketData.
4. RiskEngine bewertet technische Zulässigkeit.
5. Rejected Signale öffnen keinen Trade.
6. Approved Signale führen zu simulierten `TradeResult`-Einträgen.
7. CostModel wird technisch angewendet.
8. `BacktestResult` sammelt technische Ergebnisse.
9. Reporting gibt Metadata und technische Zähler aus.

Wichtig:

* Kein Live-Trade.
* Keine Order.
* Keine Broker-Integration.
* Keine Empfehlung.
* Keine Performance-Deutung als Entscheidungsbasis.

## 5. Trade-/Position-Lifecycle — Current vs. Potential

### Current

* Signal -> `RiskDecision` -> `TradeResult` / `BacktestResult`.
* `TradeResult` ist das bestehende Trade-Objekt.
* `Position` existiert, wird aber im Runner nicht als zentrales
  Lifecycle-Modell genutzt.
* `stop_price` wird aktuell für Sizing verwendet.
* Stop-Exit wird aktuell **nicht** als eigener Exit-Mechanismus ausgeführt.

### Potential Later

Nur Spezifikation, keine Umsetzung:

* Signal
* Risk Check
* Entry Candidate
* Simulated Open Position
* Exit Event
* Closed Trade

Mögliche Exit Events nur als zukünftige Optionen:

* end of data
* stop hit (falls später implementiert)
* explicit strategy exit (falls später vorhanden)
* max bars (falls später definiert)

## 6. CostModel Integration

* Aktueller Stand exakt nach Code.
* Kosten sind technische Berechnung über `calculate_trade_costs`.
* Keine Interpretation als Strategiequalität.
* Vorhandene Felder:
  * `fee_rate`
  * `spread`
  * `slippage`
  * je Trade: `gross_pnl`, `costs`, `net_pnl` (in `TradeResult`)
* `cost_metadata` reported `fee_rate`/`spread`/`slippage`.

## 7. Neutral Reporting Rules

Erlaubt als technische Felder:

* `signals_total`
* `approved_signals`
* `rejected_signals`
* `reason` (rejection reasons)
* `trades` / `number_of_trades` / `trades_total`
* `strategy_metadata`
* Risk-Audit (`risk_notes`)
* `cost_metadata`
* `generated_at`
* `ending_equity`
* `equity_curve`
* `metrics`

Wichtig:

* `ending_equity`/`equity_curve`/`metrics` dürfen nur als technische Outputs
  beschrieben werden.
* Keine Entscheidungsempfehlung daraus ableiten.
* Keine Ranking-Sprache.

Nicht verwenden als Bewertungssprache (der Doku-Test scannt fragment-gebaute
Tokens, damit die Testdatei sich nicht selbst matcht):

* Strategie-Superlative
* „Sieger"-Sprache
* Garantieversprechen
* direkte Handelsaufforderungen
* Profitabilitäts-Wertung

## 8. Recommended Phase 3 / Later Implementation Path

Empfehlung:

* Keine UI-Integration.
* Keine Visual-Preview-Erweiterung.
* Keine Profitabilitätsbewertung.
* Keine neue Strategie.
* Kein Live/Paper/Exchange.

Empfohlene spätere Implementierung:

### Step 1 — Runner regression tests

* Bestehenden Runner testgetrieben absichern.
* Keine neue Semantik erzwingen.
* Prüfen:
  * `DataSource.market_data` wird genutzt
  * `strategy_metadata` bleibt erhalten
  * `cost_metadata` bleibt erhalten
  * `RiskDecision` approved/rejected zählt korrekt
  * Rejected Signale erzeugen keinen `TradeResult`
  * cost application bleibt stabil
  * `ending_equity`/`equity_curve` bleiben deterministisch

### Step 2 — Lifecycle decision

* Erst nach Regression klären:
  * Stop-Exit ja/nein
  * Position-Objekt nutzen ja/nein
  * separate Entry/Exit Events ja/nein

### Step 3 — Optional CLI reporting polish

* Nur neutrale Darstellung.
* Keine Bewertung.

## 9. Test Strategy for Later Implementation

### Runner Regression Tests

* `BacktestRunner` returns `BacktestResult`.
* `BacktestResult` contains expected technical fields.
* No trades are created for rejected signals.
* Approved signals create deterministic `TradeResult` entries.
* CostModel changes only cost fields.
* `strategy_metadata` is preserved.
* `cost_metadata` is preserved.
* `equity_curve` is deterministic.

### RiskEngine Regression Tests

* `RiskLimits` validation.
* `AccountState` handling.
* `percent_risk` sizing with `stop_price`.
* rejection reasons stable.

### CLI Regression Tests

* v0/v1 selection unchanged.
* v1-only gates unchanged.
* cost flags unchanged.
* output contains technical metadata.
* no report files unless explicitly requested by existing CLI behavior.

### Safety Tests

* no API/exchange/live/paper/order path.
* no real CSV artefacts.
* no screenshot/report artefacts.
* no forbidden valuation language.

## 10. README/Roadmap Impact

README:

* optional kurzer Link auf LQ-035 als neuer technischer Track.

Roadmap (`docs/technical-status-and-roadmap.md`):

* neuer Track:
  * BacktestRunner / Trade-Lifecycle Integration
* Status:
  * Phase 1/2 specification only
  * existing Runner stack verified
  * next suggested action: Runner regression test plan, not UI work

Visual Preview Index:

* **nicht** erweitern.
* Visual Preview bleibt frozen.

## 11. Safety Boundaries

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

## 12. Phase 2 Implementation Status

* Specification finalized (this file).
* Verified current Runner/RiskEngine/CostModel/Reporting state documented.
* Integration gap documented.
* Current vs potential lifecycle documented.
* Neutral reporting rules documented.
* Recommended later implementation path documented.
* Roadmap link added.
* README link added.
* Doku-tests added (`tests/test_backtest_runner_trade_lifecycle_spec.py`).
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
