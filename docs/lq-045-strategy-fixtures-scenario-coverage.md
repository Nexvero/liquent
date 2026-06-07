# LQ-045 — Strategy Fixtures / Scenario Coverage Docs + Regression Coverage

## Status

* Phase 2 implemented / finalized.
* Strategy / fixture / scenario contract documented; regression coverage added.
* 4 ergänzende Behavior-Locks (`tests/test_strategy_fixtures_scenario_hardening.py`).
* Hohe Bestandsabdeckung (~101 Tests) war bereits vorhanden — daher bewusst
  wenige neue Tests.
* Bestehende Strategie-/Scenario-Tests, `tests/helpers/synthetic_data.py` und
  alle Fixtures unverändert; nur synthetische/lokale Daten.
* Reine Dokumentations-/Regressionsphase.
* Beschreibt den **aktuellen** Strategie-/Fixture-/Scenario-Stand, kein
  Wunschdesign.
* No strategy source changes (`src/liquent/strategy/*`).
* No new strategies, no new/changed fixtures, no builder changes.
* No exit_reason.
* No Stop-Exit.
* No Runner-Lifecycle change.
* No ranking / evaluation / recommendation logic.
* No real market data, no external downloads, no new artefacts.
* No Streamlit start.
* No dependency install.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Den bestehenden Strategie-Signal-Contract, den Fixture-Katalog und die
  synthetischen Szenarien aus dem Code/den Tests dokumentieren
  (`src/liquent/strategy/mid_breakout.py`,
  `src/liquent/strategy/mid_breakout_v1.py`, `tests/helpers/synthetic_data.py`,
  `tests/fixtures/`).
* Ergänzende Regressionstests **nur** für die identifizierten Lücken vorbereiten
  (`tests/test_strategy_fixtures_scenario_hardening.py`) — ausschließlich auf
  synthetischen/lokalen Daten.
* Keine Produktionslogik ändern.
* Diese Doku ist rein deskriptiv: keine Bewertung, kein Ranking, keine
  Empfehlung, keine Profitabilitätsaussage.

## 2. Verified Current Model

Verifiziert lesend gegen den echten Code und die bestehenden Tests
(ohne Änderung).

### Strategy Signal Contract

Beide Strategien sind rein/deterministisch (keine I/O, keine Wall-Clock-Zeit,
kein Zufall) und erfüllen `generate_signals(market_data) -> tuple[Signal, ...]`.
Referenzpreis ist `mid = (bid + ask) / 2` (kein OHLC). Signale tragen
`timestamp` (= Entry-Bar), `direction` (`LONG`/`SHORT`), `strength`,
`stop_price`; `metric` bleibt `None` (kein String in das typisierte
`LiquidityMetric | None`-Feld). Es entstehen keine `FLAT`-Signale und keine
doppelten Zeitstempel.

### Strategy v0/v1 Contract

* **v0** (`MidBreakoutStrategy`): LONG bei `mid[i] > max(window)`, SHORT bei
  `mid[i] < min(window)` (strikt, `allow_short`); `stop_price` LONG
  `= mid*(1-stop_distance_pct)`, SHORT `= mid*(1+stop_distance_pct)`;
  `strength` fix `1.0`; Entry-Indizes `lookback_bars ≤ i ≤ len-2`;
  Konstruktor-Validierung fail-safe (`ValueError`).
* **v1** (`MidBreakoutStrategyV1`): zusätzlich `breakout_threshold_pct`
  (relativer Mindestausbruch), `cooldown_bars` (Sperre nach Signal),
  `max_signals_per_day` (optional). Gleiche Stop-/Index-/Fail-safe-Regeln.
* In v0 ist `strength` konstant `1.0` und `min_strength ≤ 1.0` (Konstruktor) —
  der `min_strength`-Filter ist damit ein vorwärtskompatibler, in v0 praktisch
  **unerreichbarer** Zweig (siehe Deferred Topics).

### Fixture Catalog

