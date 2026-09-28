# LQ-616 — Closed Supervisor Launch Identity Policy

## Ergebnis

LQ-616 implementiert
`ManifestHandoffSupervisorLaunchIdentityPolicy`.

## Validierung

UID und GID müssen echte Integer zwischen 1 und 2147483647 sein.

Booleans, root, negative, übergroße und gruppendivergente Werte sind
ungültig.

Owner und Wrapper müssen verschiedene UIDs besitzen.

## Dockerdarstellung

`docker_user` materialisiert ausschließlich die validierte numerische
`wrapper_uid:wrapper_gid`-Form.

Die Darstellung enthält keine Namen oder freien Präfixe.

Alle vier Policywerte bleiben repr-frei.

## Keine I/O-Wirkung

Der Domainkonstruktor liest weder Prozessidentity noch Dateien oder Docker.

Die konkrete Adaptergrenze prüft später den Hostowner gegen den aktuellen
Prozess.

## Nächster Slice

LQ-617 integriert die Policy atomar in Launchfile und Dockerclient.
