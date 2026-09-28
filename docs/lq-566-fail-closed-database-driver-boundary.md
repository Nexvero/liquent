# LQ-566 — Fail-closed Database Driver Boundary

## Ergebnis

LQ-566 setzt den LQ-565-Vertrag direkt nach der Backendprüfung in
`build_engine` um.

Die strukturierte SQLAlchemy-URL liefert `drivername`. Nur die drei
allowlisteten vollständigen Namen erreichen die bestehende
Enginekonfiguration.

## Reihenfolge

Die Factory entscheidet in dieser Reihenfolge:

1. URL ist strukturiert parsbar;
2. Backend ist SQLite oder PostgreSQL;
3. vollständiger Treibername ist allowlistet;
4. Adapter-, Pool-, Connect-Listener- und Enginekonfiguration.

Dadurch bleibt ein MySQL-Async-Treiber ein nicht unterstütztes Backend und
wird nicht fälschlich als bloßer Treiberfehler klassifiziert.

## Fehleroberfläche

Die neue Ablehnung verwendet den eingebauten `ValueError` mit genau
`unsupported_database_driver`. Sie entsteht außerhalb eines technischen
Exceptionhandlers und besitzt weder Cause noch Context.

`create_engine` wird nicht aufgerufen. SQLite-Adapter werden ebenfalls erst
nach erfolgreicher Treiberprüfung registriert.

## Bewahrte Pfade

Bare SQLite, explizites Pysqlite und PostgreSQL/Psycopg gelangen unverändert
zu ihren bisherigen Pool-, Timeout-, Datetime- und Fremdschlüsselzweigen.

## Abgrenzung

LQ-566 ändert keine `PlatformSettings`-Signatur, Migration, Tabelle,
Portsignatur, Route, CLI oder Entry-Point-Definition.

LQ-567 prüft Async-, Legacy-, Fremd- und erlaubte Treiber regressiv.
