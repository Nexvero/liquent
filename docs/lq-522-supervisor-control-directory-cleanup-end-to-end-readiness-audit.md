# LQ-522 — Supervisor Control-Directory Cleanup End-to-End Readiness Audit

## Ergebnis

LQ-522 auditiert die gesamte Control-Directory-Cleanup-Kette von LQ-491 bis
LQ-521 gegen den aktuellen Workspace.

Die Sicherheitsprimitive und der manuelle Einzel-Operator sind implementiert.

Eine Production-Readiness- oder Releasefreigabe ist noch nicht belegbar.

## Bewertungsmaßstab

Der Audit unterscheidet implementierte Sicherheitslogik, statisch vorhandene
Tests, tatsächlich ausgeführte Evidence, operative Erreichbarkeit und
releasefähiges Packaging.

Ein vorhandener Adapter oder Testquelltext wird nicht als ausgeführter
Productionnachweis gezählt.

## Implementierte persistente Basis

Directory-ID, Handle, Leaf und irreversible Lifecyclezeiten bleiben dauerhaft
nicht wiederverwendbar gebunden.

Retired, Cleanupdecision, vier getrennte Clearancequellen, Attempt,
Clearance, Write Claim, Outcome und Reconciliation besitzen persistente
Foundations bis Head `20260826_0040`.

Es gibt keinen Cleanup durch Löschen der Registryidentität.

## Implementierte Authoritytrennung

Management, Hold, Recovery und References bleiben getrennte append-only
Revisionquellen.

Ihre Mutation liest aktuelle quellenspezifische Authority-Sets innerhalb der
Schreibtransaktion neu.

SessionPrincipal, Rolle, Membership und caller-geliefertes Allow ersetzen
keine dieser Entscheidungen.

## Implementierte atomare Clearance

LQ-508 erzeugt Started-Attempt und positive Clearance atomar.

Actor, Scope, Retired-Ziel, terminales Journal, eligible Decision und alle vier
aktuellen positiven Revisionen werden in derselben Transaktion erneut gebunden.

Ein separat vorhandener Started-Attempt wird nicht nachträglich adoptiert.

## Implementierte physische Sicherheit

Preflight und Wirkung verwenden absoluten privaten Root, No-follow-
Descriptoren, exaktes Leaf, geschlossene Inventur und kanonische Artefaktbytes.

Die Wirkung entfernt nur belegte bekannte Dateien und danach das belegte leere
Leaf.

Es gibt kein rekursives, globbasiertes oder best-effort Cleanup.

## Implementierte Exactly-once-Grenze

Der persistente Write Claim liegt vor jeder möglichen physischen Wirkung.

Execution besitzt genau eine physische Aufrufstelle und persistiert Removed
oder Unknown unmittelbar claimgebunden.

Nach möglicher Wirkung gibt es keinen automatischen zweiten Remove.

## Implementierte Reconciliation

Ein nach Crash verbliebenes `write_claimed` wird zuerst dauerhaft als Unknown
gesichert.

Danach klassifiziert der lokale Inspector absent, present oder conflict rein
lesend und persistiert den terminalen Reconciliationausgang.

Kein Reconciliationausgang reaktiviert denselben Attempt.

## Implementiertes explizites Opt-in

LQ-517 baut die Kette nur nach bewusstem Factoryaufruf auf.

LQ-519 paketiert einen separaten kurzlebigen Console Entry Point mit getrennten
`execute`- und `reconcile`-Befehlen.

Es gibt weiterhin keine automatische Planung, Directorysuche oder
Batchwirkung.

## Vorhandene Testquellen

LQ-520 beschreibt den echten PostgreSQL-Execute-Pfad bis
`completed/removed` und die gesperrte Reconciliation eines terminalen Attempts.

LQ-521 beschreibt echte PostgreSQL-Crash-Reconciliation für absent, present
und conflict mit unveränderten physischen Snapshots.

Beide Tests verwenden die bestehende wegwerfbare PostgreSQL-Fixture ohne
SQLite-Fallback.

## Blocker 1 — PostgreSQL-Evidence fehlt

In der aktuellen Arbeitsumgebung wurden LQ-520 und LQ-521 nicht gegen eine
reale PostgreSQL-Instanz ausgeführt.

SQLAlchemy, Alembic, pytest und ein konfigurierter
`LIQUENT_TEST_DATABASE_URL`-Pfad standen nicht zur Verfügung.

Es existiert keine neue commitgebundene `verification.json`, die diese Fälle
als bestanden ausweist.

Testquelltext allein schließt SQL-, Constraint-, Lock- oder Treiberfehler nicht
aus.

## Blocker 2 — Supervisor-Production-Wiring bleibt offen

Der LQ-483-Blocker ist durch die Cleanupimplementierung nicht automatisch
aufgehoben.

Appfactory, Lifespan und Deployment bauen weiterhin keinen vollständigen
Supervisorgraphen aus Engineclient, Capabilitygrenzen und privatem
Control-Directory-Lifecycle auf.

Ohne diesen Graphen entstehen im regulären Betrieb keine belegten Active-
Directories, die nach Terminalität kontrolliert retired werden können.

## Blocker 3 — Retirement ist operativ nicht erreichbar

LQ-490 implementiert kontrolliertes terminales Retirement als
Anwendungsgrenze.

Kein vorhandener Operator, HTTP-Transport oder Productionservice ruft diese
Grenze auf.

Der Cleanup-Operator darf Active nicht selbst retiren und kann diesen fehlenden
Schritt nicht ersetzen.

## Blocker 4 — Retention-Eligibility hat keinen Operator

Der persistente Decisionadapter kann eligible oder retain speichern.

