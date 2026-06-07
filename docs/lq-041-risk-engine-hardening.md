# LQ-041 — RiskEngine Hardening Docs + Regression Coverage

## Status

* Phase 2 implemented / finalized.
* RiskEngine contract documented; regression coverage added.
* 13 ergänzende Regressionstests (`tests/test_risk_engine_hardening.py`).
* `tests/test_risk.py` unverändert (26 bestehende Tests).
* Reine Dokumentations-/Regressionsphase.
* Beschreibt den **aktuellen** RiskEngine-Code, kein Wunschdesign.
* No engine.py changes.
* No runner changes.
* No exit_reason.
* No Stop-Exit.
* No new strategy.
* No CLI changes.
* No Metrics changes.
* No CostModel changes.
* No Visual Preview changes.
* No Streamlit start.
* No dependency install.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Den bestehenden RiskEngine-Contract aus dem Code dokumentieren
  (`src/liquent/risk/engine.py`, `src/liquent/domain/models.py`).
* Ergänzende Regressionstests vorbereiten, die **bestehendes** Verhalten
  festschreiben (`tests/test_risk_engine_hardening.py`).
* Keine Produktionslogik ändern.
* Diese Doku ist **keine** Trading-Anleitung und bewertet **keine** Strategie.

## 2. Verified Current Model

Verifiziert lesend gegen den echten Code (ohne Änderung).

### RiskLimits

Quelle: `src/liquent/risk/engine.py` (`@dataclass(frozen=True) class RiskLimits`).
Konservative Platzhalter-Defaults (alle `0` / `"absolute"`):

* `max_position_size: float = 0.0`
* `max_total_exposure: float = 0.0`
* `risk_per_trade: float = 0.0`
* `max_daily_drawdown: float = 0.0`
* `risk_per_trade_pct: float = 0.0` (LQ-004, additiv)
* `max_position_notional: float = 0.0` (LQ-004, additiv)
* `max_daily_loss: float = 0.0` (LQ-004, additiv)
* `max_losing_streak: int = 0` (LQ-004, additiv)
* `sizing_mode: str = "absolute"`

### AccountState

Quelle: `src/liquent/risk/engine.py` (`@dataclass(frozen=True) class AccountState`).

* `equity: float = 0.0`
* `current_exposure: float = 0.0`
* `consecutive_losses: int = 0`
* `day_drawdown: float = 0.0`
* `day_realized_loss: float = 0.0` (LQ-004, additiv)

### RiskDecision Contract

Quelle: `src/liquent/domain/models.py` (`@dataclass(frozen=True) class RiskDecision`).

* `approved: bool`
* `size: float`
* `reason: str`
* Audit-Felder (additiv, Default): `risk_amount`, `stop_distance`, `notional`,
  `capped_by_max_position`, `capped_by_max_notional`,
  `capped_by_total_exposure`.
* **kein** `rejected`-Feld — eine Ablehnung ist `approved=False` + `reason`,
  `size=0.0` (siehe `_reject`).

### evaluate Dispatch Contract

`RiskEngine.evaluate(signal, account_state, reference_price=None)` liefert
**genau eine** `RiskDecision` und dispatcht über `limits.sizing_mode`:

* `"absolute"` (Default) → `_evaluate_absolute`; `reference_price` wird ignoriert.
* `"percent_risk"` → `_evaluate_percent_risk`; `reference_price` ist Pflicht.
* unbekannter Modus → fail-safe Ablehnung
  (`reason` enthält `"unbekannter sizing_mode"`).

### Absolute Sizing Contract

`_evaluate_absolute` (fail-safe Reihenfolge):

1. `signal is None` → reject.
2. `direction == FLAT` → reject.
3. `strength <= 0.0` → reject.
4. Limits nicht positiv (`max_position_size <= 0` **oder**
   `max_total_exposure <= 0` **oder** `risk_per_trade <= 0`) → reject.
5. `max_daily_drawdown > 0` **und** `day_drawdown >= max_daily_drawdown`
   → reject (Tages-/Drawdown-Stopp).
6. `current_exposure >= max_total_exposure` → reject.
7. Sizing ohne Risikoerhöhung nach Verlustserie:
   `proposed = min(risk_per_trade, max_position_size)`.
8. `remaining = max_total_exposure - current_exposure`;
   `size = min(proposed, remaining)`; `size <= 0` → reject.
9. sonst approve mit `size`; Audit-Felder bleiben auf Default (`0.0`/`False`).

### Percent Risk Sizing Contract

`_evaluate_percent_risk` (fail-safe Reihenfolge):

