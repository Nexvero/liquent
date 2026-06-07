# LQ-048 — Domain Model Invariants Documentation / Validation Decision

## Status

* Phase 2 implemented.
* Domain model invariants / validation decision finalized.
* Current decision documented: document invariants and keep domain models as
  pure data structures.
* No runtime validation implemented.
* No validator functions implemented.
* No `__post_init__` validation.
* No production code changes.
* No src changes.
* No tools changes.
* No pyproject changes.
* No dependency installed.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Dieses Dokument folgt auf LQ-047
  (`docs/lq-047-domain-model-hardening.md`).
* Es klärt, ob Domain-Invarianten dokumentiert, getestet oder später validiert
  werden sollen.
* Es schützt die Domain Models vor unkontrollierten Breaking Changes.
* Es ist **keine** Trading-Anleitung.
* Es bewertet **keine** Strategie.

## 2. Verified Current Domain Model

Verifiziert gegen `src/liquent/domain/models.py` (nur echte Feldnamen).

### Enums

* `Direction` (`LONG` / `SHORT` / `FLAT`)
* `PositionStatus` (`OPEN` / `CLOSED`)

### Frozen dataclasses

* `Instrument`
* `MarketData`
* `OrderBookLevel`
* `OrderBookSnapshot`
* `LiquidityMetric`
* `Signal`
* `RiskDecision`
* `Position`
* `Experiment`

### Defaults

* `OrderBookLevel.side = Direction.FLAT`
* `OrderBookSnapshot.levels` → `default_factory=list`
* `LiquidityMetric.timestamp = None`
* `Signal.metric = None`
* `Signal.stop_price = None`
* `RiskDecision` audit defaults (`0.0` / `False`)
* `Position.status = PositionStatus.OPEN`
* `Experiment.parameter` → `default_factory=dict`
* `Experiment.metriken` → `default_factory=dict`

### Current Design

* Datenstrukturen sind frozen.
* Mutable Defaults werden über `default_factory` isoliert.
* Fachliche Invarianten sind dokumentiert oder implizit, aber **nicht** erzwungen.
* Keine `__post_init__`-Validierung.
* Keine separate Validator-Schicht.

## 3. Candidate Invariants

Mögliche fachliche Invarianten (dokumentiert, **nicht** implementiert). Es werden
ausschließlich **real existierende** Feldnamen verwendet.

### MarketData

* `bid > 0`
* `ask > 0`
* `ask >= bid`
* `volume >= 0` (oder `> 0`, Entscheidung offen)
* `timestamp` timezone-aware (UTC), falls später als Contract gewünscht

### OrderBookLevel

* `price > 0`
* `size >= 0` (oder `> 0`, Entscheidung offen)
* `side` ist `Direction`

### OrderBookSnapshot

* `timestamp` vorhanden
* `levels` ist Liste
* leere `levels` erlaubt oder nicht (Entscheidung offen)

### LiquidityMetric

* `spread`, `depth`, `imbalance` sind numerische technische Felder
* `timestamp` optional
* keine erfundenen value/score/rating-Felder

### Signal

* `direction` ist `Direction`
* `strength` numerisch (Pflichtfeld)
* `metric` optional
* `stop_price` optional
* wenn `stop_price` vorhanden, dann `> 0`, falls später entschieden

### RiskDecision

* `approved` ist `bool`
* `size >= 0`, falls als Contract entschieden
* `reason` optional oder Pflicht bei Ablehnung (Entscheidung offen; die
  RiskEngine befüllt es bereits bei Ablehnung)
* Audit-Felder bleiben Defaults

### Position

* `instrument` ist `Instrument`
* `entry` ist der technische Entry-Wert
* `size` ist der technische Größenwert
* `status` ist `PositionStatus`
* kein quantity-Feld behaupten
* kein entry_price-Feld behaupten

### Experiment

* `parameter` ist `dict`
* `metriken` ist `dict`
* keine Mutable-Default-Leakage (durch LQ-047 abgesichert)
* kein metrics-Feld behaupten (im Code existiert nur `metriken`)

> Hinweis: Keine Invariante wird über ein nicht-existierendes Feld behauptet.
> `Position` hat **kein** `quantity`/`entry_price`; `LiquidityMetric` hat
> **kein** value/score/rating; `Experiment` nutzt `metriken`, **kein** metrics.

## 4. Validation Placement Options

### Option A — Documentation only