Lokale, synthetische CSV-Fixtures unter `tests/fixtures/` (unverändert):

| Fixture | Repräsentiert | Erwartetes Ergebnis (verifiziert via test_strategy_evaluation) |
|---|---|---|
| `strategy_mid_breakout_long.csv` | Long-Breakout-Szenario | genau 1 Long-Trade |
| `strategy_mid_breakout_short.csv` | Short-Breakout-Szenario | genau 1 Short-Trade (bei `allow_short`); 0 bei `allow_short=False` |
| `strategy_mid_breakout_no_signal.csv` | seitwärts/kein Ausbruch | 0 Trades |
| `ohlcv_*.csv` (14 Dateien) | OHLCV-Loader-Validierungsfälle (gap/duplicate/invalid/…) | vom Daten-/Loader-Layer abgedeckt |

### Synthetic Dataset Contract

`tests/helpers/synthetic_data.py` (rein testintern, kein Produktivcode):

* `make_mid_series_dataset(name, mids, *, start, interval_minutes=5,
  description, half_spread=0.0, volume=1.0)` → `SyntheticDataset`
  (`name, description, mids, market_data`), deterministisch:
  `timestamp[i] = start + i*interval_minutes` (UTC); `bid = mid - half_spread`,
  `ask = mid + half_spread` ⇒ `mid` ist das arithmetische Mittel; fail-safe
  `ValueError` bei `interval_minutes <= 0`, `half_spread < 0`, leeren `mids`,
  `bid <= 0`.
* `InMemoryMarketDataSource` erfüllt das `DataSource`-Protocol strukturell
  (`market_data()`, `order_book_snapshots()`); `metadata`/`history_report` nur
  als Attribute, wenn explizit übergeben.

### Synthetic Builder Catalog

Deterministische Muster-Builder (12 flache Bars Historie + Schwanz,
`half_spread=0.5`):

| Builder | Mid-Muster (Schwanz) | Zweck |
|---|---|---|
| `build_sideways_with_micro_long_breakout` | `100.05, 100.0, 100.0, 102.0, 100.0` | Mikro-Long (< Threshold) + echter Long-Breakout (+2 %) |
| `build_sideways_with_micro_short_breakout` | `99.95, 100.0, 100.0, 98.0, 100.0` | Mikro-Short + echter Short-Breakout (−2 %) |
| `build_stair_breakout_for_cooldown` | `101..106` (streng steigend) | aufeinanderfolgende Breakouts (Cooldown-Vergleich) |

### Scenario Coverage Contract

Synthetische Szenarien (rein deskriptiv, nebeneinander; **kein** Ranking, **kein**
`ending_equity`) werden über `comparison_reporting` und die Vergleichstests
abgedeckt (`tests/test_synthetic_strategy_comparison.py`,
`tests/test_max_signals_comparison_report.py`).

### Determinism Invariants

* `generate_signals` ist deterministisch (gleiche Eingabe → identisches
  Signal-Tupel) — für v0 und v1 bereits getestet.
* `make_mid_series_dataset` und die Muster-Builder sind deterministisch
  (keine Wanduhr, kein Zufall).

### Safety / Synthetic-only Invariants

* Ausschließlich synthetische/lokale Daten; keine echten Marktdaten, keine
  Netzwerk-Calls, keine externen Downloads.
* Keine neu committeten CSV-/Bild-/Report-Artefakte; vorhandene Fixtures bleiben
  unverändert.
* Ausdrücklich: keine neuen Strategien, keine neuen oder geänderten Fixtures,
  keine echten Marktdaten, keine externen Downloads, keine Profitabilitäts-
  bewertung, keine Trading-Empfehlung, keine Ranking-/Bewertungslogik; nur
  synthetische/lokale Daten und keine Produktionslogik geändert.

## 3. Edge-Case Table

