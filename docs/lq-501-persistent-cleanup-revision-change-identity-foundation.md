# LQ-501 — Persistent Cleanup Revision Change Identity Foundation

## Ergebnis

LQ-501 ergänzt Revision `20260826_0037` als persistente Foundation für die vier
nichtwiederverwendbaren LQ-500-Change-IDs und ihre exakten
Vorgänger-/Ergebnisbindungen.

Der Slice implementiert noch keinen autorisierten Mutationsadapter.

## Notwendige Lücke

Revision 0036 speichert Revisionen und Clearances, aber keine getrennten
Change-IDs.

Ohne dauerhafte Changebindung könnte ein Prozessneustart exakte Retries nicht
von wiederverwendeten IDs mit anderem Intent unterscheiden.

In-Memory-Idempotenz genügt der LQ-499-Grenze nicht.

## Lineare Revision

Revision 0037 folgt ausschließlich auf `20260825_0036`.

Es entsteht kein Branch und kein zweiter Head.

Die Historie umfasst danach 37 lineare Migrationen.

## Vier leere Bindingtabellen

Die Migration erzeugt getrennte Tabellen für Management-, Hold-, Recovery- und
Referenzchanges.

Alle Tabellen bleiben nach der Migration leer.

Es gibt keinen Seed, Backfill oder die Adoption historischer Revisionen.

## Warum eigene Tabellen

Change-IDs werden nicht als nachträglich verpflichtende Spalten in die
Revisionstabellen eingefügt.

Damit bleibt eine Migration auch dann möglich, wenn Revision 0036 bereits
historische Zeilen enthält.

Nur zukünftige Mutationen über die kontrollierte Grenze benötigen eine
Changebindung.

## Managementchanges

`manifest_handoff_supervisor_cleanup_management_changes` bindet eine eindeutige
Change-ID an genau eine eindeutige Ergebnisrevision.

Actor-User-ID und Scope-ID sind Teil der persistenten Ergebnis- und
Vorgängerbindung.

Eine Managementrevision eines anderen Actor-/Scope-Paars kann nicht adoptiert
werden.

## Erwartete Managementrevision

`expected_revision_id` ist nullable für den erwarteten First-write-Zustand.

Ist sie vorhanden, verweist sie zusammengesetzt auf dasselbe Actor-/Scope-Paar.

Sie darf nicht der erzeugten Ergebnisrevision entsprechen.

## Holdchanges

`manifest_handoff_supervisor_cleanup_hold_changes` bindet Change-ID,
Ergebnisrevision, Directory und optional erwartete Holdrevision.

Ergebnis und Vorgänger müssen aus derselben Holdquelle und demselben Directory
stammen.

Cross-Directory-Adoption scheitert strukturell.

## Recoverychanges

Recovery besitzt eine eigene Change-Tabelle mit derselben geschlossenen
Bindungsform.

Hold- oder Referenzrevisionen können nicht als Recoveryvorgänger oder Ergebnis
verwendet werden.

Die Change-ID ist nur innerhalb ihrer eigenen Quelle interpretierbar.

## Referenzchanges

Referenzchanges binden ausschließlich Referenzrevisionen desselben Directorys.

Die Tabelle speichert keine Liste, Pfade oder Caller-Evidence.

Clear oder Blocked bleiben Eigenschaften der gebundenen Revision, nicht der
Changezeile.

## Change-ID als Primärschlüssel

Jede Change-ID ist nicht leer und Primärschlüssel ihrer Quelltabelle.

Ein exakter Retry kann dadurch höchstens eine persistente Bindingzeile finden.

Die gleiche ID kann in derselben Quelle nicht erneut einem anderen Ergebnis
zugewiesen werden.

## Ergebnisrevision eindeutig

Jede Ergebnisrevision ist innerhalb ihrer Change-Tabelle eindeutig.

Eine einzelne neu erzeugte Revision kann damit nicht als Ergebnis zweier
verschiedener Mutationsintents ausgegeben werden.

Die Revision bleibt zugleich Primärschlüssel ihres Systems of Record.

## Vorgänger ist kein Grant

Die optionale erwartete Revision speichert ausschließlich den beim Commit
verglichenen Concurrencyzustand.

