# LQ-322 — Owner-controlled Artifact Probe Recovery Composition

## Ergebnis

LQ-322 installiert `liquent-artifact-probe-recovery` als getrennte owner-only
Recovery-Composition für unbekannte LQ-318-Artifact-Probe-Ausgänge.

Der Command rendert die ursprüngliche Run-Bindung erneut, führt zwingend den
LQ-320-Inspector read-only aus und startet LQ-321 read-write ausschließlich
nach `recoverable`.

Tests injizieren alle Prozessbeobachtungen. Kein Dockercontainer oder externes
Volume wird tatsächlich verwendet.

## Zwei Autorisierungsdateien

Die ursprüngliche owner-only Staging-Autorisierung wird als historische
Bindung geladen. Ihr damaliges Zeitfenster darf abgelaufen sein; Struktur,
staging Environment, Run-ID, Source-Commit, Image-Digest, Compose-SHA-256,
Migration-Head und getrennte damalige Identitäten müssen weiterhin gültig
sein.

Eine zweite owner-only Recovery-Autorisierung bindet exakt:

- stabile Recovery-ID und ursprüngliche Run-ID;
- Phase `artifact_capabilities`;
- denselben Source-Commit, Image-Digest und Compose-SHA-256;
- getrennte Recovery-Executor- und Autorisiereridentitäten;
- ein aktuelles UTC-Zeitfenster von höchstens einer Stunde.

Zusätzliche Felder, andere Phase, mutable Images, abweichende Bindungen,
gleiche Identitäten oder stale Recoveryzeit enden vor Docker unavailable.

Die Recovery-Datei akzeptiert keinen Token, Prefix, Volume-Namen, Pfad,
gewünschten Ausgang oder Allow-Boolean.

## Erneute Compose-Bindung

Composefile, Runtime- und Image-Environmentdateien werden erneut über private
Grenzen geladen. Der Composehash und das Application-Image müssen den beiden
Autorisierungen entsprechen.

Der Command rendert mit festen `compose config --format json`-Argumenten und
dem exakt aus der Run-ID gebildeten Projektnamen.

Compose-Render, Trading disabled, Workercommand, Netze, Mounts, Secretziel und
Grace Period müssen erneut `passed` sein. Das Workerimage muss exakt dem
autorisierten Digest entsprechen.

Nur das genau einmal gebundene benannte Artifactvolume wird intern übernommen.
Der Caller kann kein Volume auswählen.

## Interne Tokenableitung

Der 64-Hex-Token ist derselbe vollständige SHA-256 über Projektnamen,
Separator und `artifact_capabilities` wie in LQ-318.

Beide Recoverycontainer erhalten exakt diesen intern bestimmten Token. Weder
Recovery-ID noch Actor-, Job-, Workspace-, Artifact- oder Hostwerte fließen in
den Prefix ein.

## Read-only erster Schritt

Der erste Container startet das autorisierte Image ohne Pull mit:

- Netzwerk `none`, read-only Root und UID/GID `10001:10001`;
- `no-new-privileges`, Capability-Drop `ALL` und festen Ressourcenlimits;
- geschlossenem `/tmp`-tmpfs und Logdriver `none`;
- genau dem Artifactvolume read-only;
- absolutem LQ-320-Entrypoint und internem Token.

Er erhält keine Secrets, Config, Worker-ID, Researchdaten, Ports, Bindmounts
oder Container-Environmentargumente.

`absent` wird unmittelbar als `already_absent` ausgegeben. `conflict` bleibt
`conflict`. In beiden Fällen startet kein write-fähiger Container.

## Bedingter Remove-Schritt

Nur das exakt geparste neutrale `recoverable` startet einen zweiten Container.

Er besitzt dieselben Härtungen, dasselbe Image und denselben Token. Der einzige
Unterschied ist das eine Artifactvolume read-write und der absolute
LQ-321-Entrypoint.

Der LQ-320-Ausgang ist kein Delete-Ticket: LQ-321 revalidiert den vollständigen
Bestand selbst erneut. Seine geschlossenen Ausgänge `already_absent`, `removed`
oder `conflict` werden unverändert als Recoveryergebnis übernommen.

Es gibt keinen dritten Container und keine weitere Mutation.

## Prozess- und Fehlergrenze

Alle drei möglichen Dockeraufrufe verwenden ein neues leeres CWD, ausschließlich
LANG/LC_ALL `C`, 60 Sekunden Timeout, fünf Sekunden Terminate-Grace und
begrenztes Capture.

Nonzero, stderr, Timeout, Truncation, Hard Kill, ungültiges JSON, unbekannte
Felder oder Ausgänge enden detailfrei unavailable.

Kein Prozess wird automatisch wiederholt. Nach unbekanntem Inspect- oder
Remove-Ausgang gibt es keinen Stop-, Remove-, Down-, Prune- oder Cleanupversuch.

## Neutrale Ausgabe

Erfolg schreibt ausschließlich kanonisches JSON mit Schema-Version, Operation
`artifact_probe_recovery` und `already_absent`, `removed` oder `conflict`.

Recovery-ID, Run-ID, Token, Volume, Pfade, Dateien, Inhalte, Digests,
Identitäten und technische Fehler werden nicht ausgegeben.

Kein Ausgang ändert die ursprüngliche unavailable Phase oder gewährt
Readiness, Artifactfähigkeit oder Deploymentfreigabe.

## Bundle und Nichtziele

Der neue Entry Point und das Operatormodul erhöhen die Gates auf 28 Entry
Points und 31 Operatormodule. Migrationen bleiben 27 mit Head
`20260819_0027`.

LQ-322 persistiert noch kein Recovery-Evidenceobjekt und implementiert keine
Recovery-ID-Erzeugung, echte Stagingausführung, Compose-, Schema-, SQL-,
Migration-, Port-, Domainmodell- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-323 sollte die private atomare Recovery-Evidenceablage und den
owner-kontrollierten finalen Operator-Handoff ergänzen. Dabei müssen
Recovery-ID-Nichtwiederverwendung und exakte technische Wiederholung ohne
erneuten Write nach bereits bestätigtem Abschluss geschlossen werden.
