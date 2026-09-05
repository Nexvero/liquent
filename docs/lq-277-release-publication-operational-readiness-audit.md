# LQ-277 — Release Publication Operational Readiness Audit

## Ergebnis

LQ-277 auditiert den vollständigen unterstützten Betriebsweg vom leeren
Release-Control-Plane-Bestand bis zum terminalen Publication-Receipt.

Die Signing-, Promotion- und Publication-Worker-Grenzen sind implementiert und
integriert geprüft. Der Gesamtweg ist dennoch noch nicht betriebsbereit.

Vier notwendige persistente Fähigkeiten existieren nur als interne Adapter,
nicht als kontrollierte owner-only Prozessgrenzen:

- initialer Release-Registry-Bootstrap;
- Release-Key-Proof und Aktivierung;
- initialer Publication-Control-Plane-Bootstrap;
- autorisierter persistenter Publication-Handoff.

LQ-277 erfindet dafür weder direkte Adapteraufrufe noch SQL-Runbooks.

## Auditfrage

Die maßgebliche Frage lautet nicht, ob jeder interne Adapter isoliert getestet
ist, sondern ob ein Operator aus einem leeren migrierten Bestand ausschließlich
über installierte, dokumentierte und detailarme Prozessgrenzen bis zu einem
Publication-Receipt gelangen kann.

Diese Kette muss ohne Test-Fixtures, Python-REPL, Tabellenzugriff oder
caller-gelieferte Allow-Fakten ausführbar sein.

## Erwartete Gesamtfolge

Der sichere vollständige Weg lautet:

```text
migrierter leerer Store
  -> Release Registry bootstrap
  -> Key proof + activation
  -> signing decision + detached SSHSIG
  -> current promotion verification
  -> Publication Control Plane bootstrap
  -> authorized ready_for_publication handoff
  -> supervised publication worker
  -> immutable provider reconciliation
  -> persistent receipt
```

Jede Stufe muss ihren eigenen aktuellen Authority- und Persistenzvertrag
einhalten. Keine positive Evidence darf eine spätere aktuelle Prüfung ersetzen.

## Vorhandene installierte Release-Prozesse

Das Wheel stellt derzeit genau drei releasespezifische Console Entry Points
bereit:

- `liquent-release-signing`;
- `liquent-release-promotion`;
- `liquent-release-publication`.

Sie decken die hintere Artifact- und Providerkette ab. Alle drei sind
explizite kurzlebige Offline-Prozesse ohne HTTP- oder Startup-Wiring.

## Nachgewiesene hintere Kette

LQ-246 signiert ausschließlich einen bereits autorisierten Kandidaten und
materialisiert detached SSHSIG sowie persistenzgebundene Evidence.

LQ-247 prüft Bundle, Signatur und aktuelle Registry read-only und erzeugt
kanonische Promotion-Evidence.

LQ-275/276 führt genau eine vorbereitete Publication-Arbeitseinheit durch,
bestätigt externe Sichtbarkeit und schließt atomar mit Receipt ab.

Diese Prozesse funktionieren, sobald ihre notwendigen System-of-Record-Fakten
bereits kontrolliert existieren.

## Blocker 1 — Release-Registry-Bootstrap

`DatabaseInitialReleaseAuthorityRegistryBootstrap` implementiert den atomaren
initialen Registry-Bestand und ist auf SQLite sowie PostgreSQL geprüft.

Es existiert jedoch kein installiertes owner-only Kommando, das den stabilen
Bootstrap-Request, öffentlichen Schlüssel und private Datenbankquelle sicher
an diesen Adapter bindet.

Ohne Registry-Bootstrap existiert keine aktuelle Signer-, Key- oder
Policy-Authority für Signing und Promotion.

## Blocker 2 — Key-Proof und Aktivierung

`DatabaseReleaseSigningKeyActivation` implementiert aktuelle Proof-Bindung und
Key-Aktivierung gegen die persistente Registry.

Es fehlt eine Prozessgrenze für den kontrollierten Proof-Request, die getrennte
technische Identität, aktuelle Revision und detailarme Ausgabe.

Ein privater Keypfad am Signing-Operator aktiviert keinen Key und darf diese
Authority-Mutation nicht implizit auslösen.

## Blocker 3 — Publication-Control-Plane-Bootstrap

`DatabaseInitialReleasePublicationControlPlaneBootstrap` kann einmalig Channel,
Publisher-Authority, vollständige Revision und Current-Pointer erzeugen.

Es existiert kein Entry Point oder Runbook, das diesen Bootstrap sicher aus
einem leeren Publication-Bestand ausführt und die vier erzeugten stabilen IDs
geschützt an den Folgeprozess übergibt.

Signing- oder Promotion-Evidence erzeugt keinen Publication-Channel.

## Blocker 4 — Autorisierter Handoff

`DatabaseAuthorizedReleasePublicationHandoff` prüft Promotion-Evidence,
aktuelle Registry, Publisher und Channel und persistiert atomar
`ready_for_publication`.

Es fehlt ein owner-only Operator, der stabile Handoff- und Decision-ID,
Publisher, Channel, erwartete Revision und die drei Artifact-Pfade geschlossen
entgegennimmt.

Ohne diesen Prozess kann der LQ-275-Worker keinen unterstützten persistenten
Handoff auflösen.

## Execution ist kein zusätzlicher Blocker

