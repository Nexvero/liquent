# LQ-302 — PostgreSQL Multiprocess Research Worker Proof

## Ergebnis

LQ-302 ergänzt den verpflichtenden PostgreSQL-Mehrprozessnachweis für den in
LQ-301 verdrahteten persistenten Research Worker.

Der Slice ändert keine Produktlogik. Er beweist den vollständigen vorhandenen
Pfad gegen eine migrierte Wegwerfdatenbank und zwei unabhängige Prozesse.

## Nachweisaufbau

Das bestehende PostgreSQL-Fixture erzeugt pro Test eine eigene Datenbank und
migriert sie auf den exakten Repository-Head.

Der Test legt genau einen aktiven Benutzer, einen aktiven Workspace, eine
aktive Membership und die explizite `research:write`-Permission an.

Danach akzeptiert der bestehende persistente Control-Plane-Pfad genau einen
Researchjob mit lokalem, fingerprintgebundenem CSV-Snapshot.

Es gibt keinen direkten Test-Insert für Job, Claim oder Outcome.

## Echte Prozessgrenze

Zwei über `spawn` gestartete Prozesse bauen jeweils eine eigene SQLAlchemy
Engine, ihre eigene vollständige LQ-297-Composition, einen lokalen Resolver und
einen lokalen immutable ArtifactStore auf.

Eine Prozessbarriere synchronisiert nur den Start der beiden Versuche. Sie
entscheidet weder Claim noch Gewinner.

Es gibt keinen Python-Lock, gemeinsamen Store, gemeinsame Engine oder
prozesslokalen Gewinnerzustand zwischen den Konkurrenten.

PostgreSQL entscheidet über `FOR UPDATE SKIP LOCKED`, welcher Prozess den
einzigen queued Job erhält.

## Erwartete Beobachtung

Genau ein Prozess liefert `succeeded`; genau ein Prozess liefert neutral
`idle`.

Beide Prozesse müssen regulär mit Exitcode null enden. Jede Exception wird nur
als Typname an den Elternprozess gemeldet und lässt den Test scheitern.

Der erfolgreiche Prozess führt über dieselbe Composition Claim, initialen
Heartbeat, lokalen Backtest, Artifactwrite und claimgebundene Finalisierung
aus.

Die Datenbank enthält danach genau einen Claim und genau ein erfolgreiches
Outcome. Der Job ist über den autorisierten Control-Plane-Lookup als
`succeeded` sichtbar.

Das gespeicherte Artifact existiert am erwarteten opaken Pfad; sein Inhalt
stimmt mit dem persistenten SHA-256-Nachweis überein.

## Fail-closed Grenzen

Der Nachweis verwendet ausschließlich PostgreSQL. Ohne konfigurierte
`LIQUENT_TEST_DATABASE_URL` wird er wie alle markierten Integrationsnachweise
übersprungen; bei `LIQUENT_REQUIRE_POSTGRES_TESTS=1` ist fehlende oder falsche
Konfiguration ein harter Fehler.

Es gibt keinen SQLite-Fallback und keine Behauptung von Mehrprozessatomizität
aus einem reinen In-Process-Test.

Die Worker erhalten keine caller-supplied Authority. Die Annahme und der Claim
lesen die aktuelle persistente Benutzer-, Workspace-, Membership- und
Permissionlage.

## Bewusste Nichtziele

LQ-302 fügt keine Tabelle, Spalte, SQL-Implementierung, Migration, Domainart,
Portsignatur, CLI, Compose-Einstellung oder Runtimekonfiguration hinzu.

Der Slice erzeugt keine reguläre Admission-, Membership-, Capability- oder
Researchjob-Mutationsgrenze.

Er startet keine reale Deployment-Compose-Umgebung, baut kein Image und gibt
keinen externen Host, Provider oder Datensatz frei.

Der bestehende SIGTERM-Vertrag und die 60-Sekunden-Grace-Period wurden bereits
an Entry-Point und Compose statisch geprüft; LQ-302 verändert sie nicht.

## Releaseaussage

Mit LQ-302 sind der persistente Einzeljobpfad, konkurrenzsicherer Claim,
Heartbeat, lokale Ausführung, immutable Artifactpersistenz und terminale
Finalisierung gemeinsam auf der echten PostgreSQL-Prozessgrenze spezifiziert.

Ein lokaler Lauf ohne PostgreSQL liefert weiterhin keine externe
PostgreSQL-Evidenz. Der verpflichtende CI-/Freigabelauf muss deshalb
`LIQUENT_REQUIRE_POSTGRES_TESTS=1` setzen.

## Nächster Slice

LQ-303 sollte die verbleibende operative Deployment-Evidenz auditieren:
gerendertes Compose mit realem Image, Runtime-UID/Secretrechten,
Migration-Gate, Workerstart und kontrolliertem SIGTERM in einer isolierten
Stagingumgebung.
