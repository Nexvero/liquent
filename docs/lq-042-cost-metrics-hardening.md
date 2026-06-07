# LQ-042 — CostModel/Metrics Hardening Docs + Regression Coverage

## Status

* Phase 2 implemented / finalized.
* CostModel / Metrics contract documented; regression coverage added.
* 12 ergänzende Regressionstests (`tests/test_cost_metrics_hardening.py`).
* `tests/test_backtesting.py` unverändert.
* Reine Dokumentations-/Regressionsphase.
* Beschreibt den **aktuellen** CostModel-/Metrics-Code, kein Wunschdesign.
* No metrics.py changes.
* No runner.py / CostModel logic changes.
* No new cost formula.
* No new metrics.
* No default value changes.
* No exit_reason.
* No Stop-Exit.
* No Runner-Lifecycle change.
* No new strategy.
* No Streamlit start.
* No dependency install.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Den bestehenden CostModel-/Metrics-Contract aus dem Code dokumentieren
  (`src/liquent/backtesting/runner.py` für `CostModel`,
  `src/liquent/backtesting/metrics.py` für `calculate_trade_costs` und die
  Mindestmetriken).
* Ergänzende Regressionstests vorbereiten, die **bestehendes** Verhalten
  festschreiben (`tests/test_cost_metrics_hardening.py`).
* Keine Produktionslogik ändern.
* Diese Doku ist **keine** Trading-Anleitung und bewertet **keine** Strategie.

## 2. Verified Current Model

Verifiziert lesend gegen den echten Code (ohne Änderung).

### CostModel Contract

Quelle: `src/liquent/backtesting/runner.py`
(`@dataclass(frozen=True) class CostModel`).

* `fee_rate: float = 0.0` — Anteil des Notional (z. B. `0.001` = 0.1 %).
* `spread: float = 0.0` — absoluter Preisaufschlag **pro Einheit**.
* `slippage: float = 0.0` — Anteil des Notional (z. B. `0.0005` = 0.05 %).
* Alle Defaults `0.0` ⇒ frictionless (`CostModel()` erzeugt kostenfreie Läufe).
* `frozen=True` ⇒ immutable.

### calculate_trade_costs Contract

Quelle: `src/liquent/backtesting/metrics.py`
(`calculate_trade_costs(price, quantity, cost_model)`), reine Funktion:

```
notional      = abs(price * quantity)
fee_cost      = notional * fee_rate
spread_cost   = abs(quantity) * spread
slippage_cost = notional * slippage
total_cost    = fee_cost + spread_cost + slippage_cost
```

* Ergebnis ist stets `>= 0` (Beträge über `abs()`).
* Vorzeichenbehaftete Verrechnung mit dem PnL ist Sache des Runners, **nicht**
  dieser Funktion.

### Cost Convention

* **Spread** ist **per-Einheit** modelliert (`abs(quantity) * spread`) — er
  hängt **nicht** vom Preis ab.
* **fee** und **slippage** sind **notional-basiert**
  (`abs(price * quantity) * rate`) — sie skalieren mit Preis **und** Menge.
* `abs()` macht die Kosten symmetrisch in Vorzeichen von `price` und
  `quantity`: negative Werte ergeben identische, nicht-negative Kosten. Dies ist
  ein reiner **Code-Contract** (mathematische Eigenschaft der Funktion), **keine**
  fachliche Marktannahme.
* `total_cost` ist exakt die Summe der drei Komponenten (additive Zerlegung).

### Metrics Contracts

Quelle: `src/liquent/backtesting/metrics.py` (reine Funktionen über
`Sequence[TradeResult]` bzw. `Sequence[float]`):

* `number_of_trades(trades)` → `len(trades)`.
* `win_rate(trades)` → Anteil mit `net_pnl > 0`; leere Liste → `0.0`.
  Ein `net_pnl == 0` zählt **nicht** als Win.
* `profit_factor(trades)` → `gross_profit / gross_loss` auf `net_pnl`-Basis;
  nur gewinnende Trades → `float("inf")`; leer oder ausschließlich `0.0` → `0.0`.
  `net_pnl == 0` fließt **weder** in `gross_profit` **noch** in `gross_loss`.
* `max_drawdown(equity_curve)` → maximaler Peak-to-Trough-Rückgang (≥ 0); leere
  Kurve → `0.0`; das laufende Peak wird bei neuen Hochs aktualisiert.
* `average_r_multiple(trades)` → Mittel der `r_multiple`; leer → `0.0`.
* `expectancy(trades)` → Mittel des `net_pnl`; leer → `0.0`.
* `exposure_time(trades, total_bars)` → `Σ(duration_bars) / total_bars`;
  `total_bars <= 0` → `0.0`. Der Wert **kann > 1.0** werden, wenn die Summe der
  `duration_bars` die `total_bars` übersteigt (reine Konvention, keine
  Bewertung).