Der Publication-Worker benötigt zwar eine stabile Execution-ID im geschlossenen
Request, aber nicht zwingend einen separaten Execution-Preflight-Command.

LQ-271/273 ruft den LQ-254-Preflight innerhalb der einzelnen Arbeitseinheit auf
und kann Execution und Attempt 1 atomar vorbereiten, bevor Providerzugriff
erfolgt.

Eine spätere Handoff-Prozessgrenze muss deshalb die für den Worker nötigen
Referenzen kontrolliert ausgeben oder in einem getrennt entschiedenen
owner-only Übergabefakt materialisieren. Sie darf keinen Attempt vorwegnehmen.

## Warum Tests die Lücke nicht schließen

Die End-to-End-Tests erzeugen Registry, Channel, Handoff und vorbereitete
Execution über direkt komponierte Adapter und deterministische Fixtures.

Das ist ein valider Persistenz-, Konkurrenzsicherheits- und Worker-Nachweis.
Es ist kein unterstützter Betriebsweg für ein Prozesskonto.

Testwissen über IDs, Revisionen und Tabellen darf nicht in ein Runbook
übernommen werden.

## Kein direkter SQL-Ersatz

Direkte Inserts oder Updates hätten keine geschlossene Inputform, sichere
ID-Erzeugung, aktuelle Authority-Auflösung, Konfliktsemantik, Retry-Bindung,
detailarme Ausgabe oder kontrollierte Ressourcenverantwortung.

Sie würden genau die atomaren Adapterverträge umgehen, die Slices LQ-240 bis
LQ-254 eingeführt haben.

LQ-277 dokumentiert deshalb keinen SQL-, Alembic-, Admin-Console- oder
Python-REPL-Shortcut.

## Kein Zusammenlegen der Authorities

Die vier fehlenden Grenzen dürfen nicht zu einem offenen "initialize release"
mit impliziten Allow-Entscheidungen verschmolzen werden.

Registry-Bootstrap, Key-Aktivierung, Publication-Bootstrap und Handoff besitzen
unterschiedliche Actors, stabile IDs, Retryregeln und Security-Evidence.

Signing-Executor, Promotion-Verifier, Publisher-Authority und Publication-
Executor bleiben getrennte Identitäten.

## Runtime-Isolation

HTTP-App und Runtime-Entrypoint importieren keinen Release-Bootstrap,
Key-Aktivierungs-, Handoff- oder Publication-Operator.

Diese Isolation ist korrekt und darf durch die Folgeslices nicht gelockert
werden. Fehlende Offline-Prozesse sind kein Grund für App-Startup-Mutationen.

## Externe Providerbereitschaft

LQ-276 prüft den realen Adapter und Transport gegen einen kontrollierten
In-Process-Provider, nicht gegen ein produktives Paketrepository.

Origin, TLS, Credential-Scope, create-only Semantik, Paketnamensbesitz,
Rate-Limits und Incidentweg müssen environmentbezogen separat abgenommen
werden. Diese externe Abnahme kann erst nach Schließung der internen
Prozesskette sinnvoll durchgeführt werden.

## Git- und Artefakt-Handoff

Der kumulierte Worktree bleibt uncommitted und detached. Es wurde kein Branch,
Staging, Commit, Push, Pull Request, Package-Upload oder Deployment ausgeführt.

Auch bei geschlossener Release-Control-Plane wären Code-Review, CI,
versioniertes Bundle, Signatur und bewusste Promotion weiterhin getrennte
Releaseentscheidungen.

## Statischer Auditnachweis

Der neue Test bestätigt:

- die drei vorhandenen installierten Release-Prozesse;
- das Fehlen genau der vier notwendigen Entry Points;
- die Existenz der zugehörigen persistenten Adapter;
- das Fehlen gleichnamiger Operatormodule;
- die korrekte Vorbedingung im LQ-276-Runbook;
- das Fehlen direkter SQL-Abkürzungen;
- die Isolation aller Release-Control-Plane-Adapter vom HTTP-Startup.

## Unveränderter technischer Bestand

LQ-277 ändert keinen Produktionscode, Port, Typ, Schema, SQL oder Migration.

Der Head bleibt `20260819_0024` mit 24 linearen Migrationen. Das operative
Bundle bleibt bei 15 Console Entry Points.

Es erfolgt kein echter Provider-, Datei-, Git- oder Deploymentwrite.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit:

```text
3352 passed, 588 warnings
```

## Readiness-Entscheidung

Die Publication-Worker-Grenze ist manuell geprüft, aber die vollständige
Release-Publication-Kette ist operativ blockiert.

Eine Production- oder Package-Repository-Freigabe wird nicht behauptet.

Der kleinste sichere Fortschritt ist, die vier fehlenden Prozessgrenzen in
ihrer Authority-Reihenfolge zu schließen und jeweils mit owner-only Input,
exaktem Retry, minimaler Ausgabe und PostgreSQL-Nachweis zu versehen.

## Folgeordnung

LQ-278 sollte zuerst den Vertrag für einen owner-only Release-Registry-
Bootstrap- und Key-Aktivierungsprozess entscheiden.

Danach sollten getrennte Slices dessen Implementierung, den Publication-
Control-Plane-Bootstrap und den autorisierten Handoff-Operator ergänzen.

Erst ein erneuter Gesamt-Audit darf anschließend Betriebsbereitschaft
behaupten oder eine kontrollierte externe Providerabnahme planen.
