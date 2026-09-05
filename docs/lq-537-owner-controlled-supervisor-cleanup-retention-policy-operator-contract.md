# LQ-537 — Owner-controlled Supervisor Cleanup Retention Policy Operator Contract

## Ergebnis

LQ-537 friert vier getrennte owner-kontrollierte Prozessgrenzen für die
persistente Retention-Policy-Control-Plane ein.

Der Slice implementiert noch keinen Operator und eröffnet keine
Productionwirkung.

## Vier getrennte Prozessgrenzen

Die spätere Implementation besitzt genau diese kurzlebigen One-Shot-Grenzen:

1. initialer Policy-/Authority-Bootstrap;
2. reguläre Policyänderung;
3. regulärer Authority-Lifecycle;
4. Offline-Authority-Recovery.

Keine Grenze ruft eine andere implizit auf oder führt Folgeaktionen aus.

Ein Prozess verarbeitet genau eine kanonische Requestdatei und beendet sich.

## Keine generische Action

Die vier Grenzen sind feste Console Entry Points und keine frei wählbare
`action`, Tabellen-, Methoden- oder Portauswahl.

Requests enthalten keine Modulnamen, SQL-Fragmente oder Datenklasse.

Die Datenklasse bleibt konstruktiv `supervisor_control_directory`.

Zusätzliche oder unbekannte JSON-Felder werden abgelehnt.

## Bootstraprequest

Bootstrap akzeptiert ausschließlich Bootstrap-ID, Ziel-User-ID und positive
Mindestaufbewahrung in ganzen Sekunden.

Er akzeptiert keinen Actor, Principal, erwartete Revision oder Authorityrolle.

Die Policy- und Authorityrevisionen werden weiterhin intern erzeugt.

Bootstrap erzeugt keine User-, Workspace-, Membership- oder Rollenfacts.

## Policychangerequest

Reguläre Policyänderung akzeptiert Actor-User-ID, Change-ID, optionale
erwartete Policyrevision, geschlossenen Intent und dessen optionale Dauer.

`replace` verlangt positive ganze Sekunden.

`deactivate` verlangt eine erwartete Revision und verbietet eine Dauer.

Der Operator konstruiert aus der Actor-ID nur einen `SessionPrincipal`.

Er akzeptiert keine neue Policyrevision, kein Allow und keine Authorityrolle.

Der persistente Adapter prüft Authority, Userstatus, Erwartung und
Nichtverkürzung erneut in derselben Mutation.

## Authority-Lifecyclerequest

Lifecycle akzeptiert Actor-User-ID, Change-ID, Ziel-User-ID, erwartete
Authorityrevision und genau `grant`, `deactivate` oder `reactivate`.

Der Request enthält weder resultierende Revision noch vollständige Memberliste.

Actorprincipal ist Identität und keine caller-gelieferte Permitentscheidung.

Lockoutschutz und aktuelle Userfacts bleiben Adapterpflicht.

## Offline-Recoveryrequest

Recovery akzeptiert Recovery-ID, historisch bekannte Ziel-User-ID und
erwartete Authorityrevision.

Sie akzeptiert keinen Actor und erzeugt keinen `SessionPrincipal`.

Sie darf keine neue Person, freie Ersatzmenge oder Rollenbehauptung tragen.

Der Adapter muss vollständigen effektiven Lockout und historische Bindung
erneut aus dem System of Record prüfen.

## Private Eingaben

Jede Grenze verlangt exakt eine private Datenbank-URL-Datei und eine private
kanonische JSON-Requestdatei.

Secrets dürfen nicht als Argument, Environmentfallback oder interaktive
Eingabe übergeben werden.

Beide Dateien werden descriptorgebunden ohne Symlinkfolge, owner-only,
single-link, größenbegrenzt und strikt UTF-8 gelesen.

Die Requestdatei darf keine Datenbank-URL enthalten.

## Interne Generatoren und Clock

Policy- und Authorityrevisionen werden kryptografisch stark innerhalb des
Prozesses erzeugt und typgebunden an den Adapter übergeben.

Der Operator verwendet eine aware UTC-Systemclock.

Caller können weder Revisiongenerator noch Clockwert überschreiben.

Operation-IDs bleiben ausdrücklich caller-geliefert, damit kontrollierte
Retries dieselbe persistente Identität wiederverwenden.

## Geschlossene Ergebnisse

Erfolg gibt nur die jeweilige Operation-ID und die resultierende geschlossene
Policy- oder Authorityrevision aus.

Policy-Deaktivierung gibt eine erfolgreiche `inactive`-Disposition ohne
Revision aus.

Bootstrap darf beide intern erzeugten Revisionen und die Mindestdauer
bestätigen.

Neutrale Abwesenheit und fachlicher Conflict erscheinen gemeinsam als
detailfreies `rejected`.

Technische Nichtverfügbarkeit erscheint getrennt und detailfrei als
`operator_unavailable`.

Kein Ergebnis enthält SQL, DSN, Tabellen-, Pfad-, Member- oder Stackdetail.

## Private Ergebnisausgabe

Jede Grenze verlangt eine explizite private Ergebnisdatei.

Sie wird owner-only, no-follow und atomar im bereits kontrollierten
Elternverzeichnis ersetzt.

Standardausgabe enthält kein Ergebnis- oder Fehlerdetail.

Ein persistierter Adaptererfolg bleibt auch bei verlorenem Dateihandoff durch
dieselbe Operation-ID sicher wiederholbar.

## Exitcodes

`0` bezeichnet geschriebenen geschlossenen Erfolg.

`1` bezeichnet detailfreies `rejected`.

`2` bezeichnet `operator_unavailable`, einschließlich ungültiger privater
Dateien oder nicht schreibbarer Ergebnisausgabe.

Weitere fachliche Zustände werden nicht über Exitcodes offengelegt.

## Keine Discovery

Kein Operator listet Policies, Authoritymember, User, Revisionen oder History.

Es gibt keinen Read-, Search-, Dump-, Diagnose- oder Repairmodus.

Benötigte interne IDs stammen aus einem getrennt kontrollierten Handoff.

## Keine Folgeaktion

Erfolgreiche Policyadministration startet keine Evaluation, Decision,
Clearance oder Cleanupoperation.

Authorityänderung startet keine Policyänderung.

Bootstrap und Recovery starten weder Worker noch weitere Operatoren.

Jede spätere Wirkung benötigt einen eigenen ausdrücklichen Prozessaufruf und
aktuelle System-of-Record-Prüfung.

## Keine Implementation

LQ-537 ergänzt keinen Operator, Entry Point, Parser, Reader oder Writer.

Es ändert keine Migration, Tabelle, Domain-, Port- oder Adaptersignatur.

Appfactory, HTTP, Compose, Scheduler und Productionwiring bleiben unverändert.

Der Bestand bleibt 63 Entry Points, 68 Operatormodule und 42 lineare
Migrationen bis Head `20260826_0042`.

## Nächster Slice

LQ-538 implementiert die vier owner-kontrollierten One-Shot-Operatoren mit
privaten kanonischen Requests und atomarem detailfreiem Ergebnishandoff.
