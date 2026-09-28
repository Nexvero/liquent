# LQ-1188 — Joint Engine API Durable Marker Preservation

## Ergebnis

Belässt den vollständig geschriebenen Marker bei nachgelagertem Directory-fsync-Fehler unverändert.

## Grenze

Der auslösende Aufruf bleibt technisch unavailable und behauptet keinen Erfolg.
