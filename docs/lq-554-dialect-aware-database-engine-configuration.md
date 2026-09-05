# LQ-554 — Dialect-aware Database Engine Configuration

## Ergebnis

LQ-554 setzt den LQ-553-Vertrag zentral in `build_engine` um.

Die Enginefactory parst die URL mit SQLAlchemy und trennt gemeinsam
prozesslokales In-Memory-SQLite, dateibasiertes SQLite und PostgreSQL, bevor
eine Verbindung geöffnet wird.

## In-Memory-SQLite

`sqlite://` und `sqlite:///:memory:` verwenden `StaticPool`. Dadurch gehört
genau eine Verbindung zur Engine und alle nacheinander ausgeführten Zugriffe
sehen denselben In-Memory-Bestand.

`check_same_thread=False` erlaubt die im Vertrag vorgesehene Nutzung aus
verschiedenen Threads. Diese Option gilt ausschließlich für diese beiden
In-Memory-URL-Formen.

Die in LQ-550 eingeführten expliziten `date`- und `datetime`-Adapter werden
weiterhin vor dem SQLite-Engineaufbau registriert.

## Dateibasiertes SQLite

Dateibasierte SQLite-Engines behalten `QueuePool` mit Poolgröße 3,
Max-Overflow 2 und Pool-Timeout 5 Sekunden. Es wird keine globale
Threadfreigabe hinzugefügt.

## PostgreSQL

PostgreSQL behält denselben begrenzten Pool und `connect_timeout=3`.
SQLite-spezifische Adapter, Poolklassen und Connect-Argumente gelangen nicht
in diesen Zweig.

## Gemeinsame Eigenschaften

`pool_pre_ping=True` und der Logging-Name `liquent` gelten weiterhin für alle
unterstützten Zweige. Der Factory-Aufruf selbst öffnet keine Verbindung.

## Abgrenzung

LQ-554 ändert keine Migration, Tabelle, Repositorysemantik, Portsignatur,
fachliche Zeitregel, Route, CLI, Entry Point oder Productionverdrahtung.

LQ-555 prüft Pool-, Thread-, UTC- und Dialekttrennung regressiv.
