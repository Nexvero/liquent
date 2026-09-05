# LQ-542 — Explicit Retention Operation Cleanup Composition

## Ergebnis

LQ-542 ergänzt die LQ-540-Retentionoperation als vierte explizite Grenze der
bestehenden opt-in Supervisor-Control-Directory-Cleanup-Composition.

Konstruktion bleibt vollständig inert.

## Gemeinsame Engine

Directorylookup, Policylookup, Retentionoperation, Clearance, Execution und
Reconciliation verwenden dieselbe extern besessene Datenbank-Engine.

Die Composition erzeugt oder disposed keine Engine.

Alle persistenten Adapter sehen damit denselben konfigurierten System-of-
Record-Endpunkt.

## Aktuelle Policyquelle

Die Composition erstellt genau einen persistenten LQ-533-bis-LQ-536-
Policyadapter.

Die LQ-539-Evaluation verwendet dessen aktuellen parameterlosen Policylookup.

Clock und interne Policy-/Authoritygeneratoren werden geschlossen intern
gebunden; Lookupkonstruktion führt keinen Generatoraufruf aus.

## Retentionoperation

Die Composition bindet gemeinsame Directoryauflösung, autoritative Evaluation,
persistenten Operationstore und interne Decision-ID-Erzeugung.

Sie exponiert das resultierende Objekt ausschließlich als
`retention_operation`.

Es gibt keine generische Action- oder Portauswahl.

## Inerte Konstruktion

Factory-Aufbau liest weder Directory noch Policy oder Clock.

Er erzeugt keine Decision, Operation, Clearance oder Cleanupwirkung.

Ein Caller muss `retention_operation.execute(request)` ausdrücklich aufrufen.

## Bestehende Grenzen

`clearance_creation`, `execution` und `reconciliation` bleiben unverändert
explizit verfügbar.

Retentionoperation ruft keine dieser Grenzen implizit auf.

Eine `eligible`-Decision startet daher keine Clearance oder Dateiwirkung.

## Keine neue Productionoberfläche

LQ-542 ergänzt keinen Entry Point, HTTP-Route, Worker, Scheduler, Queue oder
Compose-Service.

Die Factory bleibt ausschließlich opt-in durch einen bereits kontrollierten
Aufrufer.

## Fehlergrenze

Ungültige Abhängigkeiten und Compositionfehler bleiben detailfreie
`ManifestHandoffRegistryUnavailable`.

Keine Konfiguration, ID oder Engine-Repräsentation verlässt die Grenze.

## Bestand

Der Bestand bleibt bei 67 Entry Points, 68 fachlichen Operatormodulen plus
Initialisierer und 42 Migrationen bis Head `20260826_0042`.

## Nächster Slice

LQ-543 implementiert den owner-kontrollierten One-Shot-Retentionoperator auf
der vollständigen persistenten Composition mit privatem Ergebnishandoff.
