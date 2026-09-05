# LQ-727 — Engine API HTTP/1.1 Framing Contract

## Ziel

Die künftige lokale Proxygrenze akzeptiert pro Aufruf exakt eine vollständig
vorliegende HTTP/1.1-Nachricht und reduziert sie auf geschlossene Werte.

## Startzeile

Requests erlauben nur GET oder POST, ein sichtbares ASCII-Target von höchstens
4.096 Bytes und exakt HTTP/1.1. Responses erlauben exakt HTTP/1.1 und einen
dreistelligen Status; der Reasontext wird nie weitergegeben.

## Header

Der Headerblock ist auf 16.384 Bytes begrenzt. Namen sind lowercase Tokens,
Werte sichtbares ASCII, jede Zeile verwendet genau Doppelpunkt plus ein Space,
und kein Name darf doppelt auftreten.

Requests binden Host localhost, Accept application/json, Connection close und
optional Accept-Encoding identity. Nur Content-Type und Content-Length dürfen
den Body rahmen.

Responses akzeptieren neben der Bodyrahmung nur bekannte, nicht weitergegebene
Daemonmetadaten.

## Bodyrahmung

Ein Body erfordert eine eindeutige dezimale Content-Length ohne führende Null,
exakte Byteübereinstimmung und application/json. Die Obergrenze ist 1.048.576
Bytes.

Ohne Content-Length sind Body und Content-Type abwesend. Bei Requests wird dies
als `None`, bei Responses als leerer Body repräsentiert.

## Geschlossene Erweiterungen

Transfer-Encoding, Chunking, Trailer, Upgrade, Expect, zusätzliche Header,
zusätzliche Bytes und eine zweite gepipelinete Nachricht werden abgelehnt.

## Grenzen

Der Framer verarbeitet nur bereits vollständig gelieferte Bytes. Er liest weder
Socket noch Stream und besitzt keine Timeout-, Listener- oder Forwardingmacht.
