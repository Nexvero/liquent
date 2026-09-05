# LQ-1187 — Joint Engine API Post-fsync Unknown Outcome Contract

## Ergebnis

Klassifiziert Fehler nach erfolgreichem Datei-fsync als unbekannten Ausgang ohne automatische Rücknahme.

## Grenze

Ein möglicherweise dauerhafter Marker darf niemals heuristisch gelöscht oder neu geschrieben werden.
