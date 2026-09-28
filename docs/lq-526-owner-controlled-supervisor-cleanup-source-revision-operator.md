# LQ-526 — Owner-controlled Supervisor Cleanup Source Revision Operator

## Ergebnis

LQ-526 implementiert die vierte in LQ-524 definierte Prozessgrenze für
Management-, Hold-, Recovery- und Reference-Quellrevisionen.

Der Operator erzeugt ausschließlich eine einzelne autorisierte append-only
Quellrevision und keine Cleanup-Clearance oder physische Wirkung.

## Separater Entry Point

Der Slice ergänzt genau den Console Entry Point
`liquent-supervisor-cleanup-source-revision`.

Er ist von den drei LQ-525-Authority-Set-Prozessen getrennt.

Der Prozess ist kurzlebig, ausdrücklich gestartet und verarbeitet genau einen
Request.

## Feste Unterbefehle

Die CLI besitzt ausschließlich `management`, `hold`, `recovery` und
`reference`.

Die Auswahl erfolgt durch den Parser und nicht durch ein Requestfeld.

Es gibt kein frei wählbares `source`, `kind`, `allow`, Rollen-, Tabellen- oder
Methodenfeld.

## Managementrequest

Management verlangt exakt Actor-User-ID, Change-ID, Ziel-User-ID, Scope-ID,
erwartete Revision und Status.

Der Status ist ausschließlich `active` oder `inactive`.

Die erwartete Revision ist für die erste Revision ausdrücklich JSON-`null` und
danach eine nichtleere typisierte Managementrevision.

Ein leerer String ist kein Ersatz für `null`.

## Directorygebundene Requests

Hold, Recovery und Reference verlangen exakt Actor-User-ID, ihre typisierte
Change-ID, Directory-ID, erwartete quellenspezifische Revision und
Disposition.

Die Disposition ist ausschließlich `clear` oder `blocked`.

Auch hier bedeutet nur JSON-`null`, dass noch keine Revision erwartet wird.

Der Request enthält keine Scope-ID; LQ-507 löst den Scope aus dem persistent
gebundenen terminalen Directory und dessen Journaljob auf.

## Principal und Authority

Der Operator konstruiert einen `SessionPrincipal` ausschließlich aus der
Actor-User-ID.

Der Principal enthält keine Authority, Rolle, Membership oder Permission.

LQ-507 liest die aktuelle passende LQ-525-Authority-Menge, aktive
User-/Scope-Foundations und die Zielbindung innerhalb der Schreibtransaktion
neu.

Ein committierter Authority-Widerruf beeinflusst jede spätere Mutation.

## Feste Adapteraufrufe

Management ruft ausschließlich
`change_control_directory_cleanup_management` auf.

Hold und Recovery rufen ausschließlich ihre gleichnamigen festen Methoden auf.

Reference ruft ausschließlich
`change_control_directory_cleanup_references` auf.

Es gibt keinen dynamischen Methodennamen und keinen generischen Sourceport.

## Optimistische Revision

Der persistente Adapter vergleicht die erwartete Revision mit der aktuell
letzten Revision genau der adressierten Quelle und des adressierten Ziels.

Stale, fremde oder fehlende Erwartungen werden nicht auf den aktuellen Stand
umgebogen.

Die Change-ID bindet Actor, Ziel, Erwartung und neuen Wert idempotent.

Eine abweichende Wiederverwendung derselben Change-ID wird detailfrei
abgelehnt.

## Terminale Directorybindung

Hold-, Recovery- und Referenceänderungen akzeptieren nur ein persistentes
retired Directory mit terminal beobachtetem Journalzustand.

Der Operator kann ein Directory weder suchen noch aktivieren, retiren oder
reparieren.

Die Ergebnisprüfung bindet die zurückgegebene Entscheidung erneut an Change-
und Directory-ID.

## Management-Ergebnisbindung

Ein Managementerfolg wird erneut an Change-ID, Ziel-User-ID und Scope-ID
gebunden.

