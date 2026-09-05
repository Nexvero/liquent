# LQ-776 — Owned Engine API Process Run

## Umsetzung

`OwnedManifestHandoffSupervisorEngineApiProcessRun` bindet exakt konkreten
Hostpreflight, Listener-Lifecycle und begrenzten Serve-Loop.

`run` führt Dependency-Preflight, Listener-Open, vollständigen Hostpreflight und
Loop in fester Reihenfolge aus. Das unveränderte Loopresultat wird erst nach
erfolgreichem Listener-Retire zurückgegeben.

Der bestehende Hostpreflight erhält additiv `check_before_listener`. Diese
Methode prüft ausschließlich die bereits existierenden Hostabhängigkeiten und
liefert einen eigenen geschlossenen Readinessgrund.

`check` bleibt unverändert der vollständige Snapshot einschließlich Proxy-Socket.

## Cleanup

Ein lokal gehaltener Listenerwert entsteht erst nach erfolgreichem Open. Jeder
folgende Pfad ruft genau einmal den identitätsgebundenen Lifecycle-Retire auf.

## Nicht umgesetzt

Kein Signal, blockierendes Accept-Shutdown, Prozessentrypoint, Settingsaufbau,
Logging oder Deploymentaktivierung wird ergänzt.
