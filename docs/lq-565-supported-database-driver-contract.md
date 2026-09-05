# LQ-565 — Supported Database Driver Contract

## Ergebnis

LQ-565 ergänzt die LQ-561-Backendgrenze um eine explizite synchrone
Treiber-Allowlist.

Die zentrale Enginefactory unterstützt genau `sqlite`, `sqlite+pysqlite` und
`postgresql+psycopg`.

## SQLite

`sqlite` bezeichnet SQLAlchemys synchronen Standardpfad über Pysqlite.
`sqlite+pysqlite` erlaubt dieselbe Auswahl ausdrücklich. Beide behalten die
Pool-, Datetime- und Fremdschlüsselverträge aus LQ-549 bis LQ-560.

Asynchrone oder andere SQLite-Treiber sind nicht implizit kompatibel und
werden nicht durch einen Fallback auf Pysqlite ersetzt.

## PostgreSQL

PostgreSQL ist ausschließlich über den synchronen Psycopg-3-Treiber
`postgresql+psycopg` zugelassen. Das entspricht der bestehenden
Productionvalidierung und dem verpflichtenden Integrationstestpfad.

Bare `postgresql`, Psycopg2 und asynchrone PostgreSQL-Treiber sind außerhalb
dieser Grenze. Es gibt keinen automatischen Treiberwechsel.

## Ablehnung

Ein anderer Treibername innerhalb eines unterstützten Backends wird vor
Adapter-, Pool-, Listener-, Engine-, Treiberimport- und Verbindungsarbeit mit
genau `unsupported_database_driver` abgelehnt.

URL, Zugangsdaten und Treibername werden nicht in der Ablehnung wiederholt.
Cause und Context bleiben leer. Es wird kein neuer Exceptiontyp eingeführt.

## Prüfungsreihenfolge

Ungültige URL bleibt `invalid_database_url`. Ein nicht unterstütztes Backend
bleibt `unsupported_database_backend`, unabhängig von dessen Treibername.
Erst für ein unterstütztes Backend entscheidet die Treiber-Allowlist.

## Abgrenzung

LQ-565 ergänzt keinen Treiber, asynchronen Enginepfad, Fallback,
Konfigurationsparameter, Migration, Port, Route, CLI oder Entry Point.

LQ-566 setzt die Treiberprüfung zentral um.
