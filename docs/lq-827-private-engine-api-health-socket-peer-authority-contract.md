# LQ-827 — Private Engine API Health Socket and Peer Authority Contract

## Ziel

Der spätere lokale Healthtransport wird vor jeder Listenerimplementation an eine
vollständige unveränderliche Socket- und Kernel-Peer-Authority gebunden.

## Socketauthority

Der Socketpfad ist absolut, kanonisch, kein Rootpfad, nicht direkt unter Root und
enthält kein Parentsegment. Socket-UID/GID und Eltern-UID/GID sind separate
explizite positive Systemidentitäten.

Der spätere Socket muss unter dem festen Elternverzeichnis mit diesen Fakten
publiziert werden. Aus Pfad, Prozess-UID oder Gruppenmitgliedschaft wird nichts
abgeleitet.

## Peerauthority

Genau eine positive Peer-UID/GID-Kombination wird explizit gebunden. Eine spätere
Acceptgrenze muss aktuelle Linux-Kernelcredentials prüfen; Request, Header,
Rolle, Membership oder Allow-Boolean sind keine Autoritätsquelle.

Timeout liegt zwischen 1 und 300 Sekunden, Backlog zwischen 1 und 128. Beide sind
fest und positiv.

## Grenzen

Keine Settingsquelle, Listener-, Accept-, Stream-, Protocol- oder
Deploymentcomposition wird in diesem Slice ergänzt.
