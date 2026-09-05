# LQ-483 — Supervisor Production Wiring Implementation Blocker Audit

## Ergebnis

LQ-483 prüft, ob der LQ-482-Productionvertrag mit dem aktuellen Repository
sicher implementiert werden kann.

Die Entscheidung lautet: noch nicht, weil drei konkrete process-ownable
Productionabhängigkeiten fehlen.

## Kein Settings-only-Erfolg

Eine validierte Settingsgruppe allein stellt keinen ausführbaren
Supervisorgraphen her.

`supervisor_enabled=true` wäre irreführend, solange der Entrypoint die von
LQ-481 verlangten Abhängigkeiten nicht sicher konstruieren und besitzen kann.

Der Audit ergänzt deshalb keine teilweise Aktivierung.

## Vorhandene Schichten

Persistente Journal-, Runtime-, Artefakt- und Gatebinding-Adapter sind
implementiert.

Geschlossene Engine-, Codec-, File-, Wrapper-, Executor-, Outcome- und
Serviceverträge sowie die LQ-481-Factory sind vorhanden.

Diese Schichten bleiben absichtlich von konkreten Processressourcen getrennt.

## Blocker 1: Engineclient

`LocalDockerManifestHandoffSupervisorEngine` erwartet einen bereits gebundenen
`_LocalDockerEngineClient`.

Es existiert kein konkreter Productionadapter, der genau einen lokalen Daemon
öffnet, API-/Timeoutgrenzen festlegt, Rohantworten schließt und Ownership
implementiert.

Der HTTP-Entrypoint kann deshalb keine sichere Supervisor-Engine erzeugen oder
geordnet schließen.

## Kein improvisierter Dockerzugriff

Shell-, subprocess-, ungebundene Socket- oder Environment-DOCKER_HOST-
Fallbacks sind unzulässig.

Ein beliebiger Docker-SDK-Client ohne geschlossene Übersetzung würde die
LQ-461/LQ-462-Grenzen umgehen.

Der fehlende Adapter benötigt einen eigenen Vertrag und Tests.

## Blocker 2: Capabilityprimitive

`ControlledManifestHandoffSupervisorCapabilityExecutor` verlangt konkrete
Writer- und Recovery-Supervisorports.

Im Repository existieren dafür nur Protocols und ältere kontrollierte
Wertverträge, aber keine processfähige Implementation.

Der Entrypoint kann daher weder Writer noch Recovery nach Released sicher
ausführen.

## Kein Dummy-Outcome

Ein Stub, unmittelbares `outcome_unknown` oder No-op-Executor wäre keine
Productionfähigkeit.

Er würde Released konsumieren, ohne die zugesagte Capability auszuführen, und
könnte einen falschen terminalen Bestand erzeugen.

Fehlende Primitive muss den Service geschlossen halten.

## Blocker 3: Control-Directory-Lifecycle

`AtomicLocalManifestHandoffSupervisorControlArtifacts` verlangt ein absolutes
privates Root und einen injizierten Directory-ID-Resolver.

Es existiert keine persistente Registry oder kontrollierte Anlage für
jobbezogene Control-Directories.

Preparecommands tragen eine Directory-ID, dürfen aber keinen Hostpfad oder
Anlageparameter liefern.

## Warum ein Mapping nicht genügt

Ein in-memory Mapping ginge bei Processrestart verloren und könnte bestehende
Journal-/Runtimebindings nicht sicher wieder auflösen.

Eine direkte String-zu-Pfad-Abbildung würde Traversal-, Ownership-,
Nichtwiederverwendungs- und Retentionverträge umgehen.

Die Directorybindung muss ein dauerhaftes internes System-of-Record besitzen.

## Readinessblocker

Ohne alle drei Abhängigkeiten kann die Composition nicht vollständig aufgebaut
werden.

Readiness darf deshalb keinen aktivierten Supervisor melden.

