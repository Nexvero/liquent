# LQ-039 — Explicit Exit Reason and Stop-Exit Specification

## Status

* Phase 2 implemented.
* Explicit exit_reason / stop-exit specification finalized.
* Current model documented.
* Proposed exit_reason model documented.
* Stop-exit semantics proposal documented.
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

* Dieses Dokument folgt auf LQ-038
  (`docs/lq-038-runner-lifecycle-stop-exit-semantics.md`).
* Es bereitet eine mögliche spätere Erweiterung vor.
* Es definiert **keine** neue aktuelle Runner-Semantik.
* Es ist **keine** Trading-Anleitung.
* Es bewertet **keine** Strategie.

## 2. Verified Current Model

Verifiziert lesend gegen den echten Code (ohne Änderung):
`src/liquent/domain/models.py`, `src/liquent/backtesting/metrics.py`,
`src/liquent/backtesting/runner.py`, `src/liquent/risk/engine.py`.

### Signal

Quelle: `src/liquent/domain/models.py` (`@dataclass(frozen=True) class Signal`).

* `timestamp`
* `direction` (`Direction`: `long` / `short` / `flat`)
* `strength`
* `metric` (`LiquidityMetric | None`, Default `None`)
* `stop_price` (`float | None`, Default `None`, aktuell sizing-only)
* kein `side`-Feld
* kein `price`-Feld

### RiskDecision

Quelle: `src/liquent/domain/models.py`
(`@dataclass(frozen=True) class RiskDecision`).

* `approved` (`bool`)
* `size` (`float`)
* `reason` (`str`)
* Audit-Felder (verifiziert, additiv): `risk_amount`, `stop_distance`,
  `notional`, `capped_by_max_position`, `capped_by_max_notional`,
  `capped_by_total_exposure`
* kein `rejected`-Feld (Ablehnung = `approved=False` + `reason`)

### TradeResult

Quelle: `src/liquent/backtesting/metrics.py`
(`@dataclass(frozen=True) class TradeResult`). Aktuelle echte Felder:

* `entry_price`
* `exit_price`
* `quantity`
* `side` (`"long"` / `"short"`)
* `gross_pnl`
* `costs`
* `net_pnl`
* `r_multiple`
* `duration_bars`
* `entry_time`
* `exit_time`
* kein `exit_reason`
* kein `opened_at`
* kein `closed_at`

### Current Exit

Quelle: `src/liquent/backtesting/runner.py` (`BacktestRunner.run`).

* Close-to-Close.
* Mid/Folge-Bar-Logik (verifiziert): Entry zum Mid `(bid + ask) / 2` des
  referenzierten Bars, Exit zum Mid des Folge-Bars, `duration_bars = 1`.
* `stop_price` beeinflusst den Exit **nicht** (sizing-only).
* kein Stop-Exit.
* Der LQ-037-Regressionstest schützt dieses Verhalten
  (`tests/test_backtest_runner_regressions.py`).

## 3. Proposed Exit Reason Model

Spezifikationsentwurf (nicht implementiert):

Mögliche `exit_reason`-Werte:

* `close_to_close`
* `stop_exit`
* `end_of_data`

Optional später:

* `strategy_exit`
* `max_bars_exit`

Regeln:

* `exit_reason` ist ein rein technisches Feld.
* `exit_reason` ist **keine** Bewertung.
* `exit_reason` ist **keine** Empfehlung.
* `exit_reason` sagt nur aus, warum ein simulierter Trade technisch geschlossen
  wurde.

## 4. Stop-Exit Semantics Proposal

Mögliche Semantik (dokumentiert, **nicht** implementiert):

### Long

* `stop_price` liegt technisch unter oder gleich dem Entry-Preis.
* Stop-Hit, wenn ein späterer Bar-Mid oder ein definierter Bar-Preis
  `<= stop_price` ist.
* Exit-Preis wäre `stop_price` oder ein definierter Ausführungspreis.
* Diese Wahl muss vor Implementierung final entschieden werden.

### Short

* `stop_price` liegt technisch über oder gleich dem Entry-Preis.
* Stop-Hit, wenn ein späterer Bar-Mid oder ein definierter Bar-Preis
  `>= stop_price` ist.
* Exit-Preis wäre `stop_price` oder ein definierter Ausführungspreis.
* Diese Wahl muss vor Implementierung final entschieden werden.

### Same-bar vs next-bar

* Same-bar Stop-Check könnte zu sofortigem Exit führen.
* Next-bar Stop-Check ist einfacher und vermeidet Reihenfolge-Unklarheiten.
* Empfehlung: für die erste Implementierung nur next-bar prüfen.

### Preisbasis

Offene Optionen:

