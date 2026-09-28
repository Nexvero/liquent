# LQ-577 — SQLite URL Query Policy Contract

## Ergebnis

LQ-577 schließt die SQLite-URL-Queryfläche der zentralen Enginefactory.

SQLite-Verbindungsadressen dürfen nur die Kompatibilitätsschlüssel `timeout`
und `check_same_thread` enthalten. Deren Werte besitzen keine Policywirkung,
weil LQ-573/LQ-574 sie zentral auf 5 beziehungsweise `False` überschreiben.

## Abgelehnte Optionen

Alle anderen SQLite-Queryschlüssel werden fail-closed abgelehnt. Dazu gehören
insbesondere:

- `uri`, das den Dateinamen als SQLite-URI interpretieren würde;
- `mode`, einschließlich In-Memory- und Read-only-Modi;
- `cache`, einschließlich gemeinsamem Cache;
- `immutable` und `nolock`, die Schreib- und Lockingannahmen verändern;
- unbekannte oder zukünftige Treiberoptionen.

Damit entscheidet nicht der Aufrufer über Dateisemantik, Lebensdauer,
Schreibbarkeit, Cacheteilung oder Locking.

## Fehleroberfläche

Eine nicht erlaubte SQLite-Option wird vor Adapterregistrierung,
Poolkonfiguration, Engineaufbau, Treiberimport und Verbindung mit genau
`unsupported_database_url_option` abgelehnt.

Schlüssel, Wert, URL und Zugangsdaten werden nicht wiedergegeben. Cause und
Context bleiben leer; es entsteht kein neuer Exceptiontyp.

## Prüfungsreihenfolge

Ungültige URL, nicht unterstütztes Backend und nicht unterstützter Treiber
behalten Vorrang. Erst eine syntaktisch gültige, SQLite/Pysqlite-gebundene URL
erreicht die Querypolicy.

## PostgreSQL

PostgreSQL-Queryparameter bleiben außerhalb dieses SQLite-Vertrags. Sie können
weiterhin server- und Psycopg-spezifische Verbindungsangaben tragen; der
zentrale `connect_timeout=3` behält dennoch Vorrang.

## Abgrenzung

LQ-577 ergänzt keine URI-Unterstützung, dynamische Allowlist,
Konfigurationsoption, Migration, Portsignatur, Route, CLI oder Entry Point.

LQ-578 setzt die geschlossene Querypolicy zentral um.
