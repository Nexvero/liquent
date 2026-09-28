# LQ-310 — Closed Staging Probe Command Contract

## Zweck

LQ-310 definiert den geschlossenen staging-only Commandvertrag für das von
LQ-309 erwartete Probe-Executable.

Der Probe-Command beobachtet oder bewirkt genau eine angeforderte LQ-306-Phase
und schreibt genau ein neutrales JSON-Objekt nach stdout.

Er entscheidet weder Phasenreihenfolge noch Retry, Evidencepersistenz,
Gesamtstatus, Readiness, Deploymentfreigabe oder Cleanup.

Dieser Slice implementiert und startet den Command noch nicht.

## Feste CLI

Der Command akzeptiert ausschließlich:

- `--phase` mit genau einem der 29 bekannten Phasennamen;
- `--docker-executable` als absoluten regulären ausführbaren Pfad;
- `--authorization-file` als owner-only geschlossene LQ-306-Runbindung;
- `--compose-file` als absoluten regulären nicht verlinkten Pfad;
- `--runtime-env-file` als owner-only reguläre Datei;
- `--image-env-file` als owner-only reguläre Datei;
- `--project-name` nach der Grammatik `liquent-<opake-run-id>`.

Alle sieben Argumente sind erforderlich und dürfen genau einmal vorkommen.
Positionsargumente, unbekannte Optionen, Abkürzungen, Defaults und Werte aus
Environment, PATH oder Arbeitsverzeichnis sind unzulässig.

Der Command akzeptiert weder DSN, Secret, Imagewert, Composeprofil, Service,
Scale-Wert, Timeout, Outputpfad noch zusätzliche Dockeroption als CLI-Wert.

## Inputprüfung

Alle Pfade werden vor Dockerzugriff ohne Symlink-Follow geprüft.

Runtime- und Image-Environmentdateien müssen aktueller-Owner-besessen,
Linkcount eins und 0400 oder 0600 sein. Der Command gibt weder Dateinamen noch
Inhalte aus.

Das Composefile muss mit dem in der LQ-306-Autorisierung gebundenen SHA-256
übereinstimmen. Die Runbindung wird ausschließlich aus der expliziten
owner-only Autorisierungsdatei geladen.

Fehlende, veränderte, fremde, breite oder mehrfach verlinkte Inputs enden vor
jedem Dockeraufruf technisch detailfrei.

## Docker-Aufrufe

Der Probe-Command startet Docker ausschließlich über den expliziten absoluten
Executable-Pfad und feste argv-Listen ohne Shell.

Jeder Compose-Aufruf enthält exakt beide `--env-file`-Argumente, `--file`,
`--project-name`, den phasenspezifischen Subcommand und die feste erlaubte
Serviceauswahl.

Build, Bake, Exec mit Shell, Attach, Copy, Export, Import, Commit, Push, Login,
Logout, Contextwechsel, Pluginaufruf, System-Prune und ungeprüfte `run`-
Kommandos sind verboten.

Der Probe erbt keine Proxy-, Credential-, Registry-, Cloud-, SSH-, Git-,
Python-, Compose- oder Docker-Overridevariablen.

## Neutrales Outputschema

Bei vollständig beobachtbarer Phase schreibt stdout exakt ein UTF-8-JSON-
Objekt mit:

```json
{"schema_version":1,"phase":"<phase>","facts":{"<fact>":true}}
```

Das Boolean ist `true`, wenn die phasenspezifische Invariante beobachtet wurde,
und `false`, wenn ein eindeutiger fachlicher Bruch beobachtet wurde.

stdout enthält genau eine kanonische Zeile mit abschließendem Newline. stderr
bleibt leer. Es gibt keine weiteren Schlüssel, Kommentare, Fortschrittszeilen,
IDs, Pfade, Digests, Zählerwerte oder Fehlertexte.

Technische Nichtverfügbarkeit erzeugt kein scheinbar gültiges JSON und endet
mit Nonzero-Exit. LQ-308 reduziert diesen Ausgang ausschließlich zu
`unavailable`.

## Read-only Phasen

`image_digest` verifiziert, dass alle tatsächlich aufgelösten Images exakt den
gebundenen immutable Digestreferenzen entsprechen. Fakt:
`digest_matches`.

`image_revision` liest ausschließlich freigegebene OCI-Labels und vergleicht
die gebundene Source-Revision. Fakt: `revision_matches`.

`entrypoint` prüft im Image ohne Containerstart, dass der installierte
Research-Worker-Command auflösbar ist. Fakt: `entrypoint_present`.

`runtime_identity` prüft konfigurierte und effektive UID/GID ausschließlich
gegen `10001:10001`. Fakt: `uid_gid_matches`.

`rollback` prüft nur vorhandene gebundene Backup-/Rollback-Evidence auf
Aktualität und Digestbindung. Fakt: `rollback_current`.

`trading_disabled` prüft gerenderten Config-/Composezustand auf Konkurrenz eins,
Trading disabled und Abwesenheit von Broker-/Exchange-Eingaben. Fakt:
`trading_disabled`.

`compose_render` führt ausschließlich `docker compose config` aus und prüft
kanonisch gebundene Services sowie vollständige Interpolation. Fakt:
`render_valid`.

`command`, `networks`, `mounts`, `secret_mount` und `grace` prüfen im
gerenderten Modell exakt Workerargv, fehlende Public-Anbindung, read-only
Inputs/ein beschreibbares Artifactvolume, owner-only Secretziel und 60 Sekunden
Grace. Fakten: `command_exact`, `networks_isolated`, `mounts_bounded`,
`secret_owner_only`, `grace_bounded`.

