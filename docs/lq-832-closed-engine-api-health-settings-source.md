# LQ-832 — Closed Engine API Health Settings Source

## Umsetzung

`from_mapping` auf der Health-Socket-Authority prüft Schlüsseltopologie,
kanonischen Rohpfad und kanonische Dezimalwerte, bevor das bestehende
Authorityobjekt konstruiert wird.

`load_manifest_handoff_supervisor_engine_api_health_authority` öffnet genau einen
expliziten Pfad descriptorgebunden, prüft private Fakten, liest begrenzt und
bestätigt dieselben Fakten erneut.

Die geschlossene Environmentprojektion entfernt nur das feste Präfix und bildet
Namen auf lowercase ab. Werte werden nicht getrimmt, expandiert oder
interpoliert.

## Nicht umgesetzt

Keine globale Umgebung, gemeinsame Proxydatei, Pydantic-Gruppe, CLI,
Listenerwirkung oder Productionverdrahtung.
