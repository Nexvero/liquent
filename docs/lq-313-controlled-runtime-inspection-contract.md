# LQ-313 — Controlled Runtime Inspection Contract

## Zweck

LQ-313 definiert die kontrollierte Runtime-Inspection für die drei bislang
nicht statisch beweisbaren Phasen:

- `entrypoint` / `entrypoint_present`;
- `input_ownership` / `inputs_owner_only`;
- `data_read_only` / `data_read_only`.

Die Inspection beobachtet Eigenschaften im exakten gebundenen Application-
Image unter Runtime-UID/GID `10001:10001` und mit den tatsächlich gerenderten
Mounts.

Sie erzeugt keine Produkt-, Datenbank-, Researchjob-, Artifact- oder
Authoritymutation.

Dieser Slice implementiert und startet noch keinen Inspectioncontainer.

## Präzise Read-only-Grenze

Ein kurzlebiger Containerstart ist eine Dockerzustandsänderung. „Read-only“
bedeutet hier ausschließlich, dass der Container keine fachlichen oder
persistent nutzbaren Daten verändert.

Der Container ist rungebunden, `--rm`, ohne Restartpolicy, ohne öffentliche
Ports, ohne Docker-Socket, ohne Datenbanksecret, ohne Application-/Data-/Public-
Netz und ohne beschreibbares Artifactvolume.

Er wird nie als erfolgreicher Beleg behandelt, wenn automatische Entfernung,
Netzisolation oder Read-only-Rootfilesystem nicht eindeutig beobachtet wurde.

## Feste Serviceableitung

Die Inspection wird ausschließlich aus dem gerenderten und bereits durch
LQ-311 geprüften `research-worker`-Service abgeleitet.

Image-Digest, Runtimeuser, Config-, Worker-ID- und Researchdaten-Bindmounts
werden unverändert übernommen. Command, Entrypoint, Secrets, Netzwerke,
Artifactvolume, Depends-on, Healthcheck und Restartpolicy werden für den
Inspectioncontainer nicht übernommen.

Der Inspector akzeptiert keine caller-gelieferten zusätzlichen Mounts,
Capabilities, Devices, Environmentwerte, User, Entry Points, Commands,
Netzwerke oder Securityoptionen.

## Containerhärtung

Der feste Containeraufruf verlangt:

- exakt das autorisierte immutable Application-Image;
- User und Group `10001:10001`;
- read-only Rootfilesystem;
- `no-new-privileges`;
- Drop aller Linux-Capabilities;
- keine Devices, PID-/IPC-/UTS-/Userns-Freigaben oder Hostnames;
- Netzwerkmodus `none`;
- geschlossene stdin- und TTY-Grenze;
- begrenzten flüchtigen `/tmp`-tmpfs;
- ausschließlich die drei geprüften read-only Bindmounts;
- feste CPU-, Memory-, PID- und Prozesszeitgrenzen.

Kein Secret wird gemountet. Insbesondere ist `/run/secrets/database_url` im
Inspectioncontainer abwesend.

## Inspection-Executable

Die drei Phasen verwenden ein im Application-Image enthaltenes festes
`liquent-runtime-inspect`-Executable.

Der äußere Probe-Command überschreibt den Image-Entrypoint ausschließlich mit
diesem absoluten, im Image fest erwarteten Executable und genau einem
phasenspezifischen Argument.

Es gibt keine Shell, kein `python -c`, kein PATH-Lookup, kein beliebiges Exec,
keine Commandsubstitution und keine caller-gelieferten Prüfprogramme.

Fehlt das Executable oder stimmt seine im Releasemanifest gebundene
SHA-256-Identität nicht, ist die Phase technisch unavailable.

## Entry-Point-Phase

`entrypoint` prüft ausschließlich im installierten Package-Metadatenbestand,
dass der Console Script Name `liquent-research-worker` genau einmal auf
`liquent_platform.operators.research_worker:main` zeigt.

Zusätzlich wird geprüft, dass das aufgelöste Executable eine reguläre Datei
unter dem unveränderlichen Runtimepräfix ist, nicht verlinkt oder
group/world-writable ist und vom Runtimeuser ausführbar bleibt.

Der Inspector importiert das Zielmodul nicht und startet den Worker nicht.

Nur die vollständige Übereinstimmung ergibt
`{"entrypoint_present":true}`. Eindeutige Abwesenheit oder Abweichung ergibt
`false`; beschädigte Metadaten oder technische Lesefehler bleiben unavailable.

## Input-Ownership-Phase

