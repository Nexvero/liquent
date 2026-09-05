# LQ-766 — Private Engine API Listener Completion Audit

## Ergebnis

LQ-763 bis LQ-766 schließen Publikation, Verifikation und Retire eines einzelnen
privaten Engine-API-Unix-Listeners bis unmittelbar vor Accept.

## Geschlossene Eigenschaften

- exaktes privates Elternverzeichnis
- zwingend abwesender Zielname
- AF_UNIX/SOCK_STREAM und Close-on-exec
- feste UID/GID und Modus 0660
- fester positiver Backlog
- Pfad-/Descriptorprüfung nach Listen
- kein Übernehmen oder Entfernen fremder Pfade
- sicherer identitätsgebundener Retire
- detailfreie Fehler und expliziter Close-Retry

## Offene Blocker

Accept, Client-Close-on-exec und Timeoutsetup, Peerprüfung, Einmaloperation,
deterministischer Clientclose, begrenzter Serve-Loop, Shutdown und
Prozesslifecycle fehlen weiterhin.

Der Listener ist noch in keiner Runtime- oder Deploymentcomposition aktiviert.

## Productionstatus

Die Fähigkeit bleibt unverdrahtet; `production_ready=false` bleibt korrekt.

## Verifikation

- 248 fokussierte Listener-, Connected-Exchange-, Connector-, Peer-, Stream-, Gate-, Policy-, Host- und Migrationsprüfungen bestehen.
- 5.603 vollständige Nicht-PostgreSQL-Tests bestehen; 108 werden erwartungsgemäß übersprungen.
- Deprecation-Warnungen werden in der vollständigen Suite als Fehler behandelt.
- Die abschließende Diffprüfung bleibt die Whitespace- und Scopegrenze.

## Nächster Strang

Als Nächstes ist die kontrollierte Einmal-Accept-Operation mit Clientsetup,
Connected Exchange und Finally-Close umzusetzen.
