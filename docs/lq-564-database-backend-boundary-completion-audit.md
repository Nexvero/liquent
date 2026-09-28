# LQ-564 — Database Backend Boundary Completion Audit

## Ergebnis

LQ-564 schließt den gebündelten Härtungsstrang LQ-561 bis LQ-564 ab.

Die zentrale Enginefactory akzeptiert weiterhin SQLite und PostgreSQL, lehnt
andere Backends jedoch vor Engine-, Treiber- und Verbindungsarbeit mit einer
stabilen detailfreien Oberfläche ab.

## Fokussierter Nachweis

Der kombinierte Fokuslauf besteht mit 30 Tests. Er umfasst ungültige URLs,
nicht unterstützte Backends, bestehende Dialekt- und Poolauswahl,
SQLite-Fremdschlüsselaktivierung und das Migrationsgate.

Der Lauf behandelt `DeprecationWarning` über
`-W error::DeprecationWarning` als Fehler und endet ohne Warnung.

## Vollständige normale Suite

Die normale Suite besteht mit 5065 Tests und einem erwarteten Skip. 105
PostgreSQL-Integrationstests sind in diesem Lauf ausdrücklich abgewählt und
separat verpflichtend ausgeführt.

Es gibt keine Warning Summary.

## Vollständige PostgreSQL-Suite

Alle 105 `postgres_integration`-Tests bestehen gegen eine isolierte lokale
PostgreSQL-16-Instanz. 5066 nicht zu diesem Lauf gehörende Tests sind
abgewählt.

Damit ist belegt, dass die neue Backendprüfung den realen
`postgresql+psycopg`-Pfad, Migrationen, Pooling und serverseitige
Konkurrenzentscheidungen nicht verändert.

## Wheel-Nachweis

Wheel `liquent-0.0.1-py3-none-any.whl` wurde ohne Buildisolation erfolgreich
außerhalb des Worktrees erzeugt.

Direkt aus dem Wheel wurde eine `sqlite://`-Engine gebaut und mit `SELECT 1`
geprüft. Eine MySQL/PyMySQL-URL mit Passwortmarker wurde direkt aus demselben
Paket vor Engineaufbau mit genau `unsupported_database_backend` abgelehnt;
Cause, Context und Passwortdetail blieben leer.

## Inventar und Migration

Quelle und Wheel stimmen bei 68 Console Entry Points und 69 Operator-Dateien
überein. Der Bestand bleibt bei 42 Migrationen und Head `20260826_0042`.

Die erzeugten Verzeichnisse `build/` und `src/liquent.egg-info/` wurden nach
dem Paketnachweis gezielt entfernt. Das Wheel verbleibt außerhalb des
Worktrees.

## Diff- und Scope-Audit

`git diff --check` ist sauber.

Der Strang ergänzt nur die frühe Backend-/URL-Prüfung, fokussierte Regressionen
und vier Dokumentationsslices. Er führt keinen neuen Exceptiontyp, Dialekt,
Treiber oder Fallback ein.

Es gibt keine Migration, Tabelle, Portsignatur, Route, CLI, Entry-Point-,
Commit-, Push-, Release- oder Deploymentwirkung.

## Abschluss

Für den Datenbank-Backend-Härtungsstrang LQ-561 bis LQ-564 ist kein weiterer
Slice erforderlich.

Eine mögliche spätere Treiber-Allowlist innerhalb zugelassener Backends wäre
ein eigener Vertrag und folgt nicht aus dieser Dialektgrenze.
