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
  „Strategy v0: MidBreakoutStrategy" unten)
- `MidBreakoutStrategyV1` als additive v1-Strategie mit Breakout-Threshold und
  Cooldown (siehe „Strategy v1: MidBreakoutStrategyV1" unten)

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

### Strategy v1: MidBreakoutStrategyV1 (LQ-008)

`MidBreakoutStrategyV1` ist eine **additive** Strategieklasse neben der
bestehenden `MidBreakoutStrategy` (v0). v0 bleibt als **Regressionsbasis
unverändert**; v1 liegt in `src/liquent/strategy/mid_breakout_v1.py`. Anlass war
die im 30-Tage-Echtdatenlauf beobachtete hohe Signaldichte: v1 ergänzt zwei
deterministische Stellschrauben (Breakout-Threshold, Cooldown), um Mikro-/Noise-
Ausbrüche zu filtern und Trade-Cluster aufzubrechen. Wie v0 ist es ein
Mid-/Close-Breakout-Proxy — **keine** Handelsempfehlung, **keine** Aussage über
Profitabilität.

#### Technische Unterschiede v0 / v1

| Aspekt | v0 `MidBreakoutStrategy` | v1 `MidBreakoutStrategyV1` |
|---|---|---|
| `lookback_bars` (Default) | 3 | 12 |
| Breakout-Auslösung | jedes strikte neue Fensterhoch/-tief | nur jenseits eines relativen Schwellwerts |
| `breakout_threshold_pct` | — (keiner) | 0.001 (Default) |
| `cooldown_bars` | — (keiner) | 3 (Default) |
| `stop_distance_pct` (Default) | 0.05 (CLI) | 0.01 |
| `allow_short` (Default) | True | True |
| `min_strength` (Default) | 0.0 | 0.0 |
| `max_signals_per_day` | — | None (aktiv; None = deaktiviert) |
| `strength` | fix `1.0` | thresholdbasiert (s. u.) |
| Signaldichte | hoch möglich | gezielt reduzierbar |

#### Signal-Logik v1

Für jeden ausführbaren Bar `i` (`lookback_bars <= i <= n-2`) mit
`prev_high = max(mid[i-lookback_bars : i])` und `prev_low = min(...)`:

```text
Long:  mid[i] > prev_high * (1 + breakout_threshold_pct)
Short: mid[i] < prev_low  * (1 - breakout_threshold_pct)
```

Short-Signale nur bei `allow_short=True`. Auf dem letzten Bar wird kein Signal
erzeugt (der Close-to-Close-Runner braucht einen Folge-Bar für den Exit). Mit
`breakout_threshold_pct = 0.0` entspricht das Verhalten exakt v0 (strikter
`>`/`<`-Vergleich) — bei sonst gleichen Parametern und `cooldown_bars = 0`.

#### Cooldown

Nach einem **erzeugten** Signal auf Bar `i` werden die nächsten `cooldown_bars`
Bars (`i+1 … i+cooldown_bars`) für neue Signale übersprungen. `cooldown_bars = 0`
erlaubt ein unmittelbares Folgesignal; `cooldown_bars >= 0` wird im Konstruktor
geprüft.

#### Stop-Logik

```text
Long:  stop_price = mid[i] * (1 - stop_distance_pct)
Short: stop_price = mid[i] * (1 + stop_distance_pct)
```

Die Stop-Logik ist unverändert zu v0 und bleibt `percent_risk`-kompatibel
(Long-Stop strikt unter, Short-Stop strikt über dem Entry). **Wichtig:** Im
aktuellen Close-to-Close-Runner dient `stop_price` ausschließlich als
**Sizing-Eingang** der Risk Engine — es ist **kein ausgeführter Stop-Loss**
(der Exit ist stets der Mid des Folge-Bars).

#### Strength / min_strength

```text
breakout_threshold_pct == 0.0  →  strength = 1.0
breakout_threshold_pct  > 0.0  →  strength = min(1.0, breakout_distance_pct / breakout_threshold_pct)
                                   mit breakout_distance_pct = abs(mid[i] - breakout_level) / breakout_level
                                   und breakout_level = prev_high (Long) bzw. prev_low (Short)
```

`strength` ist ausschließlich **Signalqualität/Filter**; `min_strength` wirkt als
Signalfilter. Die `RiskEngine` skaliert die Positionsgröße **nicht** über
`strength` (sie prüft nur `> 0`).

#### Parameter

- `lookback_bars: int = 12` (> 0)
- `stop_distance_pct: float = 0.01` (0 < x < 1)
- `breakout_threshold_pct: float = 0.001` (in `[0, 0.1)`)
- `cooldown_bars: int = 3` (>= 0)
- `allow_short: bool = True`
- `min_strength: float = 0.0` (in `[0, 1]`)
- `max_signals_per_day: int | None = None` (None oder > 0; aktiv — max. Signale je
  UTC-Tag, None = deaktiviert)

Ungültige Werte werden bereits im Konstruktor mit `ValueError` abgelehnt
(fail-safe).

#### Tests

`tests/test_strategy_v1.py` deckt ab:

- Threshold blockt Mikro-Breakouts,
- Threshold erlaubt echte Long-/Short-Breakouts,
- Stop-Logik richtungskonsistent (Long-Stop < mid, Short-Stop > mid),
- Cooldown an/aus (`cooldown_bars` > 0 unterdrückt, `= 0` erlaubt Folgesignal),
- `breakout_threshold_pct = 0.0` reproduziert v0 bei gleichen Parametern,
- kein Signal auf dem letzten Bar,
- Determinismus (gleicher Input → identische Signale),
- Konstruktorvalidierung aller Parameter,
- Runner-Integration mit `percent_risk` (Risk-First End-to-End),
- statischer Scan gegen Netzwerk-/Live-/Paper-Trading-Pfade.

#### Nicht Teil von LQ-008 Phase 2/3

- keine CLI-Strategieauswahl (CLI nutzt weiterhin v0),
- keine Echtdatenläufe mit v1,
- keine Kostenmodell-Erweiterung,
- keine Optimierung, keine Parameter-Suche,
- kein Paper-Trading, kein Live-Trading, keine Exchange-API,
- keine Profitabilitätsbewertung, keine Trading-Empfehlung.

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

#### Strategieauswahl: `--strategy v0|v1` (LQ-009)

Das CLI kann explizit zwischen `MidBreakoutStrategy` (v0) und
`MidBreakoutStrategyV1` (v1) wählen:

```text
--strategy v0|v1     (Default: v0)
```

**`v0` bleibt Default** — bestehende Aufrufe ohne `--strategy` verhalten sich
exakt wie bisher (Rückwärtskompatibilität, byte-identisch reproduzierbare
Reports).

Beispiel v0 (entspricht dem Default):

```bash
python -m liquent.cli.backtest_mid_breakout \
  --strategy v0 \
  --csv tests/fixtures/strategy_mid_breakout_long.csv \
  --output reports/mid_breakout_v0.md \
  --symbol TESTUSDT --exchange synthetic --asset-class crypto \
  --overwrite
```

Beispiel v1 (mit v1-only Parametern):

```bash
python -m liquent.cli.backtest_mid_breakout \
  --strategy v1 \
  --breakout-threshold-pct 0.001 \
  --cooldown-bars 3 \
  --csv tests/fixtures/strategy_mid_breakout_long.csv \
  --output reports/mid_breakout_v1.md \
  --symbol TESTUSDT --exchange synthetic --asset-class crypto \
  --overwrite
```

Beispiel v1 mit Tageslimit (`--max-signals-per-day`, nur v1):

```bash
python -m liquent.cli.backtest_mid_breakout \
  --strategy v1 \
  --max-signals-per-day 2 \
  --csv path/to/synthetic_or_local_data.csv \
  --output reports/mid_breakout_v1_limit.md \
  --overwrite
```

Beispiel mit Kostenmodell (`--fee-rate`/`--spread`/`--slippage`):

```bash
python -m liquent.cli.backtest_mid_breakout \
  --strategy v1 \
  --fee-rate 0.001 --spread 0.0 --slippage 0.0005 \
  --csv path/to/synthetic_or_local_data.csv \
  --output reports/mid_breakout_costs.md \
  --overwrite
```

> Platzhalterpfade — keine echten Datenpfade, keine Ergebnisinterpretation. Tipp:
> `python -m liquent.cli.backtest_mid_breakout --help` listet alle Parameter
> nach Gruppen.

**Gemeinsame Parameter** (für v0 und v1):

```text
--lookback-bars
--stop-distance-pct
--min-strength
--allow-short true|false
```

**Nur v1:**

```text
--breakout-threshold-pct
--cooldown-bars
--max-signals-per-day   (INT > 0; max. Signale je UTC-Tag; ohne Angabe deaktiviert)
```

**Kostenmodell** (für v0 und v1; reale `CostModel`-Felder, Default `0.0` =
frictionless, jeweils `>= 0`):

```text
--fee-rate    (Notional-Anteil je Leg; 0.001 = 0,1 %)
--spread      (absoluter Aufschlag pro Einheit)
--slippage    (Notional-Anteil je Leg; 0.0005 = 0,05 %)
```

Der Report weist die effektiven Kosten im Abschnitt `## Cost Model` aus (auch bei
`0.0`). Ohne diese Flags bleibt das Verhalten frictionless und byte-identisch.

**Wichtig — v1-only Gating:**

- `--breakout-threshold-pct` und `--cooldown-bars` sind **nur mit
  `--strategy v1`** gültig.
- Werden sie bei `--strategy v0` gesetzt, **bricht das CLI mit Fehler ab**
  (keine Report-Datei).
- Da **ohne `--strategy` automatisch v0 gilt**, sind diese beiden Parameter auch
  **ohne explizites `--strategy v1`** ungültig.

**Strategie-Defaults** (werden nur für die jeweils gewählte Strategie
aufgelöst, sofern der Nutzer den Parameter nicht explizit setzt):

| Parameter | v0 (CLI-Default) | v1 (Default) |
|---|---|---|
| `lookback_bars` | 3 | 12 |
| `stop_distance_pct` | 0.05 | 0.01 |
| `min_strength` | 0.0 | 0.0 |
| `allow_short` | True | True |
| `breakout_threshold_pct` | — (nicht erlaubt) | 0.001 |
| `cooldown_bars` | — (nicht erlaubt) | 3 |

Gemeinsame Parameter nutzen eine Sentinel-Logik: ohne explizite Angabe greift
der Default der **gewählten** Strategie (v0: 3 / 0.05, v1: 12 / 0.01). Das CLI
validiert die Werte früh; die Strategie-Konstruktoren bleiben zusätzlich
autoritativ (fail-safe). Der Markdown-Report weist die verwendete Strategie über
`parameters["strategy"]` (Klassenname) aus; zusätzlich gibt das CLI eine
`strategy: …`-Zeile auf der Konsole aus. Die Strategieauswahl ändert weder
`BacktestRunner` noch `RiskEngine`.

### Visual Preview (lokal, optional)

`tools/visual_preview/` ist ein **lokales Entwickler-/Analysewerkzeug** zur rein
technischen Sichtbarmachung von Signaldichte und Parameterauswirkung — **nur
synthetische/lokale Preview**, **kein Live-Trading**, **keine
Trading-Empfehlung**, keine Ergebnisinterpretation.

- Die testbare Logik (`tools/visual_preview/preview_logic.py`) ist
  Streamlit-frei und nutzt nur synthetische Datasets + die bestehenden
  Strategien.
- `tools/visual_preview/app.py` ist ein **optionales** Streamlit-Skeleton;
  Streamlit ist **keine** Pflicht-Dependency und wird nur in `main()` importiert.

Die Preview zeigt (technisch, ohne Ergebnisinterpretation): **Technical Summary**,
**Mid-price chart** (mit Long/Short-Signalmarkern), **Signal table**, **Strategy
metadata** und **Safety notes**. Weiterhin gilt: **synthetic/local preview only**,
**no live trading**, **no trading recommendation**, **no profitability
assessment**, **no report files**, **no deployment**.

#### Datenquellen: Synthetic datasets + Local CSV upload

Die Preview unterstützt zwei Datenmodi:

- **Synthetic datasets** (Default; deterministische Muster).
- **Local CSV upload** (wenn Streamlit installiert ist) — über `st.file_uploader`.
  Der Upload wird **nur im Speicher** verarbeitet: **keine Speicherung**, **kein
  Download**, **keine API**, **keine Exchange**, **keine Persistenz im Repo**.

Minimales CSV-Format für den Upload:

```csv
timestamp,bid,ask,volume
2026-01-01T00:00:00+00:00,100.0,100.5,1.0
2026-01-01T00:05:00+00:00,100.2,100.7,1.0
```

**CSV format requirements:**

- **Required:** `timestamp,bid,ask` · **Optional:** `volume`.
- `timestamp` must be ISO-8601 with timezone, e.g. `+00:00` (naive timestamps are
  rejected).
- `bid` and `ask` must be positive numbers; `ask` must be greater than or equal
  to `bid`.
- `volume` defaults to `1.0` if omitted or empty.
- Rows are sorted by `timestamp`; `mid = (bid + ask) / 2`.
- Uploaded CSV files are processed **local/in-memory only** — **Liquent does not
  save uploaded CSV files**. Invalid CSVs produce a clear, row-numbered error
  message in the UI (e.g. `CSV row 3: timestamp must include timezone information,
  e.g. +00:00.`).

Keine echten Datenpfade, keine Ergebnisinterpretation, keine
Profitabilitätsaussage, keine Trading-Empfehlung.

**Requires optional Streamlit installation** (nicht Teil der Projekt-Dependencies;
`dependencies = []` bleibt unverändert). Streamlit ist als **optionales Extra**
`visual` geführt:

```bash
# optionales Visual-Extra installieren (Streamlit; nur lokal/optional):
pip install -e ".[visual]"
# oder, falls uv genutzt wird:
uv pip install -e ".[visual]"

# Preview starten:
streamlit run tools/visual_preview/app.py

# Fallback ohne Streamlit (gibt nur einen klaren Hinweis aus):
python -m tools.visual_preview.app
```

Ohne installiertes Streamlit meldet die App freundlich „Streamlit is not
installed…" und beendet sich — kein Traceback, keine Netzwerk-Calls, keine
Dateien. Die Preview zeigt ausschließlich **synthetic/local preview only**;
**no live trading**, **no trading recommendation**, keine Ergebnisinterpretation.

## 4. Projektstruktur

```text
src/liquent/domain/        Entitäten (Signal, RiskDecision, MarketData, …)
src/liquent/risk/          Risk Engine — Pflicht-Gate, Risk-First
src/liquent/data/          HistoricalFileSource, Validierung, Gap-/History-Reports
src/liquent/backtesting/   Runner, Metrics, Reporting
src/liquent/strategy/      Strategien (MidBreakoutStrategy v0, MidBreakoutStrategyV1)
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
410 passed (pytest, lokale .venv)
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
410 passed
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
