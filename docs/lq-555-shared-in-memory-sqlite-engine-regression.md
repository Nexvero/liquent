# LQ-555 — Shared In-memory SQLite Engine Regression

## Ergebnis

LQ-555 belegt den LQ-553-/LQ-554-Vertrag mit fokussierten Regressionstests.

Beide unterstützten In-Memory-URL-Formen wählen den gemeinsamen
prozesslokalen Pool. Ein in einem Thread angelegter und befüllter Bestand ist
nach Abschluss der Transaktion aus einem anderen Thread derselben Engine
lesbar.

## Datetime-Nachweis

Der Thread-Roundtrip persistiert einen offsetbewussten UTC-Datetime-Wert über
den expliziten Python-3.12-SQLite-Adapter. Der gespeicherte ISO-Text bewahrt
den Offset und löst unter `-W error::DeprecationWarning` keine Warnung aus.

Damit bleibt LQ-550 wirksam; LQ-555 ergänzt keine UTC-Normalisierung oder neue
fachliche Zeitregel.

## Pool-Nachweis

Dateibasiertes SQLite bleibt beim begrenzten Queue-Pool mit 3 regulären und 2
zusätzlichen Verbindungen sowie 5 Sekunden Wartezeit.

PostgreSQL erhält weiterhin denselben begrenzten Pool und ausschließlich dort
den 3-Sekunden-Verbindungsaufbau-Timeout. Der Test öffnet dafür keine
PostgreSQL-Verbindung, sondern prüft die Factorygrenze direkt.

## Fokussierter Lauf

Die neuen Engineprüfungen, die expliziten Adapterregressionen und das
Migrationsgate bestehen gemeinsam mit 15 Tests unter strikter
DeprecationWarning-Fehlergrenze.

## Abgrenzung

Der Test behauptet keine gleichzeitige Mehrfachtransaktionsgarantie auf einer
einzelnen In-Memory-Verbindung und keine Persistenz über Engine-Disposal oder
mehrere Engines hinweg.

LQ-555 ergänzt keine Migration, Tabelle, Portsignatur, Route, CLI, Entry Point
oder Productionwirkung. LQ-556 führt den vollständigen Abschlussaudit aus.
