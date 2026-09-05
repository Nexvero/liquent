# LQ-497 — Persistent Supervisor Control-Directory Cleanup Clearance Foundation

## Ergebnis

LQ-497 ergänzt Revision `20260825_0036` als persistente Foundation für die
geschlossenen LQ-496-Management- und Clearancefakten.

Die Revision erzeugt vier leere Revisionsquellen und eine leere
Clearancetabelle.

## Lineare Revision

Revision 0036 folgt ausschließlich auf `20260825_0035`.

Es entsteht kein Branch und kein zweiter Head.

Die Historie umfasst danach 36 lineare Migrationen.

## Keine Bestandsadoption

Alle fünf Tabellen bleiben nach Migration leer.

Bestehende Retired-Directories, Decisions und Attempts erhalten keine
automatische Authority, Clear-Disposition oder Clearance.

Es gibt keinen Seed, Backfill, Bootstrap oder Filesystemscan.

## Managementrevisionen

`manifest_handoff_supervisor_cleanup_management_revisions` hält append-only
Cleanupmanagementzustände.

Jede Revision besitzt eine globale stabile nichtleere Revision-ID als
Primärschlüssel.

Die Tabelle ist von bestehenden Registry- und Recoveryauthorities getrennt.

## Actor-/Scopebindung

Jede Managementrevision verweist auf genau einen persistenten User und einen
persistenten Manifest-Handoff-Scope.

Actor und Scope sind gemeinsam mit der Revision eindeutig adressierbar.

Ein Scopefremder Managementfakt kann dadurch keine Clearance desselben Actors
speisen.

## Managementsequenz

`sequence_number` ist für jedes Actor-/Scope-Paar eindeutig und positiv.

Ein späterer Lookup kann den höchsten vollständigen Zustand deterministisch
bestimmen.

Eine neue Revision überschreibt oder löscht keine frühere Authoritygeschichte.

## Managementstatus

Der persistente Status ist auf `active` oder `inactive` geschlossen.

Es gibt keine Rolle, Permission oder Allowspalte.

Active bleibt scopegebundene Cleanupmanagementfähigkeit und keine allgemeine
Membership.

## Managementzeit

`resolved_at` ist für jede Revision vorhanden.

Der spätere Adapter rekonstruiert sie als aware UTC.

Die Zeit erzeugt keine Authority und ersetzt keine Revision.

## Drei Zielrevisionsquellen

Hold, Recovery und Referenzen besitzen getrennte append-only Tabellen:

- `manifest_handoff_supervisor_cleanup_hold_revisions`;
- `manifest_handoff_supervisor_cleanup_recovery_revisions`;
- `manifest_handoff_supervisor_cleanup_reference_revisions`.

Ihre IDs, Sequenzen und Entscheidungen sind nicht austauschbar.

## Directorybindung

Jede Zielrevision verweist auf eine bestehende dauerhafte Control-Directory-ID.

Revision-ID und Directory-ID sind gemeinsam eindeutig adressierbar.

Die physische Existenz des Leafs wird nicht in SQL behauptet.

## Zielsequenz

Jede der drei Quellen besitzt eine positive, pro Directory eindeutige Sequenz.

Der spätere Lookup verwendet ausschließlich die höchste vollständige Revision
seiner eigenen Quelle.

Eine Holdsequenz ordnet keine Recovery- oder Referenzrevision.

## Clear oder Blocked

Alle drei Dispositionen sind auf `clear` oder `blocked` geschlossen.

Blocked bleibt ein dauerhafter historischer Fakt und wird nicht überschrieben.

Fehlende Zeilen bedeuten unbekannt und niemals implizit Clear.

## Zielentscheidungszeit

`decided_at` ist in allen drei Quellen zwingend vorhanden.

Der spätere Adapter prüft aware UTC und die Ordnung zur Retirementzeit erneut.

Die Migration berechnet keine lokale Frist.

## Clearancetabelle

`manifest_handoff_supervisor_cleanup_clearances` hält immutable aggregierte
Clearancebindungen.

`clearance_id` ist ein global stabiler nichtleerer Primärschlüssel.

Die Tabelle besitzt keinen Status und keine nachträgliche Mutation.

## Genau eine Clearance pro Attempt

`attempt_id` ist in der Clearancetabelle global eindeutig und verweist auf
einen bestehenden LQ-493-Cleanupattempt.

Ein Attempt kann nicht mit zwei Clearance-IDs oder zwei Evidenzsätzen starten.

Ein neuer fachlicher Versuch benötigt eine neue Attempt-ID.

## Retentiondecision und Directory

Decision-ID und Directory-ID bilden einen zusammengesetzten Fremdschlüssel zur
LQ-493-Decisiontabelle.

Eine Retentionentscheidung eines anderen Directorys kann nicht gebunden
werden.

Die Foundation erzwingt nicht allein, dass diese Decision die höchste oder
Eligible ist; das bleibt aktuelle Adapterprüfung.

## Managementrevision, Actor und Scope

Managementrevision-ID, Actor-User-ID und Scope-ID bilden einen
zusammengesetzten Fremdschlüssel.

