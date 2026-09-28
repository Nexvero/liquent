# LQ-756 — Controlled Engine API Daemon Connector

## Umsetzung

`ControlledManifestHandoffSupervisorEngineApiDaemonConnector` bindet einen
Daemonpfad, Timeout und optional eine Socketfactory für kontrollierte Tests.

`connect` erzeugt genau einen Stream, setzt Close-on-exec und Timeout vor dem
Connect, verbindet zum gebundenen Pfad und prüft danach Descriptor und Endpoints.

Die Standardsocketfactory ist ausschließlich `socket.socket`; der Konstruktor
führt keine I/O aus.

## Fehlercleanup

Ein lokaler Streamverweis wird erst nach erfolgreicher Factoryausgabe gehalten.
Jeder folgende Fehler führt zu genau einem best-effort Close und anschließend
zur bestehenden detailfreien technischen Nichtverfügbarkeit.

Nach erfolgreicher Rückgabe besitzt der Connector keine Referenz und keine
spätere Closeverantwortung.

## Nicht umgesetzt

Kein Credentialcheck, Exchange, Listener, Accept, Retry, Pool, Shutdown oder
Prozesslifecycle wird ergänzt.
