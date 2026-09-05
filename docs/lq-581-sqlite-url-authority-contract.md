# LQ-581 — SQLite URL Authority Contract

## Ergebnis

LQ-581 schließt die Authority-Komponente von SQLite-URLs an der zentralen
Enginefactory.

SQLite-Verbindungsadressen dürfen keinen Benutzernamen, kein Passwort, keinen
Host und keinen Port enthalten. SQLite wird ausschließlich als Engine-lokale
In-Memory-Datenbank oder über einen Authority-freien Dateipfad verwendet.

## Begründung

SQLite ist in diesem System keine netzwerkadressierte Datenbank und führt keine
serverseitige Authentifizierung aus. Authority-Felder haben daher keine
legitime Laufzeitwirkung.

Ihre Annahme würde außerdem Zugangsdatenähnliche Werte bis in tiefere
SQLAlchemy- oder Treiberfehler tragen, obwohl SQLite sie nicht benötigt.

## Ablehnung

Ist mindestens eines der vier Authority-Felder vorhanden, endet der
Factoryaufruf vor Adapterregistrierung, Querypolicy, Poolkonfiguration,
Engineaufbau, Treiberimport und Verbindung mit genau
`unsupported_database_url_authority`.

URL, Benutzername, Passwort, Host und Port werden nicht wiedergegeben. Cause
und Context bleiben leer; es entsteht kein neuer Exceptiontyp.

## Gültige SQLite-Formen

`sqlite://` und `sqlite:///:memory:` bleiben die beiden Engine-lokalen
In-Memory-Formen. Authority-freie relative und absolute Dateipfade bleiben
zulässig, vorbehaltlich der bestehenden geschlossenen Querypolicy.

## Prüfungsreihenfolge

URL-, Backend- und Treiberprüfung behalten Vorrang. Für eine gültige
SQLite/Pysqlite-URL folgt danach Authority vor Queryschlüsseln. Eine URL mit
Authority und unzulässiger Query endet daher als Authorityablehnung.

## PostgreSQL

PostgreSQL benötigt Benutzer, Passwort, Host und Port als reguläre
Verbindungsangaben und bleibt vollständig außerhalb dieses SQLite-Vertrags.

## Abgrenzung

LQ-581 ergänzt keine SQLite-Netzwerk-, Credential- oder Remote-Dateisemantik,
Migration, Portsignatur, Route, CLI oder Entry-Point-Wirkung.

LQ-582 setzt die Authoritygrenze zentral um.
