# LQ-050 — Domain Model Validation Track Freeze / Next-Track Decision

## Status

* Phase 2 implemented.
* Domain Model validation track freeze decision finalized.
* Current decision documented: freeze Domain Validation Track.
* LQ-049 remains a future plan, not an implementation trigger.
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

* Dieses Dokument folgt auf LQ-049
  (`docs/lq-049-domain-model-validator-layer-plan.md`).
* Es entscheidet bewusst, ob der Domain-Validation-Track jetzt eingefroren wird.
* Es schließt den aktuellen Domain-Model-Validation-Spezifikationsblock ab.
* Es ist **keine** Trading-Anleitung.
* Es bewertet **keine** Strategie.

## 2. Current Domain Validation Contract

* Domain Models bleiben frozen dataclasses / str-Enums.
* Domain Models bleiben reine Datencontainer.
* Invarianten sind dokumentiert, aber **nicht** runtime-erzwungen.
* Behavior-Locks (LQ-047) schützen Defaults und Struktur.
* Es gibt **keine** Validator-Schicht.
* Es gibt **keine** Validator-Funktionen.
* Es gibt **keine** `__post_init__`-Validierung.
* LQ-049 beschreibt nur einen möglichen Future Plan.
* Visual Preview bleibt unverändert.

Verifizierte echte Feldnamen (unverändert): `MarketData` (timestamp/bid/ask/
volume), `OrderBookLevel` (price/size/side), `OrderBookSnapshot` (timestamp/
levels), `LiquidityMetric` (spread/depth/imbalance/timestamp), `Signal`
(direction/strength/metric/stop_price), `RiskDecision` (approved/size/reason +
Audit), `Position` (instrument/entry/size/status), `Experiment`
(parameter/metriken). Keine erfundenen Felder (kein value/score/rating, kein
quantity/entry_price, kein metrics).

## 3. Decision Options

### Option A — Freeze Domain Validation Track

* Keine Validator-Implementierung.
* Keine Runtime-Validation.
* LQ-047/LQ-048/LQ-049 bleiben Dokumentations- und Testbasis.
* Nächsten Track außerhalb Domain Validation wählen.

Vorteile: stabil; kein Scope-Zuwachs; keine Breaking Changes; Domain Models
bleiben leichtgewichtig.
Risiken: Runtime-Validation bleibt nicht vorhanden.

### Option B — Start Validator Implementation Planning

* Noch keine Implementierung.
* Separate spätere Spezifikation: Validator API; `ValidationIssue` oder
  Fehlerstrategie; Tests zuerst; keine Domain-Model-Änderung.

Vorteile: kontrollierter Weg zu einer Validator-Schicht.
Risiken: zusätzlicher Scope; Gefahr von Überschneidung mit DataSource/RiskEngine.

### Option C — Implement Validator Layer Immediately

* Nicht empfohlen.
* Würde Code ändern.

Risiken: zu großer Sprung; unklare Aufrufpunkte; mögliche Doppelvalidierung.

### Option D — Add Runtime Validation to Domain Models

* Nicht empfohlen.
* `__post_init__` oder ähnliche harte Invarianten.

Risiken: Breaking Change; Fixture-Brüche; widerspricht der
LQ-048/LQ-049-Empfehlung.

## 4. Recommended Decision

Aktuelle Empfehlung:

* **Option A**.
* Domain Validation Track einfrieren.
* Aktueller Contract bleibt:
  * Domain Models sind reine Datenstrukturen,
  * keine Runtime-Validation,
  * keine Validator-Schicht,
  * keine `__post_init__`-Validierung.
* LQ-049 bleibt als Future Plan bestehen.
* Keine Implementierung ohne neue ausdrückliche Freigabe.

Begründung:

* LQ-047/LQ-048/LQ-049 haben den Track ausreichend dokumentiert.
* Die Validator-Implementierung ist vorbereitet, aber nicht zwingend nötig.
* Andere Tracks können jetzt fachlich wertvoller sein.
* Domain Models sollten stabil bleiben.

## 5. Possible Next Tracks

### Track A — RiskEngine hardening

