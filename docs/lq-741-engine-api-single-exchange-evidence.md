# LQ-741 — Engine API Single-Exchange Evidence

## Erfolgsnachweis

Ein fragmentierter gültiger Inspectrequest wird bytegenau zum Daemon geschrieben.
Eine gültige JSON-Antwort wird erst nach Responseprüfung mit lokaler kanonischer
Statuszeile, Connection close, Content-Type und berechneter Länge ausgegeben.

Partial Writes auf beiden Streams werden vollständig abgeschlossen. Kein Stream
wird durch die Exchange-Komposition geschlossen.

## Abwesenheit und Fehler

Inspect 404 wird ohne Daemonheader, Medientyp oder Body lokal projiziert.

Eine unerlaubte Route schreibt nichts zum Daemon. Daemon-500 mit vertraulichem
Body und eine abgeschnittene Daemonantwort schreiben nichts zum Client und
bleiben detailfrei.

Dieselbe Streaminstanz in beiden Rollen wird vor jeder I/O-Wirkung abgelehnt.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Listen, Bind, Accept, Connect, Settimeout oder
Close. Sie verarbeitet genau einen Austausch und besitzt keinen Loop.

Die Evidenz verwendet ausschließlich bereits verbundene Fake-Streams und öffnet
keine Hostfähigkeit.