Eine reine Datenbank-Head-Prüfung beweist weder Engine-, Capability- noch
Control-Directory-Composition.

## Lifespanblocker

Ohne konkreten Engineclient ist Processownership und genau-einmaliges Close
unbestimmt.

Ohne Directoryregistry ist die Reihenfolge von Rootprüfung, Resolveraufbau und
Servicecomposition unbestimmt.

Ohne Capabilityprimitive kann kein vollständiger Graph in den Lifespan
übernommen werden.

## Keine Teilaktivierung

Nur Inspect zu verdrahten und Prepare/Release geschlossen zu lassen würde die
bestehenden vollständigen Serviceports semantisch teilen.

Nur Writer oder nur Recovery zu aktivieren widerspräche der vollständigen
LQ-482-Betriebsgruppe.

Ein In-Memory-Fallback ist in Production ausgeschlossen.

## Unveränderte HTTP-Grenze

Es gibt weiterhin keine öffentliche Supervisorroute.

SessionPrincipal, Researchpermission oder Managementrolle werden nicht als
Ersatzauthority verwendet.

Der Audit öffnet keinen Transportpfad.

## Unveränderte Settings

`PlatformSettings` erhält in LQ-483 keine Supervisorfelder.

Damit kann kein Operator versehentlich eine nicht implementierbare Gruppe
aktivieren.

`public_summary` behauptet keinen Supervisorstatus.

## Unveränderter Entrypoint

`build_app` erzeugt keinen Engineclient, Directoryresolver, Capabilityexecutor
oder Supervisorservice.

Der OIDC- und bestehende App-Lifecycle bleiben unverändert.

Es gibt keinen zusätzlichen Closepfad mit ungeklärtem Ownership.

## Unveränderte Deploymentdateien

Compose und `runtime.env.example` erhalten keine vorzeitigen
Supervisorvariablen, Mounts oder Daemon-Sockets.

Insbesondere wird kein Docker-Socket in den HTTP-Container eingehängt.

Eine solche Deploymententscheidung folgt erst nach geschlossenem Client- und
Privilegevertrag.

## Sichere Reihenfolge

Zuerst benötigt das private Control-Directory einen persistenten
Lifecyclevertrag und eine nicht wiederverwendbare Registry.

Danach folgen konkreter lokaler Engineclient samt Ownership und getrennte
Writer-/Recovery-Capabilityprimitiven.

Erst anschließend darf LQ-482 in Settings und Lifespan implementiert werden.

## Warum Control-Directory zuerst

Prepare bindet Control-Directory vor Start, Ready und jeder Capabilitywirkung.

Engine- und Capabilityadapter benötigen deshalb eine bereits sicher
auflösbare, private Directorygrenze.

Ein späteres Nachrüsten würde bestehende Runtimebindings adoptieren müssen und
ist nicht zulässig.

## Fehler- und Detailgrenze

Der Audit nennt nur fehlende Komponentengruppen, keine reale DSN, Pfade,
Digests, Socketziele oder Identitäten.

Technische Laufzeitfehler bleiben unverändert detailfrei.

Es wird kein neuer Exceptiontyp eingeführt.

## Keine Implementation

LQ-483 ändert keine Settings-, Appfactory-, Entrypoint-, Compose-, Environment-
oder Runtimequelldatei.

Es ergänzt keine Migration, Tabelle, SQL-, Domain- oder Portsignatur.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

## Tests

Fokussierte statische Prüfungen belegen die drei fehlenden konkreten Grenzen,
das Verbot von Settings-only- und Teilaktivierung, unveränderte Runtimefiles
und die sichere Folge.

## Nächster Slice

LQ-484 sollte den persistenten privaten Control-Directory-Lifecyclevertrag
definieren: stabile nicht wiederverwendbare ID, kontrollierte Anlage,
read-only Auflösung, Retention und detailfreie Konflikte.

Schema, Adapter und Operator folgen getrennt.