1. `signal is None` → reject.
2. `direction == FLAT` → reject.
3. `strength <= 0.0` → reject.
4. `reference_price is None` → reject; `reference_price <= 0.0` → reject.
5. `stop_price is None` → reject; `stop_price <= 0.0` → reject.
6. `equity <= 0.0` → reject.
7. `risk_per_trade_pct <= 0.0` → reject; `risk_per_trade_pct > 1.0` → reject.
8. `max_position_size <= 0.0` → reject; `max_total_exposure <= 0.0` → reject;
   `max_daily_drawdown <= 0.0` → reject.
9. Stop-Seite konsistent zur Richtung:
   * LONG: `stop_price < reference_price`, sonst reject.
   * SHORT: `stop_price > reference_price`, sonst reject.
   * `stop_distance == 0.0` → reject (defensiv; durch die Side-Checks praktisch
     bereits ausgeschlossen).
10. Stopp-/Pausen-Regeln (jeweils `>=`, Gleichheit löst aus):
    `day_drawdown >= max_daily_drawdown` → reject;
    `max_daily_loss > 0` und `day_realized_loss >= max_daily_loss` → reject;
    `max_losing_streak > 0` und `consecutive_losses >= max_losing_streak`
    → reject; `current_exposure >= max_total_exposure` → reject.
11. Sizing:
    `risk_amount = equity * risk_per_trade_pct`,
    `stop_distance = abs(reference_price - stop_price)`,
    `size = risk_amount / stop_distance`.
12. Caps siehe „Cap Order"; danach `size <= 0` → reject.
13. sonst approve mit `size`, `risk_amount`, `stop_distance`, `notional` und den
    gesetzten `capped_by_*`-Flags.

## 3. Fail-safe / Reject Order

* Grundsatz: erst **alle** Ablehnungsgründe prüfen, nur dann freigeben
  (fail-safe statt fail-open).
* Jede Ablehnung trägt eine `reason` und `size = 0.0`.
* Reihenfolge ist im Code festgelegt (siehe Absolute/Percent Risk Contract
  oben). Diese Doku schreibt die Reihenfolge nicht neu vor, sondern hält den
  Ist-Zustand fest.

## 4. Cap Order

Im `percent_risk`-Modus wird `size` ausschließlich **verkleinert** (nie
vergrößert), in fester Reihenfolge; jede greifende Grenze setzt ihr Audit-Flag:

1. `max_position_size` (Einheiten) → `capped_by_max_position`.
2. `max_position_notional` **nur falls `> 0`** und
   `size * reference_price > max_position_notional`
   → `size = max_position_notional / reference_price`,
   `capped_by_max_notional`.
3. verbleibendes `max_total_exposure - current_exposure`
   → `capped_by_total_exposure`.

Mehrere Caps können in einem Lauf gleichzeitig greifen (mehrere Flags `True`).

## 5. Regression Invariants

* Jedes Signal erzeugt **genau eine** `RiskDecision`.
* Fail-safe: bei Unsicherheit/Fehlkonfiguration → ablehnen.
* Kein Martingale: nach Verlustserie wird das Risiko **nie** erhöht; im
  `percent_risk`-Modus ist `size` unabhängig von `consecutive_losses`
  (bis ein konfiguriertes `max_losing_streak` pausiert).
* `absolute` ist und bleibt der Default; `reference_price` wird dort ignoriert,
  Audit-Felder bleiben auf Default.
* `"absolute"`-Verhalten ist gegenüber LQ-005 unverändert.

## 6. Safety Boundaries

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

## 7. README/Roadmap Impact

README:

* LQ-041-Link in Phase 2 ergänzt,
* Teststand aktualisiert.

Roadmap:

* LQ-041 als RiskEngine-Hardening-/Regression-Track ergänzt (Phase 2).
* Status:
  * RiskEngine contract documented,
  * additional regression coverage added,
  * no engine logic changes,
  * Runner Lifecycle bleibt gemäß LQ-040 pausiert.

Visual Preview Index:

* nicht erweitern,
* LQ-041 ist kein Visual-Preview-Track.

## 8. Phase Plan

* **Phase 1** (abgeschlossen): Doku-Entwurf + Lückenabgleich gegen
  `tests/test_risk.py`; Entwurf von `tests/test_risk_engine_hardening.py`.
  Kein Commit.
* **Phase 2** (diese): Doku finalisiert, Tests finalisiert, optionaler Doku-/
  Link-Test (`tests/test_risk_engine_hardening_doc.py`), README/Roadmap minimal
  verlinkt, Teststand aktualisiert. Kein Commit.
