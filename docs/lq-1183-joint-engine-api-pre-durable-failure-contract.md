# LQ-1183 — Joint Engine API Pre-durable Failure Contract

## Ergebnis

Definiert Fehler vor erfolgreichem Marker-fsync als sicher bereinigbares unvollständiges Write.

## Grenze

Nur der in diesem Aufruf neu angelegte, noch nicht durable Marker darf entfernt werden.
