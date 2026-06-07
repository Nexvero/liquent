# LQ-051 — Liquent Milestone Review / Next-Track Decision

## Status

* Phase 2 implemented.
* Milestone review / next-track decision finalized.
* Current decision documented: do not automatically start another technical
  hardening track.
* Recommended next direction: Architecture Review or Product / Use-Case
  Definition.
* No code changes.
* No src changes.
* No tools changes.
* No pyproject changes.
* No production logic changes.
* No dependency installed.
* No live trading.
* No trading recommendation.
* No profitability assessment.

## 1. Purpose

* Dieses Dokument folgt auf LQ-050
  (`docs/lq-050-domain-model-validation-track-freeze.md`).
* Es fasst den erreichten Meilenstein zusammen.
* Es entscheidet bewusst, welcher Track als Nächstes sinnvoll ist.
* Es verhindert technische Endlosschleifen und Doppelarbeit.
* Es ist **keine** Trading-Anleitung.
* Es bewertet **keine** Strategie.

## 2. Current Milestone Summary

### Foundation / Backtesting / Risk

* lokaler Backtest-Kontext vorhanden (`BacktestRunner`, `BacktestResult`),
* RiskEngine vorhanden,
* CostModel/Metrics vorhanden,
* keine Live-/Paper-Trading-Anbindung.

### Visual Preview

* Visual Preview erstellt,
* CSV-Unterstützung dokumentiert,
* OHLCV/Bid-Ask-Schemata dokumentiert,
* Quickstart und Index vorhanden,
* Track eingefroren.

### BacktestRunner / Lifecycle

* Runner existiert,
* Regressionstests vorhanden,
* Close-to-Close bleibt Contract,
* `stop_price` sizing-only,
* kein Stop-Exit,
* `exit_reason` nur Future Spec,
* Track eingefroren.

### Domain Model

* Domain Models als frozen dataclasses / str-Enums,
* Behavior-Locks vorhanden,
* Invarianten dokumentiert,
* Validator Layer nur Future Plan,
* Track eingefroren.

### DataSource / CSV Loader

* LQ-046: `HistoricalFileSource`-Contract dokumentiert + Regressionstests,
* keine Echtdaten,
* keine echten CSV-Dateien committed.

### Reporting / CLI / Strategy Fixtures

* LQ-043 Reporting/Comparison, LQ-044 CLI Output Polish, LQ-045 Strategy
  Fixtures/Scenario Coverage — jeweils dokumentiert und abgesichert,
* keine Empfehlungen,
* keine Profitabilitätsbewertung.

## 3. Decision Options

### Option A — Pause / Architecture Review Checkpoint

* keine neue Implementierung,
* Architektur, Roadmap und Prioritäten prüfen,
* nächste fachliche Richtung bewusst festlegen.

### Option B — Product / Use-Case Definition Track

* Liquent fachlich schärfen: Zielnutzer, primärer Use Case, Research-Workflow,
  Output-Artefakte, Grenzen.

### Option C — Minimal Demo Workflow Plan

* rein lokaler Demo-Workflow mit synthetischen Daten,
* keine Echtdaten, keine Trading-Empfehlung, keine Profitabilitätsbewertung.

### Option D — Documentation / Release Summary

* technischen Stand als Milestone zusammenfassen,
* README/Roadmap konsolidieren,
* keine neuen Features.

### Option E — Start New Technical Hardening Track

* nur nach bewusster Auswahl,
* mögliche Kandidaten: RiskEngine, CostModel/Metrics, Reporting/Comparison, CLI,
  Strategy Fixtures, DataSource.
* Hinweis: mehrere davon wurden bereits gehärtet (LQ-041…LQ-046) und sollten
  nicht doppelt bearbeitet werden.

## 4. Recommended Decision

Aktuelle Empfehlung:

* **Option A oder Option B**.
* Nicht sofort weiter hardenen.
* Erst Pause/Architecture Review oder Product/Use-Case Definition.
* Danach bewusst entscheiden, ob Code, Doku oder Produktkonzept folgt.

Begründung:

* Viele technische Tracks sind abgeschlossen.
* Mehrere Bereiche sind bewusst eingefroren.
* Weiteres Hardening ohne Produktentscheidung kann ineffizient werden.
* Liquent braucht jetzt Richtung: Produkt, Research-Workflow, Demo oder bewusste
  Pause.

## 5. Proposed Next Track Candidates

### LQ-052 Candidate A — Architecture Review Checkpoint

* Roadmap konsolidieren,
* abgeschlossene Tracks markieren,
* offene Future Specs auflisten,
* keine Implementierung.

### LQ-052 Candidate B — Product / Research Workflow Definition

* Zielbild beschreiben,
* lokaler Research-Workflow,
* Inputs/Outputs,
* No-Live-Trading-Grenzen.

### LQ-052 Candidate C — Synthetic Demo Workflow Specification

* Demo-Flow mit synthetischen Daten,
* keine Echtdaten,
* keine Performance-Deutung.

### LQ-052 Candidate D — Release Summary / Milestone Tag Plan

* Milestone-Doku,
* optional später Git-Tag-Plan,
* keine Codeänderung.

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
* No reports generated.
* No profitability assessment.
* No trading recommendation.

## 7. README/Roadmap Impact

README:

* LQ-051-Link wird ergänzt.

Roadmap:

* LQ-051 als Milestone Review / Next-Track Decision ergänzt.
* Status:
  * milestone review finalized,
  * recommended next step: pause/architecture review or product/use-case
    definition.

Visual Preview Index:

* bleibt unverändert,
* LQ-051 ist kein Visual-Preview-Track.

## 8. Phase 2 Implementation Status

* Milestone review / next-track decision finalized.
* Current milestone summary documented.
* Decision options A–E documented.
* Recommended decision documented (Option A or B).
* Proposed next track candidates documented (LQ-052 A–D).
* README link added.
* Roadmap link added.
* Doku-tests added (`tests/test_liquent_milestone_review_next_track_doc.py`).
* Visual Preview Index unchanged.
* No code changes.
* No src changes, no tools changes, no pyproject changes.
* No production logic changes.
* No dependency installed, no Streamlit start, no real data, no CSV files, no
  screenshots, no reports.
* pytest result: siehe README / Roadmap (aktueller verifizierter Teststand).

## 9. Non-Goals

* keine Implementierung, keine Tests-Änderung in Phase 1,
* keine src-/tools-/pyproject-Änderung,
* keine Runner-/RiskEngine-/Strategy-/DataSource-/Reporting-/CLI-/
  Visual-Preview-/Domain-Model-Änderung,
* keine Validator-Implementierung, keine Runtime-Validation,
* keine Echtdaten, keine externen Downloads, keine API-/Exchange-/Live-/
  Paper-Anbindung,
* keine neu committeten CSV-/Bild-/Report-Artefakte,
* keine Profitabilitätsbewertung, keine Trading-Empfehlung.

## 10. Offene Entscheidungspunkte

1. Soll LQ-052 ein Architecture Review werden?
2. Soll LQ-052 ein Product / Research Workflow Track werden?
3. Soll LQ-052 ein Synthetic Demo Workflow Track werden?
4. Soll LQ-052 eine Release Summary werden?
5. Soll überhaupt weiterentwickelt oder pausiert werden?
6. Welche Future Specs bleiben nur geparkt (exit_reason/Stop-Exit, Validator
   Layer)?
7. Welche Tracks dürfen nicht erneut ohne Grund vertieft werden?
