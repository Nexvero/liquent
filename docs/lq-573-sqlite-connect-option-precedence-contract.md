# LQ-573 — SQLite Connect-option Precedence Contract

## Ergebnis

LQ-573 macht den SQLite-Verbindungs-Timeout und die Priorität zentraler
Connect-Optionen explizit.

Jede durch `build_engine` erzeugte SQLite-Verbindung verwendet einen
5-Sekunden-DBAPI-Timeout. SQLite bildet ihn als `PRAGMA busy_timeout=5000` ab.

## Dateibasierte SQLite-Engines

Dateibasierte Engines erhalten zentral `timeout=5`. Dies ergänzt den bereits
festgelegten Pool-Timeout von 5 Sekunden; beide Grenzen messen unterschiedliche
Wartephasen.

Der Pool-Timeout begrenzt das Warten auf einen freien Poolslot. Der
DBAPI-/Busy-Timeout begrenzt SQLite-Warten auf eine gesperrte Datenbank.

## In-Memory-SQLite

Engine-lokales In-Memory-SQLite erhält ebenfalls `timeout=5` und weiterhin
`check_same_thread=False` für den LQ-553-Threadvertrag.

Beide Werte gehören zur zentralen Enginekonfiguration und nicht zur
Aufruferentscheidung.

## URL-Priorität

Caller-supplied SQLite-Querywerte für `timeout` oder `check_same_thread`
dürfen die zentralen Werte nicht überschreiben. Die expliziten
`connect_args` der Factory haben Vorrang.

Die URL bleibt eine Verbindungsadresse, keine Berechtigungs- oder
Laufzeitpolicyquelle.

## PostgreSQL

PostgreSQL bleibt getrennt bei `connect_timeout=3`. SQLite-`timeout` und
`check_same_thread` gelangen nicht in den Psycopg-Zweig. Auch ein
caller-supplied PostgreSQL-Querywert überschreibt den zentralen Connect-Timeout
nicht.

## Abgrenzung

LQ-573 verspricht keinen erfolgreichen Lock-Erwerb innerhalb von fünf
Sekunden, keine Retrylogik und keine neue Nebenläufigkeitssemantik.

Es gibt keine Migration, Tabelle, Portsignatur, Route, CLI oder
Entry-Point-Wirkung. LQ-574 setzt die Optionen zentral um.
