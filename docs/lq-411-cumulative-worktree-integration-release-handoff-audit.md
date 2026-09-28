# LQ-411 — Cumulative Worktree Integration and Release Handoff Audit

## Zweck

LQ-411 auditiert den gesamten kumulierten uncommitted Arbeitsbaum und legt
einen reviewbaren Integrations- und Release-Handoff fest.

Der Slice fügt keine Produktfunktion hinzu und führt weder Branch-, Staging-,
Commit-, Push-, Pull-Request-, CI- noch Deploymentaktion aus.

## Ausgangsbasis

Der Worktree steht weiterhin detached auf Commit `83699b1`.

Es ist kein lokaler Branch ausgecheckt.

Der kumulierte Scope umfasst zum Auditzeitpunkt:

- 24 veränderte getrackte Dateien;
- 551 neue ungetrackte Dateien;
- insgesamt 575 uncommitted Pfade;
- null bewusst gestagte Dateien;
- keinen Commit, Push oder Deployment dieses Scopes.

Ignorierte Caches und lokale Testartefakte gehören nicht zu dieser Inventur.

## Top-Level-Verteilung

Die 575 uncommitted Pfade verteilen sich auf:

- 229 unter `docs`;
- 18 unter `operations`;
- 103 unter `src`;
- 222 unter `tests`;
- zwei unter `tools`;
- `pyproject.toml`.

Die Verteilung zeigt einen zusammenhängenden Plattform-, Persistenz-, Release-
und Betriebsumbau, keinen einzelnen kleinen Featurepatch.

## Getrackter gemeinsamer Kern

Die 24 veränderten getrackten Dateien enthalten zentrale gemeinsame Grenzen:

- `docs/technical-status-and-roadmap.md`;
- `pyproject.toml`;
- Compose- und Runtime-Konfiguration;
- Identity-Ports und Identity-Fehlergrenzen;
- OIDC- und Session-Application-Composition;
- HTTP-App und Entrypoint-Wiring;
- bestehende Migration- und Identitytests.

Diese Dateien tragen Änderungen vieler zeitlich späterer Slices gleichzeitig.

Eine Zuordnung nach „letztem Slice“ wäre fachlich falsch.

## Additiver Bestand

Die neuen Dateien umfassen unter anderem:

- persistente Identity-, Membership-, Lifecycle- und OIDC-Trust-Adapter;
- Migrationen 0003 bis 0027;
- Release-Registry-, Signing-, Publication- und Recoverygrenzen;
- persistente Research-Jobs und Workercomposition;
- Staging-, Runtime-Inspection- und Recoveryoperatoren;
- disposable PostgreSQL Runtime-Cleanup und Generation-Lineage;
- Volume-Disposition, Evidence-first Löschung und terminalen Handoff;
- Operations-Runbooks, Releasewerkzeuge, Verträge, Audits und Tests.

Die Dateien bauen auf denselben Ports, Exceptions, Migrationen, Entry Points
und Dokumentationsgates auf.

## Verifizierter Teststand

Die vollständige normale Suite besteht mit:

- 3945 bestandenen Tests;
- 99 Skips;
- 615 bestehenden Warnungen.

Der Volume-Track besitzt zusätzlich 120 fokussierte Tests einschließlich
Runbookaudit.

Dieser Stand belegt den aktuellen ungeteilten Endzustand.

Er belegt nicht automatisch künstlich erzeugte historische Zwischencommits.

## Bundle- und Migrationsstand

Der aktuelle Endzustand besitzt:

- 58 Console Entry Points;
- 62 Operatormodule;
- 27 lineare Migrationen;
- Migration-Head `20260819_0027`.

Die Migrationen bilden eine abhängige lineare Folge von Identity-Grundlagen
über Release-Persistenz bis zu Research-Job-Outcomes.

Ein Commit-Split darf keinen Code gegen fehlende Vorgängermigrationen oder
Migrationen ohne ihre finalen Adapter erzeugen.

## Roadmap-Drift

Der Kopf von `docs/technical-status-and-roadmap.md` nennt noch einen älteren
Zwischenstand mit 2887 Tests, 74 PostgreSQL-Integrationen und Dokumentation bis
LQ-235.

Die fortlaufenden additiven Einträge reichen inzwischen bis LQ-410 und nennen
3945 Tests sowie den aktuellen Bundlebestand.

