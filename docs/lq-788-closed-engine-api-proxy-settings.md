# LQ-788 — Closed Engine API Proxy Settings

## Umsetzung

`ManifestHandoffSupervisorEngineApiProxySettings` ist ein frozen, slots-basierter
Wert mit 21 expliziten Feldern.

`from_mapping` prüft zuerst exakte Mapform und Schlüsseltopologie, danach Pfade,
Commands, Identitäten, Timeouts und Grenzen. Erst nach vollständig erfolgreicher
Prüfung wird der unveränderliche Wert konstruiert.

Pfade werden mit ihrer `Path`-Repräsentation bytegenau auf kanonische Schreibweise
verglichen. Die fünf Hostpfade und die beiden Commands sind in ihren Gruppen
jeweils verschieden.

Integerparser akzeptieren ausschließlich kanonische ASCII-Ziffern und prüfen
ihre feldspezifischen geschlossenen Bereiche.

## Ownership

Die Eingabemap wird nicht gespeichert. Spätere Callermutation kann den
Settingswert nicht verändern.

## Nicht umgesetzt

Kein Environmentadapter, Pydantic-Feld, CLI, Secretreader, Fileloader, Reload,
Composition oder Entry Point wird ergänzt.
