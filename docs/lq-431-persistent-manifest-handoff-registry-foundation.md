# LQ-431 — Persistent Manifest Handoff Registry Foundation

## Ergebnis

LQ-431 konkretisiert die LQ-430-Registry als geschlossene Domainfakten, zwei
Ports und eine leere additive Persistenzfoundation.

Der Slice implementiert noch keine Reservierungs- oder Lookupadapter.

## Domainfakten

Neu sind stabile repr-freie IDs für:

- Registry-Scope;
- Handoff-Attempt;
- Reservierungsentscheidung;
- spätere Beobachtung.

`ManifestHandoffName` übernimmt die bestehende begrenzte ASCII-Namensform des
lokalen Writers und akzeptiert keinen Pfad.

Alle IDs sind nicht leer, intern semantisch getrennt und nicht reassigbar.

## Reserviertes Attempt

`ReservedManifestHandoffAttempt` bindet unveränderlich:

- Reservierungs-ID;
- intern erzeugte Attempt-ID;
- Registry-Scope-ID;
- Actor-UserId;
- Handoffnamen;
- serverseitige UTC-Reservierungszeit.

Identitäten und Actor werden in `repr` nicht offengelegt.

Ein detailfreier `ManifestHandoffReservationConflict` bildet divergenten Retry
oder dauerhaft belegten Namen ohne fremde Details ab.

## Beobachtungsvokabular

Das geschlossene Enum umfasst Reservierung, Writerstart, Writererfolg,
Writer-unknown, alle fünf LQ-427-Zustände, Cleanupabschluss und
Cleanup-unknown.

Es gibt keinen Zustand für Freigabe, Löschung, Reuse oder Autorisierung von
Staging und Commit.

`ManifestHandoffAttemptView` zeigt nur Scope, Attempt, ursprünglichen Actor,
Namen, neueste Beobachtungsart und Reservierungszeit.

## Geschlossene Ports

`AuthorizedManifestHandoffAttemptReservation` erhält ausschließlich:

- stabile caller-erzeugte Reservierungs-ID als Retryanker;
- Actor-UserId aus authentifiziertem Kontext;
- Registry-Scope-ID;
- validierten Handoffnamen.

Attempt-ID und Reservierungszeit fehlen bewusst in der Eingabe und müssen
innerhalb der späteren Persistenzgrenze entstehen.

Der Ausgang ist reserviertes Attempt, detailfreier Konflikt oder neutrales
`None` bei fehlender aktueller Authority.

`AuthorizedManifestHandoffAttemptLookup` erhält Actor, Scope und Namen und
liefert nur bei aktueller Scopeauthority eine begrenzte View oder neutrales
`None`.

Kein Port akzeptiert Allow-Boolean, Rolle, Status, Outcome, Digest, Dateizahl,
Pfad, Tempname oder Uhrzeit.

## Persistente Scopes und Authority

Die additive Revision `20260819_0028` folgt linear auf `20260819_0027`.

`manifest_handoff_registry_scopes` hält stabile Scopes mit ausschließlich
`active` oder `inactive`.

`manifest_handoff_registry_authorities` bindet bestehende interne UserIds an
genau einen Scope und besitzt ebenfalls nur active/inactive.

Aktiver User, aktiver Scope und aktive exakte Scopeauthority müssen später in
derselben Reservierungstransaktion frisch geprüft werden.

SessionPrincipal bleibt reine Actoridentifikation und wird nicht persistiert.

Die Migration erzeugt keinen Scope und keine Authority.

## Dauerhafte Attemptbindung

`manifest_handoff_attempts` persistiert Attempt-ID, eindeutige
Reservierungs-ID, Scope, Actor, Namen und serverseitige Reservierungszeit.

Die eindeutige Kombination aus Scope und Namen ist die konkrete
Nichtwiederverwendungsuntergrenze.

Es existiert keine Statusspalte, die einen Namen wieder freigeben könnte.

Attempts referenzieren aktive oder historisch inaktive Foundationfakten ohne
Cascade-Löschung.

## Append-only Beobachtungen

`manifest_handoff_attempt_observations` bindet jede intern erzeugte
Observation-ID an genau ein Attempt.

