# LQ-823 — Local Engine API Health Transport Contract

## Ziel

Vor einem Listener wird das private lokale Healthprotokoll als reine bounded
Request-/Response-Grenze geschlossen.

## Requests

Akzeptiert werden ausschließlich zwei bytegenau kanonische, bodylose HTTP/1.1-
Requests: `GET /live` und `GET /ready`, jeweils mit `host: local` und
`connection: close`.

Der Request ist höchstens 128 Bytes groß. Andere Methoden, Ziele, Headerformen,
Hosts, Bodies, zusätzliche Bytes oder unbekannte Routen scheitern fail-closed;
es gibt keinen 404- oder Kompatibilitätsfallback.

## Antworten

Die Antwort ist kanonisches JSON von höchstens 256 Bytes mit genau dem
booleschen Feld `live` beziehungsweise `ready` und einem festen öffentlichen
Grund. True liefert 200, false liefert 503. Content-Length ist exakt und die
Verbindung wird geschlossen.

Werte stammen ausschließlich aus dem Process Owner. Caller-Header oder Body
können keinen Zustand oder Allow-Wert liefern.

## Grenzen

Kein Socket, Stream-I/O, Listener, Accept, Thread, Server, Deployment oder
Productionclaim wird ergänzt.
