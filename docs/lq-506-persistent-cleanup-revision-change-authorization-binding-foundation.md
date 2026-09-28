# LQ-506 — Persistent Cleanup Revision Change Authorization-Binding Foundation

## Ergebnis

LQ-506 ergänzt Revision `20260826_0039` als persistente Bindung zwischen jeder
neuen LQ-501-Quellrevision-Changeentscheidung und dem autorisierenden aktuellen
LQ-504-Authority-Set-Fakt.

Der Slice implementiert noch keinen Quellrevisionsadapter.

## Verbleibende Auditlücke

Revision 0037 bindet Change-ID, Vorgänger, Ziel und Ergebnisrevision.

Sie speichert jedoch nicht, welcher authentifizierte Actor den neuen Change
autorisierte und welche Authority-Set-Revision dabei aktuell war.

Ein separater früherer Bool-Lookup wäre kein dauerhafter Commitnachweis.

## Lineare Revision

Revision 0039 folgt ausschließlich auf `20260826_0038`.

Es entsteht kein Branch und kein zweiter Head.

Die Historie umfasst danach 39 lineare Migrationen.

## Vier getrennte Authorizationtabellen

Management, Hold, Recovery und Referenzen erhalten jeweils eine eigene
Change-Authorizationtabelle.

Es gibt keine Quellartspalte und keine polymorphe Fremdschlüsselbeziehung.

Eine Authorization kann nicht zwischen Quellen verschoben werden.

## Change-ID als Primärschlüssel

Jede Authorizationzeile verwendet die quellenspezifische Change-ID als
Primärschlüssel.

Ein Change kann damit höchstens eine persistente Autorisierungsbindung besitzen.

Die ID verweist auf die bereits getrennte Change-Tabelle derselben Quelle.

## Keine Authorization ohne Change

Der Change-Fremdschlüssel verhindert eine verwaiste Authorizationzeile.

Der spätere Adapter muss Ergebnisrevision, Changebinding und Authorization in
derselben Transaktion erzeugen.

Eine Authorization allein ist kein Quellrevisionsfakt.

## Authority-Set-Revision

Jede Zeile bindet die exakte Authority-Set-Revision, die den Commit
autorisierte.

Sie ist keine vom Caller gelieferte Revisionbehauptung.

Der spätere Store liest sie aus dem aktuellen Pointer derselben
Schreibtransaktion.

## Scopebindung

Authority-Set-Revision, Handoffscope und autorisierender User bilden einen
zusammengesetzten Fremdschlüssel zur Memberhistorie derselben Authorityquelle.

Ein Holder aus einem anderen Scope kann nicht adoptiert werden.

Management-, Hold-, Recovery- und Referenzsets bleiben physisch getrennt.

## Autorisierender User

`authorized_by_user_id` bindet den internen User des authentifizierten
`SessionPrincipal`.

Der Fremdschlüssel beweist historische Mitgliedschaft im verwendeten Set.

Active-Member-, aktiver User- und aktiver Scope-Status bleiben atomare
Adapterprüfungen.

## Authorizationzeit

`authorized_at` ist zwingend vorhanden und wird später aus einer serverseitigen
aware-UTC-Uhr erzeugt.

Caller können keinen Zeitpunkt liefern.

Zeit allein erzeugt oder verlängert keine Authority.

## Managementbindung

Ein Management-Revisionschange bindet ausschließlich ein Mitglied des aktuellen
Management-Mutationsauthority-Sets desselben Scopes.

Die fachliche Cleanupmanagementfähigkeit des Targets genügt nicht.

Der Authorizer und der verwaltete Target-User bleiben getrennte Fakten.

## Holdbindung

Ein Hold-Revisionschange bindet ausschließlich das Hold-Mutationsauthority-Set
des serverseitig aus dem Ziel abgeleiteten Scopes.

Cleanupmanagement- oder Recoveryauthority kann nicht als Holdauthorization
referenziert werden.

Clear und Blocked bleiben Eigenschaften der Ergebnisrevision.

## Recoverybindung

Recoverychanges verwenden ausschließlich die Recovery-Mutationsauthority-
Memberhistorie.

Journalterminalität oder Holdauthority ist kein Ersatz.

Die Authorizationzeile speichert keinen Recoveryzustand des Ziels.

## Referenzbindung

Referenzchanges verwenden ausschließlich die Referenz-Mutationsauthority-
Memberhistorie.

Eine allgemeine Registry-, Research- oder Membershipauthority kann nicht
gebunden werden.

