# LQ-560 — SQLite Foreign-key Enforcement Completion Audit

## Ergebnis

LQ-560 schließt den gebündelten Wartungsstrang LQ-557 bis LQ-560 ab.

Jede von der zentralen Factory geöffnete SQLite-Verbindung aktiviert nun
deklarierte Fremdschlüssel. In-Memory-, Datei-, Reconnect-, PostgreSQL- und
Paketgrenzen sind vollständig grün geprüft.

## Fokussierter Nachweis

Der kombinierte Fokuslauf besteht mit 42 Tests. Er umfasst Vertrag,
Enginekonfiguration, tatsächliche Constraintabweisung, Reconnect,
Fehlerressourcen, bestehende lokal aktivierende Persistenzbereiche und das
Migrationsgate.

`DeprecationWarning` wird mit `-W error::DeprecationWarning` als Fehler
behandelt. Der Lauf endet ohne Warnung.

## Vollständige normale Suite

Die normale Suite besteht mit 5051 Tests und einem erwarteten Skip. 105
PostgreSQL-Integrationstests sind ausdrücklich abgewählt und separat
verpflichtend ausgeführt.

Der Lauf endet unter derselben strikten Warning-Grenze ohne Warning Summary.

## Vollständige PostgreSQL-Suite

Alle 105 `postgres_integration`-Tests bestehen gegen eine isolierte lokale
PostgreSQL-16-Instanz. 5052 nicht zu diesem Lauf gehörende Tests sind
abgewählt.

Die zentrale Factory registriert in diesem Dialekt keinen SQLite-Listener.
Pool-, Timeout-, Migrations- und serverseitige Constraintsemantik bleiben
unverändert.

## Wheel-Nachweis

Wheel `liquent-0.0.1-py3-none-any.whl` wurde ohne Buildisolation erfolgreich
außerhalb des Worktrees erzeugt.

Direkt aus dem Wheel wurde eine `sqlite://`-Engine gebaut. Sie meldete
`PRAGMA foreign_keys=1` und wies einen tatsächlichen Kinddatensatz ohne
Elternschlüssel mit `IntegrityError` ab.

## Inventar und Migration

Quelle und Wheel stimmen bei 68 Console Entry Points und 69 Operator-Dateien
überein. Der Bestand bleibt bei 42 Migrationen und Head `20260826_0042`.

Die vom Wheel-Bau erzeugten Verzeichnisse `build/` und
`src/liquent.egg-info/` wurden gezielt entfernt. Das Wheel verbleibt außerhalb
des Worktrees.

## Diff- und Scope-Audit

`git diff --check` ist sauber.

Der Strang verändert nur die zentrale SQLite-Verbindungsvorbereitung und
ergänzt fokussierte Regressionen sowie vier Dokumentationsslices. Bestehende
testlokale idempotente Aktivierungen bleiben unangetastet.

Es gibt keine Migration, Tabelle, Constraintdefinition, Portsignatur, Route,
CLI, Entry-Point-, Commit-, Push-, Release- oder Deploymentwirkung.

## Abschluss

Für den SQLite-Fremdschlüssel-Wartungsstrang LQ-557 bis LQ-560 ist kein
weiterer Slice erforderlich.

Eine spätere Entfernung redundanter testlokaler Listener wäre reine
Testbereinigung und ist keine Voraussetzung für das Laufzeitverhalten.
