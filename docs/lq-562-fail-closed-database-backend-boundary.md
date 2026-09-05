# LQ-562 — Fail-closed Database Backend Boundary

## Ergebnis

LQ-562 setzt den LQ-561-Vertrag am Anfang von `build_engine` um.

Die Factory parst zuerst die URL. Parser- und Typfehler werden intern
verworfen; die stabile `ValueError`-Ablehnung entsteht danach außerhalb des
technischen Handlers. Dadurch besitzt sie weder Cause noch Context.

## Prüfungsreihenfolge

Nach erfolgreichem Parsing wird der Backendname ermittelt. Nur `sqlite` und
`postgresql` gelangen zur Adapter-, Pool-, Listener- und Enginekonfiguration.

Jeder andere Backendname endet mit
`unsupported_database_backend`, bevor `create_engine` aufgerufen wird. Somit
wird auch kein optionaler Fremdtreiber importiert und keine Verbindung
versucht.

## Unterstützte Zweige

SQLite registriert weiterhin explizite Python-3.12-ISO-Adapter, wählt abhängig
von der URL den vereinbarten Pool und aktiviert Fremdschlüssel pro Verbindung.

PostgreSQL behält begrenzten Queue-Pool und Connect-Timeout. Die neue Prüfung
öffnet auf keinem Zweig selbst eine Verbindung.

## Fehleroberfläche

Die Implementierung verwendet den vorhandenen eingebauten `ValueError` und
genau zwei konstante Gründe. Sie ergänzt keinen öffentlich zu importierenden
Exceptiontyp.

## Abgrenzung

LQ-562 ändert nicht die strengere Productionvalidierung der
`PlatformSettings` und behauptet keine Unterstützung jedes denkbaren Treibers
innerhalb eines zugelassenen Backendnamens.

Keine Migration, Tabelle, Portsignatur, Route, CLI oder Entry-Point-Wirkung.
LQ-563 prüft Reihenfolge, Geheimnisfreiheit und bestehende Zweige regressiv.
