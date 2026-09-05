# LQ-318 — Hardened Artifact Capability Docker Composition

## Ergebnis

LQ-318 ergänzt `artifact_capabilities` in den installierten
`liquent-staging-phase-probe` und verbindet das LQ-317-Executable mit genau
einem gehärteten, bewusst schreibenden Inspectioncontainer.

Die lokale Testsuite injiziert sämtliche Prozessbeobachtungen. Es wurde kein
Dockercontainer und kein externes Volume gestartet oder verändert.

## Vorgeschaltete Revalidierung

Die Phase rendert zuerst ausschließlich das vollständig gebundene Composemodell
mit den autorisierten Environmentdateien, dem geprüften Composefile und dem
rungebundenen Projektnamen.

Vor dem ersten möglichen Write müssen Compose-Render, deaktiviertes Trading,
exakter Workercommand, isolierte Netze, begrenzte Mounts, owner-only Secretziel
und Grace Period erneut `passed` sein.

Das gerenderte Workerimage muss exakt dem autorisierten unveränderlichen Digest
entsprechen. Jeder Mismatch oder technische Fehler stoppt nach dem Render und
vor `docker run`.

## Exakte Volumebindung

Aus dem bereits validierten Worker-Service wird ausschließlich der Mount am
festen Ziel `/var/lib/liquent/artifacts` übernommen.

Er muss genau einmal als benanntes Dockervolume, explizit nicht read-only und
mit geschlossener Docker-Namensgrammatik vorliegen. Bindmount, fehlender oder
doppelter Mount, read-only-Status und unsichere Optionszeichen enden vor dem
Containerstart unavailable.

Der Inspectioncontainer erhält genau diesen einen Mount read-write. Config,
Worker-ID, Researchdaten und Datenbank-Secret werden nicht weitergereicht.

## Gehärteter Docker-Run

Der zweite und letzte Prozessaufruf ist fest auf `docker run --rm --pull never`
gebunden und setzt:

- einen opaken deterministischen run-/phasengebundenen Containernamen;
- Netzwerk `none` und keinerlei Portfreigabe;
- read-only Rootfilesystem;
- effektive UID/GID `10001:10001`;
- `no-new-privileges` und Capability-Drop `ALL`;
- PID-Limit 64, Memory 128 MiB und CPU 0,25;
- Logdriver `none`;
- ein 16-MiB-`/tmp`-tmpfs mit noexec, nosuid und nodev;
- genau das eine autorisierte Artifactvolume read-write;
- den absoluten Entrypoint
  `/opt/liquent/venv/bin/liquent-artifact-capability-inspect`;
- exakt das autorisierte Image und ausschließlich `--run-token <token>`.

Es gibt keine Shell, keinen PATH-Lookup, Imagepull, Build, Environmentwert,
Secret, Device, Privileged-Modus, Zusatznetz, Bindmount oder caller-geliefertes
Prüfprogramm.

## Run-Token

Der Token ist der vollständige lowercase SHA-256 über den bereits validierten
Compose-Projektnamen, einen festen Separator und den konstanten Phasennamen
`artifact_capabilities`.

Er wird intern bestimmt und ist für denselben autorisierten Run stabil sowie
gegen andere Phasen gebunden. Der CLI-Aufrufer kann Token, Prefix, Probeinhalt,
Pfad oder erwarteten Boolean nicht liefern.

Der Token enthält keine User-, Workspace-, Job-, Claim-, Artifact- oder
Hostidentität.

## Prozess- und Ergebnisgrenze

Der äußere Dockerprozess erhält ausschließlich LANG/LC_ALL `C`, ein neues
leeres CWD, 60 Sekunden Timeout, fünf Sekunden Terminate-Grace und 65536 Byte
Capture je Kanal.

Nur Exitcode null, leerer stderr und das exakte neutrale LQ-317-Schema werden
vom bestehenden LQ-308-Reducer akzeptiert. `true` ergibt `passed`, `false`
ergibt `failed`.

Timeout, Nonzero, Outputverlust, Truncation, Hard Kill oder Schemafehler ist
detailfrei unavailable.

## Unknown Outcome und Besitz

Nach `docker run` wird kein zweiter Probeaufruf gestartet. Die Composition
sendet keinen Stop-, Remove-, Down-, Prune-, Unlink- oder Cleanupbefehl.

Ein möglicherweise verbliebener Container oder Probe-Prefix bleibt
Recoverybestand des gebundenen Runs. LQ-318 erfindet weder Erfolg noch
Abwesenheit und überschreibt keine spätere Recoveryentscheidung.

Composition und Probe besitzen nur ihren kurzlebigen Prozess beziehungsweise
den exakt reservierten Prefix. Docker-Daemon, Image und Volume bleiben extern
besessen; reguläre Artifacts werden nicht adressiert.

## Bundle und Nichtziele

Es entsteht kein neuer Entry Point und kein neues Operatormodul. Bundle-Gates
bleiben 25 Entry Points, 28 Operatormodule und 27 Migrationen mit Head
`20260819_0027`.

LQ-318 enthält keinen realen Dockerlauf, Recoveryoperator, Datenbankzugriff,
Job, Evidencefinalisierung, Compose-, Schema-, SQL-, Migration-, Port-,
Domainmodell- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-319 sollte den kontrollierten Recoveryvertrag für einen unbekannten
Artifact-Probe-Ausgang definieren. Er muss exakte Run-/Prefixbindung,
read-only Inspektion vor jeder Entfernung und eine getrennte ausdrücklich
autorisierte Cleanupentscheidung festlegen.
