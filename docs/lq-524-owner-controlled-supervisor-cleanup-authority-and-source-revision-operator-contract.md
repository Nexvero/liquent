# LQ-524 — Owner-controlled Supervisor Cleanup Authority and Source Revision Operator Contract

## Ergebnis

LQ-524 friert die operativen Grenzen ein, über die die vier
Cleanup-Mutationsauthority-Sets und die vier Clearance-Quellrevisionen später
kontrolliert verändert werden dürfen.

Der Slice implementiert noch keinen Operator und eröffnet keine
Productionwirkung.

## Zweck

LQ-508 verlangt aktuelle positive Management-, Hold-, Recovery- und
Referencequellen, bevor es eine Cleanup-Clearance erzeugt.

LQ-505 und LQ-507 besitzen die persistenten Mutationsgrenzen, aber noch keinen
owner-kontrollierten betrieblichen Aufrufer.

LQ-524 schließt die Vertragslücke, ohne Retention, Retirement oder Deployment
vorwegzunehmen.

## Vier getrennte Authority-Domänen

Cleanup-Management-, Cleanup-Hold-, Cleanup-Recovery- und
Cleanup-Reference-Mutationsauthority bleiben vier unabhängige Mengen.

Authority in einer Menge gewährt keine Authority in einer anderen Menge.

Eine gemeinsame Rolle, Membership, Session oder allgemeine
Supervisorberechtigung ersetzt keine der vier aktuellen Mengen.

## Vier getrennte Quellrevisionen

Managementstatus, Holdentscheidung, Recoveryentscheidung und
Referenceentscheidung bleiben getrennte append-only Revisionsquellen.

Ein positiver Wert einer Quelle kompensiert keinen fehlenden, inaktiven oder
blockierenden Wert einer anderen Quelle.

Der Operator führt keine zusammengefasste Cleanup-Freigabe ein.

## Feste Befehlsauswahl

Jede Domäne wird über einen festen Befehlszweig ausgewählt.

Ein Request enthält kein frei wählbares `source`, `authority_kind`,
Tabellenziel, Portziel oder Methodennamen.

Der Parser ordnet jeden festen Zweig genau einem bereits vorhandenen
domänenspezifischen Command und genau einer Adaptermethode zu.

Unbekannte Befehle und zusätzliche Felder werden vor Datenbankzugriff
abgelehnt.

## Getrennte Prozessgrenzen

Die spätere Implementation erhält vier ausdrücklich gestartete, kurzlebige
owner-kontrollierte Prozessgrenzen:

1. Authority-Bootstrap;
2. reguläre Authority-Lifecycle-Mutation;
3. Offline-Authority-Recovery;
4. reguläre Quellrevisionsmutation.

Keine Grenze ruft eine andere implizit auf.

Ein Prozess bearbeitet genau einen Request und beendet sich anschließend.

## Authority-Bootstrap

Bootstrap ist ausschließlich die initiale Bildung genau einer der vier Mengen
für genau einen Scope.

Er akzeptiert Bootstrap-ID, Ziel-User-ID und Scope-ID.

Er akzeptiert weder Actor noch erwartete Revision noch Lifecycle-Intent.

Der bestehende persistente Adapter muss Bootstrap ablehnen, sobald für diese
Domäne und diesen Scope bereits eine Menge existiert.

Bootstrap erzeugt keine User-, Scope-, Membership- oder Rollenfakten.

## Reguläre Authority-Mutation

Lifecycle-Mutation akzeptiert Actor-User-ID, Change-ID, Ziel-User-ID,
Scope-ID, erwartete domänenspezifische Revision und einen geschlossenen Intent.

Der Intent ist ausschließlich `grant`, `deactivate` oder `reactivate`.

Der Operator konstruiert aus der Actor-User-ID lediglich einen
`SessionPrincipal`; dieser Principal ist Identität und keine
Authorityentscheidung.

Der Adapter löst Actor, Scope, Foundations und aktuelle domänenspezifische
Authority innerhalb der Mutation aus dem System of Record neu auf.

## Offline-Authority-Recovery

Recovery ist eine separate Notfallgrenze ohne `SessionPrincipal`.

Sie akzeptiert Recovery-ID, historisch bereits gebundene Ziel-User-ID,
Scope-ID und erwartete domänenspezifische Revision.

Sie darf nur eine vorhandene inaktive historische Person derselben Menge
reaktivieren, wenn der bestehende geschlossene Recoveryvertrag dies erlaubt.

Sie darf keine neue Person hinzufügen, keine andere Domäne verändern und
keinen Lockout durch freie Ersetzung der Menge umgehen.

Der Prozessowner ist eine Deployment- und Runbookverantwortung, keine in den
Request codierte fachliche Rolle.

## Quellrevisionsmutation

Management akzeptiert Actor-User-ID, Change-ID, Ziel-User-ID, Scope-ID,
optionale erwartete Managementrevision und den geschlossenen Status `active`
oder `inactive`.

Hold, Recovery und References akzeptieren jeweils Actor-User-ID, Change-ID,
Directory-ID, optionale erwartete quellenspezifische Revision und die
geschlossene Disposition `clear` oder `blocked`.

Es gibt kein caller-geliefertes `allow`, `eligible`, `authorized` oder
zusammengefasstes Clearancefeld.

Die aktuelle passende Mutationsauthority wird bei jeder Mutation innerhalb
der Schreibtransaktion erneut aufgelöst.

## Actor- und Zielbindung

Actor, Ziel-User, Scope und Directory werden nicht aus Anzeigenamen, Rollen
oder externen Claims abgeleitet.

Die internen IDs adressieren ausschließlich bereits vorhandene stabile Fakten.

