# LQ-570 — Central SQLite Foreign-key Test Adoption

## Ergebnis

LQ-570 entfernt die 16 in LQ-569 inventarisierten lokalen Listener und bindet
die betroffenen Tests damit ausschließlich an die zentrale Aktivierung aus
`build_engine`.

## Mechanische Änderung

Aus jedem betroffenen Testmodul wurden nur der `event.listens_for`-Dekorator,
die zugehörige Listenerfunktion und der anschließend unbenutzte `event`-Import
entfernt.

Mehrzeilige Cursorimplementierungen und kompakte einzeilige Listener werden
gleich behandelt. Es wird kein gemeinsamer Testhelper und keine neue Fixture
eingeführt.

## Bewahrte Testsemantik

Alle Enginefixtures, Migrationen, Seeds, Transaktionen und fachlichen
Assertions bleiben erhalten. Insbesondere bleiben vorhandene negative
Fremdschlüssel- und `IntegrityError`-Nachweise unverändert.

Die Tests verwenden weiterhin dateibasierte SQLite-Engines über die zentrale
Factory. Daher setzt jede neu erzeugte DBAPI-Verbindung das Pragma vor dem
ersten fachlichen Zugriff.

## Produktionsgrenze

LQ-570 ändert keine Datei unter `src/`, keine Migration und keine
Laufzeitkonfiguration. Die Produktionswirkung stammt unverändert aus LQ-558.

## Abgrenzung

Die fokussierten LQ-558-Tests bleiben unangetastet, weil sie den Listener
selbst, Reconnect, tatsächliche Constraintabweisung und Fehlerressourcen
prüfen.

LQ-570 ergänzt keine neue Testabstraktion, Portsignatur, Route, CLI oder
Entry-Point-Wirkung. LQ-571 führt die bereinigten Bereiche gemeinsam aus.