Im aktuellen Operatorinventar gibt es keinen kontrollierten Prozess, der eine
autoritative Retentionpolicy auswertet und die gebundene Cleanupdecision
erzeugt.

Manuelles SQL wie in Integrationfixtures ist keine Productionauthority.

## Blocker 5 — Vier Authority-Sets sind nicht operationalisiert

LQ-505 implementiert Bootstrap, Lifecycle, Recovery und Lookups für
Management-, Hold-, Recovery- und Reference-Mutationsauthority.

Keine dieser sechzehn Methoden besitzt einen owner-kontrollierten Operator,
Entry Point oder Production-Wiring.

Positive Authority-Sets können deshalb nicht über eine freigegebene
Betriebsgrenze initialisiert, geändert oder recovered werden.

## Blocker 6 — Quellrevisionen sind nicht operationalisiert

LQ-507 implementiert vier autorisierte append-only Revisionsmutationen.

Es gibt keinen Operator für Management active/inactive sowie Hold-, Recovery-
und Reference-clear/blocked.

Damit kann der reguläre Betrieb die von LQ-508 verlangten aktuellen positiven
Fakten nicht kontrolliert herstellen oder widerrufen.

## Blocker 7 — Technische Konfiguration ist nicht übergeben

Der Cleanup-Operator verlangt private Dateien für Datenbank-URL,
Backendinstanz-ID und absoluten `0700`-Control-Root.

Compose, `runtime.env.example`, Secretprovisioning und Runbooks definieren
derzeit weder Besitzer noch Mount, Pfad, Rotation oder Übergabe dieser Dateien.

Eine improvisierte lokale Dateiablage wäre kein geprüfter Productionvertrag.

## Blocker 8 — Incident-Handoff ist nicht durable

Bei `reconciliation_required` gibt LQ-519 Attempt- und Directory-ID nur auf
stdout aus.

Es gibt keinen atomaren privaten Resultathandoff, kein Runbook und keinen
kontrollierten read-only Pending-Lookup für den Fall verlorener Prozessausgabe.

Da Directorydiscovery bewusst geschlossen bleibt, kann ein verlorener
Identifier nicht sicher durch eine freie Suche ersetzt werden.

## Blocker 9 — Releaseinventar ist inkonsistent

Der Workspace enthält jetzt 59 `liquent-*`-Entry-Points und 66 Python-Dateien
im Operatorpaket.

`tools/operational_release_bundle.py` verlangt weiterhin exakt 58 Entry Points
und 65 Operatorfiles.

Das fail-closed Bundlegate würde den aktuellen Wheelbestand deshalb ablehnen.

Der neue Cleanup-Operator ist außerdem noch nicht Teil eines synchronisierten
Cleanup-Runbook-/Contractinventars des Operationsbundles.

## Kein Blocker — fehlende Automatik

Automatische Planung, Directorylisting und Batchcleanup fehlen absichtlich.

Für den owner-kontrollierten Einzelbetrieb sind sie keine
Readinessvoraussetzung und dürfen nicht als schnelle Blockerbehebung ergänzt
werden.

Jeder Versuch soll weiterhin eine aktuelle explizite Entscheidung benötigen.

## Kein Blocker — fehlende HTTP-Route

Eine Browser- oder öffentliche HTTP-Route ist für den Offline-Operator nicht
erforderlich.

Eine solche Route würde zusätzliche Session-, CSRF-, Disclosure- und
Authoritygrenzen eröffnen und ist nicht Teil der sicheren Restarbeiten.

## Kein Blocker — unveränderte Registryretention

Physisch entfernte Directories behalten ihre Registry-, Lifecycle-, Claim- und
Outcomehistorie.

Das ist eine erforderliche Nichtwiederverwendungs- und Audituntergrenze, kein
fehlender Garbage-Collection-Schritt.

## Sichere Restreihenfolge

Zuerst muss das Releaseinventar an den tatsächlich paketierten separaten
Operator angepasst und fail-closed erneut geprüft werden.

Danach benötigen Authority-Set-, Quellrevision-, Retentiondecision- und
Retirementgrenzen kontrollierte owner-only Operatorverträge und
Implementierungen.

Anschließend folgen private Deployment-/Runbookübergabe und durable
Reconciliation-Evidence.

Erst ein verpflichtender PostgreSQL-Gesamtlauf mit neuer commitgebundener
Verification-Evidence kann Production-Readiness erneut auditieren.

## Aktuelle Freigabeentscheidung

Die Cleanup-Kette ist als isolierte, explizit aufrufbare Sicherheitsfunktion
weit fortgeschritten.

Sie ist nicht für Productionbetrieb, Releasepublication oder automatische
Aktivierung freigegeben.

Kein Dokument darf LQ-520-/LQ-521-Testquellen als bereits ausgeführte
PostgreSQL-Evidence darstellen.

## Keine Implementation

LQ-522 verändert keine Production-, Operator-, Packaging-, Deployment- oder
Runbookdatei.

Es ergänzt keine Migration, Tabelle, SQL-, Domain- oder Portsignatur.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Statische Auditprüfungen belegen vorhandene Sicherheitsstufen, fehlende
operative Aufrufer, fehlende Runbooks, nicht ausgeführte PostgreSQL-Evidence
und die konkrete Releaseinventardrift 58/65 gegenüber 59/66.

## Nächster Slice

LQ-523 sollte zuerst das fail-closed Operational-Release-Bundle-Inventar für
den separaten Cleanup-Operator synchronisieren und durch fokussierte
Packagingtests absichern.

Authority-, Retention-, Retirement- und Deployment-Wiring bleiben danach
explizite weitere Slices.