Eine positive Sequenznummer ist innerhalb des Attempts eindeutig und erzeugt
eine vollständige historiesichere Ordnung.

Die Beobachtungsart ist auf das Domainenum begrenzt.

Digest und positive Dateizahl sind entweder gemeinsam vorhanden oder gemeinsam
abwesend.

Die Foundation erlaubt kein Überschreiben, keine Current-Projection und keine
Cascade-Löschung.

## Atomaritätsgrenze für den späteren Adapter

Eine Erstreservierung muss in einer Transaktion:

1. einen exakten Retry nach Reservierungs-ID erkennen;
2. aktuellen aktiven Actor, Scope und Scopeauthority prüfen;
3. dauerhafte Namensfreiheit im Scope serialisieren;
4. Attempt-ID und serverseitige UTC-Zeit intern erzeugen;
5. Attempt und initiale `reserved`-Beobachtung atomar persistieren.

Ohne Commit darf kein reserviertes Attempt und insbesondere kein Writerstart
ausgegeben werden.

Ein exakter Retry liefert dieselbe Attempt-ID ohne neue Beobachtung.

Abweichender Retry oder bereits anders belegter Name ist detailfreier
Konflikt.

## Lookupgrenze

Der spätere Lookup muss Actor, Userstatus, Scopestatus und Scopeauthority bei
jedem Aufruf aktuell aus dem System of Record lesen.

Fehlende oder inaktive Fakten ergeben neutrales `None`.

Beschädigte Historie, Lücken oder Duplikate sind detailfreie technische
Unverfügbarkeit und keine teilweise View.

Authorityentzug wirkt damit auf spätere Lookups und Reservierungen.

## Kein Observation-Write-Port

LQ-431 definiert bewusst noch keinen Port zum Anhängen von Beobachtungen.

Ein sicherer Port muss eine frische LQ-427-Reconciliation oder einen intern
kontrollierten Writer-/Cleanupausgang binden und darf kein caller-supplied
Outcome akzeptieren.

Diese Composition ist ein separater Slice.

## Migration und Downgrade

Die Revision legt vier leere Tabellen mit Primär-, Fremd-, Eindeutigkeits- und
Check-Constraints an.

Sie enthält keinen Seed, Backfill, automatischen Dateiimport oder erfundene
Historie.

Der Downgrade entfernt ausschließlich diese Tabellen in umgekehrter
Abhängigkeitsreihenfolge.

## Retention und Nichtwiederverwendung

Attempt- und Scope-/Name-Bindungen besitzen keinen regulären Löschpfad.

Sie bleiben mindestens über die gesamte Lebensdauer des Registry-Namensraums
erhalten und überdauern Manifestdatei und Beobachtungserfolg.

Die Migration legt keine konkrete Frist oder Archivstrategie fest.

Finale Manifest-Evidence bleibt weiterhin einer separaten
owner-kontrollierten Retentionentscheidung unterworfen.

## Tests

Fokussierte Tests belegen:

- repr-freie stabile IDs und begrenzte Namen;
- geschlossene Portsignaturen ohne Authority- oder Outcomeinjektion;
- linearen leeren Migrations-Head;
- dauerhafte Scope-/Name-Eindeutigkeit;
- vollständiges geordnetes Beobachtungsvokabular ohne Cascade-Löschung;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-431 implementiert keinen Adapter, Identifiergenerator, Clockzugriff,
Observationwriter, Bootstrap, Backfill, Operator, CLI, Route oder Composition.

Der Slice verändert Writer, Reconciler und Cleanup nicht und führt keinen
echten Handoff aus.

Es gibt kein CI-, Compose- oder Production-Wiring und keine Staging-, Commit-,
Build-, Signatur-, Promotion-, Publication- oder Deploymentauthority.

## Nächster Slice

LQ-432 sollte den persistenten autorisierten Reservierungs- und Lookupadapter
mit atomarem Retry, aktueller Scopeauthority und intern erzeugter Attempt-ID
implementieren.

Observation-Composition, Bestandsverankerung und finale Evidence-Retention
bleiben getrennt.
