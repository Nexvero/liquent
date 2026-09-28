# LQ-493 — Persistent Supervisor Control-Directory Cleanup Foundation

## Ergebnis

LQ-493 ergänzt Revision `20260825_0035` als persistente Foundation für die
geschlossenen LQ-492-Cleanupwerte.

Die Revision erzeugt genau eine leere Decision- und eine leere Attempttabelle.

## Lineare Revision

Revision 0035 folgt ausschließlich auf `20260825_0034`.

Es entsteht kein Branch und kein zweiter Head.

Die Historie umfasst danach 35 lineare Migrationen.

## Keine Bestandsadoption

Beide Tabellen bleiben nach Migration leer.

Vorhandene Retired-Directories erhalten weder eine automatische
Retentionentscheidung noch einen Cleanupattempt.

Es gibt keinen Seed, Backfill oder Filesystemscan.

## Decisiontabelle

`manifest_handoff_supervisor_control_cleanup_decisions` speichert
append-only Retentionentscheidungen pro Directory.

Jede Decision besitzt eine global stabile nichtleere Decision-ID als
Primärschlüssel.

Die Tabelle speichert keine Actorauthority und keine physische Behauptung.

## Directorybindung

Jede Decision verweist auf eine bestehende dauerhafte Control-Directory-ID.

Der Fremdschlüssel erlaubt keine Decision für eine unbekannte Registrybindung.

Ob der aktuelle Lifecycle Retired ist, bleibt eine aktuelle Adapterprüfung,
weil ein Checkconstraint keinen fremden Tabellenzustand autoritativ prüfen
kann.

## Sequenz

`sequence_number` ist pro Directory eindeutig und strikt positiv.

Damit kann eine spätere Readgrenze die höchste vollständige Decision
deterministisch bestimmen.

Eine neue Decision überschreibt keine frühere Retentiongeschichte.

## Policyrevision

Jede Decision bindet eine nichtleere stabile Policyrevision.

Die Foundation interpretiert keine Dauer, Policy oder lokale Uhrzeitregel.

Policyrevision und Decision-ID bleiben verschiedene Fakten.

## Disposition

Die persistente Disposition ist auf `retain` oder `eligible` geschlossen.

Es gibt keinen freien Status, Boolean oder Rollenwert.

`eligible` bleibt ein Retentionfakt und erteilt keine Cleanupauthority.

## Entscheidungszeit

`decided_at` ist immer vorhanden und wird später als aware UTC rekonstruiert.

Die Domain verlangt eine Zeit nicht vor Retirement.

Diese tabellenübergreifende Ordnung wird später zusätzlich fail-closed
validiert.

## Zusammengesetzte Decisionbindung

Decision-ID und Directory-ID sind gemeinsam eindeutig adressierbar.

Diese Bindung dient dem zusammengesetzten Attempt-Fremdschlüssel.

Ein Attempt kann dadurch keine gültige Decision eines anderen Directorys
verwenden.

## Attempttabelle

`manifest_handoff_supervisor_control_cleanup_attempts` hält genau eine
vollständige Lifecyclezeile pro Cleanup-Attempt-ID.

Die Attempt-ID ist Primärschlüssel und wird nicht wiederverwendet.

Es gibt keine freie Event-, Dateinamen- oder Inventurtabelle.

## Actorbindung

Jeder Attempt bindet einen bestehenden persistenten User als Actor.

Der Fremdschlüssel belegt nur Identität, nicht Aktivität, Membership,
Managementfähigkeit oder Cleanupauthority.

Diese Fakten müssen vor späterer Wirkung aktuell aus ihren Systemen of Record
aufgelöst werden.

## Attempt-Decision-Bindung

Jeder Attempt trägt Decision-ID und Directory-ID in einem zusammengesetzten
Fremdschlüssel.

Damit bleiben Ziel und verwendeter Retentionfakt dauerhaft korreliert.

Die Foundation behauptet nicht, dass die Decision beim späteren Effekt noch
aktuell oder `eligible` ist.

## Started

`started` verlangt ausschließlich die Startzeit.

Unknown-, Completion- und Reconciliationfelder müssen null sein.

Started behauptet noch keine physische Wirkung.

## Outcome Unknown

`outcome_unknown` verlangt eine Unknown-Zeit nicht vor der Startzeit.

Completion und Reconciliation bleiben in diesem Zustand null.

Die Zeile bindet unklare mögliche Wirkung dauerhaft an denselben Attempt.

## Completed

`completed` verlangt genau `removed` oder `already_absent` und eine
Completionzeit nicht vor Start.

