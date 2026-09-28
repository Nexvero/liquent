# LQ-543 — Owner-controlled Supervisor Cleanup Retention Evaluation Operator

## Ergebnis

LQ-543 implementiert den owner-kontrollierten One-Shot-Operator für genau eine
vollständige persistente Retentionoperation.

## Minimaler Request

Die private kanonische Requestdatei enthält ausschließlich Operation-ID und
Directory-ID.

Sie enthält keine Disposition, Policyrevision, Dauer, Decision-ID, Clock,
Retired-Fakten oder Allowbehauptung.

Unbekannte, fehlende oder doppelte Felder werden detailfrei abgelehnt.

## Gemeinsame Composition

Operator und Cleanup-Composition verwenden dieselbe interne LQ-542-
Retentionfactory.

Damit existiert keine zweite lokale Policy- oder Evaluationslogik.

Die Factory bindet persistenten Directorylookup, aktive Policyquelle,
autoritative Evaluation, Operationstore und interne Decision-ID.

## Private Prozessgrenze

Der Operator verlangt private Datenbank-, Request- und Ergebnisdateien.

Er verwendet den bestehenden owner-only Reader und atomaren Resultwriter.

Die Engine wird genau einmal aufgebaut und im `finally` freigegeben.

Es gibt keinen Environment- oder interaktiven Secretfallback.

## Geschlossenes Ergebnis

Erfolg schreibt Operation-ID, Directory-ID, Decision-ID, tatsächlich
verwendete Policyrevision und `retain` oder `eligible`.

Neutrale Abwesenheit oder Operation-Conflict wird detailfrei `rejected`.

Technische Fehler werden detailfrei `operator_unavailable`.

Nur Erfolg schreibt die private Ergebnisdatei.

## Idempotenz

Ein Retry derselben Operation-/Directorybindung liefert denselben persistenten
First-Writer ohne neue Policy-, Clock- oder Decisionwirkung.

Abweichende Directorybindung derselben Operation-ID wird abgelehnt.

## Keine Folgeaktion

Auch `eligible` startet keine Clearance, keinen Attempt und keinen Cleanup.

Der Operator besitzt keine Discovery, Batch-, Worker-, Queue- oder
Schedulerwirkung.

## Bestand

LQ-543 ergänzt einen Entry Point im bestehenden Retention-Operatormodul.

Der Bestand umfasst nun 68 Entry Points, 68 fachliche Operatormodule plus
Initialisierer und 42 Migrationen bis Head `20260826_0042`.

## Nächster Slice

LQ-544 ergänzt gezielte PostgreSQL-Integrationsnachweise für Policybootstrap,
Mutation, Recovery, Evaluation, Operation und Clearance-Revocation.