`input_ownership`, `data_read_only` und `artifact_capabilities` verwenden nur
einen fest definierten staging-only Inspectioncontainer ohne Shell und ohne
Netzwerk. Artifactprobes liegen unter einem dedizierten neuen Runprefix.
Fakten: `inputs_owner_only`, `data_read_only`,
`artifact_capabilities_valid`.

`migration_head`, `idle_no_mutation`, `log_redaction`, `artifact_integrity` und
`no_sigkill` lesen ausschließlich gebundene neutrale Beobachtungen. Fakten:
`migration_head_exact`, `idle_mutation_free`, `logs_redacted`,
`artifact_hash_matches`, `sigkill_unused`.

## Kontrolliert mutierende Phasen

`disposable_postgres` darf ausschließlich die dedizierte rungebundene
PostgreSQL-Serviceinstanz erstellen und deren Isolation prüfen. Es darf keine
bestehende Datenbank auswählen. Fakt: `database_isolated`.

`migration_gate` startet genau einmal ausschließlich den Compose-Service
`migration-gate`, wartet auf Exit und akzeptiert nur Exitcode null. Fakt:
`migration_gate_succeeded`.

`idle_start` startet genau einen `research-worker` nach erfolgreichem
Migration-Gate und beobachtet ein begrenztes Idleintervall. Fakt:
`idle_stable`.

`authorized_acceptance` verwendet einen festen synthetischen Actor, Workspace,
CSRF-Nachweis und Dataset-Snapshot ausschließlich über die bestehende
authentifizierte Staging-Control-Plane. Fakt: `acceptance_authorized`.

`claim_heartbeat` beobachtet genau einen Claim und mindestens den initialen
Heartbeat ohne private Identitäten auszugeben. Fakt: `claim_heartbeat_exact`.

`terminal_outcome` wartet begrenzt auf genau ein terminales Outcome und prüft,
dass kein zweites Outcome oder Claim existiert. Fakt:
`terminal_outcome_exact`.

`revocation` entzieht ausschließlich dem synthetischen Actor die vorher
gebundene `research:write`-Permission und beobachtet die fail-closed
Invalidierung des vorbereiteten zweiten Jobs vor Resolver-/Artifactzugriff.
Fakt: `revocation_fail_closed`.

`idle_sigterm` und `running_sigterm` senden jeweils genau ein SIGTERM an den
rungebundenen Workercontainer und beobachten den vertraglichen Stop. Fakten:
`idle_stop_clean` und `running_stop_bounded`.

Keine mutierende Phase darf implizit eine andere Phase, einen Retry oder
Cleanup ausführen.

## Phasenvoraussetzungen

Der Probe-Command liest keine interne LQ-306-Historie und entscheidet keine
Fortsetzung.

Er prüft jedoch vor jeder mutierenden Operation die minimal erforderlichen
externen rungebundenen Voraussetzungen. Fehlen diese, endet die Phase
technisch, ohne sie herzustellen.

Insbesondere startet `idle_start` kein Migration-Gate,
`authorized_acceptance` keinen Worker, `revocation` keinen ersten Job und eine
SIGTERM-Phase keinen Container.

## Unknown Outcome

Timeout, Docker-Daemonverlust, abgeschnittener Output, verlorene Verbindung,
unklarer Containerexit, teilweise beobachtete Datenbankmutation oder
unbestätigter Signalempfang sind technisch nicht verfügbar.

Der Command wiederholt keine Operation mit möglichem Effekt und versucht nicht,
den Ausgang durch heuristische Logs oder einen zweiten Mutationsaufruf zu
erraten.

Ein späterer read-only Recovery-/Reconciliation-Slice ist erforderlich, bevor
derselbe Run fortgesetzt oder ersetzt werden darf.

## Secret- und Loggrenze

Der Probe schreibt selbst keine Logs. Dockerstdout und -stderr werden begrenzt
im Speicher ausgewertet und nie weitergereicht.

DSNs, Secretwerte, Environmentinhalte, Authorizationheader, Cookies,
CSRF-Tokens, Hostpfade, Containerinspect-Rohdaten, Actor-/Workspace-/Job-/Claim-
IDs und Artifactinhalte verlassen die Probegrenze nicht.

Jede Exception ist detailfrei und enthält ausschließlich einen stabilen
technischen Code.

## Ressourcenbesitz

Der Probe besitzt nur seine kurzlebigen Docker-Unterprozesse und den
dedizierten Artifactprobe-Prefix, den er selbst in der entsprechenden Phase
neu erzeugt.

Composeprojekt, Container, Datenbank, Images, Volumes, Netze und synthetische
Produktdaten bleiben extern besessen.

Der Probe führt kein `compose down`, Stop-all, Volume-/Network-/Image-Prune,
Datenbankdrop oder allgemeines Artifactcleanup aus.

## Nichtziele

LQ-310 entscheidet noch keine interne Pythonmodulstruktur, konkrete
Docker-JSON-Ausgabeversion, HTTP-Clientklasse, SQL-Statements,
Reconciliation-/Cleanupgrenze oder Productionintegration.

Es gibt keine Probeimplementierung, CLI-Registrierung, Console Entry Point,
Dockerausführung, Datenbankverbindung, Signalübertragung, Schema-, SQL-,
Migration-, Port-, Domainmodell- oder Composeänderung.

## Implementierungsfolge

LQ-311 sollte den Probe-Command zunächst für die rein read-only Image-,
Compose- und effektiven Mount-/Identityphasen implementieren.

Mutierende PostgreSQL-, Job-, Revocation- und SIGTERM-Phasen bleiben danach
separate additive Implementierungsslices mit eigenen Unknown-Outcome-Tests.
