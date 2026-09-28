# LQ-591 — Local Docker Engine HTTP Client

## Ergebnis

LQ-591 implementiert den geschlossenen LQ-590-Client als
`LocalDockerEngineHttpClient`.

Der Client bleibt ohne expliziten Aufruf vollständig inert.

## Lokaler Transport

Der Productiontransport verwendet ausschließlich einen absoluten Unix-Socket.

Jeder Request öffnet eine begrenzte Verbindung, liest höchstens 1 MiB und
schließt Response und Verbindung in jedem Ausgang.

Es gibt keinen Remote-, Environment-, Context-, Proxy- oder Shellfallback.

## Feste API

Alle Pfade sind an Docker API `v1.45` gebunden.

Find, Create, Inspect, Start, Wait, Stop und Kill sind einzeln fest codiert.

Freie Methoden, Pfade, Queries oder Signale sind nicht erreichbar.

## Geschlossene Profile

Writer- und Recovery-Entrypoint sowie numerischer Containeruser werden beim
Clientaufbau gesetzt.

Create akzeptiert nur die exakte LQ-462-Spezifikation.

Der aktive private Directoryresolver liefert den einzigen Hostmount.

Netzwerk, Restart, Rootfilesystem, Capabilities, Privileged und PID-Modus
werden erneut fail-closed geprüft und fest materialisiert.

## Übersetzung

Docker-Inspect wird auf genau die vom LQ-462-Adapter erwartete Map reduziert.

Find inspiziert höchstens zwei gefundene IDs vollständig.

Create inspiziert den erzeugten Container unmittelbar erneut.

Wait akzeptiert nur eine gültige Statusantwort und liest danach denselben
Container direkt.

## Fehler und Besitz

Status-, Größen-, Transport-, Decode-, Duplicate-Key- und Strukturfehler enden
als bestehende `ManifestHandoffRegistryUnavailable`.

Daemontexte oder interne IDs werden nicht übernommen.

`close()` ist idempotent und sperrt jede spätere Operation.

## Keine Aktivierung

Der Slice ergänzt keine Dependency, Settings, Appfactory, Route, Composegruppe,
Socketmount, Migration oder Productionfreigabe.

Head bleibt `20260826_0042` mit 42 linearen Migrationen.

## Nächster Slice

LQ-592 belegt Übersetzung, Grenzen und Ownership mit einem injizierten
wirkungslosen Transport.
