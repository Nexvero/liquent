# LQ-444 — Persistent Manifest Handoff Recovery Ownership

## Ergebnis

LQ-444 implementiert die persistente Recoveryseite der LQ-442-Foundation.

`DatabaseManifestHandoffRecovery` erfüllt autorisierten Recovery-Claim,
claimgebundene Reconciliation-Appends und die drei terminalen Recovery-Endports
in einem transaktionalen Adapter.

Der Adapter ruft weder Writer noch Reconciler selbst auf.

## Gemeinsame Persistenzgrenze

Ein Adapter besitzt eine injizierte Engine und optionale serverseitige Clock.

Er erzeugt oder schließt keine Engine und liest keinen DSN.

Konstruktion führt keinen Datenbank-, Clock-, Dateisystem- oder Netzwerkzugriff
aus.

Der `repr` enthält keine Claim-, Owner-, Actor-, Scope- oder Persistenzdetails.

## Unterstützte Datenbanken

PostgreSQL ist die normative Persistenz; SQLite dient deterministischen
Foundationtests.

PostgreSQL serialisiert die beteiligten Authority-, Attempt-, Execution-,
Recovery- und Observationstabellen explizit.

SQLite verwendet seine Transaktionsserialisierung.

Andere Dialekte scheitern detailfrei technisch unverfügbar.

## Geschlossener Recoveryrequest

`claim_recovery` akzeptiert ausschließlich den LQ-441-Request aus
Recovery-Claim-ID, Actor, Scope, Handoffname und kontrolliertem Recovery-Owner.

Attempt-ID, Execution-End-ID, Execution-Claim-ID und Pfade sind keine
Callerparameter.

Es gibt keinen Prozessende-Boolean, Rollenwert, Status, Zeit- oder
Allow-Override.

Der Request autorisiert für sich keine Recovery.

## Exakter Claimretry zuerst

Ein vorhandener Recovery-Claim wird anhand seiner Claim-ID vor aktueller
Authority- oder Aktivitätsprüfung geladen.

Actor, Scope, Name und Recovery-Owner müssen exakt der gespeicherten Bindung
entsprechen.

Ein exakter Retry liefert denselben Attempt-, Execution-Claim- und
serverseitigen Claimzeitfakt auch nach Revocation oder terminalem Ende.

Divergente ID-Wiederverwendung liefert den leeren Ownershipkonflikt.

## Ableitung des Attempts

Für einen neuen Claim löst der Adapter das Attempt ausschließlich über
persistenten Scope und Handoffnamen auf.

Execution-Claim und terminaler Execution-Endnachweis werden über Foreign-Key-
gebundene Persistenzjoins abgeleitet.

Ein unbekanntes, mehrdeutiges oder nicht terminal belegtes Attempt erzeugt
keinen Recovery-Claim.

Caller können keine fremde Attempt- oder End-ID einschleusen.

## Aktuelle Recoveryauthority

Ein neuer Claim verlangt:

- aktiven User;
- aktiven Registry-Scope;
- explizit aktive scopegebundene Recoveryauthority aus Revision 0029.

Registryreservierungsfähigkeit, ordinary Membership und Researchpermissions
werden nicht als Ersatz verwendet.

Fehlende oder entzogene Recoveryauthority liefert neutral `None`.

## Recoverybedarf aus Historie

Die Attempt-Historie wird vollständig, geordnet und mit geschlossener
Faktenmatrix rekonstruiert.

Bereits durable Writererfolge, Reconciliationausgänge und Cleanupausgänge
benötigen keinen neuen Recovery-Claim.

`writer_started` oder `writer_outcome_unknown` mit terminalem Executionende
bleiben recoverbar.

Ein start-not-confirmed Executionende kann bereits aus `reserved` heraus
read-only reconciliert werden.

## Genau ein aktiver Recoveryowner

Vor Insert prüft der Adapter auf einen aktiven Claim desselben Attempts.

Der partielle eindeutige Index aus Revision 0029 erzwingt diese Grenze
zusätzlich transaktional.

Ein gleichzeitig aktiver anderer Recoveryowner führt neutral zu keinem neuen
Claim und gibt dessen Identität nicht aus.

Es gibt keine Claimübernahme aufgrund von Zeit oder Leaseablauf.

## Recovery-Claim-Ergebnis

Der Claim bindet Recovery-Claim-ID, Attempt, terminal beendeten Execution-
Claim, Recovery-Owner und serverseitige Claimzeit.

`writer_authorized` und `cleanup_authorized` bleiben nicht überschreibbar
`false`.

Der Claim öffnet ausschließlich die spätere read-only Reconciliationgrenze.

Er erzeugt keine Manifestbeobachtung von selbst.

