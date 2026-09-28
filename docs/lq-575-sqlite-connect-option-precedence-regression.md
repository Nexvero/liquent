# LQ-575 — SQLite Connect-option Precedence Regression

## Ergebnis

LQ-575 belegt Timeout, URL-Priorität, Threadvertrag und Dialekttrennung.

## Dateibasierter Nachweis

Eine dateibasierte URL behauptet `timeout=0.001`. Die tatsächlich geöffnete
Verbindung meldet dennoch `PRAGMA busy_timeout=5000`.

Ein instrumentierter Factoryaufruf mit `timeout=99` erhält explizit nur
`connect_args={"timeout": 5}` und unverändert die Poolgrenzen 3/2/5.

## In-Memory-Nachweis

Eine In-Memory-URL behauptet `timeout=0.001` und
`check_same_thread=true`. Die Verbindung meldet dennoch 5000 Millisekunden
Busy-Timeout, und ein anderer Thread liest erfolgreich den Bestand derselben
Engine.

Die instrumentierte Factory bestätigt gemeinsam `timeout=5` und
`check_same_thread=False` ohne Queue-Pool-Argumente.

## PostgreSQL-Nachweis

Eine PostgreSQL/Psycopg-URL behauptet `connect_timeout=99`. Die Factory reicht
weiterhin ausschließlich `connect_timeout=3` durch und keine SQLite-Option.

## Fokussierter Lauf

Connect-Option-, Pool-, Fremdschlüssel-, Treiber- und Migrationsregressionen
bestehen gemeinsam mit 32 Tests unter `-W error::DeprecationWarning`.

## Abgrenzung

Der Nachweis simuliert keinen fünfsekündigen Lockkonflikt und behauptet keine
erfolgreiche Transaktion nach Ablauf der Wartezeit.

LQ-576 führt den vollständigen Normal-, PostgreSQL-, Wheel-, Inventar- und
Diffaudit aus.