* `RiskLimits` / `AccountState` / `RiskDecision` tiefer testen.
* Keine Domain-Model-Änderung.

### Track B — CostModel / Metrics hardening

* Kostenformel und Metrics stabilisieren.
* Keine Bewertungssprache.

### Track C — Reporting / Comparison stabilization

* `BacktestExperimentSummary` / `comparison_reporting` absichern.
* `strategy_metadata`/`cost_metadata` sauber halten.

### Track D — CLI output polish

* technische Ausgabe lesbarer machen,
* keine Empfehlungen,
* keine neuen Reports ohne Freigabe.

### Track E — Strategy fixture/scenario coverage

* synthetische Fixtures erweitern,
* keine Echtdaten,
* keine Optimierung.

### Track F — Pause / Review checkpoint

* Architekturstand bewerten,
* nächste Priorität bewusst festlegen.

> Hinweis: RiskEngine, CostModel/Metrics, Reporting/Comparison, CLI,
> Strategy-Fixtures und DataSource wurden in LQ-041…LQ-046 bereits als
> Hardening-Tracks bearbeitet; eine erneute Vertiefung wäre nur nach bewusster
> Priorisierung sinnvoll.

## 6. Conditions Before Any Validator Implementation

* separate Implementierungsspezifikation,
* Tests zuerst,
* Validator API definieren,
* `ValidationIssue` oder Fehlerstrategie festlegen,
* keine Domain-Model-Änderung,
* keine `__post_init__`-Validierung,
* DataSource-Verantwortung abgrenzen,
* RiskEngine-Verantwortung abgrenzen,
* CLI-Aufrufpunkte separat spezifizieren,
* Visual Preview ausgeschlossen halten,
* keine Profitabilitätsbewertung.

## 7. Safety Boundaries

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

## 8. README/Roadmap Impact

README:

* LQ-050-Link wird ergänzt.

Roadmap:

* LQ-050 als freeze / next-track decision ergänzt.
* Status:
  * recommended decision: freeze Domain Validation Track,
  * no validator implementation yet,
  * future validator layer remains separate future track.

Visual Preview Index:

* bleibt unverändert,
* LQ-050 ist kein Visual-Preview-Track.

## 9. Phase 2 Implementation Status

* Domain Model validation track freeze decision finalized.
* Current Domain Validation Contract documented.
* Decision options A–D documented.
* Recommended decision documented (Option A: freeze).
* Possible next tracks documented (A–F).
* Conditions before validator implementation documented.
* README link added.
* Roadmap link added.
* Doku-tests added (`tests/test_domain_validation_track_freeze_doc.py`).
* Visual Preview Index unchanged.
* No runtime validation implemented.
* No validator functions implemented.
* No `__post_init__` validation.
* No production logic changes; `src/liquent/domain/models.py` unverändert.
* No src changes, no tools changes, no pyproject changes.
* No dependency installed, no Streamlit start, no real data, no CSV files, no
  screenshots, no reports.
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).

## 10. Non-Goals

* keine Implementierung, keine Validator-Funktionen, keine Runtime-Validation,
* keine `__post_init__`-Validierung, keine Pydantic-/Dependency-Einführung,
* keine Domain-Model-Änderung, keine Tests-Änderung in Phase 1,
* keine Runner-/RiskEngine-/Strategy-/CLI-/DataSource-/Visual-Preview-Änderung,
* keine Echtdaten, keine externen Downloads, keine API-/Exchange-/Live-/
  Paper-Anbindung,
* keine neu committeten CSV-/Bild-/Report-Artefakte,
* keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 11. Offene Entscheidungspunkte

1. Wird der Domain Validation Track jetzt eingefroren?
2. Welcher alternative Track kommt als Nächstes?
3. Soll RiskEngine hardening priorisiert werden?
4. Soll CostModel/Metrics hardening priorisiert werden?
5. Soll Reporting/Comparison stabilization priorisiert werden?
6. Soll CLI output polish priorisiert werden?
7. Soll Strategy fixture/scenario coverage priorisiert werden?
8. Soll vor neuen Tracks ein Pause/Review checkpoint erfolgen?
