# LQ-579 — SQLite URL Query Boundary Regression

## Ergebnis

LQ-579 belegt die geschlossene SQLite-Querypolicy ohne externe Verbindung.

## Abgelehnte Queryschlüssel

Regressionsfälle für `uri`, `mode=memory`, `mode=ro`, `cache=shared`,
`immutable`, `nolock` und einen unbekannten Schlüssel enden jeweils mit genau
`unsupported_database_url_option`.

Ein instrumentiertes `create_engine` erhält keinen Aufruf. Auch die globalen
SQLite-Adapter werden nicht registriert. Ein Passwort-/Detailmarker erscheint
nicht in der Exception; Cause und Context bleiben leer.

## Zulässige Queryschlüssel

`timeout` und `check_same_thread` gelangen für bare SQLite- und explizite
Pysqlite-In-Memory-URLs zur Factory. Die tatsächlichen Connect-Argumente
bleiben zentral `timeout=5` und `check_same_thread=False`.

## Reihenfolge und PostgreSQL

MySQL mit einem SQLite-artigen Queryschlüssel bleibt
`unsupported_database_backend`. SQLite/Aiosqlite bleibt
`unsupported_database_driver`.

Eine PostgreSQL/Psycopg-URL mit `sslmode` und `application_name` gelangt
unverändert zur Enginefactory; ihr Connect-Timeout bleibt zentral 3.

## Fokussierter Lauf

Query-, Connect-Option-, Treiber-, Backend-, Pool-, Fremdschlüssel- und
Migrationsregressionen bestehen gemeinsam mit 53 Tests unter
`-W error::DeprecationWarning`.

## Abgrenzung

LQ-579 behauptet keine Unterstützung der abgelehnten SQLite-URI-Funktionen und
keine PostgreSQL-Query-Allowlist.

LQ-580 führt den vollständigen Normal-, PostgreSQL-, Wheel-, Inventar- und
Diffaudit aus.