* `mid`
* `bid`/`ask`
* OHLCV `high`/`low`, falls die Datenquelle das hergibt.

Empfehlung:

* zunächst keine OHLCV-Intrabar-Semantik erzwingen,
* der bestehende Runner arbeitet mit Mid / Close-to-Close,
* ein Stop-Exit müsste mit der aktuell vorhandenen Datenbasis kompatibel
  bleiben (`MarketData` liefert `bid`/`ask`, kein OHLC).

## 5. Data Model Impact

### Minimal Change

* `TradeResult` erhält später optional/neu `exit_reason: str`.
* Bestehende Felder bleiben erhalten.
* Default für das bestehende Close-to-Close-Verhalten: `close_to_close`.

### Compatibility

* Bestehende Tests müssten bewusst angepasst oder erweitert werden.
* LQ-037-Tests, die aktuell **kein** `exit_reason` erwarten, müssten bewusst
  geändert werden.
* Reporting muss `exit_reason` neutral durchreichen, falls relevant.
* CLI darf `exit_reason` nur technisch anzeigen, falls später spezifiziert.

### Nicht empfohlen

* Stop-Exit ohne `exit_reason` einführen.
* Exit-Preis ändern, ohne den Grund sichtbar zu machen.
* Visual Preview direkt erweitern.

## 6. Runner Impact

* Der Runner müsste die Exit-Auswahl explizit machen.
* Mögliche Reihenfolge:
  1. Signal `approved` (Risk-First, unverändert),
  2. Entry simuliert,
  3. Folge-Bar prüfen,
  4. Stop-Exit oder Close-to-Close wählen,
  5. `TradeResult` mit `exit_reason` erzeugen.
* Die RiskEngine bleibt für Approval/Sizing zuständig.
* Die Stop-Ausführung gehört in den Runner, **nicht** in die RiskEngine.
* Keine Live-Order.

## 7. Metrics / Reporting / CLI Impact

* Metrics können sich technisch ändern (anderer Exit-Preis → andere PnL).
* Reporting kann `exit_reason_counts` neutral anzeigen.
* CLI kann später optional Exit-Gründe anzeigen.
* Keine Bewertungssprache.
* Kein Ranking.
* Keine Strategieempfehlung.
* Keine automatische Reportdatei.

## 8. Test Plan Before Implementation

### Data Model Tests

* `TradeResult` hat `exit_reason`.
* Default `close_to_close` für bestehendes Verhalten.
* Keine bestehenden Felder verschwinden.

### Runner Tests

* `close_to_close` erzeugt `exit_reason` `close_to_close`.
* Long Stop-Hit erzeugt `stop_exit`.
* Short Stop-Hit erzeugt `stop_exit`.
* `end_of_data` erzeugt `end_of_data`, falls später definiert.
* `stop_price` fehlt: kein Stop-Exit.
* `stop_price`-Sizing bleibt mit der RiskEngine konsistent.

### Ordering Tests

* next-bar-Regel explizit.
* Same-bar wird nicht geprüft, falls die Empfehlung übernommen wird.

### Cost/Metrics Tests

* Kosten werden nach dem Exit-Preis berechnet.
* Metrics bleiben deterministisch.
* `equity_curve` bleibt deterministisch.

### Reporting/CLI Tests

* `exit_reason` wird neutral angezeigt, falls angezeigt.
* keine Report-Artefakte.
* keine Visual-Preview-Änderung.

## 9. Recommended Decision for Later Implementation

* Keine Implementierung direkt nach Phase 2.
* Wenn Stop-Exit gewünscht ist:
  1. erst LQ-039 committen und pushen,
  2. danach separate Implementierungsphase planen,
  3. zuerst Tests für `exit_reason`,
  4. dann minimale `TradeResult`-Erweiterung,
  5. dann Runner-`exit_reason` für `close_to_close`,
  6. erst danach Stop-Exit.
* Stop-Exit **nicht** ohne `exit_reason` implementieren.
* Visual Preview bleibt außen vor.

## 10. Safety Boundaries

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

## 11. README/Roadmap Impact

README:

* LQ-039-Link wird ergänzt.

Roadmap:

* LQ-039 als optionaler future spec ergänzt.
* Status:
  * exit_reason / stop-exit specification finalized,
  * no implementation,
  * Stop-Exit remains out of the current Runner contract until separately
    approved.

Visual Preview Index:

* bleibt unverändert,
* LQ-039 ist kein Visual-Preview-Track.

## 12. Phase 2 Implementation Status

* Specification finalized.
* Verified current model documented.
* Proposed exit_reason model documented.
* Stop-exit semantics proposal documented.
* Data model impact documented.
* Runner impact documented.
* Metrics/Reporting/CLI impact documented.
* Test plan before implementation documented.
* Recommended decision documented.
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
