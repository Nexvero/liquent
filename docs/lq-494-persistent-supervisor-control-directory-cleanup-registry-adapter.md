# LQ-494 — Persistent Supervisor Control-Directory Cleanup Registry Adapter

## Ergebnis

LQ-494 implementiert die Decision- und Attemptpersistenz aus LQ-493 gegen
Revision 0035.

Der Adapter verwaltet ausschließlich persistente Lifecyclefakten und führt
weder Authorityentscheidung noch Dateisystemcleanup aus.

## Interne Persistenzgrenze

Die neue Klasse ist eine Infrastrukturprimitive für spätere kontrollierte
Composition.

Sie implementiert noch nicht den LQ-492-Cleanup-Execution-Port.

Insbesondere behauptet das Speichern von `started` keine autorisierte oder
physisch ausgeführte Löschung.

## Konstruktive Abhängigkeiten

Der Adapter erhält genau eine extern besessene SQLAlchemy-Engine und optional
eine Clock.

Der Konstruktor führt kein I/O aus.

Eine injizierte Clock muss callable sein; alle gelesenen und erzeugten Zeiten
werden als aware UTC validiert.

## Decision-Append

`record_cleanup_decision` akzeptiert ausschließlich den geschlossenen
LQ-492-Decisionwert.

Vor Insert liest der Adapter die aktuelle Control-Directory-Zeile in derselben
Transaktion.

Nur ein vollständiger exakt übereinstimmender Retired-Wert darf eine Decision
erhalten.

## Kein Decision vor Retired

Unbekannte Directory-ID bleibt vor Wirkung neutral `None`.

Reserved, Active oder eine abweichende Retired-Bindung liefern den
detailfreien Cleanupkonflikt.

Der Adapter retired oder aktiviert das Directory nicht selbst.

## Append-only Sequenz

Eine neue Decision erhält die nächste positive Sequenz des Directorys.

Frühere Decisions werden weder überschrieben noch deaktiviert.

PostgreSQL serialisiert die Sequenzentscheidung über feste Tabellenlocks;
Uniqueconstraints bleiben die letzte Race-Sperre.

## Exakter Decision-Retry

Eine bereits vorhandene Decision-ID wird vollständig rekonstruiert.

Exakt derselbe Domainwert ist idempotenter Erfolg.

Eine andere Directory-, Policy-, Disposition-, Zeit- oder Retired-Bindung mit
derselben ID ist Konflikt.

## Aktueller Decision-Lookup

`resolve_control_directory_cleanup_decision` liest ausschließlich die höchste
Sequenz für eine interne Directory-ID.

Fehlt eine Decision autoritativ, liefert der Lookup neutral `None`.

Die vollständige Retired-Bindung, IDs, Disposition und Zeit werden erneut
fail-closed rekonstruiert.

## Started-Primitive

`start_cleanup_attempt` akzeptiert den geschlossenen Cleanuprequest und einen
vollständigen Decisionwert.

Der Decisionwert ist kein Caller-Allow: Der Adapter liest in derselben
Transaktion die aktuell höchste Decision erneut.

Nur exakte Gleichheit und aktuelle Disposition `eligible` erlauben den Insert.

## Authority bleibt davor

Der Startprimitive prüft bewusst keine Workspace-Membership oder
Cleanupmanagementfähigkeit.

Eine spätere Composition darf ihn ausschließlich nach aktueller
Actor-/Zielauthority aufrufen und muss Retention, Hold, Recovery und Referenzen
nochmals prüfen.

Actor-ID und persistenter User-Fremdschlüssel allein erteilen keine Authority.

## Attemptbindung

Der neue Attempt speichert unverändert Attempt-ID, Directory-ID, Actor-ID und
Decision-ID mit serverseitiger Startzeit.

Die Startzeit darf nicht vor dem gebundenen Decisionzeitpunkt liegen.

Alle späteren Zustandsfelder beginnen null.

Der Adapter erzeugt keine Attempt-ID und ersetzt keine Calleridentität.

## Exakter Start-Retry

Eine bereits vorhandene Attempt-ID wird vollständig strukturell validiert.

Exakte Directory-, Actor- und Decisionbindung liefert denselben ursprünglichen
Request unabhängig vom inzwischen vorwärtsgerichteten Attemptzustand.

Cross-Binding mit derselben Attempt-ID ist Konflikt.

## Outcome Unknown

`record_cleanup_outcome_unknown` überführt ausschließlich denselben `started`-
Attempt nach `outcome_unknown`.

Die Unknown-Zeit stammt aus der Adapterclock und darf nicht vor Start liegen.

Exakter Retry liefert dieselbe gebundene Reconciliation-Anforderung.

## Kein Blind-Retry

Nach `outcome_unknown` ist Completion direkt nicht zulässig.

Der Adapter verlangt zuerst die getrennte Reconciliationtransition.

