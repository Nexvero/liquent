# LQ-2633 — Confirmed Bootstrap Network Provisioning

## Problem

Basis- und Edge-Compose referenzieren vier externe Docker-Netzwerke. Deren
Erzeugung war bisher eine implizite Betreiberhandlung. Ein fehlendes Netzwerk
hätte deshalb erst nach Beginn des bestätigten Bootstrap-Laufs zu einem
Compose-Fehler geführt; ein gleichnamiges, aber falsch isoliertes Netzwerk
hätte eine unerwünschte Kommunikationsgrenze erzeugen können.

## Vertrag

Der Online-Preflight untersucht jedes bereits vorhandene Netzwerk vor einer
Mutation. Alle vier Netzwerke müssen den lokalen Bridge-Treiber verwenden.
`liquent_public` ist nicht intern, damit ausschließlich der Edge dort die
Control Plane erreicht. `liquent_application`, `liquent_data` und
`liquent_observability` sind interne Bridges. Eine Abweichung beendet den
Preflight geschlossen.

Fehlende Netzwerke sind im read-only Preflight kein Fehler, sondern werden als
noch ausstehende Bootstrap-Handlung gemeldet. Erst der bereits durch das
Literal `INITIALIZE-STAGING` autorisierte Bootstrap erzeugt sie. Die
Bereitstellung ist idempotent und prüft jedes vorhandene oder neu erzeugte
Netzwerk nochmals auf Treiber und Isolation, bevor Compose einen Dienst
startet.

## Grenze

Der Slice startet keinen Container, bindet keinen Port und führt den Bootstrap
nicht aus. Er löscht auch bei einem späteren Fehlschlag keine neu erzeugten
Netzwerke: Sie enthalten zu diesem Zeitpunkt keine Anwendungsdaten und bleiben
als überprüfbare, wiederverwendbare Infrastruktur zurück. Volumes, Secrets,
DNS, Zertifikate und Dienstzustände bleiben unverändert.
