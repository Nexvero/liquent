# LQ-550 — Explicit Python 3.12 SQLite Datetime Adapters

## Ergebnis

LQ-550 implementiert den LQ-549-Vertrag zentral in der Enginefactory.

## Implementation

`_configure_sqlite_adapters()` registriert explizite Adapter für
`datetime.date` und `datetime.datetime` über das Standardmodul `sqlite3`.

`build_engine()` ruft diese Konfiguration ausschließlich für URLs mit
`sqlite:`-Schema vor dem nebenwirkungsfreien SQLAlchemy-Engineaufbau auf.

Die Registrierung ist idempotent und ersetzt nur die künftig entfernten
Standardadapter durch explizit definierte ISO-Serialisierung.

## Semantik

Offset, Mikrosekunden und der bisherige Leerraum zwischen Datum und Uhrzeit
bleiben erhalten.

Es gibt keine automatische UTC-Konvertierung. Bestehende fachliche Guards
bleiben die alleinige Authority für zulässige Zeitwerte.

## PostgreSQL

PostgreSQL verwendet weiterhin ausschließlich seine vorhandenen Psycopg- und
SQLAlchemy-Pfade. SQLite-Konfiguration wird beim PostgreSQL-Engineaufbau nicht
aufgerufen.

## Tests

Ein strikter DeprecationWarning-Test bindet Datum und aware UTC-Datetime,
liest den exakten ISO-Text zurück und belegt fehlende Python-3.12-Warnung.

Ein separater Test belegt, dass PostgreSQL-Engineaufbau die SQLite-
Konfiguration nicht berührt.

## Nächster Slice

LQ-551 prüft repräsentative persistente Adapter und UTC-Roundtrips mit als
Fehler behandelten DeprecationWarnings.
