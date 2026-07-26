# LQ-076 — Minimales In-Memory-Jobregister

## Status

- Research-Jobs besitzen zusätzlich zur `experiment_id` eine stabile `job_id`.
- Eine kleine prozesslokale Ablage unterstützt ausschließlich `add` und `get`.
- Doppelte Job-Identitäten und unbekannte Jobs scheitern explizit.
- Keine Repository-Schnittstelle, Datenbank, Liste, Löschung oder Parallelität.

## Zweck

Der in LQ-075 definierte Statuspfad muss einen gestarteten Job eindeutig
wiederfinden können. Dafür reicht in diesem Slice eine kleine In-Memory-Map.
Sie ist kein vorweggenommenes Persistenzdesign und überlebt keinen Prozessneustart.

`job_id` bezeichnet die konkrete Ausführung. `experiment_id` bezeichnet die
eingefrorene Research-Konfiguration. Mehrere spätere Ausführungen desselben
Experiments erhalten jeweils eine neue `job_id`.

## Verhalten

- `add(job)` speichert genau einen Job unter seiner `job_id`.
- Eine bereits vorhandene `job_id` wird nicht überschrieben.
- `get(job_id)` liefert genau dasselbe Jobobjekt einschließlich seines aktuellen
  Lifecycle-Zustands und seiner Evidence.
- Eine unbekannte `job_id` erzeugt einen klaren Not-found-Fehler für den späteren
  HTTP-Adapter.

## Bewusst nicht gebaut

- keine Auflistung, Filterung, Pagination oder Löschung,
- keine Haltbarkeit, Transaktion oder Locking-Abstraktion,
- keine automatische ID-Erzeugung,
- keine HTTP-Route und kein Experiment-Snapshot,
- keine Queue, Worker-, Retry-, Broker- oder Tradingfunktion.

## Definition of Done

- Job- und Experiment-Identität sind getrennt,
- doppelte Identitäten überschreiben keine vorhandenen Jobs,
- gespeicherte Jobs sind eindeutig wiederauffindbar,
- vollständige Testsuite bleibt grün,
- nächster Schritt ist der unveränderliche Experiment-Snapshot aus dem
  Implementierungsgate von LQ-075.
