# LQ-552 — Warning-free Python 3.12 Persistence Completion Audit

## Ergebnis

LQ-552 schließt den gebündelten Wartungsstrang LQ-549 bis LQ-552 ab.

Die Python-3.12-SQLite-Datetime-Deprecation ist durch explizite Adapter
beseitigt. Normale und PostgreSQL-Suite bestehen mit als Fehler behandelten
DeprecationWarnings.

## Strikte normale Suite

Die vollständige normale Suite besteht mit 5032 Tests und einem erwarteten
Skip.

105 PostgreSQL-markierte Tests sind in diesem Lauf ausdrücklich abgewählt und
separat ausgeführt.

`DeprecationWarning` ist über `-W error::DeprecationWarning` ein Fehler. Der
Lauf endet ohne Warning Summary und ohne die zuvor 789 SQLite-Datetime-
Warnungen.

## Strikte PostgreSQL-Suite

Die vollständige PostgreSQL-Suite besteht mit 105 Tests unter derselben
DeprecationWarning-Fehlergrenze.

PostgreSQL verwendet weiterhin unveränderte Psycopg-/SQLAlchemy-Adapter. Der
Lauf belegt zugleich isolierte Datenbanken und Migration bis Head
`20260826_0042`.

## Wheel

Wheel `liquent-0.0.1-py3-none-any.whl` wurde ohne Buildisolation erfolgreich
aus dem aktuellen Worktree erzeugt.

Direkter Import aus dem Wheel bestätigt `liquent`, `liquent_platform` und den
SQLite-Engineaufbau mit expliziten Adaptern über eine temporäre dateibasierte
SQLite-URL.

Die Wheelinspektion bestätigt 68 Entry Points, 69 Operator-Dateien, 42
Migrationen und Head `20260826_0042`.

Das Wheel verbleibt außerhalb des Worktrees. Erzeugte `build/`- und
`src/liquent.egg-info/`-Zwischenprodukte wurden gezielt entfernt.

## Semantik-Audit

Die expliziten Adapter serialisieren nur ISO-Text und bewahren Offset sowie
Mikrosekunden.

Sie ergänzen keine Zeitzone, konvertieren nicht nach UTC und runden nicht.
Fachliche UTC-Prüfungen in den Persistenzadaptern bleiben unverändert.

Kein SQLite-Converter oder `detect_types` verändert die SQLAlchemy-
Resultverarbeitung.

## Inventar und Diff

Der Quellbestand bleibt bei 68 Console Entry Points, 69 Operator-Dateien und
42 Migrationen.

`git diff --check` ist sauber. Im Worktree verbleibt kein vom Wheel-Build
erzeugtes Zwischenverzeichnis.

Die temporäre PostgreSQL-Instanz wird nach dem Audit kontrolliert gestoppt.

## Abgrenzung

LQ-552 ergänzt keine Migration, Tabelle, Portsignatur, Route, CLI, Entry Point,
fachliche Zeitregel oder Productionwirkung.

Es gibt keinen Commit, Push, Tag, Release, Signierung oder Deployment.

## Abschluss

Für den Python-3.12-SQLite-Datetime-Wartungsstrang ist kein weiterer Slice
erforderlich.

Ein möglicher späterer unabhängiger Slice kann die bislang nicht zugesicherte
In-Memory-SQLite-Engineunterstützung bewerten; sie wurde in diesem Strang weder
benötigt noch verändert.
