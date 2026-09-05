# LQ-728 — Closed Engine API HTTP/1.1 Framing

## Umsetzung

`ClosedManifestHandoffSupervisorEngineApiHttp11Framing` dekodiert Request und
Response getrennt in unveränderliche Werte. Startzeile, Headerblock und Body
werden genau einmal getrennt.

Die Implementierung nutzt ausschließlich Content-Length. Die deklarierte Länge
muss der gesamten verbleibenden Nachricht entsprechen; dadurch sind Suffixe,
Pipelining und widersprüchliche Rahmung nicht darstellbar.

## Requestwert

Der Requestwert enthält nur Methode, Target, normalisierten Content-Type und
Body beziehungsweise explizite Bodyabwesenheit. Headerwerte wie Host und
Connection werden geprüft, aber nicht als Autorität weitergereicht.

## Responsewert

Der Responsewert enthält nur numerischen Status, normalisierten Content-Type
und Body. Server-, Datum-, API- und Plattformmetadaten werden nicht exportiert.

## Fehlergrenze

Syntax-, Typ-, Größen-, Längen- und Erweiterungsfehler werden auf die bestehende
detailfreie technische Nichtverfügbarkeit reduziert.

## Nicht umgesetzt

Kein inkrementeller Parser, Streamreader, Socket, Timeout, Listener,
Peercredentialcheck oder Forwarder wird hinzugefügt.