Unknown- und Reconciliationfelder bleiben null.

Ein technischer Fehler kann nicht als freier Completed-Ausgang gespeichert
werden.

## Reconciled

`reconciled` verlangt einen vorherigen Unknown-Zeitpunkt, genau `absent`,
`present` oder `conflict` und eine Reconciliationzeit nicht vor Unknown.

Completed-Felder bleiben null.

Reconciliation ist eine Klassifikation und keine zweite Löschbehauptung.

## Geschlossene Nullmatrix

Ein Checkconstraint bindet jeden der vier Zustände an exakt seine zulässigen
optionalen Werte.

Partielle Completed-, Unknown- oder Reconciliationkombinationen sind
unzulässig.

State und Outcome können nicht unabhängig frei kombiniert werden.

## Ein unresolved Attempt

Ein partieller Unique-Index erlaubt pro Directory höchstens einen Attempt in
`started` oder `outcome_unknown`.

Ein zweiter paralleler unaufgelöster Mutationsversuch ist damit gesperrt.

Nach einem terminalen Completed oder Reconciled kann eine spätere
Composition nur unter neuen aktuellen Entscheidungen einen neuen Attempt
prüfen.

## Keine Wiederverwendung

Decision- und Attempt-Primärschlüssel bilden die dauerhafte Untergrenze gegen
ID-Wiederverwendung.

Die Migration definiert keinen Deletepfad.

Physischer Cleanup löscht diese Registryfakten später nicht.

## Keine Authoritytabelle

LQ-493 ergänzt keine Cleanup-Rolle, Membership oder Allowspalte.

Actor-ID, Retentionentscheidung und Directorybindung erteilen keine
Managementfähigkeit.

Aktuelle Authority bleibt eine getrennte spätere Resolverentscheidung.

## Keine Hold- oder Recoveryquelle

Die Foundation speichert keine Legal-Hold-, Investigation-, Recovery- oder
Referenzfreigabe.

Abwesenheit solcher Spalten bedeutet nicht, dass diese Voraussetzungen erfüllt
sind.

Sie müssen vor physischer Wirkung separat fail-closed aufgelöst werden.

## Keine Pfad- oder Artefaktdaten

Die Tabellen speichern weder Root, Leafkopie, Pfad, Dateinamen, Inode,
Eigentümer, Modus, Bytes noch Digest.

Leaf und Lifecycle bleiben in der bestehenden Directoryregistry.

Physische und Artefaktfakten werden nicht durch SQL erfunden.

## Kein Mutationsergebnis vor Adapter

Die Migration schreibt keine Zeile und führt keine Transition aus.

Sie entscheidet nicht, wann `started`, `outcome_unknown`, `completed` oder
`reconciled` gesetzt werden dürfen.

Der persistente Adapter folgt separat.

## Downgrade

Downgrade entfernt zuerst den partiellen Index, danach Attempt- und zuletzt
Decisiontabelle.

Die Control-Directory-Registry aus Revision 0034 bleibt unverändert.

Productiondowngrade bleibt eine separate Betriebsentscheidung.

## Gate-Synchronisierung

Der erwartete Head wird auf `20260825_0035` gesetzt.

Das operative Bundle erwartet 35 Migrationen.

Die Roadmap veröffentlicht denselben Head und dieselbe Anzahl.

## Keine Adapter- oder Dateiwirkung

LQ-493 implementiert keinen Decisionlookup, Attemptstore,
Reconciliationadapter, Retentionresolver oder Filesystemcleanup.

Es wird keine Datei geöffnet, verändert oder entfernt.

Kein technischer Exceptiontyp wird ergänzt.

## Kein Wiring

Service-Facade, Settings, Appfactory, CLI, Route, Operator, Compose,
Environment und Deployment bleiben unverändert.

Productioncleanup bleibt geschlossen.

## Tests

Fokussierte Prüfungen belegen lineare Revision, zwei leere Tabellen,
Decisionsequenz, geschlossene Disposition, zusammengesetzte Directorybindung,
Actor-FK, Attemptzustands-/Nullmatrix, monotone Zeiten, einen unresolved
Attempt pro Directory, fehlende Authority-/Pfadspalten und synchronisierte
Headgates.

## Nächster Slice

LQ-494 sollte die persistenten Decision-, Attempt-, Completion- und
Reconciliationmethoden gegen Revision 0035 implementieren.

Aktuelle Retention-/Authorityresolver, physische Löschung und
Production-Wiring folgen getrennt.
