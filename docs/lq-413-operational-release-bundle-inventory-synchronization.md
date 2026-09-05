# LQ-413 — Operational Release Bundle Inventory Synchronization

## Zweck

LQ-413 synchronisiert den lokalen Builder und Verifier für operative
Releasekandidaten mit dem kumulierten Repositorybestand.

Der Slice schließt die in LQ-412 dokumentierte statische Bundle-Drift.

Er baut, signiert, promotet, publiziert oder deployed kein Artefakt.

## Wheel-Inventar

Der Verifier erwartet fail-closed genau:

- 58 Console Entry Points;
- 65 Pythondateien unter `liquent_platform/operators`;
- 27 lineare Migrationen;
- den eindeutigen Head `20260819_0027`.

Die 65 Operator-Pythondateien bestehen aus:

- 64 Implementierungs- und Hilfsmodulen;
- einem Paketinitialisierer `__init__.py`.

Damit bleiben die Roadmap-Aussage von 64 fachlichen Modulen und die technische
Wheel-Zählung von 65 Dateien widerspruchsfrei getrennt.

## Benannte Grenzen

Die Inventargrenzen liegen nun in:

- `EXPECTED_ENTRY_POINT_COUNT`;
- `EXPECTED_OPERATOR_FILE_COUNT`;
- `EXPECTED_MIGRATION_COUNT`.

Eine Abweichung lehnt das gesamte Bundle weiterhin detailfrei ab.

Es gibt keinen toleranten Bereich und keine caller-supplied Inventarfreigabe.

## Runbook-Inventar

Das Bundle enthält jetzt alle 17 aktuellen Operations-Runbooks.

Zusätzlich zu den bisherigen Identity- und Lifecycle-Runbooks sind enthalten:

- Backup und Restore;
- initialer Staging-Bootstrap;
- Release-Environment-Readiness;
- Release-Publication-Worker;
- Research-Worker-Staging-Readiness;
- Staging-Promotion;
- disposable PostgreSQL Runtime-Cleanup;
- PostgreSQL Volume-Disposition und -Deletion.

Das Inventar bleibt exakt: ein fehlendes oder zusätzlich eingeschleustes
Runbook wird bei der Verifikation abgelehnt.

## Vertragsinventar

Das Vertragsinventar behält die bisherigen Foundation- und Handoffverträge.

Ergänzt werden die abschließenden Grenzen für:

- detached Signatur und Promotion;
- offline Publication Worker und Release-Readiness;
- Provider- und Deploymenttrennung;
- persistente Research Worker und Stagingnachweise;
- Staging Executor und Runtime Inspection;
- Artifact Capability und deren Recovery;
- Rollback Evidence und disposable PostgreSQL Disposition;
- Runtime Cleanup, Generation Lineage und operativen Handoff;
- Volume-Disposition, Autorisierung, Löschung und operativen Handoff;
- kumulierten Integrations-Handoff und Roadmap-/Gate-Konsistenz.

Diese Dokumente werden als `classification="required"` manifestiert.

## Unveränderte Sicherheitsgrenzen

Der Builder:

- verlangt standardmäßig einen sauberen Quellbaum am exakten Commit;
- akzeptiert nur reguläre, nicht symbolische Quelldateien;
- scannt Payload und Pfade auf bestehende Secretmuster;
- erzeugt deterministische Metadaten und Checksummen;
- überschreibt kein vorhandenes Ziel;
- erzeugt nur einen unsignierten, nicht promotablen Kandidaten.

Der Verifier:

- extrahiert das Archiv nicht;
- prüft Pfade, Typen, Modi und Zeitstempel;
- verlangt ein exaktes Dateiinventar;
- prüft jede Checksumme und jedes Manifestfeld;
- validiert Entry Points, Migrationen und Operatordateien erneut aus dem Wheel;
- meldet Fehler weiterhin detailfrei.

## Testanpassung

Die deterministische Wheelfixture erzeugt nun:

- 58 synthetische Console Entry Points;
- 64 synthetische Operatorimplementierungen plus `__init__.py`;
- dieselbe lineare Kette aus 27 Migrationen.

Historische statische Audittests prüfen nun die benannten Grenzen statt der
alten Literalwerte 34 und 38.

LQ-412 bleibt als Nachweis der vorgefundenen Drift nachvollziehbar, während
sein Test den nun synchronisierten Zustand anerkennt.

## Aussagegrenzen

Die Synchronisierung beweist noch keinen erfolgreichen Build des echten
aktuellen Wheels.

Sie beweist ebenfalls nicht:

- dass die normale Gesamtsuite erneut gelaufen ist;
- dass die PostgreSQL-Pflichtsuite aktuell bestanden wurde;
- dass Wheel und Source Distribution gebaut werden können;
- dass ein erzeugtes Bundle signiert oder promotierbar ist;
- dass eine externe Releaseumgebung freigegeben ist.

Diese Aussagen benötigen ihre eigenen Gates und Evidenz.

## Nichtziele

LQ-413 ändert keine Produktlogik, Ports, Modelle, Migrationen, Entry Points
oder Runtimecomposition.

Der Slice führt keine Datenbankverbindung, Publication, Signatur, Promotion,
Provideroperation, Staging- oder Deploymentaktion aus.

Er erstellt keinen Branch und staged, committed oder pusht nichts.

## Nächster Slice

LQ-414 sollte einen lokalen Packaging- und Bundle-Preflight ausführen.

Er soll Wheel und Source Distribution bauen, Metadaten und Entry-Point-Imports
prüfen, den synchronisierten Bundle-Builder mit neuer lokaler Evidenz ausüben
und jedes nicht ausführbare Pflichtgate ausdrücklich offen lassen.
