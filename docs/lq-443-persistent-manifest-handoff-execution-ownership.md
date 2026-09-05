# LQ-443 — Persistent Manifest Handoff Execution Ownership

## Ergebnis

LQ-443 implementiert die persistente Executionseite der LQ-442-Foundation.

`DatabaseManifestHandoffExecutionOwnership` erfüllt Execution-Claim,
Lease-Renewal, claimed Writerstart und die drei terminalen Execution-Endports
in einem transaktionalen Adapter.

Recovery bleibt außerhalb dieses Slices.

## Gemeinsamer Adapter

Ein Adapter besitzt die injizierte Engine, kontrollierte Lease-Dauer und
optionale serverseitige Clock.

Er erzeugt keine Engine, liest keinen DSN und besitzt die Engine nicht.

Konstruktion führt weder Datenbank- noch Clockzugriff aus.

Der `repr` enthält keine Engine-, Claim-, Owner- oder Pfaddetails.

## Unterstützte Datenbanken

Der Adapter unterstützt PostgreSQL als normative Persistenz und SQLite für
deterministische Foundationtests.

Andere Dialekte scheitern detailfrei technisch unverfügbar.

PostgreSQL serialisiert Entscheidungen über einen expliziten Tabellenlock;
SQLite nutzt seine Transaktionsserialisierung.

In-Process-Locks sind keine Korrektheitsgrundlage.

## Execution-Claim-Eingabe

`claim_execution` erhält ausschließlich stabile Claim-ID, Attempt-ID,
Actor-UserId und kontrollierte Execution-Owner-ID.

Es gibt keinen Scope-, Namen-, Pfad-, Rollen-, Status-, Zeit- oder
Allow-Override.

Scope und Name bleiben Eigenschaften des persistenten Attempts.

Claim- und Owneridentitäten werden nicht vom Adapter erzeugt; sie stammen aus
der späteren kontrollierten Composition.

## Exakter Claimretry zuerst

Ein vorhandener Claim wird anhand der Claim-ID vor aktueller Authorityprüfung
gelesen.

Stimmen Attempt, Actor und Owner exakt, liefert der Adapter denselben
persistierten Claim samt ursprünglichen Serverzeiten.

Ein späterer Authorityentzug verändert diesen historischen Retryfakt nicht.

Divergente Wiederverwendung derselben Claim-ID liefert den leeren
Ownershipkonflikt.

## Neuer Claim

Ein neuer Claim ist nur für ein existierendes Attempt zulässig, dessen
Historie exakt aus der initialen `reserved`-Observation besteht.

Der gespeicherte Attemptactor muss dem Actor entsprechen.

User, Scope und bestehende Registryauthority müssen zum Entscheidungszeitpunkt
aktuell aktiv sein.

Fehlende oder entzogene Authority liefert neutral `None`.

## Genau ein Execution-Claim je Attempt

Vor Insert prüft der Adapter auf einen bestehenden Attemptclaim; zusätzlich
erzwingt Revision 0029 die dauerhafte Eindeutigkeit.

Ein anderer Claim für dasselbe Attempt ist ein detailfreier Konflikt.

Kein terminaler Ausgang, Leaseablauf oder Dateizustand gibt den Claim frei.

Der Adapter enthält keine Delete-, Release-, Takeover- oder Rebindmethode.

## Serverseitige Lease

Claimzeit wird genau einmal aus der injizierten Clock gelesen.

Leaseende wird ausschließlich aus dieser Zeit und der kontrolliert injizierten
positiven `timedelta`-Dauer berechnet.

Der Caller liefert weder Zeit noch Ablaufwert.

Der zurückgegebene Claim hält `writer_authorized=false`.

## Lease-Renewal

Jede Renewal erhält eine stabile Renewal-ID als Retryanker sowie Claim und
Owner.

Ein exakter ID-Retry wird vor aktuellem Zustand aufgelöst und liefert dieselben
Serverzeiten.

Divergente Wiederverwendung liefert den detailfreien Ownershipkonflikt.

Eine neue Renewal ist nur für denselben Owner und einen noch nicht terminalen
Execution-Claim zulässig.

## Leaseablauf bleibt Hinweis

