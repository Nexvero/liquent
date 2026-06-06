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
- `MidBreakoutStrategy` als erste regelbasierte v0-Strategie (siehe
  „Strategie v0: MidBreakoutStrategy" unten)

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

### Strategy v0: MidBreakoutStrategy

`MidBreakoutStrategy` ist das erste einfache Strategie-Modul in Liquent. Es dient
ausschließlich dazu, die Research-/Backtesting-Pipeline zu validieren — es ist
**keine** Handelsempfehlung und **keine** Aussage über Profitabilität.

Die Strategie arbeitet auf dem Mittelkurs `MarketData.mid`:

```text
mid = (bid + ask) / 2
```

Für CSV-Daten über `HistoricalFileSource` gilt das aktuelle v1-Mapping
`close -> bid = ask = close`, also `mid == close`. `MidBreakoutStrategy` ist
damit ein **Mid-/Close-Breakout-Proxy** — kein echtes Intrabar-High/Low-Breakout
(kein ATR, kein Orderbook).

#### Signal-Logik

Für jeden ausführbaren Bar `i` betrachtet die Strategie die vorangehenden
`lookback_bars` Mid-Preise.

Long-Signal:

```text
mid[i] > max(mid[i-lookback_bars : i])
```

Short-Signal:

```text
mid[i] < min(mid[i-lookback_bars : i])
```

Beide Vergleiche sind strikt (Gleichstand erzeugt kein Signal). Short-Signale
lassen sich mit `allow_short=False` abschalten. Auf dem letzten Bar wird kein
Signal erzeugt, weil der Close-to-Close-Runner einen Folge-Bar für den
simulierten Exit benötigt.

#### Stop-Logik

Die Strategie liefert immer einen `stop_price` (Voraussetzung für
`percent_risk`-Sizing):

```text
Long:  stop_price = mid[i] * (1 - stop_distance_pct)
Short: stop_price = mid[i] * (1 + stop_distance_pct)
```

Mit `0 < stop_distance_pct < 1` liegt der Long-Stop strikt unter und der
Short-Stop strikt über dem Entry — passend zur strikten Stop-Prüfung der
Risk Engine.

#### Parameter

- `lookback_bars: int` (> 0)
- `stop_distance_pct: float` (0 < x < 1)
- `min_strength: float = 0.0` (in `[0, 1]`)
- `allow_short: bool = True`

Ungültige Werte werden bereits im Konstruktor mit `ValueError` abgelehnt
(fail-safe). Die Signalstärke ist in v0 fix `1.0`, da die Risk Engine `strength`
nur auf `> 0` prüft und die Positionsgröße nicht damit skaliert.

#### Risk-Integration

Die Strategie berechnet **keine** Positionsgröße und kennt weder Equity noch
Risk-Limits. Das Sizing erfolgt ausschließlich in der `RiskEngine`.

```text
MarketData
→ MidBreakoutStrategy.generate_signals(...)
→ Signal mit stop_price
→ RiskEngine.evaluate(..., reference_price=entry_price)
→ BacktestResult
→ Reporting
```

#### Sicherheitsgrenzen

`MidBreakoutStrategy` ist:

- lokal,
- deterministisch,
- frei von Netzwerk-Calls,
- ohne Exchange-Anbindung,
- keine Live-Trading-Komponente,
- keine Paper-Trading-Komponente,
- nicht optimiert,
- keine Profitabilitätsaussage,
- keine Handelsempfehlung.

### Lokaler CLI-Backtest-Report

Liquent enthält ein **rein lokales** CLI-Modul, das die aktuelle
`MidBreakoutStrategy` gegen eine lokale OHLCV-CSV auswertet und einen
deterministischen Markdown-Report schreibt.

Aufruf aus dem Projektwurzelverzeichnis:

```bash
. .venv/bin/activate

python -m liquent.cli.backtest_mid_breakout \
  --csv tests/fixtures/strategy_mid_breakout_long.csv \
  --output reports/mid_breakout_example.md \
  --symbol TESTUSDT \
  --exchange synthetic \
  --asset-class crypto \
  --timeframe 5m \
  --overwrite
```

Das CLI orchestriert ausschließlich die bestehende Pipeline:

```text
HistoricalFileSource
→ MidBreakoutStrategy
→ RiskEngine percent_risk
→ BacktestRunner
→ BacktestExperimentSummary
→ Markdown-Report
```

Verhalten in v0:

- nur lokale CSV als Eingabe,
- `sizing_mode = percent_risk` (fest),
- keine Netzwerk-Calls,
- keine Exchange-Anbindung,
- kein Live-Trading,
- kein Paper-Trading,
- keine API-Keys,
- deterministischer Markdown-Output (kein Zeitstempel, kein Zufall),
- kein Überschreiben ohne `--overwrite`.

Generierte Reports werden unter `reports/` abgelegt — dieser Ordner ist von Git
ignoriert (Ausnahme: `reports/README.md`). Das CLI ist ausschließlich für lokale
Research-/Backtesting-Workflows gedacht und ist keine Handelsempfehlung.

#### Datenlücken bei echten CSVs

Reale OHLCV-Exporte enthalten häufig Lücken (z. B. Börsen-Wartung).
`--gap-policy tolerate` kann mit `--max-gaps N` kombiniert werden, um bis zu `N`
Lücken zuzulassen; `--gap-policy flag` lädt trotz Lücken und meldet sie.
`--gap-policy reject` (Default) bricht bei der ersten Lücke ab.

Beispiel (Pfad ist nur ein **Beispiel**; keine echten Daten im Repo):

```bash
python -m liquent.cli.backtest_mid_breakout \
  --csv data/raw/crypto/binance/BTCUSDT/5m/BTCUSDT_5m_2026-05-01_2026-05-31.csv \
  --output reports/real_btcusdt_5m.md \
  --symbol BTCUSDT \
  --exchange binance \
  --asset-class crypto \
  --timeframe 5m \
  --gap-policy tolerate \
  --max-gaps 5 \
  --history-policy flag \
  --overwrite
```

## 4. Projektstruktur

```text
src/liquent/domain/        Entitäten (Signal, RiskDecision, MarketData, …)
src/liquent/risk/          Risk Engine — Pflicht-Gate, Risk-First
src/liquent/data/          HistoricalFileSource, Validierung, Gap-/History-Reports
src/liquent/backtesting/   Runner, Metrics, Reporting
src/liquent/strategy/      Strategien (MidBreakoutStrategy, v0-Proxy)
src/liquent/cli/           Lokales CLI (backtest_mid_breakout -> Markdown-Report)
tests/                     stdlib-Testsuite
tests/fixtures/            OHLCV-Test-CSV (nur Fixtures, keine Marktdaten)
data/                      Datenpolicy + Platzhalter (siehe data/README.md)
reports/                   Lokale Report-Ausgaben (ignoriert, nur README getrackt)
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
Aktueller verifizierter Teststand:
225 passed (pytest, lokale .venv)
```

Frühere Läufe erfolgten über einen temporären stdlib-Harness, weil `pytest`/`pip`
auf dem VPS zunächst nicht verfügbar waren. Das lokale Tooling ist inzwischen
eingerichtet (siehe „Local test setup"); der frühere Harness wird nicht
committed.

### Local test setup

Liquent nutzt eine lokale Python-Virtualenv für Entwicklung und Tests.

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m pytest
```

Das Verzeichnis `.venv/` ist ausschließlich lokal und darf nicht committed
werden (bereits in `.gitignore`).

Aktueller verifizierter lokaler Teststand:

```text
225 passed
```

Die aktuelle Testsuite benötigt keine Live-Trading-Zugangsdaten, keine
Exchange-API-Keys und keine Netzwerk-Calls.

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
- Tooling: lokale `.venv` mit `pytest` eingerichtet (erledigt) — ggf. CI ergänzen
- Optional: CI später über GitHub Actions, aber noch nicht jetzt
