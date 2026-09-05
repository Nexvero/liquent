# LQ-796 — Closed Owner-only Engine API Proxy Settings Source

## Umsetzung

`load_manifest_handoff_supervisor_engine_api_proxy_settings` öffnet genau einen
expliziten absoluten Pfad mit No-follow und Close-on-exec.

Der Loader prüft vollständige private Dateifakten, liest begrenzt über denselben
Deskriptor, bestätigt unveränderte Fakten und decodiert danach die geschlossene
Environmentprojektion.

Die projizierten Namen werden ausschließlich durch Entfernen des festen Präfixes
und ASCII-Lowercase auf die bekannten Settingsfelder abgebildet. Werte werden
nicht getrimmt, expandiert oder interpoliert.

## Ownership

Der Loader schließt seinen Deskriptor auf jedem Pfad. Er speichert weder Datei
noch Rohinhalt im Ergebnis.

## Nicht umgesetzt

Keine globale Umgebung, Pydantic-Integration, CLI, Compositionausführung,
Signalinstallation, Socketöffnung oder Productionfreigabe.