## Revocation nach Claim

Nach eindeutigem Claimgewinn wird die direkte Outcomesicherung mechanisch an
Claim und Owner gebunden.

Ein späterer Authorityentzug verhindert nicht, dass das bereits frisch
beobachtete Ergebnis appendiert und der Recoveryowner terminal gesichert wird.

Der Entzug verhindert aber jeden späteren neuen Recovery-Claim.

Er autorisiert weder Writer noch Cleanup.

## Fünf quellenspezifische Appends

Der Adapter implementiert ausschließlich:

- `record_manifest_absent`;
- `record_manifest_temporary_only`;
- `record_manifest_handed_off`;
- `record_manifest_handed_off_pending_cleanup`;
- `record_manifest_handoff_conflict`.

Es gibt keine generische Kindmethode und keine Writer- oder Cleanupmethode.

## Faktenmatrix

Temporary-only, handed-off und handed-off-pending-cleanup verlangen exakt
`ManifestHandoffFacts`.

Absent und conflict verbieten Fakten.

Digest und Dateizahl werden nicht aus Caller-Dictionaries rekonstruiert,
sondern müssen aus dem kontrollierten direkten LQ-427-Ergebnis stammen.

Attempt, Scope, Name und Sequenz sind keine Portparameter.

## Atomarer Recoveryappend

Der Adapter verlangt einen aktiven, nicht terminalen Claim und exakt denselben
Recovery-Owner.

Er validiert die vollständige Attempt-Historie und bestimmt die nächste
Sequenz serverseitig.

Manifestobservation und Bindung an den Recovery-Claim werden in derselben
Transaktion eingefügt.

Ein Commit erzeugt daher beide Fakten oder keinen.

## Start-not-confirmed-Reconciliation

Ist der Writerstart nach Claim nie bestätigt und sein Prozessende direkt
terminal belegt, darf Recovery eine Reconciliationobservation unmittelbar nach
`reserved` appendieren.

Das ist kein nachträglich erfundenes `writer_started` und keine
Writerautorisation.

Die Observation ist zwingend an den Recovery-Claim gebunden.

Ein zweiter Writer bleibt dauerhaft verboten.

## Observationretry zuerst

Ein vorhandener Observation-ID-Retry wird vor aktuellem Claimzustand geladen.

Claim, Owner, Kind und Fakten müssen exakt übereinstimmen.

Exakte Wiederholung liefert dieselbe Observation, Sequenz und Serverzeit auch
nach Recovery-Ende oder Revocation.

Divergente Wiederverwendung oder eine nicht claimgebundene vorhandene
Observation-ID liefert Ownershipkonflikt.

## Nur eine Observation je Recovery-Claim

Revision 0029 und der Adapter erlauben pro Recovery-Claim höchstens eine
Reconciliationobservation.

Ein zweiter Observationversuch überschreibt den ersten nicht und liefert
Konflikt.

Ein unklarer Commit wird ausschließlich mit derselben Observation-ID und
denselben Fakten retried.

Der Reconciler wird durch diesen Adapter nie erneut ausgeführt.

## Quellenspezifische Recovery-Enden

Der Adapter implementiert getrennt:

- `record_outcome_secured`;
- `record_outcome_unknown`;
- `record_start_not_confirmed`.

Jede Methode erhält stabile Recovery-End-ID, Recovery-Claim und Owner.

Exitcode, Signal, PID, Host, Zeit und Prozessdetail sind keine Callerfelder.

## Secured-Ende

`outcome_secured` verlangt eine bereits atomar claimgebundene
Reconciliationobservation.

Ohne Observation liefert der Adapter neutral `None` und erfindet keinen
Erfolg.

Endzeile und terminales `ended_at` des Recovery-Claims werden in derselben
Transaktion geschrieben.

Danach ist der aktive Claimindex für eine spätere Entscheidung freigegeben,
während Claim und Endhistorie erhalten bleiben.

## Unknown und Start-not-confirmed

`outcome_unknown` und `start_not_confirmed` sind nur ohne bereits gesicherte
Recoveryobservation zulässig.

Sie belegen das terminale Ende des konkreten Recoveryowners, nicht einen
Manifestzustand.

Danach darf ein neuer autorisierter Recovery-Claim mit neuer Claim-ID und
frischer Reconciliation entstehen.

Die alte Claim-ID wird niemals wiederverwendet.

## Endretry zuerst

Ein vorhandener Recovery-Endfakt wird anhand der End-ID vor aktuellem Zustand
aufgelöst.

Claim, Owner, Kind und Claim-`ended_at` müssen exakt konsistent sein.

Exakte Wiederholung liefert denselben Fakt; Divergenz liefert Konflikt.

