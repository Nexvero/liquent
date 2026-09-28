# LQ-561 — Supported Database Backend Contract

## Ergebnis

LQ-561 macht die bislang implizite Datenbankgrenze der zentralen Enginefactory
beobachtbar: Liquent unterstützt dort ausschließlich die SQLAlchemy-Backends
`sqlite` und `postgresql`.

## Unterstützte Grenze

SQLite umfasst dateibasierte und die in LQ-553 definierten Engine-lokalen
In-Memory-URLs. PostgreSQL umfasst den bestehenden synchronen
Persistenzpfad; Productionkonfiguration verlangt weiterhin gesondert
`postgresql+psycopg`.

Die Backendentscheidung folgt der strukturiert geparsten SQLAlchemy-URL. Ein
caller-supplied Backendflag oder eine Allow-Behauptung existiert nicht.

## Nicht unterstützte Backends

Andere Backends werden vor Engineaufbau, Treiberimport, Poolerzeugung und
Verbindungsversuch fail-closed abgelehnt.

Die Ablehnung trägt nur den stabilen Grund
`unsupported_database_backend`. URL, Benutzername, Passwort, Host,
Datenbankname, Treiber- oder Parserdetail werden nicht wiedergegeben.

## Ungültige URL

Eine nicht parsbare oder typfalsche Eingabe wird getrennt mit dem stabilen
Grund `invalid_database_url` abgelehnt. Auch diese Ablehnung enthält keine
Eingabe- oder Parserdetails und keine verkettete technische Ursache.

## Bestehende Dialekte

Die Grenze verändert weder SQLite-Pool-, Adapter- und Fremdschlüsselverträge
noch PostgreSQL-Pool-, Timeout- oder serverseitige Constraintsemantik.

## Abgrenzung

LQ-561 führt keinen neuen Exceptiontyp, Treiber, Dialekt, Fallback oder
Konfigurationsparameter ein.

Es gibt keine Migration, Tabelle, Portsignatur, Route, CLI, Entry-Point- oder
Productionaktivierung. LQ-562 setzt die Ablehnung zentral um.