Damit ist die Roadmap intern historisch vollständig, aber ihr konsolidierter
Kopf ist veraltet.

Vor Release muss der Kopf auf den aktuellen Endzustand gebracht werden, ohne
historische Sliceeinträge zu löschen oder umzuschreiben.

## Warum chronologische Slice-Commits nicht mechanisch sicher sind

Die Slices wurden iterativ im selben Worktree aufgebaut.

Zentrale Dateien enthalten heute die endgültige Kombination zahlreicher
früher und später Slices.

Ein chronologischer Split per Verzeichnis oder interaktivem Hunk-Staging könnte:

- Ports ohne ihre Implementierungen veröffentlichen;
- Exceptions ohne alle Verbraucher abtrennen;
- Entry Points ohne Operatormodule erzeugen;
- Wiring vor Persistenz oder Migrationen einführen;
- Migrationen ohne finale Modell- und Adapterannahmen veröffentlichen;
- Runbooks von installierten Commands trennen;
- Tests und Roadmap vom tatsächlich ausführbaren Code entkoppeln.

Ein solcher Split wäre nur nach Rekonstruktion historischer Dateiversionen und
vollständigem Test jedes Zwischenstands vertretbar.

## Warum ein reiner Verzeichnissplit nicht genügt

`src`, `tests`, `operations` und `docs` sind keine unabhängigen Releasepakete.

Produktcode benötigt die linearen Migrationen und Entry-Point-Metadaten.

Runbooks referenzieren installierte Commands und deren exakte Ausgänge.

Tests sind Teil der Sicherheitsnachweise für Claims, Evidence, Unknown Outcome
und fail-closed Authority.

Dokumente definieren bindende Grenzen, die nicht erst nachträglich getrennt
vom zugehörigen Code integriert werden sollten.

Ein Verzeichnissplit würde Reviewoptik verbessern, aber keine ausführbaren
Zwischenstände garantieren.

## Empfohlene Integrationsform

Der sichere Standardweg ist ein einzelner atomarer Commit des vollständig
grünen Endzustands.

Die Reviewbarkeit wird über klar getrennte PR-Abschnitte, Dateiinventare,
Migrationsgruppen, Gateberichte und Runbooks hergestellt, nicht über
scheinbar chronologische Teilcommits.

Ein atomarer Commit erlaubt einen eindeutigen Gesamtrollback auf `83699b1`.

Selektives Zurückrollen einzelner späterer Capability-Gruppen ist ohne erneute
Abhängigkeitsanalyse und vollständigen Test nicht freigegeben.

## Empfohlener Branch

Nach ausdrücklicher Benutzerfreigabe sollte ein Branch direkt vom aktuellen
detached HEAD erzeugt werden.

Empfohlener Name:

```text
codex/lq-411-platform-integration-handoff
```

Branch-Erzeugung muss eine separate, überprüfbare Aktion bleiben und darf
nicht still mit Staging oder Commit gekoppelt werden.

LQ-411 erzeugt diesen Branch nicht.

## Empfohlener Commit

Empfohlener Commit-Titel:

```text
feat: complete supervised research platform control plane
```

Der Commitbody sollte mindestens nennen:

- persistente Identity-, OIDC-, Membership- und Lifecycle-Control-Plane;
- Release-Registry, Signing, Publication, Recovery und Provider-Handoff;
- persistente Research-Jobs und Worker-/Staging-Composition;
- disposable PostgreSQL Runtime-Cleanup und Evidence-Lineage;
- owner-kontrollierte Volume-Disposition und -Deletion;
- Operations-Runbooks und fail-closed Betriebsgrenzen;
- verifizierten Test-, Entry-Point- und Migrationsstand.

Der Commit darf erst nach den nachfolgenden Gates entstehen.

## PR-Reviewabschnitt A — Identity und Access

Reviewer prüfen zuerst:

- stabile User-/Workspace-/External-Identity-Fakten;
- Admission, Bootstrap und Onboarding;
- OIDC-Logintransaktionen, Browser-Sessions und Trustverwaltung;
- Membership, Research-Capabilities und Revocation;
- Authority-, User- und Workspace-Lifecycle einschließlich Recovery;
- Migrationen 0003 bis 0016.

