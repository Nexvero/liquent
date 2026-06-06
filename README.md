# Liquent — understand liquidity

Liquent ist ein risk-first Research- und Backtesting-Framework zur Analyse von
Liquiditäts- und Marktdaten. Der aktuelle Stand ist eine lokale, deterministische
Backtesting-Basis ohne Live-Trading, ohne Exchange-Anbindung und ohne produktive
Ausführung.

> Leitprinzip: Liquent **misst und erklärt** Liquidität. Es trifft keine Aussage
> über garantierte Profitabilität und spricht keine Handelsempfehlung aus.

**Stabiler Projektstand:** Backtesting / Risk / Data Foundation v1
(LQ-005 Phase 1–5, LQ-004 Phase 1–5, LQ-003 Phase 1–4 abgeschlossen).

## 1. Projektbeschreibung

Liquent stellt eine modulare, deterministische Grundlage bereit, um Strategien
gegen lokale historische OHLCV-Daten zu simulieren. Jeder simulierte Trade
durchläuft zwingend eine Risk Engine (Risk-First). Der Fokus liegt auf
Reproduzierbarkeit, Auditierbarkeit und klaren Sicherheitsgrenzen — nicht auf
Ausführung.

## 2. Sicherheitsprinzipien

- Kein Live-Trading.
- Kein Paper-Trading im aktuellen Stand.
- Keine Exchange-API.
- Keine Netzwerk-Calls.
- Keine API-Keys.
- Keine echten Marktdaten im Repo.
- RiskEngine-Gate vor jedem simulierten Trade.
- `percent_risk` erfordert `stop_price`.
- Signale ohne Stop werden im `percent_risk`-Modus abgelehnt.
- Backtests sind Forschungs-/Analysewerkzeuge, keine Handlungsempfehlung.

## 3. Aktueller Funktionsumfang

### Backtesting

- `BacktestRunner`
- `BacktestResult`
- Close-to-Close Simulation
- Equity Curve
- deterministische Experiment-ID
- Strategy Protocol
- `MomentumStubStrategy` als technischer Default-Stub
- keine echte Strategie im Produktcode

### Metrics

- `number_of_trades`
- `win_rate`
- `profit_factor`
- `max_drawdown`
- `average_r_multiple`
- `expectancy`
- `exposure_time`
- `worst_losing_streak`
- `best_trade`
- `worst_trade`

### Risk

- absolute sizing mode als Default
- percent_risk sizing explizit verfügbar
- `risk_per_trade_pct`
- `max_position_size`
- `max_position_notional`
- `max_total_exposure`
- `max_daily_drawdown`
- `max_daily_loss`
- `max_losing_streak`
- `reference_price` vom Runner
- `stop_price` im Signal
- Audit-Felder in `RiskDecision`
  (`risk_amount`, `stop_distance`, `notional`,
  `capped_by_max_position`, `capped_by_max_notional`, `capped_by_total_exposure`)

### Data

- `HistoricalFileSource`
- lokales OHLCV-CSV-Schema:
  `timestamp,open,high,low,close,volume`
- OHLCV-Validierung
- Gap-Erkennung:
  - `reject`
  - `flag`
  - `tolerate`
- Timeframes:
  - `1m`
  - `5m`
  - `15m`
  - `1h`
- `DataSourceMetadata`
- `HistoryReport` / Mindesthistorie
- `data/raw` und `data/processed` ignoriert

### Reporting

- `BacktestExperimentSummary`
- `summary_to_markdown`
- `summary_to_dict`
- Risk Notes je nach `sizing_mode`
- Safety Flags:
  - `live_execution`
  - `network_calls`
  - `paper_trading`

## 4. Projektstruktur

```text
src/liquent/domain/        Entitäten (Signal, RiskDecision, MarketData, …)
src/liquent/risk/          Risk Engine — Pflicht-Gate, Risk-First
src/liquent/data/          HistoricalFileSource, Validierung, Gap-/History-Reports
src/liquent/backtesting/   Runner, Metrics, Reporting
tests/                     stdlib-Testsuite
tests/fixtures/            OHLCV-Test-CSV (nur Fixtures, keine Marktdaten)
data/                      Datenpolicy + Platzhalter (siehe data/README.md)
```

Hinweis: `src/liquent/bot/` und `src/liquent/ui/` existieren nur als inaktive
Skeleton-Platzhalter und gehören **nicht** zum aktuellen Funktionsumfang.

## 5. Datenpolicy

Siehe [`data/README.md`](data/README.md) für Details.

- Echte Daten gehören nicht ins Git.
- `data/raw/` und `data/processed/` sind ignoriert.
- Nur `data/README.md` und die `.gitkeep`-Platzhalter werden getrackt.
- Test-Fixtures liegen getrennt unter `tests/fixtures/`.

## 6. Teststand

```text
Letzter bekannter Teststand:
169 Tests grün über stdlib-Harness.
```

Im aktuellen VPS-Environment wurden Tests über einen temporären stdlib-Harness
ausgeführt, weil `pytest`/`pip` nicht verfügbar waren. Der Harness wird nicht
committed.

## 7. GitHub / Remote

```text
Remote:
origin -> github-liquent:Nexvero/liquent.git

Branch:
main
```

Der Zugriff erfolgt über einen repo-spezifischen Deploy-Key. Es werden keine
privaten Schlüssel, Fingerprints oder Schlüssel-Pfade im Repository dokumentiert.

## 8. Nicht im aktuellen Stand

- keine echte Strategie
- keine Strategie-Optimierung
- kein Paper-Trading
- kein Live-Trading
- keine Exchange-API
- keine On-chain-Daten
- keine Orderbook-/Tickdaten
- keine Funding-/Open-Interest-Daten
- keine produktive Automatisierung

## 9. Nächste Schritte

- LQ-005 Phase 6: Vault-/Obsidian-Export optional vorbereiten
- Erste einfache Strategie nur nach separater Spezifikation
- LQ-003 v2: echte OHLC-Speicherung prüfen
- Tooling: `pytest`/`pip`/`venv` auf dem VPS sauber einrichten
- Optional: CI später über GitHub Actions, aber noch nicht jetzt
