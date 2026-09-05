# LQ-703 — Minimal Supervisor Deployment Capability Contract

## Ziel

Dieser Vertrag beschreibt die kleinste zulässige Hostfähigkeit für den
Manifest-Handoff-Supervisorkandidaten vor jeder Composeaktivierung.

Eine laufende Entrypointcomposition ohne vollständige Hostfähigkeit bleibt
not-ready und darf keinen Teilbetrieb behaupten.

## Engine-API-Grenze

Der Control-Plane-Prozess benötigt genau die vom geschlossenen
`LocalDockerEngineHttpClient` verwendeten Containeroperationen.

Ein roh gemounteter Docker-Daemon-Socket vermittelt jedoch technisch eine weit
größere Hostautorität als dieser Clientvertrag.

Vor Aktivierung ist daher eine dedizierte, eingeschränkte lokale Engine-API-
Grenze erforderlich, die ausschließlich die feste API-Version, Operationen,
Labels und Containerprofile des Supervisors akzeptiert.

Pull, Build, Exec, Attach, Logs, freie Container, freie Mounts, Hostnetwork und
privilegierte Profile bleiben außerhalb dieser Grenze.

## Control-Wurzel

Die konfigurierte Control-Wurzel muss im Control-Plane-Container und auf dem
Docker-Host unter demselben absoluten Pfad liegen.

Der Daemon interpretiert dynamische Child-Bindquellen im Hostnamensraum; eine
abweichende Containerpfadübersetzung würde auf einen anderen Hostpfad zeigen.

Die Wurzel ist ein dedizierter persistenter Hostpfad, kein Named Volume und
keine breite Elternwurzel.

## Rechte und Identität

Der Control-Plane-Prozess läuft mit der konfigurierten Host-Owner-UID.

Die Control-Wurzel und jedes Child-Verzeichnis gehören dieser UID, sind Modus
0700 und werden nicht von anderen Diensten geteilt.

Die konfigurierte Reader-GID ist eine kontrollierte Zusatzgruppe des Parents
und die primäre GID der Wrapper; Wrapper-UID und Parent-UID bleiben verschieden.

Die Engine-API-Grenze besitzt eine getrennte Zusatzgruppe. Root, privilegiert,
Host-PID und zusätzliche Linux-Capabilities bleiben verboten.

## Parent-Launchdokument

Vor Container-Create muss der Parent das kanonische `launch-binding.json`
no-replace in das gebundene Control-Verzeichnis schreiben.

Die Datei gehört Host-Owner-UID und Reader-GID, hat Modus 0640 und wird dem
Child ausschließlich read-only unter dem festen Launchpfad gebunden.

Eine Digestangabe oder ein Dockerlabel ersetzt die physische Publikation nicht.

## Childfähigkeiten

Writer und Recovery erhalten weiterhin nur die bereits festgelegten
profilgetrennten Mounts.

Sie erhalten weder Engine-API-Zugriff noch die Control-Wurzel, sondern nur ihr
einzelnes gebundenes Child-Verzeichnis.

## Readiness und Shutdown

Readiness verlangt aktuelle Engine-API-, Control-Wurzel-, Identitäts- und
Launchpublisher-Prüfung vor positiver Aussage.

Shutdown markiert stopping, verhindert neue Preparevorgänge, schließt den
Engineclient und lässt bereits persistierte terminale Fakten unverändert.

## Nicht Teil dieses Slices

Keine Compose-, Socket-, Proxy-, Mount-, User-, Group-, Schema-, SQL-, Port-,
Migrations-, CLI-, Deployment- oder Productionaktivierung wird umgesetzt.
