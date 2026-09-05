# LQ-739 — Engine API Single-Exchange Contract

## Ziel

Auf genau einem bereits verbundenen Clientstream und einem davon verschiedenen,
bereits verbundenen Daemonstream wird höchstens ein vollständig gegateter
Request-/Response-Austausch ausgeführt.

## Feste Reihenfolge

Die Clientnachricht wird begrenzt gelesen und vollständig durch Framing, Route
und gegebenenfalls Create-Semantik autorisiert. Erst danach darf dieselbe
bytegenaue Nachricht zum Daemon geschrieben werden.

Die Daemonantwort wird begrenzt gelesen und mit dem Requestnachweis
operationsgebunden autorisiert. Erst danach wird eine kanonische lokale Antwort
zum Client geschrieben.

## Responseprojektion

Nur Status, normalisierter Content-Type und autorisierter Body verlassen die
Responsepolicy. Reasonphrase und Header werden lokal aus einer festen Tabelle
erzeugt.

JSON-Antworten erhalten Connection close, application/json und exakte
Content-Length. Bodylose Antworten erhalten nur Connection close.

Daemonmetadaten und Fehlerdetails werden nie weitergereicht.

## Fehlerwirkung

Ein abgelehnter Request erzeugt keine Daemonschreibwirkung. Eine abgelehnte oder
unvollständige Daemonantwort erzeugt keine Clientschreibwirkung.

Ein Fehler nach begonnener Daemonschreibwirkung kann ein unbekanntes
Upstreamergebnis bedeuten und wird nicht automatisch wiederholt.

## Ownership

Beide Streams, ihre Timeouts und ihr Close gehören dem Aufrufer. Derselbe Stream
darf nicht beide Rollen erfüllen.

## Grenzen

Kein Listener, Accept, Connect, Socketaufbau, Timeout, Close, Retry oder Loop
wird in diesem Slice ergänzt.
