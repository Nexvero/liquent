# LQ-1184 — Joint Engine API Pre-durable Marker Cleanup

## Ergebnis

Entfernt bei Write- oder Datei-fsync-Fehler den neuen Marker descriptor-relativ und synchronisiert das Register erneut.

## Grenze

Bestehende Marker werden niemals durch Cleanup berührt.
