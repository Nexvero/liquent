# LQ-704 — Supervisor Host Capability and Path Identity Evidence

## Ergebnis

Statische Evidenz verfolgt Enginezugriff, Controlpfad, Parentidentität und
Launchdatei durch den aktuellen Entrypoint- und Deploymentbestand.

## Fehlende Enginefähigkeit

Der Control-Plane-Service mountet keinen Docker-Socket und keine eingeschränkte
Engine-API-Grenze.

Der konfigurierte `/run/docker.sock`-Wert ist im Runtimebeispiel nur
auskommentiert und erzeugt keine Fähigkeit.

## Fehlende Pfadidentität

Compose bindet keine dedizierte Supervisor-Control-Wurzel unter demselben
absoluten Host- und Containerpfad.

Der sichere Resolver kann deshalb im realen Deployment keine für den Hostdaemon
gültige Child-Bindquelle liefern.

## Fehlende Prozessidentität

Der Control-Plane-Service legt weder feste UID/GID noch die getrennten Reader-
und Engine-API-Zusatzgruppen fest.

Settingswerte allein ändern keine Kernelidentität und keine Socketberechtigung.

## Fehlender Launchpublisher

`AtomicLocalManifestHandoffSupervisorLaunchDocuments` erzwingt korrekte
Eigentümer-, Gruppen- und Modusfakten, wird aber in der neuen process-eigenen
Composition noch nicht erzeugt.

Der Kandidat erhält keine Parentgrenze, die das Launchdokument vor Create
publiziert.

## Bestehende Schutzwirkung

Wrappercommands, feste Childpfade, profilgetrennte Datenmounts und externe
Launchanker bleiben implementiert.

Ohne die vier Hostvoraussetzungen sind sie nicht erreichbar und
`production_ready=false` bleibt korrekt.
