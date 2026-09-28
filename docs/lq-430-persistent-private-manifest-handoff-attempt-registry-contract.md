# LQ-430 — Persistent Private Manifest Handoff Attempt Registry Contract

## 1. Zweck und Status

LQ-430 definiert den Vertrag für eine persistente, nicht wiederverwendbare
Registry privater Manifest-Handoffversuche.

Die Registry schließt die in LQ-429 festgestellte Lücke zwischen aktuell
beobachtbarer Dateitopologie und historischer Namensbelegung.

Dieser Slice implementiert keine Registry und verändert die bestehenden
Writer-, Reconciliation- oder Cleanup-Module nicht.

## 2. System of Record

Die Registry ist das spätere normative System of Record für die Frage, ob ein
Handoffname jemals innerhalb eines Registry-Scopes beansprucht wurde.

Final-, Temp- oder sonstige Dateiabwesenheit ist dafür niemals autoritativ.

Das Dateisystem bleibt System of Record für den aktuell beobachtbaren lokalen
Handoffzustand, nicht für historische Nichtwiederverwendung.

Beide Quellen dürfen nicht ineinander umgedeutet werden.

## 3. Stabiler Registry-Scope

Jede Registry besitzt eine intern erzeugte stabile `RegistryScopeId`.

Sie bezeichnet genau einen owner-kontrollierten privaten Handoff-Namensraum.

Die ID ist nicht aus Pfad, Ownername, Hostname, Zeit, Repository, Branch oder
Manifestdigest abgeleitet.

Sie ist nicht reassigbar und darf bei Verschiebung, Umbenennung oder
Neukonfiguration eines Verzeichnisses nicht auf einen anderen Namensraum
übertragen werden.

Ein lokaler Pfad allein identifiziert keinen Registry-Scope.

## 4. Stabile Attempt-Identität

Jeder erstmalig akzeptierte Versuch erhält eine intern erzeugte stabile
`HandoffAttemptId`.

Sie ist nicht aus Scope, Name, Zeit, Digest oder Dateiinode abgeleitet und wird
nie erneut vergeben.

Eine Attempt-ID bindet dauerhaft genau:

- eine `RegistryScopeId`;
- einen normalisierten, begrenzten Handoffnamen;
- den initialen Versuch als historische Tatsache.

Scope und Name einer bestehenden Attempt-ID sind unveränderlich.

## 5. Dauerhafte Namensbindung

Innerhalb eines Registry-Scopes darf ein Handoffname höchstens einer
`HandoffAttemptId` zugeordnet sein.

Die erste erfolgreiche Reservierung beansprucht den Namen dauerhaft.

Keiner der folgenden Zustände gibt ihn frei:

- Fehler vor Writerstart;
- Writer-Erfolg oder Writer-unknown;
- `manifest_absent` oder `manifest_temporary_only`;
- Pending-cleanup, Konflikt oder Cleanup-Erfolg;
- Löschung der Temp- oder Finaldatei;
- Retentionabschluss, Prozessneustart oder Ownerwechsel.

Es gibt kein Delete-and-recreate, Upsert, Rebind oder Namensrecycling.

## 6. Reservierungsgrenze

Eine neue Reservierung muss vor jeder möglichen Writer-Dateisystemmutation
durable committed sein.

Existiert bereits eine Namensbindung im Scope, endet die Anfrage neutral
fail-closed ohne Writeraufruf.

Ein Fehler oder unbekannter Commit-Ausgang der Reservierung darf ebenfalls
keinen Writer starten.

Er wird ausschließlich über dieselbe Attempt-ID und das Registry-System of
Record read-only aufgelöst.

LQ-430 entscheidet noch nicht über Transaktions- oder Aufrufsignaturen.

## 7. Actor und Authority

Ein authentifizierter Prozess- oder Sessionkontext kann den anfragenden Actor
identifizieren, erteilt aber allein keine Registry-Authority.

Die spätere Reservierungsgrenze muss Scope, Actor und aktuelle
owner-kontrollierte Registryfähigkeit aus dem maßgeblichen Systemzustand
binden.

Sie darf keinen caller-supplied Allow-Boolean, Rollennamen, Scope-Override,
freien Ownerwert oder bereits genehmigten Status akzeptieren.

Fehlender, inaktiver oder nicht zum Scope gebundener Actor scheitert
fail-closed.

LQ-430 führt keine konkrete Actor-, Rollen- oder Capability-Persistenz ein.

## 8. Registry-Fakten und Beobachtungen

Normativ erforderlich sind mindestens:

- unveränderliche Scope- und Attempt-Identität;
- dauerhaft beanspruchter Handoffname;
- unterscheidbare Reservierungsentscheidung;
- historiesichere, geordnete Handoffbeobachtungen;
- Erkennbarkeit eines technisch unbekannten Ausgangs.

Beobachtungen dürfen vorhandene Historie nicht überschreiben oder den Namen
freigeben.

Dateibasierte Outcomes werden nur nach frischer LQ-427-Reconciliation
übernommen; Callerbehauptungen sind keine Registry-Fakten.

Digest und Dateizahl dürfen nur aus validierten kanonischen Manifestbytes
stammen.

## 9. Zustandsordnung

