# LQ-330 — Disposable PostgreSQL Staging Composition

## Ergebnis

LQ-330 implementiert die kontrolliert mutierende LQ-303-Phase
`disposable_postgres` innerhalb von `liquent-staging-phase-probe`.

Die Composition validiert den autorisierten Compose-Render, beweist die
Abwesenheit aller exakt abgeleiteten Runressourcen, führt genau einen
PostgreSQL-Start aus und inspiziert anschließend die Isolation read-only.

Sie führt keine Migration, keinen Seed, Restore, Cleanup oder Retry aus.

## Autorisierte Eingaben

Die Phase verwendet ausschließlich die bereits geschlossene Probegrenze:

- owner-only aktuelle Staging-Run-Autorisierung;
- daraus abgeleiteten Projektnamen;
- SHA-256-gebundenes Composefile;
- owner-only Runtime- und Image-Environmentdateien;
- unveränderlichen PostgreSQL-Image-Digest;
- expliziten absoluten Dockerpfad;
- erneut gerendertes vollständiges Composemodell.

Es gibt keinen zusätzlichen Service-, Image-, Netzwerk-, Volume-, Container-,
Database-, User-, Timeout- oder Allow-Wert vom Caller.

## Geschlossener Compose-Render

Vor dem ersten möglichen Docker-Effekt verlangt die Composition exakt die
sieben bekannten Services und einen geschlossenen PostgreSQL-Service.

Der PostgreSQL-Service muss enthalten:

- den gebundenen unveränderlichen PostgreSQL-Digest;
- keine veröffentlichten Ports;
- Database und User exakt `liquent`;
- Password ausschließlich über `/run/secrets/postgres_password`;
- genau das feste PostgreSQL-Password-Secret;
- Netze ausschließlich `application` und `data`;
- genau ein PostgreSQL-Datenvolume;
- festen `pg_isready`-Healthcheck;
- `no-new-privileges`, Cap-drop `ALL` und die geschlossene Start-Allowlist.

Doppelte JSON-Schlüssel, unbekannte Services, mutable Images oder abweichende
Sicherheitswerte enden vor der Mutation technisch unavailable.

## Rungebundene Ressourcen

Aus dem bereits validierten Projektnamen werden ausschließlich abgeleitet:

- `<project>-postgres-1` als Container;
- `<project>-application` und `<project>-data` als interne Netze;
- `<project>-postgres-data` als Datenvolume.

Das gerenderte Composemodell muss exakt diese Namen binden. Beide Netze müssen
intern und nicht extern sein. Das Volume darf nicht extern sein.

Globale Namen, Productionressourcen, bestehende `liquent_*`-Netze oder
persistente gemeinsame Volumes sind nicht zulässig.

## Abwesenheitsnachweis

Vor `compose up` führt die Composition ausschließlich read-only Listen für den
exakten Container, beide Netze und das Volume aus.

Jeder Aufruf verwendet den absoluten Dockerpfad, eine feste argv-Liste,
temporäres leeres CWD und ausschließlich `LANG=C`, `LC_ALL=C`.

Nur vier erfolgreiche leere Ergebnisse beweisen Abwesenheit. Ein vorhandener
Name, Nonzero-Exit, stderr, Timeout, Truncation oder Hard Kill endet vor der
Mutation unavailable.

Bestehende Ressourcen werden weder übernommen noch inspiziert, um sie
nachträglich passend zu erklären.

## Exakt eine Mutation

Nach vollständigem Abwesenheitsnachweis wird genau einmal ausgeführt:

`docker compose ... up --detach --no-build --no-recreate postgres`

Der feste Composeprefix enthält beide Environmentdateien, Composefile und
rungebundenen Projektnamen.

Es gibt kein Pull, Build, Scale, zweiten Service, Migration-Gate, Application-
oder Workerstart.

Die Phase führt den Mutationsaufruf höchstens einmal aus.

## Unknown Outcome

Nonzero-Exit, stderr, Timeout, Outputtruncation, Hard Kill oder interne
Prozessstörung beim Start ist technisch unavailable.

Nach einem solchen Ausgang gibt es keinen zweiten `up`, kein Inspect als
heuristische Erfolgsannahme, kein `down`, Stop, Remove, Prune oder
Volume-/Network-Cleanup.

Möglicherweise erzeugte Ressourcen bleiben externer Recoverybestand. Die
State-Machine darf aus diesem Slice keinen scheinbaren Failnachweis ableiten.

## Read-only Isolationsinspektion

Nur nach eindeutig erfolgreichem Start wird der exakt abgeleitete Container
einmal read-only inspiziert.

`database_isolated=true` verlangt gemeinsam:

- laufenden und gesunden Zustand;
- exakt den autorisierten PostgreSQL-Image-Digest;
- passende Compose-Projekt- und Service-Labels;
- keine Portbindungen;
- ausschließlich die beiden rungebundenen internen Netze;
- genau das rungebundene Volume am PostgreSQL-Datenziel.

Ein eindeutig beobachteter Invariantenbruch ergibt neutrales `false` und damit
`failed`. Malformed oder technisch unvollständige Inspektion bleibt
unavailable.

Der Nachweis enthält keine Container-, Netzwerk-, Volume-, Image- oder
Hostdetails.

## Keine Produkt- oder Datenbankoperation

Die Phase öffnet keine Datenbankverbindung und führt keine SQL-Anweisung aus.

Sie erzeugt kein Liquent-Schema, keinen User, Workspace, Membership-, Role-,
Permission-, Job-, Claim-, Outcome- oder Artifactbestand.

Ob Migrationen den erwarteten Head erreichen, entscheiden ausschließlich die
späteren Phasen `migration_gate` und `migration_head`.

Es gibt kein `alembic downgrade`, Restore, Seed oder Application-Rollback.

## Tests

Tests beweisen den exakten einmaligen Start nach vier leeren
Abwesenheitsnachweisen, erfolgreichen neutralen Output und fehlenden
Prozessretry.

Sie prüfen vorhandene Ressourcen und externe Netze vor Mutation, Unknown
Outcome ohne Inspect oder Wiederholung sowie neutralen Fail bei einem
eindeutig ungesunden gestarteten Container.

Kein Test startet Docker oder PostgreSQL.

## Bundle und Nichtziele

Das neue Operatormodul erhöht das Gate auf 34 Operatormodule. Entry Points
bleiben 30, Migrationen 27 und der Head `20260819_0027`.

Es gibt keine Schema-, SQL-, Migration-, Port-, Domainmodell-, Compose- oder
Production-Wiring-Änderung und keinen realen Staginglauf.

## Nächster Slice

LQ-331 sollte eine strikt read-only Reconciliation für einen Unknown Outcome
von `disposable_postgres` implementieren. Sie darf nur exakt rungebundene
Ressourcen klassifizieren und weder fortsetzen noch bereinigen.
