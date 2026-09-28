# LQ-568 — Database Driver Boundary Completion Audit

## Ergebnis

LQ-568 schließt den gebündelten Treiberhärtungsstrang LQ-565 bis LQ-568 ab.

Die synchrone Enginefactory akzeptiert genau SQLite/Pysqlite und
PostgreSQL/Psycopg. Async-, Legacy- und Fremdtreiber werden vor Adapter-,
Engine-, Import- und Verbindungsarbeit detailfrei abgelehnt.

## Fokussierter Nachweis

Der kombinierte Fokuslauf besteht mit 51 Tests. Er umfasst Treiber- und
Backendreihenfolge, erlaubte Pfade, Pooling, Fremdschlüssel, Migration und
Productionkonfiguration.

`DeprecationWarning` wird mit `-W error::DeprecationWarning` als Fehler
behandelt. Der Lauf endet ohne Warnung.

## Vollständige normale Suite

Die normale Suite besteht mit 5079 Tests und einem erwarteten Skip. 105
PostgreSQL-Integrationstests sind ausdrücklich abgewählt und separat
verpflichtend ausgeführt.

Der Lauf endet ohne Warning Summary.

## Vollständige PostgreSQL-Suite

Alle 105 `postgres_integration`-Tests bestehen gegen eine isolierte lokale
PostgreSQL-16-Instanz. 5080 nicht zu diesem Lauf gehörende Tests sind
abgewählt.

Damit bleibt der reale synchrone `postgresql+psycopg`-Pfad einschließlich
Migrationen, Pooling und serverseitiger Konkurrenzentscheidungen vollständig
erhalten.

## Wheel-Nachweis

Wheel `liquent-0.0.1-py3-none-any.whl` wurde ohne Buildisolation erfolgreich
außerhalb des Worktrees erzeugt.

Direkt aus dem Wheel wurde eine `sqlite+pysqlite:///:memory:`-Engine gebaut
und mit `SELECT 1` geprüft. Eine PostgreSQL/Asyncpg-URL mit Passwortmarker
wurde aus demselben Paket vor Engineaufbau mit genau
`unsupported_database_driver` abgelehnt; Cause, Context und Passwortdetail
blieben leer.

## Inventar und Migration

Quelle und Wheel stimmen bei 68 Console Entry Points und 69 Operator-Dateien
überein. Der Bestand bleibt bei 42 Migrationen und Head `20260826_0042`.

Die erzeugten Verzeichnisse `build/` und `src/liquent.egg-info/` wurden nach
dem Paketnachweis gezielt entfernt. Das Wheel verbleibt außerhalb des
Worktrees.

## Diff- und Scope-Audit

`git diff --check` ist sauber.

Der Strang ergänzt nur die frühe Treiberprüfung, fokussierte Regressionen und
vier Dokumentationsslices. Er ergänzt keinen Treiber, Async-Pfad, Fallback
oder neuen Exceptiontyp.

Es gibt keine Migration, Tabelle, Portsignatur, Route, CLI, Entry-Point-,
Commit-, Push-, Release- oder Deploymentwirkung.

## Abschluss

Für den Datenbanktreiber-Härtungsstrang LQ-565 bis LQ-568 ist kein weiterer
Slice erforderlich.

Ein späterer zusätzlicher Treiber oder Async-Persistenzpfad benötigt einen
eigenen Vertrag, Abhängigkeitssatz und vollständigen Integrationsnachweis.
