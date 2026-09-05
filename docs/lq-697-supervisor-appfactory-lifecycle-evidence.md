# LQ-697 — Supervisor Appfactory Lifecycle Evidence

## Ergebnis

Ausführbare Evidenz belegt Factory-Aufbau, not-ready und Shutdown als einen
gekoppelten Weg.

## Vollständiger Pfad

Eine vollständige Gruppe startet den App-Lifespan, liefert detailfrei HTTP 503
mit `manifest_handoff_supervisor_not_ready` und schließt den Prozess beim Ende
genau einmal.

Die explizite Datenbank-Engine bleibt danach verwendbar.

## Teilgruppen

Separat geprüft werden fehlender Prozess, Probe, Ownershipmarker, aktive
Settings und explizite Engine.

Keine dieser Ablehnungen übernimmt oder schließt caller-besessene Ressourcen.

## Identität und Health

Ein an einen anderen Prozess gebundener Probe wird abgelehnt.

Ebenso scheitert die Mischung mit einer fremden `ProcessHealth`-Instanz.

## Geschlossene Auswahl

Der reale Production-Entrypoint übergibt weiterhin kein Supervisorargument und
ruft die Processcomposition nicht auf.
