# LQ-549 — Python 3.12 SQLite Datetime Compatibility Contract

## Ergebnis

LQ-549 definiert die Wartungsgrenze für die unter Python 3.12 veralteten
impliziten SQLite-Date-/Datetime-Adapter.

Die Änderung ist Infrastrukturkompatibilität und keine neue fachliche
Zeitsemantik.

## Beobachtbarer Bestand

Persistenzadapter übergeben validierte `date`- und `datetime`-Werte als
gebundene Parameter an SQLAlchemy.

SQLite speichert diese Werte als ISO-Text. Die bestehenden Adapter lesen Text
oder vom Dialekt rekonstruierte Datetimes und prüfen UTC weiterhin selbst.

Python 3.12 warnt, weil `sqlite3` seine historischen impliziten Adapter später
entfernen wird. Die Warnung entsteht beim Binden, nicht bei einer fachlichen
Entscheidung.

## Vertrag

Der Prozess registriert für SQLite explizite Adapter für exakt `date` und
`datetime`.

`date` wird mit `isoformat()` serialisiert.

`datetime` wird mit `isoformat(" ")` serialisiert und bewahrt vorhandenen
Offset sowie Mikrosekunden. Es erfolgt keine Konvertierung, Normalisierung,
Zeitzonenergänzung oder Rundung.

Naive oder nicht-UTC Werte werden nicht durch diesen Adapter legitimiert.
Fachliche Persistenzgrenzen behalten ihre bestehenden UTC-Prüfungen.

## Scope

Die Registrierung geschieht nur beim Aufbau einer `sqlite:`-Engine und öffnet
keine Verbindung.

PostgreSQL-Engineaufbau und Psycopg-Adapter bleiben unverändert.

Es wird kein Converter und kein `detect_types` aktiviert, damit SQLAlchemy
seine bestehenden Resultprozessoren unverändert behält.

## Nichtziele

Keine Migration, Spaltenänderung, Datenumschreibung, Clockänderung oder neue
Zeitdomain ist Bestandteil dieses Slices.

## Nächster Slice

LQ-550 implementiert die expliziten SQLite-Adapter zentral in `build_engine`.