| Eingang | Ergebnis (aktuell) |
|---|---|
| `len < lookback_bars + 2` | keine Signale (`()`) |
| leere Eingabe | `()` |
| potenzieller Breakout nur auf letztem Bar | kein Signal (kein Exit-Bar) |
| Gleichstand `mid[i] == prev_high` | kein Signal (strikt) |
| generiertes Signal | `metric is None`, `strength == 1.0` (v0) |
| `build_*`-Builder | deterministisch (zwei Aufrufe gleich) |
| Builder-`market_data` | `bid = mid-0.5`, `ask = mid+0.5`, Länge == `len(mids)` |

## 4. Regression Invariants

* Strategie-Signale: kein FLAT, keine doppelten Timestamps, `metric is None`.
* Reine, deterministische Erzeugung (Signale, Datasets, Builder).
* Nur synthetische/lokale Daten; keine Artefakte.
* Rein deskriptiv: keine Bewertung, kein Ranking, keine Empfehlung.

## 5. Safety Boundaries

* No API keys.
* No exchange credentials.
* No network calls by Liquent.
* No external data download by Liquent.
* No live data source.
* No orders.
* No paper-trading connection.
* Nur synthetische/lokale Daten; keine neu committeten CSV/Screenshots/Reports.
* No profitability assessment.
* No trading recommendation.
* No ranking / evaluation language.

## 6. README/Roadmap Impact

README:

* optional kein Link in Phase 1,
* Phase 2 kann den LQ-045-Link ergänzen.

Roadmap:

* LQ-045 als Strategy-Fixtures-/Scenario-Coverage-/Regression-Track ergänzen
  (Phase 2).
* Status:
  * strategy / fixture / scenario contract documented,
  * additional regression coverage added,
  * no production logic changes,
  * Runner Lifecycle bleibt gemäß LQ-040 pausiert.

Visual Preview Index:

* nicht erweitern,
* LQ-045 ist kein Visual-Preview-Track.

## 7. Phase Plan

* **Phase 1** (abgeschlossen): Doku-Entwurf + Lückenabgleich gegen die
  bestehenden Strategie-/Scenario-Tests; Entwurf von
  `tests/test_strategy_fixtures_scenario_hardening.py`. Kein Commit.
* **Phase 2** (diese): Doku finalisiert, Tests finalisiert, Doku-/Link-Test
  (`tests/test_strategy_fixtures_scenario_hardening_doc.py`), README/Roadmap
  minimal verlinkt, Teststand aktualisiert. Kein Commit.
* **Phase 3**: Commit der erwarteten Dateien. Kein Push ohne separate Freigabe.

## 7a. Implementation Status (Phase 2)

* Strategy / fixture / scenario contract documented (Verified Current Model,
  Fixture Catalog, Synthetic Dataset/Builder Catalog, Scenario Coverage,
  Determinism Invariants, Edge-Case Table).
* 4 ergänzende Behavior-Locks hinzugefügt
  (`tests/test_strategy_fixtures_scenario_hardening.py`) — nur synthetische/
  lokale Daten; hohe Bestandsabdeckung war bereits vorhanden, daher bewusst
  wenige neue Tests.
* Verifiziert/abgesichert: v0- und v1-Signale tragen `metric is None`;
  Builder-Determinismus (alle drei Muster-Builder); Builder-`market_data`
  spiegelt `half_spread=0.5`-Verdrahtung (`bid = mid-0.5`, `ask = mid+0.5`,
  `len(market_data) == len(mids)`).
* Fixture-Katalog dokumentiert, aber **nicht** doppelt getestet (long→1, short→1
  bei `allow_short`, no_signal→0 sind bereits durch
  `tests/test_strategy_evaluation.py` abgedeckt).
* Der `min_strength`-Filter in v0 ist defensiv/unerreichbar (`strength` fix
  `1.0`, `min_strength ≤ 1.0`) — nur dokumentiert, nicht getestet.
* Bestehende Strategie-/Scenario-Tests unverändert.
* `src/liquent/strategy/*` unverändert (keine Produktionslogik).
* `tests/helpers/synthetic_data.py` unverändert; alle Fixtures unverändert;
  keine neuen CSVs oder Artefakte.