Ein zweites End überschreibt das erste nicht.

## Bereits gelöster Ausgang

Ist die Attempt-Historie bereits durch Writererfolg, Reconciliation oder
Cleanup aufgelöst, erzeugt `claim_recovery` neutral keinen weiteren Claim.

Dateizugriff findet dabei nicht statt.

Temporary-only, pending-cleanup und conflict bleiben sichtbare gelöste
Recoverybeobachtungen, aber autorisieren keine Cleanupmutation.

Weiteres operatives Handeln bleibt einem separaten Slice vorbehalten.

## Neutrale Ausgänge

Neutral `None` bleibt mindestens:

- unbekannter Scope/Name oder fehlender Execution-Endnachweis;
- fehlende aktuelle Recoveryauthority;
- bereits gelöste Attempt-Historie;
- anderer aktiver Recoveryowner;
- fremder Claimowner;
- Appends oder Endarten, die nicht zum Claimzustand passen.

Keine fremde ID oder Historie wird offengelegt.

## Konflikte

Der leere `ManifestHandoffOwnershipConflict` vereinheitlicht divergente
Claim-, Observation- oder End-ID-Wiederverwendung und zweite permanente
Bindungsversuche.

Es gibt kein Upsert, Last-write-wins oder Reassignment.

Konflikt autorisiert weder Reconciliation noch einen weiteren Claim.

Wiederholung ändert den Konflikt nicht.

## Technische Unverfügbarkeit

Ungültige Typen, unbrauchbare Clock, beschädigte UTF-8-/Zeit-/Faktenwerte,
unmögliche Historie, inkonsistentes End-`ended_at`, SQL- und
Infrastrukturfehler werden als bestehende detailfreie
`ManifestHandoffRegistryUnavailable` vereinheitlicht.

Persistenz-, Constraint-, Actor-, Scope-, Claim- und Pfaddetails verlassen den
Adapter nicht.

## Keine Lease- oder Fencingfiktion

Der Recoveryadapter liest keinen Leaseablauf als Prozessende.

Er verlangt den persistenten direkten Execution-Endnachweis aus LQ-443.

Es gibt keinen Claimtakeover und keinen Fencingtoken.

Kein Recoveryausgang kann den LQ-426-Writer öffnen.

## Retention

Recovery-Claims, Enden und Observationbindungen bleiben historiesicher
erhalten.

Nur `ended_at` des Claims wird atomar mit seinem Endfakt gesetzt, um aktive
Ownership zu serialisieren.

Keine Attempt-, Execution-, Observation- oder alte Recoveryzeile wird gelöscht
oder reassigned.

## Revision und Scope

LQ-444 nutzt Revision `20260824_0029` ohne neue Migration.

Execution-Claims, Starts, Leases und Execution-Enden werden ausschließlich
gelesen.

Es gibt keinen Seed, Backfill oder Bestandsimport.

Attempts ohne terminalen Execution-Endnachweis bleiben fail-closed.

## Keine Composition oder Prozesssteuerung

Der Adapter startet, wartet, signalisiert oder beendet keinen Prozess.

Er ruft weder LQ-426 noch LQ-427 oder LQ-428 auf.

Supervisorintegration und der kontrollierte Aufruf des Reconciler bleiben
separate Compositionarbeit.

Es gibt keine CLI, Route, Scheduler-, Compose-, CI- oder Productionverdrahtung.

## Tests

Fokussierte SQLite-Tests belegen:

- explizite aktuelle Recoveryauthority für neue Claims;
- exakten Claimretry nach Revocation und divergenten Konflikt;
- höchstens einen aktiven Recoveryowner;
- fünf source-spezifische Appends ohne erneute Authorityprüfung;
- Faktenmatrix und Observationretry;
- secured-Ende erst nach Observation;
- atomare Endzeile und Claimterminalisierung;
- unknown-Ende mit neuer Recoverygeneration;
- start-not-confirmed-Reconciliation unmittelbar nach reserved;
- kein Recovery-Claim nach durablem Writererfolg;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-444 implementiert keinen Reconcilerwrapper, Recoverycomposer, Supervisor,
claimed Writercomposer oder Cleanup.

Scope-/Recoveryauthority-Bootstrap, Bestandsverankerung und finale
Evidence-Retention bleiben separat.

Staging, Commit, Push, Build, Signatur, Promotion, Publication und Deployment
werden weder ausgeführt noch autorisiert.

## Nächster Slice

LQ-445 sollte den kontrollierten Supervisor- und Prozessende-Adaptervertrag
für claimed Writer- und Recoveryausführungen definieren.

Claimed Writerintegration, Recoverycomposition, Bestandsverankerung, Cleanup
und Retention bleiben danach separate Slices.
