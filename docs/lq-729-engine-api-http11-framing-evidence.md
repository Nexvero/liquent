# LQ-729 — Engine API HTTP/1.1 Framing Evidence

## Positive Evidenz

Die Tests belegen bodyloses GET, JSON-POST mit exakter Länge, JSON-Responses mit
bekannten Daemonmetadaten sowie bodylose 204-, 304- und 404-Responses.

Die resultierenden Werte enthalten nur die für Route- und Responsepolicy
benötigten Fakten.

## Smuggling- und Erweiterungsabwehr

Explizit geprüft werden angehängte zweite Requests, Length-Mismatch, führende
Nullen, Transfer-Encoding, Chunking, Trailer, Upgrade, doppelte Header,
nichtkanonische Headernamen und HTTP/1.0.

Header- und Bodyobergrenzen werden unabhängig belegt. Vertraulicher ungültiger
Input erscheint nicht in der beobachtbaren Fehlermeldung.

## Fähigkeitsgrenze

Die öffentliche Oberfläche besitzt weder Listen, Bind, Connect, Recv, Send noch
Close. Der Test beweist damit einen reinen Decoder und keinen aktiven Transport.

Route-, Create-, Host- und Responsepolicy bleiben getrennte nachfolgende Gates.
