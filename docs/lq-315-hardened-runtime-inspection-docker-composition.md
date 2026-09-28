# LQ-315 — Hardened Runtime Inspection Docker Composition

## Ergebnis

LQ-315 ergänzt die drei LQ-314-Runtimephasen in den installierten
`liquent-staging-phase-probe`.

Für `entrypoint`, `input_ownership` und `data_read_only` rendert die Probe
zuerst das gebundene Composemodell, prüft alle sieben vorhandenen statischen
Workerinvarianten erneut und startet danach genau einen gehärteten
Inspectioncontainer.

In der lokalen Testsuite wird Docker vollständig injiziert; es wurde kein
realer Container gestartet.

## Zweistufiger Nachweis

Die Phase führt zuerst ausschließlich den bereits gebundenen
`docker compose ... config --format json`-Aufruf aus.

Compose-Render, Trading disabled, Workercommand, Netze, Mountstruktur,
Secretdefinition und Grace müssen jeweils `passed` sein. Ein Mismatch beendet
die Phase vor Containerstart.

Danach muss das gerenderte Workerimage exakt dem autorisierten Image-Digest
entsprechen. Aus den bereits geprüften Mounts werden ausschließlich die drei
absoluten Bindquellen für Config, Worker-ID und Researchdaten übernommen.

Komma, NUL oder Zeilenumbruch in einer Quelle, doppelte oder fehlende Ziele und
nicht absolute Quellen enden vor Containerstart technisch unavailable.

## Fester Docker-Run

Der zweite und letzte Aufruf beginnt exakt mit `docker run --rm --pull never`.

Er setzt:

- opaken deterministischen run-/phasengebundenen Containernamen;
- Netzwerk `none`;
- read-only Rootfilesystem;
- User `10001:10001`;
- `no-new-privileges` und Capability-Drop `ALL`;
- PID-Limit 64, Memory 128 MiB und CPU 0,25;
- Logdriver `none`;
- 16-MiB-`/tmp`-tmpfs mit noexec, nosuid und nodev;
- genau drei read-only Bindmounts;
- festen absoluten Entrypoint
  `/opt/liquent/venv/bin/liquent-runtime-inspect`;
- exakt das autorisierte Image und `--phase <phase>`.

Es gibt kein Secret, Artifactvolume, Environmentargument, Port, zusätzliches
Netz, Device, Privileged, Shell, PATH-Lookup oder implizites Imagepull.

## Prozess- und Outputgrenze

Der Inspectioncontainer erhält das geschlossene LANG/LC_ALL-C-Environment des
äußeren Dockerprozesses, ein neues leeres CWD, 60 Sekunden Timeout, fünf
Sekunden Terminate-Grace und 65536 Byte je Kanal.

Nur Exitcode null, leerer stderr und exakt der neutrale LQ-314-Output wird durch
den bestehenden LQ-308-Parser akzeptiert.

Nonzero, Timeout, Truncation, Hard Kill, verlorener Output oder Schemafehler ist
technisch unavailable. Es gibt keinen zweiten Run, Remove-, Stop- oder
Cleanupversuch.

## Entscheidungs- und Ressourcenbesitz

Ein Boolean `false` bleibt eindeutige neutrale Phase-Evidence; der äußere
Executor entscheidet später über Fortsetzung und LQ-304 über Readiness.

Probe und Composition besitzen keinen Docker-Daemon, kein Image, Dataset oder
Mountsource. Ein unbekannt zurückgebliebener Container bleibt Recoverybestand.

## Bundle und Nichtziele

Es entsteht kein neuer Entry Point oder Operatormodul; Bundle-Gates bleiben 24
Entry Points und 27 Operatormodule bei Head `20260819_0027`.

Keine Artifactfähigkeit, Datenbank-, Migration-, Job-, Revocation-, Log- oder
SIGTERM-Phase wird implementiert. Es gibt keine Schema-, SQL-, Migration-,
Port-, Domainmodell- oder Composeänderung und keine reale Stagingfreigabe.

## Nächster Slice

LQ-316 sollte die kontrollierte Artifact-Capability-Probe definieren. Sie ist
die erste bewusst schreibende Probe und benötigt einen dedizierten neuen
rungebundenen Prefix, atomare Read-back-Prüfung und eine separate
Cleanup-/Unknown-Outcome-Grenze.