Ein anderer Folgezustand liefert Konflikt und startet keine neue Wirkung.

## Completion

`complete_cleanup_attempt` akzeptiert nur geschlossene Attempt-ID,
Directory-ID und Cleanupoutcome.

Nur `started` darf direkt nach `completed` übergehen.

Der Adapter erzeugt serverseitig die UTC-Abschlusszeit und gibt den
geschlossenen Completed-Wert zurück.

## Completion-Retry

Ein bereits Completed-Attempt liefert den gespeicherten Completed-Wert, wenn
der angeforderte Ausgang exakt übereinstimmt.

Ein anderer Ausgang oder eine andere Directorybindung ist Konflikt.

Removed und already_absent werden nicht aus SQL oder Dateiabwesenheit
abgeleitet; eine spätere physische Composition muss sie vor dem Storeaufruf
belegen.

## Reconciliationtransition

`record_cleanup_reconciliation` akzeptiert den geschlossenen
Reconciliationrequest und genau einen der drei geschlossenen Ausgänge.

Nur `outcome_unknown` darf nach `reconciled` übergehen.

Die Reconciliationzeit ist serverseitig, aware UTC und nicht vor Unknown.

## Reconciliation-Retry

Ein bereits Reconciled-Attempt liefert den gespeicherten Wert bei exakt
demselben Ausgang.

Ein anderer Ausgang ist Konflikt.

Reconciliation führt keine zweite Completion und keine Dateioperation aus.

## Vollständiger Attempt-Lookup

`resolve_cleanup_attempt` rekonstruiert je nach Zustand genau Request,
Reconciliation-required, Completed oder Reconciled.

Unbekannte Attempt-ID liefert neutral `None`.

Freie Mappings oder interne SQL-Zeilen verlassen die Grenze nicht.

## Erneute Nullmatrixprüfung

Der Adapter vertraut nicht allein auf Checkconstraints.

Bei jedem Lookup prüft er erlaubte und verbotene optionale Felder sowie die
monotone Decision-/Start-/Unknown-/Completion-/Reconciliationzeit erneut.

Partielle oder beschädigte Persistenz ist technische Unverfügbarkeit.

## Vorwärtsgerichtete Zustände

Erlaubt sind ausschließlich:

- `started` zu `outcome_unknown`;
- `started` zu `completed`;
- `outcome_unknown` zu `reconciled`.

Es gibt kein Reset, Reopen, Retry-as-new, Recomplete oder Unreconcile.

## PostgreSQL-Serialisierung

Writes sperren Identity-User, Control-Directory, Cleanup-Decision und
Cleanup-Attempt in fester Reihenfolge mit Share-Row-Exclusive.

Damit werden Sequenz, aktuelle Decision und Attempttransition gemeinsam
serialisiert.

Der Adapter führt keine Row- oder Tabellenlöschung aus.

## SQLite-Testgrenze

SQLite bleibt ausschließlich unterstützte lokale Testgrenze.

Andere Dialekte als PostgreSQL und SQLite werden abgelehnt.

Read-only Lookups nehmen keinen PostgreSQL-Write-Lock.

## Fehlergrenze

SQL-, Lock-, Decode-, Clock-, State-, Zeit- und Strukturfehler werden über die
bestehende `ManifestHandoffRegistryUnavailable`-Grenze vereinheitlicht.

LQ-494 benennt keinen neuen technischen Exceptiontyp.

IDs, SQL und Infrastrukturdetails verlassen die Grenze nicht.

## Keine Authority

Der Adapter akzeptiert keine Session, Workspace-ID, Rolle, Permission oder
Allowentscheidung.

Der Actor im Request wird persistiert, aber nicht autorisiert.

Aktuelle Authority und Revocation bleiben Aufgabe der späteren Composition.

## Keine Datei

Der Adapter importiert weder `Path` noch `os`.

Er öffnet, inventarisiert, synchronisiert oder entfernt keine Datei.

Persistierte Outcomes sind keine selbst erzeugten physischen Beweise.

## Kein Schema oder Wiring

Revision 0035 bleibt unverändert; LQ-494 ergänzt keine Migration.

Head bleibt `20260825_0035` mit 35 linearen Migrationen.

Es gibt kein Service-, CLI-, Route-, Operator-, Compose-, Environment- oder
Production-Wiring.

## Tests

Fokussierte Prüfungen belegen Decision-Append/Lookup, Retiredbindung,
Sequenzierung, aktuelle Eligible-Prüfung, Startretry, drei vorwärtsgerichtete
Transitionen, vollständige Rekonstruktion, Nullmatrix-/UTC-Prüfung, Locks und
fehlende Datei-/Authoritymacht.

## Nächster Slice

LQ-495 sollte die aktuelle Retention-, Hold-, Recovery-, Referenz- und
Cleanupmanagement-Authorityauflösung vor dem Attemptstart definieren.

Physischer Cleanup und Production-Wiring folgen getrennt.