Ihr Fremdschlüssel beweist Existenz und Zielbindung, aber keine aktuelle
Authority.

Der spätere Adapter muss den höchsten Zustand innerhalb derselben Transaktion
vergleichen.

## First-write bleibt fail-closed

NULL als erwartete Revision bedeutet nicht automatisch, dass ein erster Write
erlaubt ist.

Der spätere Store muss leeren Bestand und dedizierte aktuelle
Mutationsauthority gemeinsam prüfen.

Revision 0037 erzeugt keine positive erste Revision.

## Exakter Retry

Die spätere Implementation kann anhand der Changezeile Ergebnisziel,
Vorgängerrevision und vollständigen gebundenen Revisionswert rekonstruieren.

Nur vollständige Gleichheit mit dem erneut eingereichten Command ist ein
erfolgreicher Retry.

Abweichung bleibt detailfreier Mutationskonflikt.

## Atomarer Append

Neue Revisionszeile und zugehörige Changezeile müssen später in derselben
Transaktion committen.

Eine Zeile ohne die andere ist für neue LQ-500-Mutationen unzulässig.

Die Migration selbst führt keinen Append aus.

## Clearance-Idempotenz

Für Clearancecreation bleibt die nichtwiederverwendbare Attempt-ID die
Retryidentität.

Revision 0036 erzwingt bereits höchstens eine Clearance pro Attempt.

LQ-501 ergänzt deshalb keine fünfte Change-Tabelle für Clearances.

## Attempt-/Clearance-Atomarität

Die neuen Tabellen lösen nicht die gemeinsame Attempt-/Clearancetransaktion.

Der spätere Adapter muss beide bestehenden Tabellen weiterhin atomar schreiben
und alle gebundenen Revisionen aktuell revalidieren.

Ein LQ-494-Einzelattempt wird nicht nachträglich adoptiert.

## Keine Mutationauthorities

Revision 0037 erfindet keine Management-Lifecycle-, Hold-, Recovery- oder
Referenz-Mutationsauthority.

SessionPrincipal, Membership, Researchpermission und Cleanupmanagement werden
nicht als solche Authority persistiert oder umgedeutet.

Die vier autoritativen Quellen benötigen eine explizite folgende Foundation.

## Keine Callerentscheidung

Es gibt keine Rolle, Permission, Allowspalte, freie Quellart oder
caller-gelieferte Sequenz.

Change- und Revision-ID bleiben getrennte Fakten.

Zeit und Status werden weiterhin ausschließlich in der Ergebnisrevision
gespeichert.

## Keine physische Wirkung

Die Migration speichert weder Root, Leaf, Pfad, Dateinamen noch Artefaktbytes.

Sie öffnet, verändert und entfernt keine Datei oder kein Verzeichnis.

Eine Changebindung erteilt keine Cleanup-Execution-Authority.

## Downgrade

Downgrade entfernt Reference-, Recovery-, Hold- und zuletzt
Management-Changebindings.

Revisionen, Clearances, Attempts und Directoryregistry bleiben unverändert.

Ein Productiondowngrade bleibt eine separate Betriebsentscheidung.

## Gate-Synchronisierung

Der erwartete Head wird auf `20260826_0037` gesetzt.

Das operative Bundle erwartet 37 Migrationen.

Die Roadmap veröffentlicht denselben Head und dieselbe Anzahl.

## Keine Adapterimplementation

LQ-501 ergänzt keinen INSERT-, Grant-, Revoke-, Block-, Clear- oder
Clearance-Creation-Pfad.

Es gibt keine ID- oder Zeitgenerierung, Lockentscheidung oder Portänderung.

Production-Wiring und physischer Cleanup bleiben geschlossen.

## Tests

Fokussierte Prüfungen belegen lineare Revision, vier leere getrennte Tabellen,
nichtleere Change-IDs, eindeutige Ergebnisse, quell- und zielgebundene
Vorgängerrevisionen, fehlenden Backfill, rückwärts gerichteten Downgrade und
synchronisierte Headgates.

## Nächster Slice

LQ-502 sollte die getrennten persistenten Mutationsauthority-Fakten für
Management-Lifecycle, Hold, Recovery und Referenzen definieren.

Erst danach kann der autorisierte append-only Schreibadapter ohne implizite
Authorityannahme implementiert werden.
