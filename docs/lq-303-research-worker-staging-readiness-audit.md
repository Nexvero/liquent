# LQ-303 — Research Worker Staging Readiness Audit

## Ergebnis

LQ-303 definiert das fail-closed Evidence-Gate für einen realen isolierten
Staginglauf des persistenten Research Workers.

Der reale Lauf wurde in diesem isolierten Worktree nicht ausgeführt und ist
nicht freigegeben. Hier stehen kein Docker-Daemon, kein gebundenes
Releaseimage, keine Staging-PostgreSQL-URL und keine freigegebenen
Runtime-Secrets zur Verfügung.

Der aktuelle externe Readinessstatus ist deshalb detailfrei `unavailable`,
nicht `approved`.

## Neu geschlossene Vertragslücke

Das Runbook bindet jede Bewertung an genau einen opaken Run, eine
Repositoryrevision, einen unveränderlichen Image-Digest, einen
Compose-Dateihash und den erwarteten Migration-Head.

Evidence eines anderen Laufs, Images oder Environments darf nicht übernommen
werden. Mutable Tags, Platzhalter und unvollständige Bindungen scheitern
geschlossen.

## Image- und Rendernachweis

Vor jedem Start muss das reale Image den installierten
`liquent-research-worker`, die gebundene Revision und Runtime-UID/GID
`10001:10001` nachweisen.

Compose muss mit den realen expliziten Environmentquellen gerendert werden.
Der Rendernachweis prüft Commandargumente, interne Netze, fehlende Ports,
read-only Inputs, einzig beschreibbares Artifactvolume, Secretziel,
Concurrency eins und 60 Sekunden Grace Period.

Gerenderte Evidence darf keine DSN-, Secret- oder privaten Hostpfadwerte
enthalten.

## Effektive Dateigrenze

Compose-Text allein beweist keine wirksame owner-only Grenze.

Das Runbook verlangt deshalb eine In-Container-Inspektion vom exakten
Runtimeuser: reguläre Dateien, Linkcount eins, Owner UID 10001 und Modus 0400
oder 0600 für Config, Worker-ID und Datenbank-URL.

Researchdaten müssen effektiv read-only sein. Das Artifactvolume muss die
owner-kontrollierte Directorypolicy und die für immutable Writes erforderliche
Create-, Fsync-, Link- und Read-back-Semantik erfüllen.

Ein dedizierter temporärer Probe-Prefix darf nach erfolgreicher Verifikation
wieder entfernt werden; andere Artifacts bleiben unverändert.

## Migration und leerer Start

Das Migration-Gate muss vor dem Worker mit Exitcode null abschließen.

Ein unabhängiger Read-only-Nachweis muss danach den exakten Alembic-Head sehen.
Der Worker muss über mindestens ein begrenztes Idle-Intervall stabil laufen,
ohne bei leerer Queue Job-, Claim-, Outcome-, Artifact- oder Authorityfakten zu
erzeugen.

Logs dürfen keine privaten Identitäts-, Job-, Pfad-, DSN-, Credential- oder
Fehlerdetails enthalten.

## Kontrollierter Jobnachweis

Ein synthetischer Stagingjob muss über die vorhandene authentifizierte,
CSRF-geschützte und aktuell autorisierte Control Plane angenommen werden.

Der Nachweis bindet genau einen Claim, initialen Heartbeat, ein terminales
Outcome und ein hashverifiziertes immutable Artifact.

Ein zweiter Job wird nach Entzug von `research:write`, aber vor Claim geprüft.
Er muss ohne Resolver- und Artifactzugriff invalidiert werden. Damit wird nicht
nur der Happy Path, sondern auch aktuelle Revocation am Workerpfad beobachtet.

## SIGTERM-Nachweis

Im Idle-Fall muss genau ein SIGTERM weitere Claims verhindern und innerhalb
der 60-Sekunden-Frist zu normalem Exit führen.

Im Running-Fall muss entweder die claimgebundene Finalisierung innerhalb der
Frist gelingen oder spätere Lease-Recovery greifen. Doppelte terminale Outcomes
sind in beiden Fällen ausgeschlossen.

SIGKILL ist kein erfolgreicher Nachweis des kontrollierten Pfads.

## Entscheidungsgrenze

Außerhalb des geschützten Evidencebestands wird nur `approved`, `rejected` oder
`unavailable` festgehalten.

Fehlende, veraltete, unzugängliche, mehrdeutige oder secrettragende Evidence
ist `unavailable`. Eine explizit verletzte Invariante ist `rejected`.

Keine negative Entscheidung nennt Secret, Hostpfad, Job, Actor oder internen
Infrastrukturgrund.

Approval gilt nur für den gebundenen Staginglauf und Digest. Es autorisiert
weder Production noch automatische Deployments, Skalierung, Trading oder die
Erzeugung regulärer Produktfakten.

## Nichtziele

LQ-303 fügt keine Produktlogik, Tabelle, Spalte, Migration, SQL-Operation,
Portsignatur, CLI oder automatische Deploymentaktion hinzu.

Der Slice liest keine realen Secrets, startet keine Container, migriert keine
externe Datenbank und sendet kein Signal an einen externen Prozess.

## Nächster Slice

LQ-304 sollte das Runbook in einer ausdrücklich freigegebenen isolierten
Stagingumgebung ausführen, den vollständigen redigierten Evidencebestand
binden und genau eine detailfreie Readinessentscheidung festhalten.
