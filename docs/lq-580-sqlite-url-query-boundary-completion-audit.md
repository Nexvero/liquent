# LQ-580 — SQLite URL Query Boundary Completion Audit

## Ergebnis

LQ-580 schließt den SQLite-URL-Query-Härtungsstrang LQ-577 bis LQ-580 ab.

SQLite-URLs akzeptieren nur noch die zentral überschriebenen
Kompatibilitätsschlüssel `timeout` und `check_same_thread`. Andere
Queryoptionen können Datei-, URI-, Cache-, Schreib- oder Lockingsemantik nicht
mehr außerhalb der Factory verändern.

## Fokussierter Nachweis

Der kombinierte Fokuslauf besteht mit 56 Tests. Er umfasst Querypolicy,
Connect-Option-Priorität, Fehlerreihenfolge, Backend, Treiber, Pool,
Fremdschlüssel und Migration.

`DeprecationWarning` wird mit `-W error::DeprecationWarning` als Fehler
behandelt. Der Lauf endet ohne Warnung.

## Vollständige normale Suite

Die normale Suite besteht mit 5112 Tests und einem erwarteten Skip. 105
PostgreSQL-Integrationstests sind ausdrücklich abgewählt und separat
verpflichtend ausgeführt.

Es gibt keine Warning Summary.

## Vollständige PostgreSQL-Suite

Alle 105 `postgres_integration`-Tests bestehen gegen eine isolierte lokale
PostgreSQL-16-Instanz. 5113 nicht zu diesem Lauf gehörende Tests sind
abgewählt.

Damit bleiben PostgreSQL/Psycopg-Querywerte einschließlich Socketpfad und Port
außerhalb der SQLite-Policy vollständig nutzbar.

## Wheel-Nachweis

Wheel `liquent-0.0.1-py3-none-any.whl` wurde ohne Buildisolation erfolgreich
außerhalb des Worktrees erzeugt.

Direkt aus dem Wheel blieb eine SQLite-URL mit `timeout=0.001` zentral bei
`PRAGMA busy_timeout=5000`. Eine URL mit `uri=true&mode=memory` wurde vor
Engineaufbau mit genau `unsupported_database_url_option` abgelehnt; Cause und
Context blieben leer.

## Inventar und Migration

Quelle und Wheel stimmen bei 68 Console Entry Points und 69 Operator-Dateien
überein. Der Bestand bleibt bei 42 Migrationen und Head `20260826_0042`.

Die erzeugten Verzeichnisse `build/` und `src/liquent.egg-info/` wurden nach
dem Paketnachweis gezielt entfernt. Das Wheel verbleibt außerhalb des
Worktrees.

## Diff- und Scope-Audit

`git diff --check` ist sauber.

Der Strang ergänzt nur die frühe SQLite-Queryprüfung, fokussierte Regressionen
und vier Dokumentationsslices. Er ergänzt keine URI-, Read-only-, Shared-
Cache-, Immutable- oder No-lock-Unterstützung.

Es gibt keine Migration, Tabelle, Portsignatur, Route, CLI, Entry-Point-,
Commit-, Push-, Release- oder Deploymentwirkung.

## Abschluss

Für den SQLite-URL-Query-Härtungsstrang LQ-577 bis LQ-580 ist kein weiterer
Slice erforderlich.

Eine spätere zusätzliche SQLite-Queryoption benötigt einen eigenen Vertrag
und darf nicht still durch Treiberakzeptanz freigeschaltet werden.
