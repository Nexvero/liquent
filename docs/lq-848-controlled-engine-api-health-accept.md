# LQ-848 — Controlled Engine API Health Accept

## Ergebnis

Implementiert einen Health-spezifischen Accept mit exakter Exchange-Abhängigkeit, unverändertem Socketpfad und positivem Timeout.

## Grenze

Der akzeptierte Client wird bei Erfolg und Fehler genau einmal geschlossen.
