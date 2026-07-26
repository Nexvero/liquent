# LQ-078 — Lesende Research-API

## Status

- Jobstatus und erfolgreiche Evidence sind über zwei kleine HTTP-GET-Routen
  lesbar.
- Beide Routen verwenden das bestehende In-Memory-Register und die vorhandene
  `BacktestExperimentSummary`.
- Unbekannte Jobs und noch nicht vorhandene Evidence liefern neutrale 404-Codes.
- Kein Start-Endpunkt, keine Runner-Factory, Authentifizierung oder Persistenz.

## Routen

| Route | Ergebnis |
|---|---|
| `GET /v1/research/jobs/{job_id}` | Job-, Experiment- und Lifecycle-Status |
| `GET /v1/research/jobs/{job_id}/evidence` | vorhandene Evidence eines erfolgreichen Jobs |

Ein Evidence-Link erscheint im Status ausschließlich für `Succeeded`. Ein
laufender, bereiter oder fehlgeschlagener Job veröffentlicht keine Teil-Evidence.
Ein No-Signal-Lauf bleibt ein gültiger Erfolg mit `number_of_trades = 0`.

## Fehler

- `research_job_not_found`: die Job-ID ist im aktuellen Prozess unbekannt.
- `research_evidence_not_found`: der Job existiert, besitzt aber keine Evidence.

Interne Exceptions, Stacktraces und Dateipfade werden nicht übertragen.

## Bewusst nicht gebaut

- kein `POST`-Start und keine Input-Auflösung,
- keine Jobliste, Filterung, Löschung oder Pagination,
- keine Authentifizierung oder Mandantentrennung,
- keine Datenbank, Queue, Worker oder WebSockets,
- keine OpenAPI-Veröffentlichung, UI, Release oder Deployment.

## Definition of Done

- Status bildet die vorhandene Job- und Experiment-Identität ab,
- Evidence verwendet das bestehende neutrale Modell,
- unfertige Jobs liefern keine Teil-Evidence,
- unbekannte Ressourcen scheitern ohne interne Details,
- vollständige Testsuite bleibt grün,
- nächster Schritt kann die gezielte Snapshot-zu-Runner-Auflösung spezifizieren.
