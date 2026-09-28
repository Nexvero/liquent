# LQ-824 — Closed Engine API Health Protocol

## Umsetzung

`ClosedManifestHandoffSupervisorEngineApiHealthProtocol` akzeptiert
ausschließlich einen exakten Process Owner und besitzt keine I/O-Oberfläche.

Eine geschlossene Byte-Map klassifiziert die beiden erlaubten Requests. Live
wird aus dem detailbegrenzten Snapshot gelesen, Ready aus der gebundenen
Readinessprobe.

Technische Live-Auflösungsfehler werden zu 503 mit dem festen Unavailable-Grund.
Die Readinessgrenze ist bereits selbst fail-closed. Fremde Wertformen werden
ebenfalls auf unavailable reduziert.

Antworten werden deterministisch mit sortiertem kompaktem JSON, festen Headern
und berechneter Content-Length erzeugt.

## Nicht umgesetzt

Kein Unix-Pfad, Listenerlifecycle, Peercredential, Streamreader, Serve Loop,
Healthserver oder Deploymentanschluss.