* Invarianten bleiben dokumentiert.
* Keine Runtime-Validierung.
* LQ-047 Behavior-Locks bleiben Hauptschutz.

### Option B — Test-only contract

* Invarianten werden in Tests als gewünschter Contract dokumentiert.
* Keine Runtime-Validierung.
* Tests dürfen **nicht** behaupten, dass Runtime-Validation existiert.

### Option C — Separate validation functions

* Validierung außerhalb der dataclasses; mögliche spätere Funktionen:
  `validate_market_data(...)`, `validate_signal(...)`,
  `validate_risk_decision(...)`. Kein `__post_init__`.

### Option D — `__post_init__` inside frozen dataclasses

* harte Runtime-Invarianten direkt in den Models.
* aktuell **nicht** empfohlen (Breaking Change, brüchige Fixtures/Parser).

### Option E — Pydantic or external validation layer

* zusätzliche Dependency/Komplexität.
* aktuell **nicht** empfohlen.

## 5. Recommended Decision

Aktuelle Empfehlung:

* **Option A + B** jetzt.
* Domain Models bleiben reine Datenstrukturen.
* Invarianten dokumentieren.
* Behavior-Locks behalten.
* Keine Runtime-Validierung in Domain Models.
* Keine `__post_init__`-Validierung.
* Wenn später Validierung benötigt wird:
  * **Option C** bevorzugen,
  * separate Validator-Funktionen außerhalb der frozen dataclasses,
  * zuerst Tests, dann Validator.
* **Option D** und **E** aktuell nicht umsetzen.

Begründung:

* LQ-047 hat den Datenstruktur-Charakter abgesichert.
* Harte Invarianten wären ein Breaking Change.
* Separate Validatoren wären später kontrollierter.
* DataSource-/Parser-Validierung sollte nicht mit Domain-Datencontainern
  vermischt werden.

## 6. Recommended Future Test Strategy

* Doku-/Contract-Tests für dokumentierte Invarianten.
* Negative Tests nur gegen separate Validatoren, falls Option C später kommt.
* Keine Tests, die aktuell Runtime-Validation erwarten.
* Fixture-Kompatibilität prüfen.
* DataSource-Loader-Validierung separat halten.
* RiskEngine-Validierung separat halten.
* Domain-Model-Behavior-Locks aus LQ-047 beibehalten.

## 7. Compatibility / Risk Analysis

* Runtime-Validierung könnte bestehende synthetische Tests brechen.
* Frozen dataclasses mit `__post_init__` sind schwerer zu erweitern.
* DataSource-Parser könnten doppelte Validierung bekommen.
* Die RiskEngine sollte fachliche Risikoentscheidung bleiben, **nicht**
  allgemeiner Model-Validator.
* Die CLI sollte keine Domain-Model-Validierung duplizieren.
* Visual Preview bleibt unberührt.

## 8. Safety Boundaries

* No API keys.
* No exchange credentials.
* No network calls by Liquent.
* No external data download by Liquent.
* No live data source.
* No orders.
* No paper-trading connection.
* No real CSV files committed.
* No screenshots committed.
* No reports generated.
* No profitability assessment.
* No trading recommendation.

## 9. README/Roadmap Impact

README:

* LQ-048-Link wird ergänzt.

Roadmap:

* LQ-048 als Domain-Model-invariants-/validation-decision ergänzt.
* Status:
  * recommendation: document invariants; no runtime validation in domain models,
  * future validation should prefer separate validator functions.

Visual Preview Index:

* bleibt unverändert,
* LQ-048 ist kein Visual-Preview-Track.

## 10. Phase 2 Implementation Status

* Domain model invariants / validation decision finalized.
* Verified current domain model documented.
* Candidate invariants documented.
* Validation placement options documented (A–E).
* Recommended decision documented (A + B now; C later if needed; D/E not now).
* Future test strategy documented.
* Compatibility / risk analysis documented.
* README link added.
* Roadmap link added.
* Doku-tests added (`tests/test_domain_model_invariants_validation_decision_doc.py`).
* Visual Preview Index unchanged.
* No runtime validation implemented.
* No validator functions implemented.
* No `__post_init__` validation.
* No production logic changes; `src/liquent/domain/models.py` unverändert.
* No src changes, no tools changes, no pyproject changes.
* No dependency installed, no Streamlit start, no real data, no CSV files, no
  screenshots, no reports.
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).
