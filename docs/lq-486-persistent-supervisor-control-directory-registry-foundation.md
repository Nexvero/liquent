# LQ-486 — Persistent Supervisor Control-Directory Registry Foundation

## Ergebnis

LQ-486 ergänzt Revision `20260825_0034` als persistente Foundation des
LQ-484/LQ-485-Control-Directory-Lifecycles.

Die Revision erzeugt genau eine leere Registrytabelle.

## Lineare Revision

Revision 0034 folgt ausschließlich auf `20260825_0033`.

Es entsteht kein Branch und kein zweiter Head.

Die Historie umfasst danach 34 lineare Migrationen.

## Registrytabelle

`manifest_handoff_supervisor_control_directories` hält genau eine vollständige
Lifecyclezeile pro Directory-ID.

Es gibt keine Event-, Pfad-, Cleanup- oder Aliasnebentabelle.

Die Tabelle bleibt nach Migration leer.

## Directory-ID

`directory_id` ist ein nichtleerer LargeBinary-Primärschlüssel.

Die Registry kann dieselbe ID nicht erneut anlegen oder umwidmen.

Ein späteres Retirement entfernt den Primärschlüssel nicht.

## Handlebindung

`handle_id` ist nicht null, global eindeutig und verweist auf einen bestehenden
Supervisor-Journaljob.

Damit besitzt jeder Job höchstens eine Registrybindung und jedes Directory
genau einen Job.

Cross-Handle-Adoption ist auf Schemaebene ausgeschlossen.

## Opaques Leaf

`leaf` ist nicht null, exakt 64 Zeichen lang, kleingeschrieben und global
eindeutig.

Die Spalte speichert kein Root und keinen Pfadseparatorvertrag.

Die spätere Domain-/Adaptergrenze validiert zusätzlich die geschlossene
Hexform.

## Warum kein Pfad gespeichert wird

Das process-eigene Root bleibt konstruktive Runtimeconfiguration.

Die Registry bindet nur ein opakes Leaf innerhalb dieses Roots.

Absolute oder relative Hostpfade würden Deploymentdetails persistieren und
unsichere Adoption erleichtern.

## Zustandswert

`state` akzeptiert ausschließlich `reserved`, `active` oder `retired`.

Unbekannte, freie oder rückwärtsgerichtete Zustände können nicht gespeichert
werden.

Transitionen werden später durch den Adapter zusätzlich serialisiert.

## Reserved-Zeit

`reserved_at` ist immer vorhanden und entsteht genau einmal bei der
dauerhaften ID-/Handle-/Leafreservation.

Retry darf sie nicht ersetzen.

## Activated-Zeit

`activated_at` ist in Reserved null und in Active oder Retired zwingend
vorhanden.

Wenn vorhanden, darf sie nicht vor `reserved_at` liegen.

Sie wird bei Retirement nicht verändert.

## Retired-Zeit

`retired_at` ist ausschließlich in Retired vorhanden.

Sie darf nicht vor `activated_at` liegen.

Die Zeile bleibt nach Retirement erhalten.

## Geschlossene Nullmatrix

Reserved verlangt beide späteren Zeiten null.

Active verlangt Activated gesetzt und Retired null.

Retired verlangt beide Zeiten gesetzt.

Partielle Kombinationen scheitern am Checkconstraint.

## Nichtwiederverwendung

Primärschlüssel und Uniqueconstraints bilden die dauerhafte Untergrenze gegen
Directory-, Handle- und Leaf-Wiederverwendung.

Die Migration definiert keinen Deletepfad.

Spätere Retention darf diese Nichtwiederverwendungsinvariante nicht aufheben.

## Keine physische Behauptung

Eine Reserved- oder Active-Zeile enthält keinen Eigentümer-, Modus-, inode-,
Symlink-, fsync- oder Existenzbeweis.

Physische Fakten bleiben Sache des späteren Filesystemadapters.

Active darf erst durch die Lifecyclecomposition nach sicherer Anlage gesetzt
werden.

## Keine Authority

Die Tabelle enthält keine User-ID, Workspace-ID, Session, Rolle, Permission
oder Allowentscheidung.

Directory-, Handle- und Leafwerte erteilen keine Supervisorfähigkeit.

Authority bleibt vor späteren Lifecyclemutationen.

## Kein Seed oder Backfill

Die Migration erzeugt keine Registryzeile und adoptiert keinen vorhandenen
Filesystembestand.

Bestehende Runtime-Control-Directory-IDs werden nicht automatisch gebunden.

Production bleibt geschlossen, bis kontrollierte neue Lifecycles existieren.

## Downgrade

Downgrade entfernt ausschließlich die neue Registrytabelle.

Es verändert keine Journal-, Runtime-, Gate- oder Artefakttabelle.

Productiondowngrade bleibt eine separate Betriebsentscheidung.

## Gate-Synchronisierung

Der erwartete Head wird auf `20260825_0034` gesetzt.

Das operative Bundle erwartet 34 Migrationen.

Die Roadmap veröffentlicht denselben Head und dieselbe Anzahl.

## Keine Adapterimplementation

LQ-486 implementiert keinen Store-/Lookupport, Leafgenerator,
Filesystemadapter, Resolver oder Lifecyclecomposer.

Es gibt kein CLI-, Route-, Operator-, Compose- oder Production-Wiring.

## Tests

Fokussierte Prüfungen belegen lineare Revision, leere Einzeltabelle,
PK-/Unique-/FK-Bindungen, geschlossene State-/Zeitmatrix, monotone Zeiten,
fehlende Pfad-/Authorityspalten und synchronisierte Headgates.

## Nächster Slice

LQ-487 sollte den persistenten Registryadapter mit internem sicherem
Leafgenerator, exaktem Reservationretry, vorwärtsgerichteten Transitionen und
vollständigen Lookups implementieren.

Filesystemanlage und Active-Composition folgen danach getrennt.