`input_ownership` öffnet Config- und Worker-ID-Datei jeweils mit
No-follow-Semantik und prüft ausschließlich den offenen Descriptor.

Beide Inputs müssen regulär, UID 10001, Linkcount eins und Modus 0400 oder 0600
sein. Sie müssen unter den exakt gebundenen Containerzielen liegen.

Dateiinhalte werden nicht gelesen. Namen, Hostquellen, Größe und Metadatenwerte
werden nicht ausgegeben.

Alle Bedingungen gemeinsam ergeben `{"inputs_owner_only":true}`. Ein
eindeutiger Metadatenmismatch ergibt `false`; Race, verschwundener Mount oder
I/O-Fehler ist unavailable.

Die Datenbank-URL wird in dieser Phase ausdrücklich nicht geprüft, weil sie im
Inspectioncontainer nicht gemountet wird. Ihre effektive Secretgrenze bleibt
eine getrennte spätere Phase.

## Data-read-only-Phase

`data_read_only` öffnet den Research-Datenroot mit No-follow- und
Directorysemantik und prüft, dass er ein echtes Verzeichnis unter dem exakt
gebundenen Containerziel ist.

Der Inspector verifiziert Mountinfo gegen eine allowlistete read-only
Bindmountdarstellung und prüft, dass weder Root noch ein bereits vorhandenes
synthetisches Fixture vom Runtimeuser schreibbar sind.

Er führt keinen Create-, Open-for-write-, Rename-, Link-, Unlink-, Chmod- oder
Probe-Write-Versuch aus. Fehlende Schreibberechtigung wird aus effektiven
Mountflags und Descriptor-/Accessmetadaten beobachtet, nicht durch eine
absichtlich fehlschlagende Mutation.

Nur vollständige Übereinstimmung ergibt `{"data_read_only":true}`. Ein
eindeutig beschreibbarer Mount ergibt `false`; unlesbare oder mehrdeutige
Mountinfo bleibt unavailable.

## Neutrale Ausgabe

Das innere Inspection-Executable schreibt exakt dieselbe kanonische
Ein-Zeilen-Struktur wie LQ-310: Schema-Version eins, exakte Phase und genau das
zugehörige Boolean-Faktum.

stderr bleibt leer. Es gibt keine UID-, Mode-, Mount-, Paket-, Pfad-,
Executable-, Inode- oder Fehlerdetails.

Der äußere Probe-Command akzeptiert nur Exitcode null, begrenzten stdout,
leeren stderr und das exakte phasenspezifische Schema. Alles andere ist
technisch unavailable.

## Unknown Outcome und Containerende

Timeout, Dockerverlust, unklarer Containerstart, verlorener Output,
unklare Auto-Removal-Wirkung oder erforderlicher SIGKILL sind unavailable.

Der Probe-Command startet keinen zweiten Inspectioncontainer für dieselbe Phase
und versucht keine automatische Bereinigung oder Wiederholung.

Ein zurückgebliebener rungebundener Inspectioncontainer ist Incident-/Recovery-
Bestand und kein Grund für `passed` oder einen ungebundenen Remove-Aufruf.

## Ressourcenbesitz

Das innere Executable besitzt nur geöffnete read-only Descriptoren und seine
begrenzten Outputbytes.

Der äußere Probeprozess besitzt nur den von ihm gestarteten kurzlebigen
Inspectionprozess. Image, Mountquellen, Dataset und Docker-Daemon bleiben
extern besessen.

Es gibt kein `compose down`, Containerprune, Volume-/Netzwerkcleanup oder
Löschen eines zurückgebliebenen unbekannten Containers.

## Nichtziele

LQ-313 entscheidet noch keine interne Implementierung des Inspectors,
Paketmetadatenbibliothek, Mountinfo-Parserdetails, exakte CPU-/Memory-/PID-
Zahlen oder Docker-JSON-Version.

Keine Artifactfähigkeit, Secretownership der Datenbank-URL, Migration,
Datenbankreadiness, Job-, Revocation-, Log- oder SIGTERM-Phase wird
implementiert.

Es gibt keine CLI-Registrierung, Containeroperation, Schema-, SQL-, Migration-,
Port-, Domainmodell- oder Composeänderung.

## Implementierungsfolge

LQ-314 sollte zuerst das reine `liquent-runtime-inspect`-Executable über
injizierte Package-, Descriptor- und Mountinfo-Grenzen implementieren.

LQ-315 kann danach die gehärtete Docker-Run-Composition in den äußeren
staging-only Probe-Command ergänzen.
