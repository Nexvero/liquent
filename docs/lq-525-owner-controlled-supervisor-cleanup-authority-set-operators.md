# LQ-525 — Owner-controlled Supervisor Cleanup Authority-Set Operators

## Ergebnis

LQ-525 implementiert die drei in LQ-524 getrennten owner-kontrollierten
Prozessgrenzen für Bootstrap, regulären Lifecycle und Offline-Recovery der vier
Cleanup-Mutationsauthority-Sets.

Die vier Clearance-Quellrevisionsmutationen bleiben geschlossen.

## Separate Entry Points

Der Slice ergänzt genau drei Console Entry Points:

- `liquent-supervisor-cleanup-authority-bootstrap`;
- `liquent-supervisor-cleanup-authority-lifecycle`;
- `liquent-supervisor-cleanup-authority-recovery`.

Jeder Entry Point startet genau einen kurzlebigen Prozess und besitzt nur die
für seine Grenze zulässige Requestform.

## Gemeinsames internes Modul

Die drei Entry Points verwenden ein gemeinsames internes Operatormodul für
private Dateizugriffe, strikte Parser, Readinessprüfung und geschlossene
Ergebnisse.

Diese technische Wiederverwendung verschmilzt die drei Prozessgrenzen nicht.

Kein Entry Point kann implizit in einen anderen Modus wechseln.

## Vier feste Domänen

Jeder Entry Point besitzt ausschließlich die vier festen Unterbefehle
`management`, `hold`, `recovery` und `reference`.

Der Request enthält kein `source`, `kind`, `allow`, Rollenfeld, Tabellenziel
oder Methodennamen.

Jeder Unterbefehl wird explizit an den zugehörigen bestehenden Commandtyp und
die zugehörige Adaptermethode gebunden.

## Bootstrap

Der Bootstraprequest enthält exakt Bootstrap-ID, Ziel-User-ID und Scope-ID.

Er enthält keinen Actor, Intent und keine erwartete Revision.

Der persistente LQ-505-Adapter prüft erneut aktive User-/Scope-Foundations und
dass für diese Domäne in diesem Scope noch keine Authority-Menge existiert.

Eine exakte Bootstrap-ID-Wiederholung bleibt idempotent; abweichende Bindung
oder bereits vorhandene Menge wird detailfrei abgelehnt.

## Lifecycle

Der Lifecyclerequest enthält exakt Actor-User-ID, Change-ID, Ziel-User-ID,
Scope-ID, erwartete domänenspezifische Revision und Intent.

Der Intent wird durch den bestehenden Enum auf `grant`, `deactivate` oder
`reactivate` begrenzt.

Der Operator baut den `SessionPrincipal` ausschließlich aus der Actor-ID.

LQ-505 prüft Actor, Ziel, Scope, aktuelle Menge und aktuelle aktive
domänenspezifische Authority innerhalb derselben Schreibtransaktion erneut.

Ein letzter effektiv aktiver Member kann nicht deaktiviert werden.

## Offline-Recovery

Der Recoveryrequest enthält exakt Recovery-ID, Ziel-User-ID, Scope-ID und
erwartete domänenspezifische Revision.

Diese Grenze konstruiert keinen `SessionPrincipal`.

LQ-505 erlaubt nur die Reaktivierung eines bereits historisch vorhandenen
Members, wenn die aktuelle Menge keinen effektiv aktiven Member mehr besitzt.

Recovery kann keine neue Person hinzufügen und keine andere Domäne ersetzen.

## Private Dateigrenzen

Jeder Prozess verlangt `--database-url-file`, `--request` und
`--result-file`.

Datenbank-URL und Request werden über die descriptorgebundene, no-follow,
owner-only, single-link, `0400`-/`0600`- und größenbegrenzte LQ-519-Grenze
gelesen.

Es gibt keinen Environmentfallback und keine Secretwerte auf der
Kommandozeile.

Das Ergebnis wird atomar als neue private `0600`-Datei in einem bereits
privaten Verzeichnis geschrieben und überschreibt keine vorhandene Datei.

## Striktes JSON

Requests müssen geschlossene JSON-Objekte mit genau den erwarteten Feldern
sein.

