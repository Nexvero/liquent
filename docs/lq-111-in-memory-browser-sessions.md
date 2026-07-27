# LQ-111 — In-Memory Browser Sessions

## Status

- Ein kleiner `InMemoryBrowserSessions`-Adapter erfüllt den bestehenden
  `BrowserSessionLookup`-Port für Tests und lokale Ausführung.
- Der Adapter übernimmt eine Kopie vorgegebener Session-Records.
- Bekannte Records werden ausschließlich über die bestehende pure
  Gültigkeitsprüfung aufgelöst.
- Unbekannte, abgelaufene und widerrufene Sessions liefern neutral `None`.

## Grenze

Die Uhr wird explizit injiziert. Der Lookup verändert weder Records noch Zeit
und bietet keine Schreiboperationen. Damit ist er reproduzierbar, aber kein
Produktionsspeicher.

## Bewusst nicht enthalten

- kein Anlegen, Verlängern, Rotieren oder Widerrufen von Sessions,
- keine Datenbank oder verteilte Konsistenz,
- keine automatische Injection in die HTTP-Anwendung,
- keine Cookie-Ausgabe oder Login-/Logout-Route,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

Vor einem schreibenden Session-Lifecycle muss LQ-112 dessen Befehlsgrenze und
atomare Rotationsregeln festlegen. Shared Environments bleiben gesperrt.