Der Adapter erlaubt dem unveränderten Claimowner eine Renewal auch nach dem
vorherigen Leaseende.

Zeitablauf erzeugt weder Prozessende noch Recovery- oder Takeoverfähigkeit.

Ein fremder Owner erhält neutral `None`.

Nach terminalem Endnachweis ist keine neue Renewal mehr möglich.

`recovery_authorized` bleibt fest `false`.

## Claimed Writerstart

`start_claimed_execution` erhält nur Observation-ID, Claim-ID und Owner-ID.

Der Adapter löst Attempt, Actor und Scope aus dem Claim beziehungsweise
Attemptbestand auf.

Ein neuer Start verlangt denselben Owner, fehlendes Execution-Ende, keinen
vorherigen Start und aktuelle User-/Scope-/Registryauthority.

Ein Authorityentzug zwischen Claim und Start sperrt den Writerstart.

## Atomarer Start

Der Adapter validiert, dass die Attempt-Historie exakt bei `reserved` steht.

Danach werden `writer_started` als Sequenz zwei und die Claimbindung in
derselben Transaktion eingefügt.

Ein Commit erzeugt daher entweder beide Fakten oder keinen.

Der Composer darf den Writer später nur nach dem zurückgegebenen
`StartedManifestHandoffExecution` öffnen.

## Startretry

Ein Retry derselben Observation-ID, desselben Claims und Owners liefert die
gespeicherte Startbindung vor aktueller Authorityprüfung.

Der Adapter validiert dabei erneut, dass die referenzierte Observation
`writer_started` ist und zum Claimattempt gehört.

Dieselbe Observation-ID für einen anderen Claim oder Owner sowie ein zweiter
Start für denselben Claim liefert Konflikt.

Eine bereits anderweitig vorhandene Observation-ID wird nicht überschrieben.

## Keine Lease als Startbedingung

Der claimed Start verlangt keinen noch nicht abgelaufenen Leasezeitpunkt.

Lease ist nach LQ-440 kein Fencingmechanismus und kann den weiterhin eindeutig
gebundenen Owner nicht allein durch Zeit entmachten.

Aktuelle Authority und dauerhafte Ownerbindung bleiben die normativen
Startbedingungen.

Es gibt keine Claimübernahme.

## Quellenspezifische Execution-Enden

Der Adapter implementiert getrennt:

- `record_outcome_secured`;
- `record_outcome_unknown`;
- `record_start_not_confirmed`.

Es gibt keinen generischen Kindparameter an der Portgrenze.

Jede Methode erhält stabile End-ID, Execution-Claim und Owner.

## Endretry zuerst

Ein vorhandener Endfakt wird anhand der End-ID vor aktuellem Zustand
aufgelöst.

Exakte Bindung liefert denselben Claim, Attempt, Kind und dieselbe Serverzeit.

Divergente ID-Wiederverwendung liefert Konflikt.

Ein zweites End für denselben Claim überschreibt den ersten nicht.

## Start-not-confirmed

`start_not_confirmed` ist nur zulässig, wenn keine claimed Startbindung
existiert und die Attempt-Historie weiterhin exakt `reserved` ist.

Es behauptet keine Dateiabwesenheit.

Nach diesem End sind Start und Lease-Renewal gesperrt.

Der Attemptname und Execution-Claim bleiben dauerhaft verbraucht.

## Outcome-unknown

`outcome_unknown` verlangt einen eindeutig claimed `writer_started`.

Es darf auch dann gesichert werden, wenn noch keine Writeroutcomeobservation
existiert.

Der direkte Supervisorfakt belegt ausschließlich terminales Prozessende mit
unklarer Outcomesicherung.

Er autorisiert keinen Writerretry.

## Outcome-secured

`outcome_secured` verlangt claimed Start und mindestens eine nachfolgende
durable Outcomeobservation.

Nur `writer_started` allein reicht nicht.

Die Historie wird auf lückenlose Sequenzen, initiales `reserved`, exakt
claimgebundenes `writer_started` und zulässige Folgeübergänge geprüft.

Beschädigte Historie ist technische Unverfügbarkeit, kein Endfakt.

## Authority nach Start

