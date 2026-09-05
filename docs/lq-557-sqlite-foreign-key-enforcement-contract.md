# LQ-557 — SQLite Foreign-key Enforcement Contract

## Ergebnis

LQ-557 schließt eine bestehende Abweichung zwischen SQLite-Schema und
Laufzeitverhalten: Jede durch die zentrale Enginefactory geöffnete
SQLite-Verbindung muss deklarierte Fremdschlüssel durchsetzen.

## Beobachtbarer Vertrag

Für dateibasierte und gemeinsam prozesslokale In-Memory-SQLite-Engines gilt
auf jeder neuen DBAPI-Verbindung `PRAGMA foreign_keys=ON`.

Ein Schreibvorgang, der auf keinen vorhandenen Elternschlüssel verweist, wird
von SQLite abgewiesen. Die Enginefactory ersetzt oder übersetzt diesen
technischen Datenbankfehler nicht; bestehende Adaptergrenzen behalten ihre
jeweilige detailfreie Fehlerabbildung.

## Verbindungslebensdauer

SQLite verwaltet die Einstellung pro Verbindung. Darum wird sie beim
Connect-Ereignis gesetzt und nicht nur einmal beim Engineaufbau geprüft.

Nach Pool-Reconnect oder Engine-Disposal erhält jede neue Verbindung dieselbe
Einstellung. Ein Aufrufer muss das Pragma nicht erneut registrieren.

## Transaktionsgrenze

Die Aktivierung erfolgt unmittelbar nach Erzeugung der DBAPI-Verbindung und
vor deren erster fachlicher Transaktion. Sie öffnet keine fachliche
Transaktion und führt keine Migration aus.

LQ-557 ändert keine Deferrability-, Cascade-, Locking- oder
Isolationseigenschaft vorhandener Constraints.

## Dialektgrenze

Der Vertrag gilt ausschließlich für SQLite. PostgreSQL erzwingt seine
Constraints serverseitig und erhält weder ein Pragma noch einen
SQLite-Connect-Listener.

## Abgrenzung

LQ-557 ergänzt keine Migration, Tabelle, Constraintdefinition, Portsignatur,
Route, CLI, Entry Point oder Productionaktivierung.

LQ-558 implementiert die Aktivierung zentral in der Enginefactory.