Zentrale Dokumente reichen von LQ-183 bis LQ-232.

## PR-Reviewabschnitt B — Release-Control-Plane

Danach folgen:

- Release-Authority-Registry und Bootstrap;
- Key-Aktivierung und Signing;
- Publication-Target, Work, Attempt, Handoff und Package Index;
- Reconciliation, Retry, Recovery und Executorregistrierung;
- Migrationen 0017 bis 0025;
- Releasebundle- und Promotionwerkzeuge;
- zugehörige Runbooks und Providergrenzen.

Dieser Abschnitt umfasst im Wesentlichen LQ-234 bis LQ-288.

## PR-Reviewabschnitt C — Research Jobs und Worker

Dieser Abschnitt umfasst:

- persistente Research-Jobtypen, Ports und Migrationen 0026 bis 0027;
- Jobcomposition, Claim/Lease und Finalisierung;
- lokalen Artifact Store;
- Workerloop, Configuration und Entrypoint;
- Compose-Wiring und PostgreSQL-End-to-End-Nachweise.

Zentrale Slices sind LQ-289 bis LQ-304.

## PR-Reviewabschnitt D — Staging und Recovery

Reviewer prüfen:

- kontrollierten Staging-Executor und Prozessadapter;
- read-only Probe- und Runtime-Inspection-Grenzen;
- Dockercomposition und Artifact-Capability-Auflösung;
- Recovery-Inspect, begrenzte Mutation und Reconciliation;
- Rollback-Evidence und Staging-Handoff.

Dieser Abschnitt umfasst LQ-305 bis LQ-328.

## PR-Reviewabschnitt E — Runtime Cleanup

Danach folgen:

- disposable PostgreSQL Composition und Reconciliation;
- Runtime-Disposition, Preflight, Cleanup und Finalisierung;
- Continuation-, Recontinuation- und Chained-Pfade;
- begrenzte Generation-Lineage bis zur positiven Obergrenze;
- terminaler Handoff und Runtime-Cleanup-Runbook.

Zentrale Slices sind LQ-329 bis LQ-387.

## PR-Reviewabschnitt F — Volume Disposition und Deletion

Der letzte fachliche Abschnitt umfasst:

- read-only Volume-Disposition;
- Deletion-Preflight und Evidence-first initiale Löschung;
- ursprünglichen Unknown-Outcome-Inspector und Finalizer;
- einzige Continuation samt Inspector und Finalizer;
- terminalen LQ-398-Handoff;
- End-to-End-, Readiness- und Runbooknachweise.

Dieser Abschnitt umfasst LQ-388 bis LQ-410.

## PR-Reviewabschnitt G — Gesamtgates und Betriebsartefakte

Zum Abschluss prüfen Reviewer:

- konsolidierten Roadmap-Kopf;
- alle 27 Migrationen als lineare Kette;
- alle 58 Entry Points und 62 Operatormodule;
- Operations-Compose und Runtimekonfiguration;
- Release- und Cleanup-Runbooks;
- Packaginginhalt für erforderliche Betriebsartefakte;
- vollständige Test- und PostgreSQL-Gateberichte;
- Secret-, Konfliktmarker- und Differenzsauberkeit.

Dieser Abschnitt führt keine neue Funktion ein.

## Pflichtgates vor Staging

Vor jeder Stagingaktion müssen mindestens laufen:

1. vollständige normale Suite;
2. verpflichtende PostgreSQL-Integrationssuite mit freigegebenem Test-DSN;
3. Migration-Upgrade von leerer Datenbank bis Head;
4. Entry-Point-Import- und Paketmetadatenprüfung;
5. Wheel- und Source-Distribution-Build;
6. Prüfung, dass erforderliche Runbooks und Betriebsartefakte im vorgesehenen
   Releasebundle enthalten sind;
7. Konfliktmarkersuche;
8. Secret- und Credentialscan;
9. `git diff --check`;
10. erneute uncommitted Dateiinventur.

Ein fehlendes PostgreSQL-DSN oder nicht ausgeführtes Packaginggate darf nicht
als bestanden ausgegeben werden.

## Roadmap- und Gate-Konsolidierung vor Staging

Vor Staging muss ein separater rein dokumentarischer Schritt:

