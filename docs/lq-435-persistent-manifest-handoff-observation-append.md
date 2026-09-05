# LQ-435 — Persistent Manifest Handoff Observation Append

## Ergebnis

LQ-435 implementiert die zehn LQ-434-Portmethoden mit einem gemeinsamen
privaten, atomaren und append-only Persistenzalgorithmus.

Der Adapter komponiert oder startet Writer, Reconciler und Cleanup nicht.

## Adaptergrenze

`DatabaseManifestHandoffObservationAppend` erhält eine extern besessene Engine
und eine kontrollierte UTC-Clock.

Er erzeugt keine Engine, liest keinen DSN und besitzt keine Connection über
einen Methodenaufruf hinaus.

Sein `repr` enthält keine IDs, Fakten oder Persistenzdetails.

## Getrennte öffentliche Methoden

Alle zehn quellenspezifischen Methoden bleiben öffentlich getrennt.

Sie bestimmen Observationart und Faktenpflicht fest aus der Methodenauswahl.

Nur der private Adapteralgorithmus erhält intern Kind und Authoritymodus.

Es existiert keine öffentliche generische Appendmethode.

## Observation-ID-Retry

Eine vorhandene Observation-ID wird vor Attempt-, Authority- und
Übergangsprüfung gelesen.

Exakt gleiche Attempt-, Kind- und Faktenbindung liefert dieselbe Sequenz und
Zeit ohne Clockread oder neue Zeile.

Abweichende Wiederverwendung ergibt
`ManifestHandoffObservationConflict` ohne gespeicherte Details.

Beschädigte gespeicherte Retryfakten sind technische Unverfügbarkeit.

## Writerstart und Authority

Nur `record_writer_started` verlangt aktuelle aktive Fakten für:

- den ursprünglichen Actor des Attempts;
- dessen persistenten Registry-Scope;
- die exakte Scopeauthority des Actors.

Fehlende oder inaktive Fakten ergeben neutral `None` vor Clockread und Append.

Der Start ist nur bei aktuell letzter `reserved`-Observation zulässig und kann
damit höchstens einmal erfolgen.

## Ergebnisappend nach Start

Writer-, Reconciliation- und Cleanupausgänge prüfen keine aktuelle
Userauthority erneut.

Sie sichern mechanisch den tatsächlichen Ausgang eines bereits gestarteten
Attempts und gewähren keine neue Operation.

Ein späterer Authorityentzug kann den Ergebnisappend deshalb nicht
unterdrücken, sperrt aber jeden neuen Writerstart und autorisierten Lookup.

## Historienvalidierung

Vor einem neuen Append rekonstruiert der Adapter die vollständige geordnete
Observationhistorie des Attempts.

Sie muss:

- lückenlos bei Sequenz 1 beginnen;
- dort exakt `reserved` ohne Manifestfakten enthalten;
- nur bekannte Observationarten tragen;
- für jede spätere Sequenz die LQ-434-Faktenmatrix erfüllen;
- gültige Observation-IDs und UTC-Zeiten enthalten.

Beschädigung ist detailfreie technische Unverfügbarkeit, nicht neutrales
Stale und nicht reparierbar durch Append.

## Übergangsmatrix

Die feste Mindestordnung lautet:

- `reserved` → `writer_started`;
- `writer_started` → Writererfolg oder Writer-unknown;
- jeder bereits gestartete Zustand → frische Reconciliationobservation;
- aktuelles Pending-cleanup → Cleanupabschluss oder Cleanup-unknown;
- nach Cleanupabschluss oder Cleanup-unknown → spätere frische
  Reconciliation.

Stale oder unzulässiger Übergang ergibt neutral `None` ohne Clockread und
Mutation.

Kein Zustand erlaubt einen zweiten Writerstart.

## Atomare Sequenz

PostgreSQL serialisiert die Registry-Foundation und Observationhistorie vor
Retry-, Authority- und Übergangsentscheidung.

SQLite trägt denselben funktionalen Einzelprozessvertrag.

Die nächste Sequenz ist ausschließlich die lückenlos validierte Historienlänge
plus eins.

Sequenz, UTC-Zeit und neue Observation committen in derselben Transaktion.

Die bestehende eindeutige Attempt-/Sequenz-Constraint bleibt die letzte
Konkurrenzgrenze.

## Faktenpersistenz

Manifestdigest und Dateizahl werden gemeinsam oder gemeinsam nicht
persistiert.

Der Adapter konstruiert das geschlossene Append-Ergebnis erneut aus exakt den
committeten Eingaben und der serverseitigen Zeit.

Er erzeugt keinen Digest und liest keine Manifestdatei.

## Fehlergrenze

Fehlendes Attempt und fachlich unzulässiger Übergang sind neutrales `None`.

Divergente Observation-ID ist der detailfreie Domainkonflikt.

SQL-, Dialekt-, Clock-, Encoding-, Historien- und Infrastrukturfehler werden
detailfrei als `manifest_handoff_registry_unavailable` vereinheitlicht.

Interne IDs, SQL, DSN, Actor-, Scope- und Faktenwerte verlassen die Grenze
nicht.

## Tests

Fokussierte SQLite-Tests belegen:

- aktuellen autorisierten einmaligen Writerstart;
- Ergebnissicherung nach Authorityentzug;
- neutralen Startentzug ohne Clockread;
- exakten Retry und divergenten Konflikt;
- Reconciliation-/Cleanup-Übergänge und monotone Sequenzen;
- fail-closed beschädigte Initialhistorie;
- fehlende Composition und Migration.

PostgreSQL-Konkurrenz mit unabhängigen Verbindungen bleibt vor
Production-Wiring gesondert zu belegen.

## Nichtziele

LQ-435 implementiert keinen Writer-, Reconciliation- oder Cleanupwrapper,
Scope-Bootstrap, Bestandsverankerung, Operator, CLI, Route oder Wiring.

Die Revision bleibt `20260819_0028`; es gibt keine neue Migration, keinen Seed
und keinen Backfill.

Es wird kein echter Handoff ausgeführt und keine Datei verändert.

## Nächster Slice

LQ-436 sollte die kontrollierte Registry-zu-Writer-Composition definieren,
einschließlich Scope-/Zielwurzelbindung und Unknown-Routing, ohne sie bereits
automatisch zu verdrahten.

Scope-Bootstrap, Bestandsverankerung und finale Evidence-Retention bleiben
separat.
