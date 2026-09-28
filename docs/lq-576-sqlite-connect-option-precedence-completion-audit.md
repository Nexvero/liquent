# LQ-576 — SQLite Connect-option Precedence Completion Audit

## Ergebnis

LQ-576 schließt den Engine-Härtungsstrang LQ-573 bis LQ-576 ab.

Dateibasierte und In-Memory-SQLite-Verbindungen verwenden zentral fünf
Sekunden DBAPI-/Busy-Timeout. Caller-supplied URL-Werte überschreiben weder
diesen Timeout noch den In-Memory-Threadvertrag.

## Fokussierter Nachweis

Der kombinierte Fokuslauf besteht mit 35 Tests. Er umfasst tatsächlichen
Busy-Timeout, Factoryoptionen, URL-Priorität, Threadzugriff, Pooling,
Fremdschlüssel, Treiber und Migration.

`DeprecationWarning` wird mit `-W error::DeprecationWarning` als Fehler
behandelt. Der Lauf endet ohne Warnung.

## Vollständige normale Suite

Die normale Suite besteht mit 5095 Tests und einem erwarteten Skip. 105
PostgreSQL-Integrationstests sind ausdrücklich abgewählt und separat
verpflichtend ausgeführt.

Es gibt keine Warning Summary.

## Vollständige PostgreSQL-Suite

Alle 105 `postgres_integration`-Tests bestehen gegen eine isolierte lokale
PostgreSQL-16-Instanz. 5096 nicht zu diesem Lauf gehörende Tests sind
abgewählt.

PostgreSQL bleibt damit getrennt bei Psycopg und dem zentralen
`connect_timeout=3`; keine SQLite-Option gelangt in den realen Pfad.

## Wheel-Nachweis

Wheel `liquent-0.0.1-py3-none-any.whl` wurde ohne Buildisolation erfolgreich
außerhalb des Worktrees erzeugt.

Direkt aus dem Wheel wurde eine In-Memory-SQLite-Engine mit den
caller-supplied URL-Werten `timeout=0.001` und `check_same_thread=true`
gebaut. Die tatsächliche Verbindung meldete dennoch
`PRAGMA busy_timeout=5000`.

## Inventar und Migration

Quelle und Wheel stimmen bei 68 Console Entry Points und 69 Operator-Dateien
überein. Der Bestand bleibt bei 42 Migrationen und Head `20260826_0042`.

Die erzeugten Verzeichnisse `build/` und `src/liquent.egg-info/` wurden nach
dem Paketnachweis gezielt entfernt. Das Wheel verbleibt außerhalb des
Worktrees.

## Diff- und Scope-Audit

`git diff --check` ist sauber.

Der Strang ergänzt nur explizite SQLite-Connect-Argumente, fokussierte
Regressionen und vier Dokumentationsslices. Er ergänzt keine dynamische
Konfiguration, Retry- oder Locklogik.

Es gibt keine Migration, Tabelle, Portsignatur, Route, CLI, Entry-Point-,
Commit-, Push-, Release- oder Deploymentwirkung.

## Abschluss

Für den SQLite-Connect-Option-Härtungsstrang LQ-573 bis LQ-576 ist kein
weiterer Slice erforderlich.

Eine spätere konfigurierbare Timeoutpolicy wäre ein eigener Vertrag und darf
nicht still über URL-Queryparameter eingeführt werden.
