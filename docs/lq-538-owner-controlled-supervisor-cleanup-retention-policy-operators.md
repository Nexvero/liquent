# LQ-538 — Owner-controlled Supervisor Cleanup Retention Policy Operators

## Ergebnis

LQ-538 implementiert die vier in LQ-537 festgelegten owner-kontrollierten
One-Shot-Operatorgrenzen.

Ein gemeinsames internes Modul stellt vier feste Console Entry Points bereit;
es gibt keine generische caller-wählbare Action.

## Feste Entry Points

Die Grenzen sind Bootstrap, Policychange, Authority-Lifecycle und
Authority-Recovery.

Jede Grenze akzeptiert ausschließlich private Datenbank-, Request- und
Ergebnisdateipfade.

Ein Aufruf verarbeitet genau einen Request und beendet sich.

## Geschlossene Parser

Jeder Request verlangt seine exakte Feldmenge und lehnt unbekannte, fehlende
oder doppelte JSON-Schlüssel ab.

Bootstrap bindet Bootstrap-ID, Ziel-User und positive ganze Sekunden.

Policychange bindet Actor, Change-ID, optionale Expected-Revision, geschlossenen
Intent und die dazu passende optionale Dauer.

Lifecycle bindet Actor, Change-ID, Ziel, Expected-Authorityrevision und
geschlossenen Intent.

Recovery bleibt ohne Actor und `SessionPrincipal`.

## Sichere private Dateien

Der Operator verwendet die bestehende owner-only private Reader- und atomare
Result-Writer-Grenze.

Es gibt keinen Environment-, Argument- oder interaktiven Secretfallback.

Die Datenbank-Engine wird pro Prozess genau einmal erzeugt und im `finally`
wieder freigegeben.

## Interne Tatsachen

Aware UTC-Clock sowie Policy- und Authorityrevisiongeneratoren werden intern
an den persistenten Adapter gebunden.

Revisionen verwenden getrennte geschlossene Typen und kryptografisch starkes
Material.

Caller können weder Clock noch Resultatrevision vorgeben.

## Persistente Ausführung

Vor der Mutation verlangt der Operator eine positive Database-Readiness.

Alle fachlichen Authority-, Erwartungs-, Lockout-, Nichtverkürzungs- und
Retryprüfungen bleiben im persistenten LQ-533-bis-LQ-536-Adapter.

Der Operator rekonstruiert keine Authority aus dem Request.

## Ergebnisse

Bootstrap gibt Operation sowie Policy- und Authorityrevision aus.

Aktiver Policychange gibt Operation, `active` und Revision aus;
Deaktivierung gibt Operation und `inactive` ohne erfundene Revision aus.

Lifecycle und Recovery geben Operation und resultierende Authorityrevision aus.

Fachlicher Conflict und neutrale Abwesenheit werden `rejected` mit Exitcode 1.

Erfolg wird `applied` mit Exitcode 0.

Technische oder private Eingabefehler werden detailfrei
`operator_unavailable` mit Exitcode 2.

Nur Erfolg schreibt eine private atomare Ergebnisdatei.

## Keine Folgeaktion

Kein Operator startet Evaluation, Decision, Clearance, Cleanup oder einen
anderen Control-Plane-Operator.

Es gibt keine Discovery, Schleife, Queue, Batch- oder Schedulerwirkung.

## Bestand

Der Slice ergänzt vier Console Entry Points und ein Operatormodul.

Das synchronisierte Inventar umfasst 67 Entry Points, 68 fachliche
Operatormodule plus Paketinitialisierer und 42 Migrationen bis Head
`20260826_0042`.

## Nächster Slice

LQ-539 komponiert die persistente aktive Policyquelle mit der bestehenden
Retention-Evaluation, ohne Operator- oder Cleanup-Folgeaktion.