* `worst_losing_streak(trades)` → längste Folge mit `net_pnl < 0`; leer → `0`.
  Ein `net_pnl == 0` **unterbricht** die Serie (Bedingung ist strikt `< 0`).
* `best_trade(trades)` → `max(net_pnl)`; leer → `0.0`.
* `worst_trade(trades)` → `min(net_pnl)`; leer → `0.0`. Bei rein negativer Liste
  ist `best_trade` der kleinste Verlustbetrag (das Maximum bleibt negativ).

### Edge-Case Table

| Funktion | Eingang | Ergebnis (aktuell) |
|---|---|---|
| `calculate_trade_costs` | `quantity == 0` | `0.0` |
| `calculate_trade_costs` | negative `quantity` | identisch zu positiver `quantity` (≥ 0) |
| `calculate_trade_costs` | negative `price` | identisch zu positivem `price` (Code-Contract) |
| `calculate_trade_costs` | `CostModel()` | `0.0` (frictionless) |
| `win_rate` | `net_pnl == 0` | zählt nicht als Win |
| `profit_factor` | nur gewinnende Trades | `float("inf")` |
| `profit_factor` | leer / nur `0.0` | `0.0` |
| `profit_factor` | `net_pnl == 0` gemischt | wird ignoriert (weder Gewinn noch Verlust) |
| `max_drawdown` | leere Kurve | `0.0` |
| `max_drawdown` | Erholung + tieferer Trough | größter Peak-to-Trough-Rückgang |
| `exposure_time` | `total_bars <= 0` | `0.0` |
| `exposure_time` | `Σ bars > total_bars` | `> 1.0` |
| `worst_losing_streak` | `net_pnl == 0` in Serie | unterbricht die Serie |
| `best_trade` / `worst_trade` | leere Liste | `0.0` |
| `best_trade` | rein negative Liste | kleinster Verlustbetrag (negativ) |

## 3. Regression Invariants

* Kosten sind deterministisch und stets `>= 0`.
* `total_cost == fee_cost + spread_cost + slippage_cost` (additive Zerlegung).
* Spread ist per-Einheit; fee/slippage sind notional-basiert.
* Alle Metriken liefern für die leere Liste sichere Defaults (`0.0` / `0`).
* `net_pnl == 0` ist neutral: kein Win, kein Verlust, unterbricht Verlustserien.
* Reine Funktionen: keine Seiteneffekte, kein I/O, nur Standardbibliothek.

## 4. Safety Boundaries

* No API keys.
* No exchange credentials.
* No network calls by Liquent.
* No external data download by Liquent.
* No live data source.
* No orders.
* No paper-trading connection.
* No real CSV files committed.
* No screenshots committed.
* No report files generated.
* No profitability assessment.
* No trading recommendation.
* No equity/performance display as decision basis.

## 5. README/Roadmap Impact

README:

* LQ-042-Link in Phase 2 ergänzt,
* Teststand aktualisiert.

Roadmap:

* LQ-042 als CostModel-/Metrics-Hardening-/Regression-Track ergänzt (Phase 2).
* Status:
  * CostModel / Metrics contract documented,
  * additional regression coverage added,
  * no production logic changes,
  * Runner Lifecycle bleibt gemäß LQ-040 pausiert.

Visual Preview Index:

* nicht erweitern,
* LQ-042 ist kein Visual-Preview-Track.

## 6. Phase Plan

* **Phase 1** (abgeschlossen): Doku-Entwurf + Lückenabgleich gegen
  `tests/test_backtesting.py`; Entwurf von
  `tests/test_cost_metrics_hardening.py`. Kein Commit.
* **Phase 2** (diese): Doku finalisiert, Tests finalisiert, Doku-/Link-Test
  (`tests/test_cost_metrics_hardening_doc.py`), README/Roadmap minimal verlinkt,
  Teststand aktualisiert. Kein Commit.
* **Phase 3**: Commit der erwarteten Dateien. Kein Push ohne separate Freigabe.

## 6a. Implementation Status (Phase 2)

* CostModel / Metrics contract documented (Verified Current Model, Cost
  Convention, Metrics Contracts, Edge-Case Table, Regression Invariants).
* 12 ergänzende Regressionstests hinzugefügt
  (`tests/test_cost_metrics_hardening.py`) — Behavior-Lock, keine neuen Features.
* `tests/test_backtesting.py` unverändert.
* `src/liquent/backtesting/metrics.py` unverändert (keine Produktionslogik).
* `src/liquent/backtesting/runner.py` / `CostModel` unverändert.
* CostModel bleibt frictionless per Default; Spread bleibt per-Einheit;
  fee/slippage bleiben notional-basiert.
