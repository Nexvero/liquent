# LQ-587 — PostgreSQL Supervisor Control-directory Retirement Evidence

## Ergebnis

LQ-587 belegt den LQ-586-Operatorpfad gegen eine echte isolierte
PostgreSQL-16-Instanz.

## Terminaler Erfolgsfall

Der Test migriert eine eigene Wegwerfdatenbank bis Head `20260826_0042` und
erzeugt ein Active-Directory mit gebundenem Writerjournal.

Das Journal enthält die gültige Sequenz `launch_committed` gefolgt von
`terminal_observed` mit geschlossenem terminalem Outcome. Backendinstanz,
Handle und Directory sind persistent konsistent gebunden.

`execute_one` liest diese Fakten über dieselben Produktionsadapter und setzt
das Directory serverseitig von Active auf Retired. Ergebnis und Datenbankzeile
tragen dieselbe aware UTC-Retirementzeit.

## Retry

Ein zweiter identischer Aufruf liefert exakt dieselbe Directory-ID, Handle-ID
und Retirementzeit. Er erzeugt keinen zweiten Lifecyclefact und ersetzt den
persistierten Zeitpunkt nicht.

## Wirkungsfreie Ablehnung

Ein Active-Directory ohne Terminaltransition bleibt Active und liefert
neutral kein Operatorresultat. Eine unbekannte Directory-ID bleibt ebenfalls
neutral und erzeugt keine Zeile.

## PostgreSQL-Grenzen

Der Nachweis verwendet die bestehenden table locks und Transaktionen der
Registry- und Journaladapter. Es gibt keinen SQLite-Fallback und keine
manuelle Retirement-SQL-Wirkung im Test.

## Fokussierter Lauf

Die zwei PostgreSQL-Tests bestehen unter
`-W error::DeprecationWarning` gegen jeweils isolierte migrierte Datenbanken.

## Abgrenzung

LQ-587 startet keine Retentionevaluation, Clearance oder physische
Cleanupwirkung. Es ergänzt keine Migration, Tabelle, Portsignatur, Route oder
Productionaktivierung.

LQ-588 führt den vollständigen Normal-, PostgreSQL-, Wheel-, Inventar- und
Diffaudit aus.
