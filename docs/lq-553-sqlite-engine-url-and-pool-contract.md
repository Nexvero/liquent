# LQ-553 — SQLite Engine URL and Pool Contract

## Ergebnis

LQ-553 definiert die bislang offene In-Memory-SQLite-Engineunterstützung.

`sqlite://` und `sqlite:///:memory:` bezeichnen für Liquent eine gemeinsam
prozesslokal nutzbare Datenbank pro erzeugter Engine. Alle Verbindungen dieser
Engine sehen denselben Bestand, auch wenn sie nacheinander aus verschiedenen
Threads verwendet werden.

## Lebensdauer und Isolation

Die Gemeinsamkeit endet an der Engine-Grenze. Eine zweite Engine für dieselbe
URL erhält einen unabhängigen Bestand. Nach `dispose()` gibt es keine
Persistenzzusage.

Damit ist In-Memory-SQLite für begrenzte lokale Prüfungen geeignet, aber kein
Ersatz für eine dateibasierte oder externe Datenbank und keine
Production-Persistenz.

## Dateibasierte SQLite-URLs

Eine SQLite-URL mit Dateipfad bleibt dateibasiert. Sie behält den bestehenden
begrenzten Connection-Pool mit Größe 3, höchstens 2 zusätzlichen Verbindungen
und 5 Sekunden Pool-Wartezeit.

Der neue Vertrag ändert weder Dateipfade noch Transaktions-, Locking- oder
Durability-Semantik.

## Thread-Grenze

Die gemeinsam prozesslokale In-Memory-Engine darf ihre einzelne Verbindung
über Threads hinweg verwenden. Gleichzeitige Nutzung derselben Verbindung
wird dadurch nicht als neue fachliche Nebenläufigkeitsgarantie eingeführt.

Aufrufer bleiben für geordnete Transaktionen und Lebensdauer verantwortlich.

## Dialektgrenzen

Die Auswahl folgt der von SQLAlchemy geparsten Backend- und Datenbankangabe,
nicht einer unstrukturierten Präfixheuristik.

PostgreSQL bleibt außerhalb des In-Memory-Vertrags. Seine Poolgrenzen und der
Verbindungsaufbau-Timeout bleiben unverändert.

## Abgrenzung

LQ-553 ergänzt keine Migration, Tabelle, fachliche Persistenz, Portsignatur,
Route, CLI, Entry Point oder automatische Productionaktivierung.

LQ-554 setzt diese Enginekonfiguration dialectbewusst um.
