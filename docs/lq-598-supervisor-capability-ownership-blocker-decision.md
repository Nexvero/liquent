# LQ-598 — Supervisor Capability Ownership Blocker Decision

## Ergebnis

LQ-598 schließt den Auditstrang LQ-595 bis LQ-598 ab.

Eine direkte konkrete Implementation der alten LQ-446-Ports hinter LQ-468 ist
für den Docker-Productiongraph ausdrücklich abgelehnt.

## Begründung

Der aktuelle Parent publiziert Ready und Consumed selbst und ruft danach eine
weitere Capabilityprimitive auf.

Damit fehlen direkter Kindprozesshandshake, direkter Gatekonsum und eine
belegte physische Einmaligkeitsgrenze.

Eine zusätzliche Primitive könnte dieselbe fachliche Wirkung verdoppeln.

## Verbindliches Zielbild

Genau der gebundene Wrappercontainer publiziert Ready, konsumiert Release,
führt Writer oder Recovery einmal aus und publiziert Terminal.

Der Parent commitet Entscheidungen, publiziert nur Release-Token und
korreliert Wrapper-, Engine- und Journalfakten.

Der Parent führt keine zweite Capability aus.

## Sichere Implementierungsreihenfolge

1. kanonisches gebundenes Wrapper-Jobdokument und Rollen festlegen;
2. Writer- und Recovery-Wrapperentrypoints implementieren;
3. direkte Ready-/Consumed-/Terminal-Artefakte regressiv belegen;
4. Prepare-/Release-/Terminalservice observation-only umstellen;
5. Crash-, Release-Unknown- und Restartpfade auf PostgreSQL belegen;
6. erst danach LQ-482-All-or-nothing-Production-Wiring erneut auditieren.

## Weiterhin nutzbar

Der LQ-591-Dockerclient und der LQ-462-Engineadapter bleiben gültige isolierte
Komponenten.

Persistente Journal-, Runtime-, Gatebinding- und Directoryadapter bleiben
ebenfalls verwendbar.

Nur die heutige Parent-/Wrapper-Wirkungsverteilung muss korrigiert werden.

## Weiterhin geschlossen

Settings, Appfactory, Lifespan, Compose, Docker-Socket-Mount und Deployment
bleiben unverändert geschlossen.

Es gibt keine öffentliche Route, keinen Scheduler und keinen automatischen
Startup-Reconciler.

## Keine Mutation

LQ-598 verändert keine Productionquelle, Signatur, Migration oder Tabelle.

Der fokussierte Architektur-, Vertrags- und Quellaudit besteht mit 76 Tests.

Die vollständige normale Regression besteht unter strikter
DeprecationWarning-Grenze mit 5163 Tests und einem erwarteten Skip; 107
PostgreSQL-Tests bleiben mangels Persistenzänderung bewusst abgewählt.

Es führt keinen Dockerzugriff, Commit, Push, Release oder Deployment aus.

Head bleibt `20260826_0042` mit 42 linearen Migrationen.

## Nächster Strang

LQ-599 definiert das kanonische wrappergebundene Jobdokument und seine
vollständige Handle-, Profil-, Runtime-, Gate-, Claim-, Owner- und
Scopebindung.
