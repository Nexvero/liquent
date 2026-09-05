# LQ-768 — Controlled Engine API Single Accept

## Umsetzung

`ControlledManifestHandoffSupervisorEngineApiAccept` bindet festen Socketpfad,
Clienttimeout und die konkrete Connected-Exchange-Operation.

`serve_one` prüft zuerst den Listener, ruft genau einmal Accept, setzt
Inheritability false und Timeout am Client, prüft dessen Descriptorfakten und
ruft danach genau einmal den Connected Exchange.

Der Client wird unabhängig vom Ergebnis genau einmal geschlossen. Ein
erfolgreicher Exchange mit fehlgeschlagenem Client-Close bleibt technische
Nichtverfügbarkeit.

## Detailfreiheit

Listener-, Accept-, Setup-, Descriptor-, Exchange- und Closefehler werden auf
die bestehende detailfreie technische Grenze reduziert.

## Nicht umgesetzt

Kein Listener-Lifecycle, Connect an der Oberfläche, Retry, Acceptloop,
Parallelismus, Signal- oder Prozesslifecycle wird ergänzt.
