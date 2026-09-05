# LQ-563 — Database Backend Boundary Regression

## Ergebnis

LQ-563 belegt die neue Dialektgrenze ohne externe Datenbankverbindung.

## Nicht unterstützte Backends

MySQL-, Oracle- und Microsoft-SQL-Server-URLs werden mit genau
`unsupported_database_backend` abgelehnt. Ein instrumentiertes
`create_engine` erhält dabei keinen Aufruf.

Die verwendeten Passwortmarker erscheinen nicht in der Exception. Cause und
Context bleiben leer.

## Ungültige Eingaben

Eindeutig nicht parsbare Strings und eine typfalsche Eingabe enden mit genau
`invalid_database_url`. Parsertext und Eingabedetail verlassen die Grenze
nicht; `create_engine` bleibt unberührt.

## Unterstützte Backends

`sqlite://`, explizites `sqlite+pysqlite:///:memory:` und
`postgresql+psycopg` erreichen jeweils genau einmal die Enginefactory.

Zusammen mit Pool-, Fremdschlüssel- und Migrationsregressionen bestehen 27
Tests unter `-W error::DeprecationWarning`.

## Abgrenzung

Der Nachweis lädt keinen nicht unterstützten Treiber, öffnet keine Verbindung
und erweitert die Plattform nicht um einen neuen Dialekt.

LQ-563 ergänzt keine Migration, Tabelle, Portsignatur, Route, CLI oder
Entry-Point-Wirkung. LQ-564 führt den vollständigen Abschlussaudit aus.
