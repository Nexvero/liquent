# LQ-572 — Central SQLite Foreign-key Test Adoption Completion Audit

## Ergebnis

LQ-572 schließt den Testadoptionsstrang LQ-569 bis LQ-572 ab.

Alle 16 zuvor redundanten Testmodule beziehen SQLite-Fremdschlüsselaktivierung
nur noch aus der zentralen Enginefactory. Keine Produktionsdatei wurde in
diesem Strang verändert.

## Fokussierter Nachweis

Der kombinierte Fokuslauf besteht mit 269 Tests. Er umfasst den statischen
Adoptionsguard, alle 16 bereinigten Module und die direkte zentrale
LQ-558-Listenerregression.

Der Lauf behandelt `DeprecationWarning` mit
`-W error::DeprecationWarning` als Fehler und endet ohne Warnung.

## Vollständige normale Suite

Die normale Suite besteht mit 5085 Tests und einem erwarteten Skip. 105
PostgreSQL-Integrationstests sind ausdrücklich abgewählt und separat
verpflichtend ausgeführt.

Es gibt keine Warning Summary.

## Vollständige PostgreSQL-Suite

Alle 105 `postgres_integration`-Tests bestehen gegen eine isolierte lokale
PostgreSQL-16-Instanz. 5086 nicht zu diesem Lauf gehörende Tests sind
abgewählt.

Die reine SQLite-Testbereinigung verändert damit weder PostgreSQL-Migrationen
noch serverseitige Constraint- oder Konkurrenzsemantik.

## Wheel-Nachweis

Wheel `liquent-0.0.1-py3-none-any.whl` wurde ohne Buildisolation erfolgreich
außerhalb des Worktrees erzeugt.

Direkt aus dem Wheel wurde eine `sqlite://`-Engine gebaut. Ein angelegter
Kinddatensatz ohne Elternschlüssel wurde ohne testlokalen Listener als
`IntegrityError` abgewiesen.

## Inventar und Migration

Quelle und Wheel stimmen bei 68 Console Entry Points und 69 Operator-Dateien
überein. Der Bestand bleibt bei 42 Migrationen und Head `20260826_0042`.

Die erzeugten Verzeichnisse `build/` und `src/liquent.egg-info/` wurden nach
dem Paketnachweis gezielt entfernt. Das Wheel verbleibt außerhalb des
Worktrees.

## Diff- und Scope-Audit

`git diff --check` ist sauber.

Der Strang entfernt ausschließlich 16 redundante Listenerblöcke und ihre
unbenutzten Eventimports. Er ergänzt Dokumentation und einen statischen
Adoptionsguard, aber keine Produktionssemantik.

Es gibt keine Migration, Tabelle, Constraintdefinition, Portsignatur, Route,
CLI, Entry-Point-, Commit-, Push-, Release- oder Deploymentwirkung.

## Abschluss

Für den zentralen SQLite-Fremdschlüssel-Testadoptionsstrang LQ-569 bis LQ-572
ist kein weiterer Slice erforderlich.

Neue SQLite-Persistenztests sollen `build_engine` verwenden und dürfen die
zentrale Verbindungsvorbereitung nicht durch lokale Listener überdecken.