Die Registry ist kein frei beschreibbarer Statusdatensatz.

Eine spätere Implementierung muss monotone historische Übergänge abbilden:

- durable Reservierung vor Writerstart;
- gestarteter Versuch nur nach belegter Reservierung;
- Writer-Ergebnis oder outcome unknown;
- frische Reconciliation nach unknown;
- optional belegter redundanter Tempcleanup;
- fortdauernde finale Evidenzretention.

Abwesenheit ist eine Beobachtung, kein Rücksetzen auf unbenutzt.

Konflikt ist eine Untersuchungssperre, keine Mutationserlaubnis.

## 10. Retry und Unknown-Ausgänge

Technischer Retry darf nur dieselbe `HandoffAttemptId` und exakt dieselbe
ursprüngliche Reservierungsabsicht adressieren.

Er darf keinen zweiten Writerlauf auslösen, wenn ein möglicher Writer-Effekt
nicht zuvor read-only geklärt wurde.

Dieselbe Attempt-ID mit anderem Scope oder Namen ist ein detailfreier
Konflikt.

Eine neue Attempt-ID für denselben Namen ist immer unzulässig.

Unknown bleibt historiesicher sichtbar, bis eine autoritative Registry-
Entscheidung und erforderliche frische Dateireconciliation es auflösen.

## 11. Konkurrenz und Atomarität

Gleichzeitige Reservierungen desselben Namens müssen im normativen
Persistenzsystem in genau eine sichtbare Reihenfolge gebracht werden.

Höchstens eine kann die erstmalige Bindung erzeugen.

Prüfung auf Namensfreiheit, Erzeugung von Attempt-ID, Namensbindung und
Reservierungsentscheidung müssen atomar committen oder vollständig
ausbleiben.

In-Process-Locks, Dateiabwesenheit und Check-then-insert über getrennte
Transaktionen genügen nicht.

## 12. Neutrale Ablehnung und technische Unverfügbarkeit

Bereits belegter Name, abweichender Retry oder fehlende aktuelle Authority
enden neutral und ohne Writer- oder Dateimutationen.

Sie geben keine fremde Attempt-ID, Actoridentität, Historie oder Pfade aus.

Beschädigte Registry-Fakten, unauflösbare Mehrdeutigkeit und
Infrastrukturfehler bleiben davon getrennte detailfreie technische
Unverfügbarkeit.

LQ-430 benennt keinen neuen Exceptiontyp und legt keine Transportabbildung
fest.

## 13. Retention und Nichtwiederverwendung

Die Namensbindungs- und Attempt-ID-Tombstone-Untergrenze ist die gesamte
Lebensdauer des Registry-Namensraums und überdauert die Dateievidenz.

Sie darf nicht verkürzt werden, solange derselbe Scope oder ein daraus
fortgeführter Namensraum Namen interpretieren kann.

Attempt- und Outcomehistorie bleibt mindestens so lange erhalten, wie Retry,
Unknown-Reconciliation, Audit oder Nichtwiederverwendung davon abhängen.

Diese Untergrenzen legen keine konkrete Frist, Tabelle, Archivstufe oder
physische Löschstrategie fest.

Finale Manifestdateien besitzen weiterhin ihre separate
owner-kontrollierte Retentionentscheidung.

## 14. Integration mit LQ-426 bis LQ-428

Der aktuelle LQ-426-Writer kennt keine Registry-Reservierung und bleibt daher
nur eine explizite lokale Dateigrenze.

LQ-427 und LQ-428 bleiben für aktuelle Dateizustände zuständig und dürfen
Registryhistorie weder erzeugen noch entfernen.

Eine spätere Composition muss Reservierung und Writer so ordnen, dass niemals
vor durablem Registry-Commit geschrieben wird.

Sie darf vorhandene Writer-Signaturen in diesem Slice nicht vorwegnehmen.

## 15. Keine Bootstrap- oder Bestandsfiktion

LQ-430 importiert bestehende Dateien nicht automatisch als historische
Attempts.

Eine spätere Einführung in einen bereits verwendeten Namensraum benötigt eine
separate Bestandsaufnahme und Verankerungsentscheidung.

Sie darf aus Dateiabwesenheit keine freie Historie und aus einer Finaldatei
keinen vollständig bekannten Writerverlauf erfinden.

Bootstrap, Backfill und Recovery bleiben getrennte spätere Slices.

## 16. Nichtziele

Dieser Slice erzeugt keine Datei, Tabelle, Spalte, SQL-Anweisung, Migration,
Port-, Modell- oder Methodensignatur.

Er implementiert keinen Adapter, Operator, CLI, Route, Settings-, CI-,
Compose- oder Production-Wiring-Pfad.

Er entscheidet keine Registry-Technologie, ID-Darstellung, Uhr, konkrete
Retentionfrist oder Löschfreigabe.

Er staged, committed, pusht, baut, signiert, promotet, publiziert oder deployed
nichts.

## 17. Nächster Slice

LQ-431 sollte die persistente Registry-Foundation mit geschlossenen
Domainfakten und Ports sowie der minimalen additiven Persistenz konkretisieren.

Writer-Composition, Bestandsverankerung und finale Evidence-Retention bleiben
danach weiterhin separate Entscheidungen.