Damit kann eine Revision weder einem anderen Actor noch einem anderen Scope
zugeordnet werden.

Die Foundation erzwingt nicht allein, dass die Revision noch aktuell und
Active ist.

## Holdrevision und Directory

Holdrevision-ID und Directory-ID bilden einen zusammengesetzten Fremdschlüssel
zur Holdquelle.

Cross-Directory-Holdclearance ist strukturell ausgeschlossen.

Die gleiche Form gilt getrennt für Recovery und Referenzen.

## Terminal-Observation

Jede Clearance verweist auf eine persistente Supervisor-Terminal-Observation.

Der Fremdschlüssel verhindert erfundene Terminal-IDs.

Die vollständige Journalterminalität sowie Handle- und Scopekonsistenz bleiben
zusätzliche fail-closed Adapterprüfungen.

## Clearancezeit

`cleared_at` ist immer vorhanden.

Der spätere Adapter verlangt aware UTC und eine Zeit nicht vor allen gebundenen
Entscheidungen.

Eine Zeit allein macht Blocked oder Inactive nicht positiv.

## Warum keine Outcomespalte

Eine Clearancezeile repräsentiert ausschließlich eine positive vollständige
Aggregation.

Inactive, Retain und Blocked werden nicht als Clearance gespeichert.

Fachliche Ablehnung bleibt außerhalb der Tabelle detailfrei.

## Kein Caller-Snapshot

Die Tabellen speichern autoritative Revisionen, nicht ein Caller-geliefertes
Evidence-Dict.

Der spätere Adapter muss jede Revision aus ihrem System of Record lesen und
aktuell vergleichen.

Es gibt keine JSON-, Payload- oder Boolean-Allowspalte.

## Attemptbindung ohne Wirkungsbehauptung

Der FK zu einem Cleanupattempt belegt nur die persistente Beziehung.

Er behauptet weder erfolgte Dateioperation noch Completed-Ausgang.

`started` bleibt gemäß LQ-494 vor physischer Wirkung revalidierungspflichtig.

## Revocation

Eine spätere Inactive-, Blocked- oder sonstige neue höhere Revision löscht eine
ältere Clearance nicht.

Sie sperrt aber jede spätere noch nicht erfolgte Wirkung bei aktueller
Revalidierung.

Clearancehistory ist kein stale Fortsetzungsrecht.

## Nichtwiederverwendung

Alle Revisions- und Clearance-Primärschlüssel bleiben dauerhaft gebunden.

Die Migration definiert keinen Deletepfad.

Physischer Cleanup entfernt keine dieser Tabellenzeilen.

## Keine Pfad- oder Artefaktbytes

Die Tabellen speichern weder Root, Leaf, Pfad, Dateinamen, Inode, Modus,
Eigentümer, Bytes noch Digest.

Directory- und Artefaktfakten bleiben in ihren bestehenden Systemen of Record.

Die Foundation führt keine Inventur durch.

## Keine Policy- oder Holdberechnung

Revision 0036 erzeugt keine Management-, Hold-, Recovery- oder
Referenzentscheidung.

Sie berechnet nichts aus Zeit, Kosten, Speicher oder Prozesszustand.

Die jeweiligen autorisierten Mutationsgrenzen folgen separat.

## Downgrade

Downgrade entfernt zuerst die Clearancetabelle, danach Reference-, Recovery-,
Hold- und zuletzt Managementrevisionen.

Cleanupattempts, Decisions und Control-Directory-Registry bleiben
unverändert.

Productiondowngrade bleibt eine eigene Betriebsentscheidung.

## Gate-Synchronisierung

Der erwartete Head wird auf `20260825_0036` gesetzt.

Das operative Bundle erwartet 36 Migrationen.

Die Roadmap veröffentlicht denselben Head und dieselbe Anzahl.

## Keine Adapterimplementation

LQ-497 implementiert keinen Management-, Hold-, Recovery-, Referenz- oder
aggregierten Clearance-Resolver.

Es gibt keinen Grant/Revoke-, Decisionappend- oder Attemptstartadapter.

Kein technischer Exceptiontyp wird ergänzt.

## Keine Datei oder Wiring

Es wird keine Datei geöffnet, verändert oder entfernt.

Service-Facade, Settings, Appfactory, CLI, Route, Operator, Compose,
Environment und Deployment bleiben unverändert.

Productioncleanup bleibt geschlossen.

## Tests

Fokussierte Prüfungen belegen lineare Revision, fünf leere Tabellen,
Actor-/Scope- und Directorysequenzen, geschlossene Statuswerte,
zusammengesetzte Cross-Target-Sperren, genau eine Clearance pro Attempt,
Terminal-FK, fehlende Pfad-/Allowspalten und synchronisierte Headgates.

## Nächster Slice

LQ-498 sollte den persistenten Management-, Hold-, Recovery-, Referenz- und
aggregierten Clearanceadapter gegen Revision 0036 implementieren.

Physischer Cleanup und Production-Wiring folgen getrennt.