* README-Link + Teststand aktualisiert.
* Roadmap-Link + Status aktualisiert.
* Doku-/Link-Test hinzugefügt: 12 Tests
  (`tests/test_strategy_fixtures_scenario_hardening_doc.py`).
* Visual Preview Index unverändert.
* No exit_reason, no Stop-Exit, no new strategy, no new signal logic, no
  new/changed fixtures, no new/changed builders.
* No dependency installed, no Streamlit start, no real market data, no external
  download, no artefacts.
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).

## 8. Test Plan

Ergänzende Behavior-Locks in `tests/test_strategy_fixtures_scenario_hardening.py`
— ausschließlich **bestehendes** Verhalten, nur synthetische/lokale Daten, keine
neuen Artefakte.

Adoptierte Lücken (echtes, bisher nicht explizit gesichertes Verhalten):

* **strategy** — v0-Signale haben `metric is None` (und `strength == 1.0`).
* **strategy** — v1-Signale haben `metric is None`.
* **builder** — alle drei Muster-Builder sind deterministisch (zwei Aufrufe
  liefern identische `SyntheticDataset`-Werte).
* **builder** — Builder-`market_data` spiegelt `half_spread=0.5`
  (`bid = mid-0.5`, `ask = mid+0.5`) und `len(market_data) == len(mids)`.

Bewusst **nicht** übernommen (bereits abgedeckt in den ~101 Bestandstests):

* unzureichende Historie / leere Eingabe → `()` (test_strategy
  `test_too_little_data_returns_empty`).
* kein Signal auf dem letzten Bar (`test_no_signal_on_last_bar`).
* `stop_price`-Numerik LONG/SHORT (`test_long_stop_…`, `test_short_stop_…`).
* Signal-`timestamp` = Entry-Bar (`test_long_breakout_single_signal_…`).
* `generate_signals`-Determinismus (v0/v1).
* Gleichstand/kein Duplikat/kein FLAT.
* Fixture-Trade-Anzahl long→1/short→1/no_signal→0 (test_strategy_evaluation) —
  nur im Fixture Catalog dokumentiert, nicht doppelt getestet.
* micro_long-/stair-Builder-`mids`-Shape und `make_mid_series_dataset`-
  Validierung (test_synthetic_data_helpers).

Bewusst **nicht** als Test übernommen (im Code vorwärtskompatibel/unerreichbar):

* `min_strength`-Filter in v0 (`strength` fix `1.0`, `min_strength ≤ 1.0`) — der
  Filterzweig ist in v0 nicht erreichbar; nur dokumentiert.

## 9. Non-Goals

* keine Änderung an `src/liquent/strategy/*` (Strategie-Produktionslogik),
* keine neuen Strategien, keine neuen/geänderten Fixtures,
* keine Änderung an `tests/helpers/synthetic_data.py`,
* keine Änderung an bestehenden Strategie-/Scenario-/Helper-Tests,
* kein `exit_reason`, keine Stop-Exit-Logik, keine Runner-Lifecycle-Änderung,
* keine RiskEngine-/CostModel-/Metrics-/Reporting-/Comparison-/CLI-Änderung,
* keine Ranking-/Bewertungslogik,
* keine echten Marktdaten, keine externen Downloads, keine neu committeten
  CSV-/Bild-/Report-Artefakte,
* keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 10. Deferred Topics

1. Der `min_strength`-Filter wird in v0 nicht ausgelöst (`strength` fix `1.0`);
   eine variable Stärke ist ein separater, ausdrücklich freizugebender Track.
2. Zusätzliche synthetische Szenarien/Builder bleiben außerhalb dieses Tracks
   (keine neuen Fixtures/Builder hier).
3. Echte (nicht-synthetische) Marktdaten-Szenarien sind bewusst ausgeschlossen.
4. Ein generischer Fixture-Katalog-Generator bleibt offen.
