# LQ-582 — Fail-closed SQLite URL Authority Boundary

## Ergebnis

LQ-582 setzt den LQ-581-Vertrag in `build_engine` nach der Treiber- und vor der
SQLite-Queryprüfung um.

Die strukturierte SQLAlchemy-URL stellt `username`, `password`, `host` und
`port` getrennt bereit. Sobald einer dieser Werte nicht `None` ist, endet die
Factory mit `unsupported_database_url_authority`.

## Vollständige Reihenfolge

Die frühe SQLite-Prüfung lautet:

1. URL ist parsbar;
2. Backend ist unterstützt;
3. Treiber ist synchron allowlistet;
4. SQLite-Authority ist vollständig leer;
5. SQLite-Queryschlüssel sind geschlossen allowlistet;
6. Adapter-, Pool-, Connect-Option-, Listener- und Enginekonfiguration.

Ein leerer Benutzername mit vorhandenem Passwort gilt ebenfalls als
Authority. Die Entscheidung basiert auf strukturierten Feldern, nicht auf
Substring- oder Präfixprüfung.

## Keine Nebenwirkung

Bei Ablehnung wird `create_engine` nicht aufgerufen und kein globaler
SQLite-Adapter registriert. Es wird weder Datei- noch Netzwerkzugriff
versucht.

## Bewahrte Pfade

Authority-freie SQLite-Datei- und In-Memory-URLs behalten Pool-, Timeout-,
Thread-, Fremdschlüssel- und Queryverträge.

PostgreSQL/Psycopg behält Benutzer-, Passwort-, Host- und Portfelder sowie den
zentralen Connect-Timeout.

## Abgrenzung

LQ-582 ändert keine Productionkonfiguration, Migration, Tabelle,
Portsignatur, Route, CLI oder Entry-Point-Definition.

LQ-583 prüft Authorityfelder, Reihenfolge und Dialekttrennung regressiv.