Execution-Ende ist die mechanische Sicherung eines direkt beobachteten
terminalen Supervisorausgangs.

Es liest deshalb keine neue Registryauthority und bleibt nach Entzug
sicherbar.

Der Entzug verhindert jedoch jeden späteren neuen Claim oder claimed Start.

Execution-Ende erteilt keine Recovery-, Cleanup- oder andere Authority.

## Neutrale Ausgänge

Neutral `None` bleibt mindestens:

- unbekanntes Attempt oder Claim;
- fehlende aktuelle Authority für neuen Claim oder Start;
- fremder Owner;
- unpassender terminaler Ausgang für den Startzustand;
- Renewal nach terminalem Endnachweis.

Diese Ausgänge geben keine fremden IDs oder Historie aus.

## Konflikte

Der leere `ManifestHandoffOwnershipConflict` bezeichnet divergente stabile
ID-Wiederverwendung oder konkurrierende permanente Bindung.

Er enthält keine Claim-, Attempt-, Owner-, Observation- oder Zeitdetails.

Es gibt kein Last-write-wins, Upsert oder Reassignment.

Wiederholung ändert den Konflikt nicht.

## Technische Unverfügbarkeit

Ungültige Typen, unbrauchbare Clock, Zeitüberlauf, beschädigte UTF-8-Fakten,
mehrdeutige Zeilen, unmögliche Historie, SQL- und Infrastrukturfehler werden
als bestehende detailfreie `ManifestHandoffRegistryUnavailable` vereinheitlicht.

Constraint-, Tabellen-, Driver-, Host- und Pfaddetails verlassen den Adapter
nicht.

Neutralität und Konflikt bleiben davon getrennt.

## Retention

Claims, Lease-Renewals, Startbindungen und Execution-Enden werden nur
eingefügt und niemals gelöscht oder reassigned.

Der Adapter mutiert keine bestehende Observation und gibt keinen Namen frei.

Die Retentionuntergrenzen aus LQ-440/LQ-442 bleiben unverändert.

Es gibt keine konkrete Frist oder Löschoberfläche.

## Revision und Scope

LQ-443 verwendet Revision `20260824_0029` ohne neue Migration.

Recoveryauthority-, Recovery-Claim-, Recovery-End- und
Recoveryobservationstabellen bleiben unberührt.

Es gibt keinen Seed, Backfill oder Bestandsimport.

Historische Attempts ohne Execution-Claim werden nicht automatisch
übernommen.

## Keine Composerintegration

LQ-439 wird in diesem Slice noch nicht auf Execution-Claims umgestellt.

Der neue Adapter ruft weder Writer noch Reconciler auf.

Supervisoradapter und claimed Composerintegration bleiben separat.

Es gibt keine CLI, Route, Factory, Scheduler-, Compose-, CI- oder
Productionverdrahtung.

## Tests

Fokussierte SQLite-Tests belegen:

- aktuellen Authoritycheck für neue Claims;
- exakten Claimretry nach Revocation;
- dauerhaft genau einen Claim je Attempt;
- Revocation zwischen Claim und Start;
- atomare claimgebundene Startobservation;
- exakten Startretry und Konflikt beim zweiten Start;
- stabile Renewal nach Leaseablauf ohne Recoveryauthority;
- source-spezifische terminale Zustandsgrenzen;
- secured erst nach durablem Outcome;
- exakten Endretry und divergenten Konflikt;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-443 implementiert keinen Recovery-Claim, Recovery-Ende,
Recoveryobservation-Append, Supervisor, Writerwrapper oder Composer.

Scope-/Authority-Bootstrap, Bestandsverankerung, Cleanup und finale
Evidence-Retention bleiben separat.

Staging, Commit, Push, Build, Signatur, Promotion, Publication und Deployment
werden weder ausgeführt noch autorisiert.

## Nächster Slice

LQ-444 sollte die autorisierte persistente Recovery-Claim-, Recovery-End- und
claimgebundene Reconciliation-Observationgrenze implementieren.

Supervisorintegration, claimed Writercomposition, Recoverycomposition,
Bestandsverankerung, Cleanup und Retention bleiben danach separate Slices.
