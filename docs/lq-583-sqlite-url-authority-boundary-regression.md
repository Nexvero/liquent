# LQ-583 — SQLite URL Authority Boundary Regression

## Ergebnis

LQ-583 belegt die geschlossene SQLite-Authoritygrenze ohne externe
SQLite-Ressource.

## Abgelehnte Authorityformen

Regressionsfälle decken Benutzer mit Passwort und Host, Benutzer mit Host,
leeren Benutzer mit Passwort, Host allein sowie Host mit Port ab.

Jeder Fall endet mit genau `unsupported_database_url_authority`. Ein
instrumentiertes `create_engine` erhält keinen Aufruf, globale SQLite-Adapter
werden nicht registriert, und ein Passwortmarker erscheint nicht in der
Exception. Cause und Context bleiben leer.

## Reihenfolge

Eine SQLite-URL mit Authority sowie `uri=true&mode=ro` endet als
Authorityablehnung. Damit ist Authority vor der bestehenden Querypolicy
belegt.

## Bewahrte SQLite-Pfade

Beide In-Memory-Formen öffnen weiterhin erfolgreich eine Verbindung. Zwei
Authority-freie dateibasierte URLs führen ebenfalls `SELECT 1` erfolgreich
aus.

## PostgreSQL

Eine PostgreSQL/Psycopg-URL mit Benutzer, Passwort, Host und Port gelangt
unverändert zur Enginefactory und behält `connect_timeout=3`.

## Fokussierter Lauf

Authority-, Query-, Connect-Option-, Treiber-, Backend-, Pool-,
Fremdschlüssel- und Migrationsregressionen bestehen gemeinsam mit 63 Tests
unter `-W error::DeprecationWarning`.

## Abgrenzung

LQ-583 behauptet keine SQLite-Remote- oder Credentialsemantik und verändert
keine PostgreSQL-Authoritypolicy.

LQ-584 führt den vollständigen Normal-, PostgreSQL-, Wheel-, Inventar- und
Diffaudit aus.
