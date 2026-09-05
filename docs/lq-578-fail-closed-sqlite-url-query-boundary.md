# LQ-578 — Fail-closed SQLite URL Query Boundary

## Ergebnis

LQ-578 setzt den LQ-577-Vertrag in `build_engine` unmittelbar nach der
Treiberprüfung um.

Für SQLite muss die Menge strukturierter Queryschlüssel eine Teilmenge von
`timeout` und `check_same_thread` sein. Andernfalls endet der Factoryaufruf mit
`unsupported_database_url_option`.

## Reihenfolge

Die vollständige frühe Prüfung lautet nun:

1. URL ist parsbar;
2. Backend ist SQLite oder PostgreSQL;
3. Treiber ist synchron allowlistet;
4. SQLite-Queryschlüssel sind geschlossen allowlistet;
5. Adapter-, Pool-, Connect-Option-, Listener- und Enginekonfiguration.

Dadurch bleibt etwa MySQL mit `uri=true` ein Backendfehler und
SQLite/Aiosqlite mit `uri=true` ein Treiberfehler.

## Zulässige Kompatibilitätswerte

Zulässige URL-Werte für `timeout` und `check_same_thread` werden nicht als
Konfiguration übernommen. Die expliziten `connect_args` aus LQ-574
überschreiben sie weiterhin.

## PostgreSQL-Trennung

Der PostgreSQL-Zweig wird von der SQLite-Schlüsselprüfung nicht berührt.
Psycopg-Optionen in der URL bleiben erhalten, während der zentrale
Connect-Timeout über `connect_args` Vorrang hat.

## Aufbauwirkung

Die Prüfung öffnet keine Verbindung, lädt keinen optionalen Treiber und
registriert bei Ablehnung keine globalen SQLite-Adapter.

## Abgrenzung

LQ-578 ändert keine URL-Signatur, Migration, Tabelle, Portsignatur, Route, CLI
oder Entry-Point-Definition. LQ-579 prüft Wirkung und Reihenfolge regressiv.