Referenz-Evidence bleibt im autoritativen Quellsystem.

## Aktueller Pointer bleibt Adapterpflicht

Der zusammengesetzte Fremdschlüssel beweist historische Setmitgliedschaft, aber
nicht, dass die Setrevision beim Commit current war.

Der spätere Adapter muss Pointer, Active-Member, aktiven User und aktiven Scope
unter derselben Sperrordnung prüfen.

Ein stale positives Set darf keinen neuen Change autorisieren.

## Retry nach Entzug

Eine bereits committierte Authorizationbindung bleibt nach Authorityentzug
historisch erhalten.

Dadurch kann ein exakter Retry derselben Change-ID weiterhin vor aktueller
Authorityprüfung rekonstruiert werden.

Ein neuer Change nach Entzug muss den aktuellen negativen Bestand sehen und
scheitern.

## Principal ist keine Authority

Die persistierte User-ID dokumentiert den Actor, erteilt aber selbst keine
Authority.

SessionPrincipal, Session-ID, Cookie und CSRF-Nachweis werden nicht gespeichert.

Die Authority entsteht ausschließlich aus dem aktuell gebundenen Setmember.

## Keine caller-supplied Allowentscheidung

Es gibt keine Allow-, Role-, Permission-, Authorized- oder Evidence-Spalte.

Die Authorization ist das Ergebnis einer serverseitigen atomaren Entscheidung,
nicht ihr Eingabeparameter.

Ein früheres LQ-505-True wird nicht persistiert oder übernommen.

## Keine Bestandsadoption

Alle vier Tabellen bleiben nach Migration leer.

Bestehende 0036-Revisionen oder 0037-Changebindings erhalten keine erfundene
Authorization.

Es gibt keinen Seed, Backfill oder Bootstrap.

## Neue Writes müssen vollständig sein

Der spätere LQ-500-Schreibadapter darf eine neue Quellrevision nur erzeugen,
wenn Revision, Changebinding und Authorizationbinding gemeinsam committen.

Ein neuer Change ohne Authorization ist für den kontrollierten Pfad ungültig.

Historische ungebundene Zeilen werden nicht nachträglich productionwirksam.

## Nichtwiederverwendung und Retention

Change-ID, Authority-Set-Revision, Scope und Authorizer bleiben dauerhaft an den
Commit gebunden.

Die Foundation definiert keinen Delete- oder Updatepfad.

Historie bleibt mindestens für Retry, Audit und Entzugsnachweis erhalten.

## Keine Mutationsauthority-Verwaltung

LQ-506 verändert keine Authority-Sets, Members, Current-Pointer, Bootstrap-,
Lifecycle- oder Recoveryentscheidungen aus Revision 0038.

Der LQ-505-Adapter bleibt die einzige dafür vorgesehene Persistenzgrenze.

Authorizationbinding ist kein Authority-Lifecycle.

## Keine Quellrevisionmutation

Die Migration erzeugt keine Management-, Hold-, Recovery- oder
Referenzrevision und keine Changeentscheidung.

Sie erzeugt keine IDs und keine Zeiten.

Der autorisierte Appendalgorithmus folgt separat.

## Keine Clearance oder Dateioperation

LQ-506 erzeugt weder Attempt noch Clearance.

Es speichert keine Directory-ID, Handles, Roots, Leafs, Pfade oder
Artefaktbytes.

Physischer Cleanup und Production-Wiring bleiben geschlossen.

## Downgrade

Downgrade entfernt Reference-, Recovery-, Hold- und zuletzt
Management-Authorizationbindings.

Change-, Revisions- und Authority-Historien bleiben unverändert.

Productiondowngrade bleibt eine separate Betriebsentscheidung.

## Gate-Synchronisierung

Der erwartete Head wird auf `20260826_0039` gesetzt.

Das operative Bundle erwartet 39 Migrationen.

Die Roadmap veröffentlicht denselben Head und dieselbe Anzahl.

## Tests

Fokussierte Prüfungen belegen vier leere getrennte Tabellen, Change-PK/FK,
quellenspezifische Authority-Memberbindung aus Setrevision, Scope und Authorizer,
zwingende Authorizationzeit, fehlende Allow-/Role-/Evidencefelder, fehlende
Adoption und reversen Downgrade.

## Nächster Slice

LQ-507 sollte die vier autorisierten append-only Quellrevisionmutationen
implementieren und Ergebnisrevision, Changebinding sowie Authorizationbinding
atomar schreiben.

Atomare Attempt-/Clearancecreation und physischer Cleanup folgen getrennt.