Der System-of-Record-Lookup muss aktive Foundations und die konkrete
Scope-/Directorybindung erneut prüfen.

Caller-Behauptungen über Aktivität, Zugehörigkeit oder Authority werden nicht
akzeptiert.

## Fail-closed Aktualität

Inaktive oder fehlende User-, Scope- oder Directorygrundlagen lehnen die
Mutation neutral und detailfrei ab.

Fehlende, inaktive, falsche oder zwischenzeitlich widerrufene Authority lehnt
reguläre Mutationen ebenfalls ab.

Ein committierter Widerruf muss jede spätere Entscheidung beeinflussen.

Es gibt keinen Authority-Cache und keinen aus einem früheren Request
übernommenen positiven Snapshot.

## Optimistische Bindung

Jede nichtinitiale Mutation ist an die erwartete aktuelle Revision ihrer
eigenen Domäne gebunden.

Eine veraltete, fremde oder fehlende erwartete Revision darf nicht still auf
den neuesten Stand umgebogen werden.

Initiale Quellrevisionen verwenden ausschließlich das bereits definierte
explizite `None` als erwarteten Zustand.

## Idempotenz

Bootstrap-, Lifecycle-, Recovery- und Change-IDs werden vom Requeststeller
explizit geliefert und sind typgebunden.

Eine exakte Wiederholung darf das bereits committierte Ergebnis zurückgeben.

Dieselbe ID mit abweichender Bindung oder anderem Intent wird detailfrei
abgelehnt.

Der Operator erzeugt keine zweite ID als stillen Retry.

## Private Eingaben

Jede Prozessgrenze verlangt eine private Datei für die Datenbank-URL und eine
private kanonische JSON-Requestdatei.

Es gibt keinen Environmentfallback, keine Kommandozeilenwerte für Secrets und
keine interaktive Eingabe.

Dateien werden descriptorgebunden ohne Symlinkfolge, nur owner-kontrolliert,
single-link, größenbegrenzt und als striktes UTF-8 gelesen.

Die konkrete Wiederverwendung bestehender sicherer Reader bleibt eine
Implementationsentscheidung des Folgeslices.

## Geschlossene Ergebnisse

Ein erfolgreiches oder exakt wiederholtes Ergebnis gibt nur Operation-ID,
Scope-ID und neue domänenspezifische Revision-ID aus.

Bei Quelländerungen darf zusätzlich die bereits im Command gebundene Ziel-ID
ausgegeben werden.

Neutrale Abwesenheit, fachliche Ablehnung, stale Revision, Kollision und
Lockout erscheinen gemeinsam als `rejected` ohne Detail.

Technische Nichtverfügbarkeit erscheint getrennt als `operator_unavailable`,
ebenfalls ohne Datenbank-, SQL-, Authority- oder Pfaddetail.

Der Vertrag benennt keine neue Exception.

## Keine Discovery

Der Operator listet keine User, Scopes, Directories, Authority-Mitglieder,
Revisionen oder offenen Mutationen.

Er bietet keinen Read-, Search-, Dump-, Diagnose- oder Repairbefehl.

Benötigte IDs und erwartete Revisionen stammen aus einem getrennt
kontrollierten betrieblichen Handoff.

## Keine implizite Folgeaktion

Eine erfolgreiche Authority- oder Quellmutation erzeugt keine Clearance,
Retentiondecision, Retiremententscheidung und keinen Cleanup-Attempt.

Sie startet weder LQ-519 noch einen anderen Operator.

Jede spätere Wirkung benötigt ihre eigene aktuelle Prüfung und ihren eigenen
ausdrücklichen Aufruf.

## Keine fachliche Erweiterung

LQ-524 ergänzt keine User-, Scope-, Workspace-, Membership-, Rollen- oder
Research-Permission-Erzeugung.

Es ergänzt keine allgemeine Admission- oder Onboardinggrenze.

Die vier Cleanup-Authorities bleiben von regulärer Membership und sonstigen
Capabilities getrennt.

## Keine Runtime- oder Schemwirkung

Dieser Slice ergänzt keinen Console Entry Point, Operatorcode, Appfactory-,
HTTP-, Worker-, Scheduler-, Queue-, Batch- oder Production-Wiringpfad.

Er ändert keine Tabelle, Migration, SQL-, Domain-, Port- oder Methodensignatur.

Der eindeutige Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Sicherheitsuntergrenzen

Stabile interne IDs werden niemals einer anderen fachlichen Identität
zugeordnet.

Authority-Set-, Change-, Bootstrap-, Recovery- und Quellrevisionshistorie
bleibt mindestens so lange erhalten, wie daraus Authority-, Clearance-, Claim-,
Outcome- oder Auditentscheidungen ableitbar sein müssen.

Entzogene IDs, Revisionen und historische Bindungen werden nicht als neue
Identitäten oder Operationen wiederverwendet.

Der Vertrag legt dafür weder Tabellenform noch konkrete Aufbewahrungsdauer
fest.

## Tests

Statische Vertragstests belegen die vier Domänen, vier Prozessgrenzen,
geschlossenen Inputs, aktuelle Authorityauflösung, detailfreien Outcomes und
die ausdrücklich ausgeschlossenen Wirkungen.

Sie behaupten keine ausgeführte PostgreSQL- oder Operator-Evidence.

## Nächster Slice

LQ-525 implementiert zuerst die drei owner-kontrollierten Authority-Set-
Operatorgrenzen für Bootstrap, Lifecycle und Offline-Recovery.

Die Quellrevisionsimplementation, Retention, Retirement, Deployment,
Incident-Handoff und verpflichtende PostgreSQL-Evidence bleiben getrennte
Folgeslices.