- den Roadmap-Kopf von 2887 auf den aktuellen verifizierten Teststand heben;
- den Dokumentationsstand bis LQ-411 nennen;
- 58 Entry Points, 62 Operatormodule und 27 Migrationen festhalten;
- den detached und uncommitted Status korrekt ausweisen;
- Volume-, Runtime- und Releasebereitschaft ohne Deploymentclaim trennen;
- historische additive Sliceeinträge unverändert erhalten.

Diese Aktualisierung darf keine Produktlogik verändern.

## Stagingplan nach ausdrücklicher Freigabe

Erst nach erfolgreicher Konsolidierung und allen verfügbaren Pflichtgates:

1. Branch vom exakten `83699b1` erzeugen;
2. aktuellen Status und Top-Level-Verteilung erneut sichern;
3. ausschließlich bekannte Ziele unter `docs`, `operations`, `src`, `tests`,
   `tools` und `pyproject.toml` stagen;
4. keine ignorierten Dateien mit Force aufnehmen;
5. staged Dateizahl gegen das neue Inventar prüfen;
6. `git diff --cached --check` ausführen;
7. staged Secret- und Konfliktmarkerscan wiederholen;
8. staged Diff nach den sieben Reviewabschnitten prüfen;
9. erst danach den atomaren Commit erzeugen.

LQ-411 führt keinen dieser Schritte aus.

## Rollbackgrenze

Vor Push ist die sichere Rollbackgrenze der unveränderte Commit `83699b1` plus
der separat erhaltene uncommitted Handoffbestand.

Nach atomarem Commit ist ein vollständiger Revert dieses einen Commits die
primäre technische Rollbackstrategie.

Ein selektiver Revert einzelner Migrationen, Ports, Operatoren oder
Runbookgruppen ist nicht automatisch sicher.

Produktive Datenbankdowngrades oder Löschung persistierter Fakten sind keine
durch diesen Plan autorisierte Rollbackmaßnahme.

## Remote- und Releasegrenze

Ein lokaler Commit ist noch kein Release.

Push und Pull Request benötigen separate ausdrückliche Benutzerfreigabe.

Remote-CI muss normale und PostgreSQL-Pflichtgates reproduzieren.

Deployment, Migration einer echten Umgebung, Authority-Bootstrap,
Release-Publication und jeder Cleanup- oder Volume-Lauf bleiben separat
freizugebende externe Aktionen.

## Aktuelle Blockerentscheidung

Es besteht kein identifizierter Bedarf für weitere Produktfunktion vor dem
Integrations-Handoff.

Aktuelle Blocker sind:

- veralteter konsolidierter Roadmap-Kopf;
- noch nicht erneut ausgeführte PostgreSQL-Pflichtsuite für den Endstand;
- noch nicht erneut ausgeführter finaler Packaging-/Bundle-Preflight;
- noch nicht ausgeführter finaler Secret- und Konfliktmarkerscan;
- detached HEAD und fehlender reviewbarer Branch;
- vollständig ungestagter und uncommitteter Gesamtbestand.

Diese Blocker verlangen Konsolidierung und Verifikation, keine neue
Plattformfähigkeit.

## Readiness-Entscheidung

Der aktuelle Endzustand ist funktional umfangreich und in der normalen Suite
grün, aber noch nicht als reviewbarer Git- oder Releaseartefakt übergeben.

Der sichere nächste Schritt ist eine rein dokumentarische Roadmap-/Gate-
Konsolidierung, danach die verfügbaren Pflichtgates und erst nach separater
Freigabe Branch, Staging und atomarer Commit.

Weitere Feature-Slices sind bis dahin nicht empfohlen.

## Nichtziele und Bundle

LQ-411 implementiert keinen Operator, Entry Point, Test, Migration, Runbook,
Produktcode oder Production-Wiring.

Es erzeugt keinen Branch, staged keine Datei, committed, pusht oder deployed
nichts und erstellt keinen Pull Request.

Bundle-Gates bleiben bei 58 Entry Points, 62 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-412 sollte den konsolidierten Kopf der technischen Status- und Roadmapdatei
auf den verifizierten Endstand aktualisieren und einen statischen
Konsistenznachweis ergänzen.

Der Slice darf historische additive Einträge nicht löschen und keine
Produktlogik, Migration, Entry Points, Branches oder Git-Historie verändern.
