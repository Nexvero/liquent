# LQ-556 — Dialect-aware Engine Completion Audit

## Ergebnis

LQ-556 schließt den gebündelten Enginewartungsstrang LQ-553 bis LQ-556 ab.

Der explizite In-Memory-SQLite-Vertrag, seine dialectbewusste Umsetzung und
die Trennung zu dateibasiertem SQLite sowie PostgreSQL sind vollständig grün
geprüft.

## Fokussierter Nachweis

Der abschließende Fokuslauf umfasst 18 Tests. Er verbindet die neuen
Engine- und Vertragsregressionen mit den expliziten SQLite-Datetime-Adaptern
und dem bestehenden Migrationsgate.

`DeprecationWarning` wird über `-W error::DeprecationWarning` als Fehler
behandelt. Der Lauf endet ohne Warnung.

## Vollständige normale Suite

Die normale Matrix besteht mit 5041 Tests. 106 Tests werden in diesem Lauf
erwartungsgemäß ausgelassen; darin liegt der separat verpflichtend ausgeführte
PostgreSQL-Pfad.

Der vollständige Lauf verwendet dieselbe strikte DeprecationWarning-Grenze
und endet ohne Warning Summary.

## Vollständige PostgreSQL-Suite

Alle 105 `postgres_integration`-Tests bestehen gegen eine isolierte lokale
PostgreSQL-16-Instanz. 5042 nicht zu diesem Lauf gehörende Tests sind
abgewählt.

Jeder Integrationstest verwendet weiterhin eine eigene migrierte
Wegwerfdatenbank. Die Engineänderung beeinflusst weder Psycopg-Optionen noch
serverseitige Konkurrenzentscheidungen.

## Wheel und In-Memory-Smoke-Test

Wheel `liquent-0.0.1-py3-none-any.whl` wurde ohne Buildisolation erfolgreich
außerhalb des Worktrees erzeugt.

`liquent` und `liquent_platform` wurden direkt aus dem Wheel importiert. Eine
direkt aus dem Wheel gebaute `sqlite://`-Engine öffnete die gemeinsame
prozesslokale Verbindung und führte `SELECT 1` erfolgreich aus.

Dieser Smoke-Test schließt genau die vor LQ-553 bestehende Lücke: Die
In-Memory-URL scheitert nicht mehr an inkompatiblen Queue-Pool-Argumenten.

## Inventar und Migration

Quelle und Wheel stimmen bei 68 Console Entry Points, 69 Operator-Dateien und
42 Migrationen überein. Der erwartete Migrations-Head bleibt
`20260826_0042`.

Die erzeugten Verzeichnisse `build/` und `src/liquent.egg-info/` wurden nach
dem Paketnachweis gezielt entfernt. Das Wheel verbleibt außerhalb des
Worktrees.

## Diff- und Scope-Audit

`git diff --check` ist sauber.

Der Strang ändert zentral die Enginefactory, ergänzt fokussierte Regressionen
und vier Dokumentationsslices. Er ergänzt keine Migration, Tabelle,
Portsignatur, Route, CLI, Entry Point oder Productionverdrahtung.

Es gibt keinen Commit, Push, Tag, Release, Signierung oder Deployment.

## Abschluss

Für den In-Memory-SQLite-Enginewartungsstrang LQ-553 bis LQ-556 ist kein
weiterer Slice erforderlich.

Spätere Slices dürfen neue Persistenzanforderungen nur als eigenständigen
Vertrag einführen; aus diesem lokalen Testadapter folgt keine Production-
Durability- oder Nebenläufigkeitszusage.