* negative `quantity` ist als `abs()`-Code-Contract abgesichert.
* negative `price` ist bewusst **nicht** getestet, nur als fachlich
  missverständlicher mathematischer Code-Contract dokumentiert.
* README-Link + Teststand aktualisiert.
* Roadmap-Link + Status aktualisiert.
* Doku-/Link-Test hinzugefügt: 9 Tests
  (`tests/test_cost_metrics_hardening_doc.py`).
* Visual Preview Index unverändert.
* No exit_reason, no Stop-Exit, no new strategy, no new metric, no new cost
  formula, no default changes.
* No dependency installed, no Streamlit start, no real data, no artefacts.
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).

## 7. Test Plan

Ergänzende Regressionstests in `tests/test_cost_metrics_hardening.py` — sie
schreiben ausschließlich **bestehendes** Verhalten fest (keine neuen Features,
keine Änderung an `tests/test_backtesting.py`).

Adoptierte Lücken (echtes, bisher nicht explizit gesichertes Verhalten):

* **cost** — fee-only ist notional-basiert (skaliert mit Preis und Menge).
* **cost** — spread-only ist per-Einheit (preisunabhängig, skaliert mit Menge).
* **cost** — slippage-only ist notional-basiert.
* **cost** — `quantity == 0` → `0.0`.
* **cost** — negative `quantity` ergibt identische, nicht-negative Kosten
  (reiner Code-Contract über `abs()`).
* **cost** — additive Zerlegung: `total == fee_only + spread_only + slippage_only`.
* **metrics** — `win_rate`: `net_pnl == 0` zählt nicht als Win.
* **metrics** — `worst_losing_streak`: `net_pnl == 0` unterbricht die Serie.
* **metrics** — `max_drawdown`: Erholung und danach tieferer Trough (neues Peak).
* **metrics** — `exposure_time` kann `> 1.0` werden.
* **metrics** — `best_trade`/`worst_trade` bei rein negativer Liste.
* **metrics** — `profit_factor` ignoriert `net_pnl == 0` in beiden Summen.

Bewusst **nicht** als Test übernommen (fachlich missverständlich, nur
mathematischer Code-Contract ohne sinnvollen Domain-Wert):

* negative `price`-Symmetrie — ein negativer Preis ist kein realistischer
  Marktwert; ein Test könnte als fachliche Marktannahme missverstanden werden.
  Die `abs()`-Symmetrie ist bereits über die negative `quantity` als
  Code-Contract abgesichert. Nur dokumentiert (siehe Edge-Case Table /
  Deferred Topics), nicht getestet.

Bewusst **nicht** übernommen (bereits abgedeckt in `tests/test_backtesting.py`):

* kombinierte Kosten fee+spread+slippage; `CostModel()` frictionless.
* `win_rate` leer / Standardfall; `profit_factor` normal / `inf` / leer /
  all-zero.
* `max_drawdown` leer / einfacher Drawdown / monoton steigend.
* `exposure_time` Standardfall / `total_bars <= 0` / leer.
* `worst_losing_streak` leer / Unterbrechung durch Gewinn.
* `best_trade`/`worst_trade` gemischte Liste; alle Leerlisten-Defaults.

## 8. Non-Goals

* keine Änderung an `src/liquent/backtesting/metrics.py` (Produktionslogik),
* keine Änderung an `src/liquent/backtesting/runner.py` / `CostModel`,
* keine Änderung an `tests/test_backtesting.py`,
* keine neue Kostenformel, keine neuen Metriken, keine geänderten Defaults,
* kein `exit_reason`, keine Stop-Exit-Logik, keine Runner-Lifecycle-Änderung,
* keine RiskEngine-/CLI-/Strategie-/Visual-Preview-Änderung,
* keine Echtdaten, keine CSV-/Screenshot-/Report-Artefakte,
* keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 9. Deferred Topics

1. Negative `price`/`quantity` werden nur als mathematischer Code-Contract
   dokumentiert; eine fachliche Marktsemantik (Short-Notation o. Ä.) ist
   separat zu klären.
2. `exposure_time > 1.0` bleibt als Konvention bestehen; ob überlappende
   Positionen jemals modelliert werden, ist ein späterer Runner-Track (derzeit
   Close-to-Close, keine Überlappung).
3. Fachliche Festlegung realistischer `CostModel`-Defaultwerte (separater Task,
   06_Backtesting).
4. Mögliche Erweiterung des Kostenmodells (Gebührenstaffeln, komplexeres
   Slippage-Modell) bleibt außerhalb dieses Tracks.