Die private Ergebnisdatei enthält Operation-ID, Ziel-User-ID, Scope-ID und
neue Revision-ID.

## Directory-Ergebnisbindung

Ein Hold-, Recovery- oder Referenceerfolg wird erneut an Change-ID und
Directory-ID gebunden.

Die private Ergebnisdatei enthält Operation-ID, Directory-ID und neue
Revision-ID.

Der intern aufgelöste Scope wird nicht durch einen caller-gelieferten Wert
ersetzt.

## Private Dateien

Der Prozess verlangt `--database-url-file`, `--request` und `--result-file`.

URL und Request verwenden die bestehende descriptorgebundene no-follow,
owner-only, single-link, `0400`-/`0600`- und größenbegrenzte Grenze.

Es gibt keinen Environmentfallback, keine Secretargumente und keine
interaktive Eingabe.

Das Ergebnis wird atomar in eine neue private `0600`-Datei geschrieben und
überschreibt keine vorhandene Datei.

## Striktes JSON

Doppelte, fehlende und zusätzliche Felder werden abgelehnt.

Außer `expected_revision_id: null` müssen alle Werte nichtleere, unveränderte
Strings sein.

Unbekannte Status-, Dispositions- und ID-Werte erreichen den Adapter nicht.

## Readiness und Engine

Der Operator baut genau eine Engine aus der privaten URL und prüft den
aktuellen Readiness-/Migrationsstand vor jeder Mutation.

Die Engine wird auf allen Pfaden disposed.

Es gibt keine Migration, Schemaerzeugung oder toleranten Fallback.

## Geschlossene Outcomes

Erfolg schreibt das gebundene private Ergebnis und gibt `applied` aus.

Neutrale Abwesenheit sowie der bestehende detailfreie Mutation-Conflict geben
`rejected` mit Exitcode 5 aus.

Malformed Input endet detailfrei mit Exitcode 2.

Technische Datei-, Readiness-, Persistenz- oder Ergebnisfehler enden als
`supervisor_cleanup_source_revision_operator_unavailable` mit Exitcode 4.

Keine SQL-, Authority-, User-, Scope-, Directory-, Pfad- oder Exceptiondetails
verlassen die Grenze.

## Keine Authority-Set-Mutation

Der Operator ruft keine Bootstrap-, Lifecycle- oder Recoverymethode aus
LQ-525 auf.

Er kann Authority-Mitglieder weder hinzufügen noch deaktivieren oder
reaktivieren.

## Keine Folgeaktion

Eine erfolgreiche Quellrevision erzeugt keine Clearance, Retentiondecision,
Retiremententscheidung und keinen Cleanup-Attempt.

Sie startet weder LQ-519 noch einen anderen Operator.

## Keine Discovery oder Automatik

Es gibt keine User-, Scope-, Directory-, Revisions- oder Authoritysuche und
kein Listing.

Batch, Schleifen, Queue, Worker, Scheduler, Daemon, HTTP, Appfactory und
Production-Autostart bleiben geschlossen.

## Packaging

Der Bestand steigt auf 63 Console Entry Points und 68 gepackte Operatorfiles,
also 67 fachliche Implementierungs- und Hilfsmodule plus Initialisierer.

Bundlekonstanten, aktive Inventarguardrails und required Contracts werden auf
diesen exakten Bestand synchronisiert.

## Kein Schema

LQ-526 ergänzt keine Migration, Tabelle, Spalte, SQL-, Domain-, Port- oder
Adaptersignatur.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Statische Tests prüfen Entry Point, feste Requestformen, explizites JSON-null,
Principalgrenze, feste Adaptermethoden, Ergebnisbindung, Readiness, Disposal,
geschlossene Outcomes und ausgeschlossene Folgeaktionen.

Sie behaupten keine ausgeführte PostgreSQL-Evidence.

## Nächster Slice

LQ-527 definiert die owner-kontrollierte Retention-Eligibility-Operatorgrenze.

Retirement, Deployment, Incident-Handoff und verpflichtende PostgreSQL-
Evidence bleiben separat.
