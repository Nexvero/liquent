# LQ-567 — Database Driver Boundary Regression

## Ergebnis

LQ-567 belegt die synchrone Treiber-Allowlist ohne externe Verbindung.

## Abgelehnte Treiber

SQLite/Aiosqlite, SQLite/APSW, PostgreSQL/Asyncpg, PostgreSQL/Psycopg2 und
bares PostgreSQL werden jeweils mit genau
`unsupported_database_driver` abgelehnt.

Ein instrumentiertes `create_engine` erhält keinen Aufruf. Für abgelehnte
SQLite-Treiber werden auch die globalen SQLite-Adapter nicht registriert.
Passwortmarker, Cause und Context verlassen die Grenze nicht.

## Erlaubte Treiber

`sqlite://`, `sqlite+pysqlite:///:memory:` und
`postgresql+psycopg` erreichen jeweils genau einmal `create_engine`.

Ein MySQL/Asyncmy-Beispiel bestätigt, dass die bestehende Backendablehnung
Vorrang vor der Treiberablehnung hat.

## Fokussierter Lauf

Treiber-, Backend-, Pool-, Fremdschlüssel-, Migrations- und
Productionkonfigurationsregressionen bestehen gemeinsam mit 48 Tests unter
`-W error::DeprecationWarning`.

## Abgrenzung

LQ-567 lädt keinen abgelehnten Treiber und behauptet keine asynchrone
Kompatibilität oder automatische Treibermigration.

LQ-568 führt den vollständigen Normal-, PostgreSQL-, Wheel-, Inventar- und
Diffaudit aus.
