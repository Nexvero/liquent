# LQ-574 — Central SQLite Connect Options

## Ergebnis

LQ-574 setzt den LQ-573-Vertrag dialect- und URL-formabhängig in
`build_engine` um.

## Dateibasierter Zweig

Dateibasiertes SQLite behält den begrenzten Queue-Pool mit Größe 3,
Max-Overflow 2 und Pool-Timeout 5. Zusätzlich erhält `create_engine` explizit
`connect_args={"timeout": 5}`.

## In-Memory-Zweig

`sqlite://` und `sqlite:///:memory:` behalten `StaticPool`. Ihre Connect-
Argumente enthalten gemeinsam `check_same_thread=False` und `timeout=5`.

URL-Querywerte werden von diesen expliziten Argumenten beim DBAPI-Aufbau
überschrieben. Der bestehende Fremdschlüssel-Connect-Listener läuft danach auf
der vorbereiteten Verbindung.

## PostgreSQL-Zweig

PostgreSQL verwendet weiterhin ausschließlich
`connect_args={"connect_timeout": 3}` sowie den bestehenden Queue-Pool.

Die Implementierung teilt keine SQLite-Option mit PostgreSQL und keine
PostgreSQL-Option mit SQLite.

## Bewahrte Reihenfolge

URL-, Backend- und Treiberprüfung aus LQ-561 bis LQ-568 erfolgen weiterhin vor
Adapter-, Pool- und Connect-Option-Konfiguration.

Der Factory-Aufruf öffnet weiterhin keine Verbindung. Der DBAPI-Timeout wird
erst beim tatsächlichen Verbindungsaufbau wirksam.

## Abgrenzung

LQ-574 ergänzt keinen Konfigurationsparameter, Retry, Lockmanager,
Exceptiontyp, Treiber oder Dialekt.

Keine Migration, Portsignatur, Route, CLI oder Entry-Point-Wirkung. LQ-575
prüft die zentrale Priorität regressiv.
