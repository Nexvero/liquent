# LQ-559 — SQLite Foreign-key Regression Evidence

## Ergebnis

LQ-559 belegt die zentrale Fremdschlüsselaktivierung an den beobachtbaren
Enginegrenzen.

## In-Memory-SQLite

Sowohl `sqlite://` als auch `sqlite:///:memory:` melden auf ihrer Verbindung
`PRAGMA foreign_keys=1`.

Die Regression legt Eltern- und Kindtabelle an und bestätigt, dass ein Kind
mit unbekanntem Elternschlüssel als `IntegrityError` abgewiesen wird. Damit
wird nicht nur der Pragmawert, sondern seine tatsächliche Wirkung geprüft.

## Dateibasiertes SQLite

Eine dateibasierte Engine meldet die Aktivierung auf der ersten Verbindung.
Nach `dispose()` erzeugt der nächste Zugriff eine Ersatzverbindung, die das
Pragma erneut mit Wert 1 erhält.

Damit hängt die Zusage nicht von einem einzelnen Poolslot oder einer einmalig
vorbereiteten Verbindung ab.

## PostgreSQL und Fehlerpfad

Ein direkt geprüfter PostgreSQL-Factoryaufruf registriert keinen
SQLite-Connect-Listener und öffnet keine Verbindung.

Ein künstlich fehlschlagendes Pragma bestätigt, dass der Listener seinen
Cursor auch im Fehlerfall schließt und den technischen Fehler nicht verdeckt.

## Fokussierter Lauf

Neue Regressionen, bestehende Enginekonfiguration, zwei bisher lokal
aktivierende Persistenzbereiche und das Migrationsgate bestehen gemeinsam mit
39 Tests unter `-W error::DeprecationWarning`.

## Abgrenzung

LQ-559 behauptet keine neue Constraintdefinition, Cascade-Semantik,
PostgreSQL-Regel oder fachliche Fehlerabbildung.

LQ-560 führt den vollständigen Normal-, PostgreSQL-, Wheel-, Inventar- und
Diffaudit aus.
