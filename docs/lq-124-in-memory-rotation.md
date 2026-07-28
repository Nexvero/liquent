# LQ-124 — In-Memory Rotation

## Ergebnis

Der lokale `InMemoryBrowserSessions`-Adapter erfüllt zusätzlich den
`BrowserSessionRotationStore`-Port. Damit können Erzeugung, Lookup und atomare
Rotation lokal denselben Store verwenden.

## Verhalten

- Die aktuelle Session muss vorhanden, nicht abgelaufen und nicht widerrufen sein.
- Die Replacement-ID muss frei und von der aktuellen ID verschieden sein.
- Der Principal des Replacement-Records wird ausschließlich aus dem bestehenden
  Record übernommen; CSRF-Nachweis und Ablauf stammen aus dem übergebenen
  `IssuedBrowserSession`.
- Bei Erfolg wird der alte Record mit einem einzigen gelesenen Uhrzeitwert
  widerrufen und der neue Record angelegt. Ein vollständiger neuer
  Records-Snapshot wird aufgebaut und in einem Schritt übernommen, sodass alte
  und neue Session nie gleichzeitig aktiv beobachtbar sind.
- Unbekannte, abgelaufene oder widerrufene Quelle, Ziel-ID-Kollision, identische
  aktuelle und neue ID oder ein bereits abgelaufenes Replacement lassen den
  gesamten Zustand unverändert und liefern neutral `False`.
- Die injizierte Uhr wird höchstens einmal pro Rotationsversuch gelesen und nur,
  wenn die Quelle existiert und eine Zeitprüfung erforderlich ist.
- Rückgabe und Fehler enthalten kein internes Session-Material.

## Bewusst nicht enthalten

- keine Threading-Infrastruktur, Locks oder Transaktionen,
- keine Datenbank oder verteilte Konsistenz,
- keine HTTP-, Cookie-, Login-/Logout- oder Provider-Integration,
- keine CORS-, Deployment- oder Shared-Environment-Änderung,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-125 kann den idempotenten Widerruf als Port und Anwendungsfall ergänzen.
Persistente oder verteilte Speicherung bleibt eine separate
Architekturentscheidung.
