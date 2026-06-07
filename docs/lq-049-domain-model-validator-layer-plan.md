# LQ-049 — Domain Model Validator Layer Decision / Implementation Plan

## Status

* Phase 2 implemented.
* Domain model validator layer decision finalized.
* Current decision documented: plan only; no validator implementation yet.
* Future validator layer should stay outside frozen dataclasses.
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

* Dieses Dokument folgt auf LQ-048
  (`docs/lq-048-domain-model-invariants-validation-decision.md`).
* Es plant eine mögliche spätere separate Validator-Schicht.
* Es implementiert **keine** Validatoren.
* Es schützt die Domain Models vor unkontrollierten Runtime-Invarianten.
* Es ist **keine** Trading-Anleitung.
* Es bewertet **keine** Strategie.

## 2. Verified Current Domain Model Context

Verifiziert gegen `src/liquent/domain/models.py` (nur echte Feldnamen).

### Domain Models bleiben unverändert

* frozen dataclasses,
* str-Enums,
* keine Runtime-Validation,
* keine Validator-Schicht,
* keine `__post_init__`-Validierung.

### Echte Feldnamen

* `MarketData`: `timestamp`, `bid`, `ask`, `volume`
* `OrderBookLevel`: `price`, `size`, `side`
* `OrderBookSnapshot`: `timestamp`, `levels`
* `LiquidityMetric`: `spread`, `depth`, `imbalance`, `timestamp`
* `Signal`: `direction`, `strength`, `metric`, `stop_price`
* `RiskDecision`: `approved`, `size`, `reason` plus Audit-Felder
* `Position`: `instrument`, `entry`, `size`, `status`
* `Experiment`: `parameter`, `metriken`

### Nicht existente Feldnamen

* kein `LiquidityMetric` value/score/rating als echtes Feld
* kein `Position` quantity/entry_price als echtes Feld
* kein `Experiment` metrics als echtes Feld, sondern `metriken`

## 3. Validator Layer Scope Options

### Option A — No validator layer now

* Keine Validator-Schicht.
* LQ-047/LQ-048 bleiben Dokumentations- und Testschutz.
* Status quo bleibt.

### Option B — Validator layer plan only

* Validator-Schicht wird geplant, aber nicht implementiert.
* Kandidaten und API werden dokumentiert.
* Keine Codeänderung.

### Option C — Implement separate validator functions later

* spätere Funktionen außerhalb der Domain Models.
* mögliche Modulstruktur: `src/liquent/domain/validation.py`.
* mögliche Funktionen: `validate_market_data(...)`,
  `validate_order_book_level(...)`, `validate_order_book_snapshot(...)`,
  `validate_liquidity_metric(...)`, `validate_signal(...)`,
  `validate_risk_decision(...)`, `validate_position(...)`,
  `validate_experiment(...)`.

Wichtig: Diese Funktionen existieren aktuell nicht. Das Modul existiert aktuell
nicht. In LQ-049 werden sie nicht implementiert.

### Option D — Runtime validation inside dataclasses

* `__post_init__` in Domain Models.
* aktuell **nicht** empfohlen.

### Option E — External validation framework

* Pydantic oder ähnliches.
* aktuell **nicht** empfohlen.

## 4. Recommended Decision

Aktuelle Empfehlung:

* Jetzt **Option B**: Validator layer plan only.
* Keine Implementierung.
* Domain Models bleiben reine Datenstrukturen.
* Keine Runtime-Validation.
* Keine `__post_init__`-Validierung.
* Falls später Validator-Schicht gewünscht:
  * **Option C** separat planen,
  * Tests zuerst,
  * Validatoren außerhalb der frozen dataclasses,
  * keine Pydantic-/Dependency-Einführung.
* **Option D** und **E** aktuell nicht umsetzen.

Begründung:

* LQ-047/LQ-048 haben Domain Models stabilisiert.
* Eine sofortige Validator-Implementierung ist aktuell nicht nötig.
* Separate Validatoren wären später kontrollierter.
* DataSource- und RiskEngine-Verantwortlichkeiten müssen sauber getrennt
  bleiben.

## 5. Candidate Validator API

Möglicher späterer Entwurf (**nicht** implementiert).

Mögliche Rückgabe:

* Liste von `ValidationIssue`, **oder**
* `raise ValueError`,
* Entscheidung offen.

Mögliche spätere Funktionen:

* `validate_market_data(data: MarketData)`
* `validate_order_book_level(level: OrderBookLevel)`
* `validate_order_book_snapshot(snapshot: OrderBookSnapshot)`
* `validate_liquidity_metric(metric: LiquidityMetric)`
* `validate_signal(signal: Signal)`
* `validate_risk_decision(decision: RiskDecision)`
* `validate_position(position: Position)`
* `validate_experiment(experiment: Experiment)`

Wichtig:

* Diese Funktionen existieren aktuell nicht.
* `ValidationIssue` existiert aktuell nicht.
* In Phase 2 nicht implementieren.
* Keine Importpfade als existent behaupten.

## 6. Candidate Validation Rules

Mögliche Regeln (dokumentiert, **nicht** implementiert; nur echte Feldnamen).

### MarketData

