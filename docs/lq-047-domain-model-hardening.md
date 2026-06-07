# LQ-047 — Domain Model Hardening

## Status

* Phase 2 implemented.
* Domain model hardening documented.
* Domain model behavior locks implemented (7 Tests).
* No production code changes.
* No src changes.
* No pyproject changes.
* No dependency installed.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Domain-Model-Verhalten absichern (Behavior-Locks).
* Bestehende Dataclasses/Enums dokumentieren.
* Keine neue Domain-Logik erzwingen.
* Keine Produktionslogik ändern.
* Rein deskriptiv: keine Bewertung, kein Ranking, keine Empfehlung, keine
  Profitabilitätsaussage.

## 2. Verified Current Domain Model

Verifiziert lesend (und mit einem reinen In-Memory-Check) gegen den echten Code
(`src/liquent/domain/models.py`). Reine Datenstrukturen, bewusst **keine** Logik;
Invarianten sind dokumentiert, aber nicht erzwungen.

### Enums

* `Direction(str, Enum)`: `LONG == "long"`, `SHORT == "short"`,
  `FLAT == "flat"` (str-Enum: Werte und String-Vergleich).
* `PositionStatus(str, Enum)`: `OPEN == "open"`, `CLOSED == "closed"`.

### Dataclasses (alle `frozen=True`)

* `Instrument`: `symbol`, `base`, `quote`.
* `MarketData`: `timestamp`, `bid`, `ask`, `volume`.
* `OrderBookLevel`: `price`, `size`, `side` (Default `Direction.FLAT`).
* `OrderBookSnapshot`: `timestamp`, `levels` (`default_factory=list`).
* `LiquidityMetric`: `spread`, `depth`, `imbalance`, `timestamp` (Default `None`).
* `Signal`: `timestamp`, `direction`, `strength`, `metric` (Default `None`),
  `stop_price` (Default `None`).
* `RiskDecision`: `approved`, `size`, `reason` + Audit-Defaults
  (`risk_amount`, `stop_distance`, `notional`, `capped_by_*`).
* `Position`: `instrument`, `entry`, `size`, `status` (Default
  `PositionStatus.OPEN`).
* `Experiment`: `hypothese`, `parameter` (`default_factory=dict`), `metriken`
  (`default_factory=dict`).

### Default- / Frozen- / Hashing-Eigenschaften (verifiziert)

* `frozen=True` ⇒ Attribut-Zuweisung nach Konstruktion wirft
  `dataclasses.FrozenInstanceError`.
* `default_factory`-Felder (`Experiment.parameter`/`metriken`,
  `OrderBookSnapshot.levels`) sind pro Instanz unabhängig (kein geteilter
  mutable Default).
* `Instrument` und `MarketData` sind hashbar (alle Felder hashbar) und
  wertgleich-vergleichbar.
* `Experiment` und `OrderBookSnapshot` sind **nicht** hashbar (`TypeError`), da
  sie `dict`-/`list`-Felder tragen.

## 3. Behavior Locks

Die 7 Tests in `tests/test_domain_model_hardening.py` (rein in-memory):

1. `test_direction_enum_values_and_str` — `Direction`-Werte + str-Vergleich
   (LONG/SHORT/FLAT) und vollständige Wertmenge.
2. `test_position_status_enum_values_and_str` — `PositionStatus`-Werte +
   str-Vergleich (OPEN/CLOSED) und vollständige Wertmenge.
3. `test_frozen_dataclasses_raise_on_mutation` — Attribut-Set auf `Instrument`,
   `MarketData`, `Signal`, `RiskDecision`, `Position` wirft
   `FrozenInstanceError`.
4. `test_default_factory_fields_are_independent` — `Experiment.parameter`/
   `metriken` und `OrderBookSnapshot.levels` sind pro Instanz unabhängig.
5. `test_optional_field_defaults` — `OrderBookLevel.side == Direction.FLAT`,
   `LiquidityMetric.timestamp is None`, `OrderBookSnapshot.levels == []`.
6. `test_equality_and_hashing` — wertgleiche `Instrument` sind `==`, hashbar und
   als Set-/Dict-Key nutzbar.
7. `test_dict_list_dataclasses_are_unhashable` — `Experiment` und
   `OrderBookSnapshot` sind unhashbar (`TypeError`).

Nur echte Testinhalte dokumentiert — keine erfundenen Tests.

## 4. Compatibility

* Bestehende Tests bleiben grün.
* Bestehende Domain-Modelle bleiben unverändert.
* Keine neue Validierung.
* Keine Invarianten-Erzwingung in Phase 2.
* Keine Auswirkungen auf Runner, RiskEngine, CLI, Visual Preview.
* `tests/test_domain.py` (10 Bestandstests) unverändert.

## 5. Safety Boundaries

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

## 6. README/Roadmap Impact

* README-Link ergänzt (Domain Model Hardening).
* Roadmap-Link ergänzt (LQ-047).
* Teststand aktualisiert.
* Visual Preview Index unverändert; LQ-047 ist kein Visual-Preview-Track.

## 7. Phase 2 Implementation Status

* Doku finalisiert (Status, Verified Current Domain Model, Behavior Locks,
  Compatibility, Safety Boundaries).
* 7 Domain-Behavior-Locks vorhanden (`tests/test_domain_model_hardening.py`).
* Doku-/Link-Test ergänzt (`tests/test_domain_model_hardening_doc.py`).
* README/Roadmap aktualisiert.
* Tests grün.
* Keine Produktionslogik geändert; `src/liquent/domain/models.py` unverändert.
* Keine neuen Domain-Felder, keine neue Validierung, keine erzwungenen
  Invarianten.
* Keine Dependency installiert, kein Streamlit-Start, keine Echtdaten, keine
  Artefakte.
* Kein Commit, kein Push (folgt in Phase 3 nach Freigabe).
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).

## 8. Non-Goals

* keine Änderung an `src/liquent/domain/models.py` (keine neuen Felder, keine
  erzwungenen Invarianten, keine neue Validierung/Serialization),
* keine Änderung an bestehenden Domain-Tests,
* kein `exit_reason`, keine Stop-Exit-Logik, keine Runner-Lifecycle-Änderung,
* keine Strategie-/DataSource-/RiskEngine-/CostModel-/Metrics-/Reporting-/
  Comparison-/CLI-/Visual-Preview-Änderung,
* keine Ranking-/Bewertungslogik,
* keine echten Marktdaten, keine externen Downloads, keine API-/Exchange-/Live-/
  Paper-Anbindung,
* keine neu committeten CSV-/Bild-/Report-Artefakte,
* keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 9. Deferred Topics

1. Eine eigene Serialization-API (`to_dict`/`from_dict`) bleibt außerhalb dieses
   Tracks (`dataclasses.asdict` ist stdlib, kein Projekt-Contract).
2. Erzwungene fachliche Invarianten (Vorzeichen, Spannen, Stop-Konsistenz)
   bleiben bewusst in den Fachmodulen, nicht im Domänenmodell.
3. Zusätzliche Domain-Felder/-Entitäten bleiben separaten, ausdrücklich
   freizugebenden Tracks vorbehalten.
