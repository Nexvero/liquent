# LQ-326 — Artifact Capability and Recovery End-to-End Audit

## Ergebnis

LQ-326 auditiert die vollständige lokale Artifact-Capability- und Recoverykette
von LQ-316 bis LQ-325.

Die implementierte Kette ist intern geschlossen und fail-closed verkettet. Sie
ist jedoch noch kein realer Stagingnachweis: In diesem Worktree wurde kein
realer Dockercontainer gestartet, kein gebautes autorisiertes Digest-Image
inspiziert und kein echtes Staging-Artifactvolume verändert.

Die externe Research-Worker-Staging-Readiness bleibt unavailable.

## Geprüfte Slice-Kette

Der Audit bindet:

- LQ-316: Vertrag der ersten bewusst schreibenden Capability-Probe;
- LQ-317: descriptor-relatives In-Image-Executable;
- LQ-318: gehärtete Docker-Run-Composition;
- LQ-319: getrennter Recoveryvertrag;
- LQ-320: read-only Prefixklassifikation;
- LQ-321: revalidierendes exaktes Remove;
- LQ-322: owner-only read-only-then-write Recovery-Composition;
- LQ-323: atomare Evidence und stabiler Claim;
- LQ-324: konservativer Claim-Reconciliation-Vertrag;
- LQ-325: read-only Claim-Reconciliation-Operator.

Alle elf Dokumente LQ-316 bis LQ-326 sind im Repository vorhanden und in der
Roadmap fortgeschrieben.

## Lokaler Dateisystem-End-to-End-Nachweis

Der Audit führt die drei In-Image-Kernfunktionen auf einem privaten temporären
owner-only Root real aus.

Ein erfolgreicher Capabilitylauf erstellt, publiziert, liest zurück und
entfernt seinen Prefix vollständig. LQ-320 beobachtet danach `absent`; LQ-321
liefert idempotent `already_absent` ohne neue Wirkung.

Ein injiziert verlorenes Hardlink-Acknowledgement hinterlässt bewusst
temporären und finalen Namen. LQ-320 klassifiziert diesen exakten gemeinsamen
Inode-/Linkcount-Zustand als `recoverable`; LQ-321 entfernt ihn gezielt und
LQ-320 bestätigt anschließend Abwesenheit.

Ein unbekannter Name wird stabil als `conflict` klassifiziert. LQ-321 verändert
weder Datei noch Inhalt.

Damit sind Erfolg, Unknown-Outcome-Recovery und Conflict-Fail-closed lokal ohne
Dockerwirkung belegt.

## Phasenordnung

`artifact_capabilities` liegt in der unveränderlichen 29-Phasen-Reihenfolge
nach `data_read_only` und vor `migration_gate`.

Die normale Staging-State-Machine kann die schreibende Probe deshalb erst nach
den statischen und Runtime-read-only Gates erreichen. Ein nicht bestandenes
Artifact-Gate stoppt alle späteren Datenbank-, Worker-, Job- und Signalphasen.

Die Reihenfolge wird im Audit direkt gegen das kanonische `PHASES`-Tupel
geprüft.

## Prozess- und Capability-Trennung

Fünf getrennte Console Entry Points bilden die Kette:

- Capability-Inspector;
- Recovery-Inspector;
- Recovery-Remove;
- owner-only Recovery-Composition;
- owner-only Claim-Reconciliation.

Die normale LQ-318-Composition mountet nur das Artifactvolume read-write.
Recovery startet immer LQ-320 read-only und LQ-321 nur nach `recoverable`.

Claim-Reconciliation enthält keinen LQ-321-Entrypoint und konstruiert
ausschließlich einen read-only Artifactvolume-Mount. `recoverable` und
`conflict` bleiben dort `retained`.

## Evidence-first und Unknown Outcome

LQ-323 veröffentlicht finale Recovery-Evidence vor Claimentfernung. Exakte
Wiederholung liest diese Evidence vor Docker und verändert sie nicht.

LQ-325 publiziert Recovery- und Reconciliation-Evidence vor Entfernung eines
Recovery-Claims. Ein Crashrest nach Evidence wird beim exakten Retry ohne
Dockerzugriff geschlossen.

Fehlt bestätigte Evidence nach einem unbekannten Prozessausgang, bleibt der
stabile Claim bestehen. Es gibt keinen automatischen Retry, Force-Unlock,
Volume-Remove, Compose-Down, Prune oder Blind-Cleanup.

## Neutrale Entscheidungsgrenzen

Capability-Evidence enthält ausschließlich ein Boolean-Faktum. Recovery und
Reconciliation geben ausschließlich ihre geschlossenen neutralen Ausgänge aus.

Run-, Recovery-, Reconciliation-, Token-, Volume-, Prefix-, Pfad-, Datei-,
Inode-, Inhalts-, Identity- und Fehlerdetails verlassen die jeweiligen
Prozessgrenzen nicht.

Kein Recoveryausgang schreibt die ursprüngliche unavailable Stagingphase um
oder gewährt Readiness, Artifactfähigkeit, Productiondeployment oder Trading.

## Bundle- und Migrationsaudit

Das installierbare Inventar ist konsistent auf:

- 29 Console Entry Points;
- 32 Operatormodule;
- 27 Migrationen;
- Migration-Head `20260819_0027`.

Bundle-Builder, Bundle-Fixtures und LQ-288-Reaudit erzwingen dieselben Werte.
LQ-326 fügt keinen Entry Point und kein Operatormodul hinzu.

## Verbleibende externe Blocker

Nicht vorhanden und nicht behauptet sind:

- ein gebautes, signiertes und für diesen Run autorisiertes Application-Image;
- ein erreichbarer kontrollierter Docker-Daemon;
- ein isoliertes echtes Staging-Artifactvolume;
- reale owner-only Run-, Recovery- und Reconciliation-Autorisierungen;
- externe Evidence aus einem echten Containerlauf;
- die Ausführung der restlichen LQ-303-Gates ab `disposable_postgres`;
- eine unabhängige finale LQ-304-Readinessentscheidung.

Ohne diese Fakten darf kein lokaler Test als Stagingfreigabe interpretiert
werden. Readiness bleibt unavailable.

## Nichtziele

LQ-326 startet keinen Container, baut oder pullt kein Image, öffnet keine
Datenbank, erzeugt keinen Stagingjob und sendet kein Signal.

Es gibt keine Schema-, SQL-, Migration-, Port-, Domainmodell-, Compose-,
Operator-, Production-Wiring- oder Deploymentänderung.

## Nächster Slice

LQ-327 sollte zum nächsten noch nicht implementierten LQ-303-Gate wechseln:
den Vertrag für eine isolierte disposable PostgreSQL-Bereitstellung und den
nachfolgenden rollback-current Nachweis. Ein realer Staginglauf bleibt weiterhin
eine separate ausdrücklich autorisierte externe Operation.
