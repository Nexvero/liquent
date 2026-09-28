# LQ-432 — Persistent Authorized Manifest Handoff Registry

## Ergebnis

LQ-432 implementiert die LQ-431-Ports für atomare Reservierung und
autorisierten Lookup persistenter privater Manifest-Handoffattempts.

Der Adapter startet keinen Writer und schreibt keine spätere Beobachtung.

## Adapter

`DatabaseManifestHandoffRegistry` erhält eine extern besessene SQLAlchemy-
Engine, zwei getrennte ID-Generatoren und eine UTC-Clock.

Er erzeugt keine Engine, liest keinen DSN und besitzt keine Connection über
einen Methodenaufruf hinaus.

Sein `repr` enthält keine IDs, Namen, Actoren oder Datenbankdetails.

## Neue Reservierung

Die Reservierungsgrenze erhält ausschließlich Reservierungs-ID, Actor-UserId,
Registry-Scope-ID und validierten Handoffnamen.

Attempt-ID, Observation-ID und Reservierungszeit entstehen innerhalb der
Persistenzgrenze aus kontrollierten Abhängigkeiten.

Eine erfolgreiche neue Reservierung persistiert atomar:

- dauerhafte Scope-/Name-/Attempt-Bindung;
- ursprünglichen Actor und Reservierungs-ID;
- serverseitige UTC-Reservierungszeit;
- initiale Observation mit Sequenz 1 und Art `reserved`.

Ohne Commit wird kein reserviertes Attempt ausgegeben.

## Aktuelle Authority

Vor jeder neuen Reservierung werden in derselben Transaktion frisch gelesen:

- aktiver interner User für exakt den Actor;
- aktiver Registry-Scope;
- aktive Registryauthority desselben Users im exakt gleichen Scope.

Fehlt einer dieser Fakten oder ist er inaktiv, endet die Entscheidung neutral
mit `None` und ohne ID-/Clockgeneratorzug oder Mutation.

SessionPrincipal wird nicht persistiert und Actoridentifikation allein erteilt
keine Authority.

Der Adapter akzeptiert keinen Allow-Boolean, Rollenwert, Status oder
Authoritysnapshot.

## Konkurrenz

PostgreSQL serialisiert Registry-Foundation, Authorities, Attempts und
Observationen vor der Erstentscheidung mit einem Datenbanklock.

SQLite trägt denselben funktionalen Einzelprozessvertrag.

Die eindeutige Scope-/Name-Constraint bleibt die letzte dauerhafte
Konkurrenzgrenze.

In-Process-Locks oder Dateiabwesenheit werden nicht verwendet.

## Exakter Retry

Die Reservierungs-ID wird vor aktueller Authorityprüfung aufgelöst.

Ein exakt identischer Retry liefert dieselbe Attempt-ID und ursprüngliche
Reservierungszeit ohne neue IDs, Clockread oder Observation.

Das gilt auch nach späterem Authorityentzug, damit ein verlorener Commit-
Ausgang historiesicher auflösbar bleibt.

Der Retry erteilt keine Writerauthority und verändert keine Registry-Fakten.

## Konflikt

Dieselbe Reservierungs-ID mit anderem Actor, Scope oder Namen ergibt
`ManifestHandoffReservationConflict`.

Eine neue Reservierungs-ID für einen bereits dauerhaft gebundenen Scope-/
Namen ergibt denselben detailfreien Konflikt.

Der Konflikt enthält weder fremde Attempt-ID noch Actor-, Scope-, Namens- oder
Persistenzdetails.

Es gibt kein Upsert, Rebind oder Namensrecycling.

## Autorisierter Lookup

Lookup erhält Actor, Scope und Namen.

Bei jedem Aufruf werden aktiver User, aktiver Scope und aktive exakte
Scopeauthority neu gelesen.

Nur dann wird das Attempt mit seiner höchsten geordneten Observation als
begrenzte `ManifestHandoffAttemptView` rekonstruiert.

Fehlende Authority oder fehlendes Attempt ergibt neutral `None`.

Authorityentzug wirkt damit auf jeden späteren Lookup.

## Persistenzvalidierung

IDs werden nur aus nicht leeren UTF-8-Bytes rekonstruiert.

Reservierungszeiten müssen UTC sein und Observationarten das geschlossene
Domainenum erfüllen.

Ein exakter Retry verlangt genau eine initiale Sequenz-1-Observation der Art
`reserved`.

Mehrdeutige, beschädigte oder nicht rekonstruierbare Fakten enden detailfrei
als `manifest_handoff_registry_unavailable`.

Technische Fehler werden ohne SQL-, Pfad-, ID-, DSN- oder Treiberdetails
vereinheitlicht.

## Keine Dateisystemauthority

Reservierung schreibt keine Manifestdatei und prüft keine Final- oder
Tempdatei.

Sie ist notwendige Vorbedingung einer späteren Writer-Composition, startet den
Writer aber nicht automatisch.

Lookup autorisiert weder Reconciliation noch Cleanup.

Kein Ausgang autorisiert Staging, Commit, Push, Build, Publication oder
Deployment.

## Tests

Fokussierte SQLite-Tests belegen:

- atomare Attempt- und initiale Observationserzeugung;
- exakten Retry ohne Generatoren oder erneute Authority;
- detailfreie Konflikte für divergenten Retry und belegten Namen;
- fail-closed neue Reservierung und Lookup nach User-, Scope- oder
  Authoritydeaktivierung;
- begrenzte aktuelle View;
- fehlende Writer- und Entry-Point-Verdrahtung.

Die PostgreSQL-Locksemantik bleibt vor Production-Wiring zusätzlich mit zwei
unabhängigen Verbindungen zu belegen.

## Nichtziele

LQ-432 implementiert keinen Scope-/Authority-Bootstrap, Lifecycle,
Observation-Write-Port, Writer- oder Reconciliation-Composition, Backfill,
Retentiondeleter, Operator, CLI oder Route.

Es gibt keine weitere Migration, keinen Entry Point und kein CI-, Compose-
oder Production-Wiring.

Der Slice führt keinen echten Handoff aus und verändert keine Manifestdatei.

## Nächster Slice

LQ-433 sollte den kontrollierten Observation-Append-Vertrag für intern
gebundene Writer-, Reconciliation- und Cleanupausgänge definieren.

Scope-Bootstrap, Bestandsverankerung, Writer-Composition und finale
Evidence-Retention bleiben separat.
