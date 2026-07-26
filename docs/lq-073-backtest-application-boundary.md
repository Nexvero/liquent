# LQ-073 — Backtest Application Boundary

## Status

- Eine minimale Anwendungsgrenze zum vorhandenen deterministischen
  `BacktestRunner` ergänzt.
- Der Produktworkflow benötigt nur `run() -> BacktestResult`.
- Die vorhandene neutrale `BacktestExperimentSummary` bleibt das Ergebnis;
  kein paralleles Evidence-Modell wurde angelegt.
- Keine Queue, Persistenz, Adapterhierarchie oder neue Abhängigkeit eingeführt.

## Vertrag

```text
Slice-1-Anwendungsworkflow
          ↓ execute_local_research
BacktestExecution.run()
          ↓
vorhandener BacktestResult
          ↓ vorhandenes Reporting
BacktestExperimentSummary
```

Die Grenze besteht aus einem Ein-Methoden-Protocol und einer reinen
Orchestrierungsfunktion. Dadurch kann der bestehende Runner direkt verwendet
und in Anwendungstests durch einen kleinen Stub ersetzt werden. Der Research-
Kern wird nicht dupliziert oder in eine neue Abstraktionsschicht verschoben.

Ein Lauf mit null Signalen oder Trades bleibt ein erfolgreich erzeugbares,
neutrales Ergebnis. Technische Ausführungsfehler werden nicht abgefangen oder
umbenannt; deren Jobstatus-Orchestrierung gehört erst in den nächsten
In-Memory-Workflow.

## Bewusst nicht gebaut

- kein zweiter Runner und kein neues Result-/Evidence-Schema,
- keine Factory, Registry oder Adapter-Basisklasse,
- kein asynchroner Worker und keine Queue,
- keine Datenbank- oder HTTP-Anbindung,
- keine Broker-, Paper- oder Live-Ausführung.

## Definition of Done

- Produktcode besitzt genau einen schmalen Einstieg in den Research-Kern,
- ein Runner wird pro Aufruf genau einmal ausgeführt,
- bestehendes Reporting und Sicherheitsflags bleiben erhalten,
- ein No-Signal-Lauf bleibt gültige technische Evidenz,
- vollständige Testsuite bleibt grün,
- nächster Schritt ist LQ-074: kleiner ausführbarer In-Memory-Workflow.