Doppelte, fehlende, zusätzliche, leere oder nichtstringförmige Werte werden
vor dem Adapteraufruf abgelehnt.

Die feste CLI-Auswahl, nicht ein Requestfeld, bestimmt die Authority-Domäne.

## Readiness und Ressourcenbesitz

Jeder Prozess liest genau eine Datenbank-URL, baut genau eine Engine und prüft
den aktuellen Migration-/Readiness-Gate vor der Mutation.

Die Engine wird auf Erfolgs-, Ablehnungs- und Fehlerpfaden disposed.

Der Operator migriert nicht, erzeugt kein Schema und besitzt keinen
Verbindungsfallback.

## Ergebnisbindung

Ein Erfolg wird nur akzeptiert, wenn die zurückgegebene Revision den festen
domänenspezifischen Typ besitzt und der Scope exakt dem Command entspricht.

Die private Ergebnisdatei enthält ausschließlich `operation_id`, `scope_id`
und `revision_id`.

stdout enthält nur das geschlossene Outcome `applied` oder `rejected`.

## Fehlergrenze

Neutrale Abwesenheit und der bestehende detailfreie Conflictwert werden als
`rejected` mit Exitcode 5 ausgegeben.

Malformed Input endet detailfrei mit Exitcode 2.

Readiness-, Persistenz-, Datei- und unerwartete technische Fehler enden
detailfrei als jeweiliges `operator_unavailable` mit Exitcode 4.

SQL-, Tabellen-, Authority-, User-, Scope-, Pfad- und Exceptiondetails werden
nicht ausgegeben.

## Aktuelle Widerrufswirkung

Der Operator übergibt keinen Authority-Snapshot und keinen Allowwert an den
Adapter.

Jede Lifecyclemutation liest die aktuelle Menge und aktive Foundations in der
Schreibtransaktion neu.

Ein committierter Widerruf beeinflusst deshalb jede spätere Mutation.

## Kein Discovery- oder Batchpfad

Es gibt keinen List-, Search-, Dump-, Read-, Diagnose-, Repair-, Batch-,
Schleifen-, Queue-, Worker-, Scheduler- oder Daemonbefehl.

Jeder Prozess bearbeitet genau eine bekannte Domäne und genau einen Request.

## Keine Folge- oder Quellenwirkung

Kein Authority-Operator erzeugt Management-, Hold-, Recovery- oder
Referencequellrevisionen.

Er erzeugt keine Clearance, Retentiondecision, Retiremententscheidung, keinen
Cleanup-Attempt und keine physische Dateiwirkung.

Er ruft keinen anderen Operator auf.

## Keine fachliche Erzeugung

Der Slice erzeugt keine User, Scopes, Workspaces, Memberships, Rollen,
Research-Permissions, Directories oder Admissionfakten.

Er mutiert ausschließlich die bereits durch LQ-505 definierte ausgewählte
Authority-Set-Historie.

## Packaging

Das Paketinventar steigt von 59 auf 62 Console Entry Points.

Ein gemeinsames neues Operatormodul erhöht die gepackten Operatorfiles von 66
auf 67 beziehungsweise die fachlichen Implementierungs- und Hilfsmodule von 65
auf 66.

Die fail-closed Bundlekonstanten und aktiven Inventarguardrails werden auf
diesen exakten Bestand synchronisiert.

## Kein Schema

LQ-525 ergänzt keine Migration, Tabelle, Spalte, SQL-, Domain-, Port- oder
Adaptersignatur.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Statische Tests prüfen feste Entry Points und Domänen, exakte Requests,
Principaltrennung, explizite Adapteraufrufe, Readiness, Engine-Disposal,
geschlossene Ergebnisse und ausgeschlossene Wirkungen.

Sie behaupten keine PostgreSQL-Ausführung.

## Nächster Slice

LQ-526 implementiert die separate owner-kontrollierte Grenze für die vier
Management-/Hold-/Recovery-/Reference-Quellrevisionsmutationen.

Retention, Retirement, Deployment, Incident-Handoff und verpflichtende
PostgreSQL-Evidence bleiben getrennt.