* **Phase 3**: Commit der erwarteten Dateien. Kein Push ohne separate Freigabe.

## 8a. Implementation Status (Phase 2)

* RiskEngine contract documented (Verified Current Model, Dispatch, Absolute /
  Percent Risk, Fail-safe / Reject Order, Cap Order, Regression Invariants).
* 13 ergänzende Regressionstests hinzugefügt
  (`tests/test_risk_engine_hardening.py`) — Behavior-Lock, keine neuen Features.
* `tests/test_risk.py` unverändert.
* `src/liquent/risk/engine.py` unverändert (keine Produktionslogik geändert).
* `src/liquent/domain/models.py` unverändert.
* README-Link + Teststand aktualisiert.
* Roadmap-Link + Status aktualisiert.
* Doku-/Link-Test hinzugefügt: 9 Tests
  (`tests/test_risk_engine_hardening_doc.py`).
* Visual Preview Index unverändert.
* No exit_reason, no Stop-Exit, no new strategy.
* No dependency installed, no Streamlit start, no real data, no artefacts.
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).

## 9. Test Plan

Ergänzende Regressionstests in `tests/test_risk_engine_hardening.py` — sie
schreiben ausschließlich **bestehendes** Verhalten fest (keine neuen Features,
keine Änderung an `tests/test_risk.py`).

Adoptierte Lücken (echtes, bisher nicht explizit gesichertes Verhalten):

* **absolute** — `size = min(risk_per_trade, max_position_size)`, beide
  Bindungsrichtungen.
* **absolute** — verbleibendes Exposure deckelt `size`
  (`size = min(proposed, remaining)`).
* **absolute** — `day_drawdown == max_daily_drawdown` (Gleichheit) → reject.
* **absolute** — `FLAT`-Signal → reject.
* **percent_risk** — `reference_price <= 0` (Wert, nicht `None`) → reject.
* **percent_risk** — `stop_price <= 0` (Wert, nicht `None`) → reject.
* **percent_risk** — Config-Rejects: `max_daily_drawdown <= 0`,
  `max_position_size <= 0`, `max_total_exposure <= 0`.
* **percent_risk** — mehrere Caps greifen gleichzeitig (finale `size` + alle
  drei `capped_by_*`-Flags + Cap-Reihenfolge).
* **percent_risk** — kein Scaling mit `consecutive_losses` unterhalb des
  Streak-Limits (`size` identisch).
* **Invariante** — jeder geprüfte Pfad liefert genau eine `RiskDecision` mit
  `approved`-bool, `size`-float und (bei Ablehnung) nichtleerer `reason`.

Bewusst **nicht** übernommen (bereits abgedeckt in `tests/test_risk.py`):

* `current_exposure == max_total_exposure` (test_exposure_limit_blocks_new_risk).
* `day_drawdown ==` / `consecutive_losses ==` im percent_risk-Modus
  (Tests 14 / 16).
* `risk_per_trade_pct > 1.0` (Test 9), `equity <= 0` (Test 10).
* aktiver Notional-Cap (Test 12), Audit-Felder bei Approval (Test 18).

Bewusst **nicht** als Test übernommen (im Code defensiv, aber praktisch
unerreichbar):

* `stop_distance == 0` (durch die strikten Side-Checks ausgeschlossen).
* `size <= 0`-Reject im absolute-Modus (der Exposure-Check greift davor).

## 10. Non-Goals

* keine Änderung an `src/liquent/risk/engine.py` (Produktionslogik),
* keine Änderung an `src/liquent/domain/models.py`,
* keine Änderung an `tests/test_risk.py`,
* kein `exit_reason`, keine Stop-Exit-Logik,
* keine neuen Sizing-Modi,
* keine fachliche Festlegung der Platzhalter-Limits,
* keine Runner-/CostModel-/Metrics-/CLI-/Strategie-/Visual-Preview-Änderung,
* keine Echtdaten, keine CSV-/Screenshot-/Report-Artefakte,
* keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 11. Open Decisions / Deferred Topics

1. Sollen die Platzhalter-Limit-Defaults fachlich festgelegt werden
   (separater Task)?
2. Soll der defensive `stop_distance == 0`-Pfad langfristig erreichbar bleiben
   oder als toter Zweig markiert werden?
3. Soll der `size <= 0`-Reject im absolute-Modus dokumentiert toter Zweig
   bleiben?
4. Soll `max_daily_loss` / `day_realized_loss` über den percent_risk-Modus
   hinaus genutzt werden?
5. Soll der absolute-Modus eigene Notional-/Streak-Limits erhalten (derzeit nur
   percent_risk)?