* `bid > 0`
* `ask > 0`
* `ask >= bid`
* `volume >= 0` (oder `> 0`, Entscheidung offen)
* `timestamp` timezone-aware (Entscheidung offen)

### OrderBookLevel

* `price > 0`
* `size >= 0` (oder `> 0`, Entscheidung offen)
* `side` ist `Direction`

### OrderBookSnapshot

* `timestamp` timezone-aware (Entscheidung offen)
* `levels` ist Liste
* leere `levels` erlaubt oder nicht (Entscheidung offen)

### LiquidityMetric

* `spread`, `depth`, `imbalance` numerisch
* `timestamp` optional oder timezone-aware (Entscheidung offen)
* keine value/score/rating-Felder behaupten

### Signal

* `direction` ist `Direction`
* `strength` numerisch
* `metric` optional
* `stop_price` optional
* `stop_price > 0`, falls vorhanden und später entschieden

### RiskDecision

* `approved` ist `bool`
* `size >= 0`, falls später als Contract entschieden
* `reason` bei Ablehnung optional oder Pflicht (Entscheidung offen)
* Audit-Felder bleiben optional/default

### Position

* `instrument` ist `Instrument`
* `entry` technischer Entry-Wert
* `size` technischer Größenwert
* `status` ist `PositionStatus`
* kein quantity-Feld behaupten
* kein entry_price-Feld behaupten

### Experiment

* `parameter` ist `dict`
* `metriken` ist `dict`
* kein metrics-Feld behaupten

## 7. Placement / Responsibility Boundaries

### Domain Models

* bleiben Datencontainer,
* keine Validatoren in dataclasses.

### Validator Layer

* wäre rein technische Konsistenzprüfung,
* keine Risikoentscheidung,
* keine Strategieentscheidung.

### DataSource

* darf Import-/CSV-/Parsing-spezifische Validierung behalten,
* nicht alles in einen Domain-Validator verschieben.

### RiskEngine

* bleibt Risiko-/Sizing-Entscheidung,
* kein allgemeiner Domain-Validator.

### CLI

* soll Validatoren nur später bewusst aufrufen, falls spezifiziert,
* keine doppelte Logik.

### Visual Preview

* bleibt unberührt.

## 8. Future Implementation Plan

Falls später Option C umgesetzt wird:

1. Doku finalisieren.
2. Tests für die Validator-API schreiben.
3. `ValidationIssue` oder Fehlerstrategie festlegen.
4. `src/liquent/domain/validation.py` anlegen.
5. Nur reine Validator-Funktionen implementieren.
6. Keine Domain-Model-Änderung.
7. Keine DataSource-/RiskEngine-Verkabelung im ersten Schritt.
8. Danach separat entscheiden, wo Validatoren aufgerufen werden.

## 9. Safety Boundaries

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

## 10. README/Roadmap Impact

README:

* LQ-049-Link wird ergänzt.

Roadmap:

* LQ-049 als validator layer decision / implementation plan ergänzt.
* Status:
  * recommendation: plan only; no validator implementation yet,
  * future validator layer should stay outside frozen dataclasses.

Visual Preview Index:

* bleibt unverändert,
* LQ-049 ist kein Visual-Preview-Track.

## 11. Phase 2 Implementation Status

* Domain model validator layer decision finalized.
* Verified current domain model context documented.
* Validator layer scope options documented (A–E).
* Recommended decision documented (B now; C later if needed; D/E not now).
* Candidate validator API documented as future-only (functions/module do not
  exist yet).
* Candidate validation rules documented (real field names only).
* Placement / responsibility boundaries documented.
* Future implementation plan documented.
* README link added.
* Roadmap link added.
* Doku-tests added (`tests/test_domain_model_validator_layer_plan_doc.py`).
* Visual Preview Index unchanged.
* No runtime validation implemented.
* No validator functions implemented.
* No `__post_init__` validation.
* No production logic changes; `src/liquent/domain/models.py` unverändert.
* No src changes, no tools changes, no pyproject changes.
* No dependency installed, no Streamlit start, no real data, no CSV files, no
  screenshots, no reports.
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).

## 12. Non-Goals

* keine Implementierung, keine Validator-Funktionen, keine Runtime-Validation,
* keine `__post_init__`-Validierung, keine Pydantic-/Dependency-Einführung,
* keine Domain-Model-Änderung, keine Tests-Änderung in Phase 1,
* keine Runner-/RiskEngine-/Strategy-/CLI-/DataSource-/Visual-Preview-Änderung,
* keine Echtdaten, keine externen Downloads, keine API-/Exchange-/Live-/
  Paper-Anbindung,
* keine neu committeten CSV-/Bild-/Report-Artefakte,
* keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 13. Offene Entscheidungspunkte

1. Soll später überhaupt eine Validator-Schicht implementiert werden?
2. Soll `ValidationIssue` als Dataclass eingeführt werden?
3. Soll die Validator-API Fehler sammeln oder sofort werfen?
4. Welche Validatoren sind zuerst sinnvoll?
5. Wo sollen Validatoren später aufgerufen werden?
6. Wie bleibt DataSource-Validierung getrennt?
7. Wie bleibt die RiskEngine getrennt?
8. Soll Runtime-Validation weiterhin vermieden werden?
