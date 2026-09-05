# LQ-558 — Central SQLite Foreign-key Activation

## Ergebnis

LQ-558 setzt den LQ-557-Vertrag in `build_engine` um.

Nach dem verbindungslosen Engineaufbau registriert die Factory ausschließlich
für SQLite einen Connect-Listener. Dieser führt auf jeder neu erzeugten
DBAPI-Verbindung `PRAGMA foreign_keys=ON` aus.

## Ressourcenbehandlung

Der Listener öffnet einen Cursor, führt genau das Pragma aus und schließt den
Cursor in jedem Fall. Scheitert die Aktivierung, wird die Verbindung nicht als
erfolgreich vorbereitet behandelt; der ursprüngliche technische Fehler bleibt
an der Infrastrukturgrenze erhalten.

## Zusammenspiel mit LQ-550 bis LQ-556

Die expliziten Python-3.12-Datetime-Adapter werden weiterhin vor dem
Engineaufbau registriert.

In-Memory-SQLite behält `StaticPool` und die Engine-lokale gemeinsame
Verbindung. Dateibasiertes SQLite behält seinen begrenzten `QueuePool`.
Der Listener gilt für beide Formen und verändert deren Lebensdauer nicht.

PostgreSQL behält Poolgröße, Overflow, Pool-Timeout und Connect-Timeout. Für
diesen Zweig wird kein Listener registriert.

## Aufbauwirkung

`build_engine` öffnet weiterhin keine Verbindung. Das Pragma wird erst beim
ersten tatsächlichen Checkout einer neu erzeugten DBAPI-Verbindung ausgeführt.

## Abgrenzung

LQ-558 entfernt keine vorhandenen testlokalen Listener. Deren erneutes Setzen
auf `ON` ist idempotent und erlaubt eine getrennte spätere Testbereinigung.

Es gibt keine Migration, Tabelle, Constraintänderung, Portsignatur, Route,
CLI, Entry-Point- oder automatische Fachwirkung.

LQ-559 belegt Enforcement, Reconnect und Dialekttrennung regressiv.
