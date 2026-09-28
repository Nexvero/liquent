# LQ-434 — Manifest Handoff Observation Types and Closed Ports

## Ergebnis

LQ-434 konkretisiert den LQ-433-Vertrag als geschlossene Domainfakten und drei
quellenspezifische Portgruppen.

Der Slice implementiert keinen Persistenzadapter und verändert die Migration
nicht.

## Manifestfakten

`ManifestHandoffFacts` enthält ausschließlich:

- einen kleingeschriebenen SHA-256 mit exakt 64 Hexzeichen;
- eine positive, echte Integer-Dateizahl.

Der Digest bleibt aus `repr` ausgeschlossen.

Die Fakten dürfen in einer späteren Composition nur aus einem direkten
typisierten Writer-, Reconciliation- oder Cleanupresultat konstruiert werden.

Ein beliebiger Transportcaller erhält keine öffentliche Faktenannahmegrenze.

## Append-Ergebnis

`AppendedManifestHandoffObservation` bindet repr-frei Observation-ID und
Attempt-ID sowie:

- positive serverseitige Sequenz größer als 1;
- geschlossene Observationart;
- aware UTC-Zeit;
- ausschließlich bei manifesttragenden Ausgängen Manifestfakten.

Sequenz 1 bleibt der atomaren Reservierung aus LQ-432 vorbehalten.

## Faktenmatrix

Manifestfakten sind exakt erforderlich für:

- `writer_handed_off`;
- `manifest_temporary_only`;
- `manifest_handed_off`;
- `manifest_handed_off_pending_cleanup`;
- `cleanup_completed`.

Fakten sind insbesondere verboten für:

- `writer_started`;
- `writer_outcome_unknown`;
- `manifest_absent`;
- `manifest_handoff_conflict`;
- `cleanup_outcome_unknown`.

Damit kann Unknown, Abwesenheit oder Konflikt keinen Digest und keine
Dateizahl vortäuschen.

## Detailfreier Konflikt

`ManifestHandoffObservationConflict` ist ein leerer, unveränderlicher Wert.

Er repräsentiert ausschließlich divergente Wiederverwendung derselben
Observation-ID und enthält keine gespeicherte Bindung oder Differenzdetails.

Stale oder fachlich unzulässige Übergänge bleiben davon getrennt neutrales
`None`.

## Writer-Port

`ControlledManifestHandoffWriterObservationAppend` besitzt genau getrennte
Methoden für:

- Writerstart;
- belegten Writererfolg mit Fakten;
- Writer-outcome-unknown ohne Fakten.

Es gibt keinen allgemeinen Writerstatusparameter.

## Reconciliation-Port

`ControlledManifestHandoffReconciliationObservationAppend` besitzt genau eine
Methode je LQ-427-Ausgang.

Temporary-only, handed-off und pending-cleanup verlangen Fakten.

Abwesenheit und Konflikt akzeptieren keine Fakten.

Technische Unverfügbarkeit besitzt keine Appendmethode.

## Cleanup-Port

`ControlledManifestHandoffCleanupObservationAppend` trennt:

- belegten Cleanupabschluss mit Fakten;
- Cleanup-outcome-unknown ohne Fakten.

Nicht anwendbar, Konflikt und technische Unverfügbarkeit besitzen keine
Appendmethode.

## Gemeinsame Eingaben

Jede Methode erhält nur:

- intern kontrollierte stabile Observation-ID als Retryanker;
- persistente Attempt-ID;
- genau dort erforderliche Manifestfakten.

Kein Port erhält Observationkind, Sequenz, Zeit, Scope, Name, Actor, Pfad,
Tempname, Allow-Boolean, Rolle oder Authoritysnapshot.

## Gemeinsamer Ausgang

Jede Methode liefert ausschließlich:

- `AppendedManifestHandoffObservation` bei committetem Append oder exaktem
  Retry;
- `ManifestHandoffObservationConflict` bei divergenter Observation-ID;
- neutrales `None` bei stale oder unzulässigem Übergang.

Technische Persistenzfehler bleiben einer späteren detailfreien
Adapterfehlergrenze vorbehalten.

## Authoritygrenze

Die Ports tragen bewusst keinen User- oder Authorityparameter.

Aktuelle Authority für Writer- oder Cleanupstart muss die spätere Composition
vor dem jeweiligen Operationsstart über den kontrollierten Attempt-/Scopepfad
auflösen.

Nach Operationsstart sichern diese Ports nur dessen tatsächlichen Ausgang und
erteilen keine neue fachliche Authority.

Reconciliation bleibt read-only und benötigt eine kontrollierte
Attempt-/Zielwurzelbindung statt caller-gelieferter Authority.

## Serverseitige Entscheidungen

Observationart ist durch die aufgerufene Methode bestimmt.

Sequenznummer und UTC-Zeit entstehen erst innerhalb des späteren Adapters.

Der Adapter muss Observation-ID-Retry, Attempthistorie, erlaubten Übergang und
nächste Sequenz atomar serialisieren.

Die Ports erlauben kein Last-write-wins und keine caller-seitige
Sequenzberechnung.

## Keine generische Implementierungsabkürzung

Ein späterer Adapter darf intern einen gemeinsamen privaten Algorithmus
verwenden.

Seine öffentlichen Portmethoden müssen jedoch getrennt bleiben und ihre feste
Observationart sowie Faktenmatrix selbst erzwingen.

Ein öffentliches generisches `append(kind, payload)` würde den LQ-433-Vertrag
verletzen.

## Migration

Das bestehende LQ-431-Schema kann alle neuen Fakten bereits tragen.

LQ-434 ändert deshalb weder Revision `20260819_0028` noch Migration-Head und
Migrationszahl.

Es wird kein Seed, Backfill oder Observationseintrag erzeugt.

## Tests

Fokussierte Tests belegen:

- Digest-, Dateizahl-, Sequenz- und UTC-Validierung;
- repr-freie IDs und Manifestfakten;
- exakte Faktenmatrix;
- leeren detailfreien Konflikt;
- vollständige quellenspezifische Methodentopologie;
- Abwesenheit generischer Kind-, Sequenz- und Zeitparameter;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-434 implementiert keinen Adapter, Übergangsalgorithmus, Lock, SQL-Append,
Clock- oder ID-Generatorzugriff, Writer-/Reconciliation-/Cleanupwrapper,
Bootstrap, Operator, CLI, Route oder Wiring.

Es wird kein echter Handoff ausgeführt und keine Datei verändert.

## Nächster Slice

LQ-435 sollte den persistenten Observation-Append-Adapter mit atomarer
Transition-, Retry- und Sequenzprüfung implementieren.

Writer-Composition, Scope-Bootstrap, Bestandsverankerung und finale
Evidence-Retention bleiben separat.
