# LQ-1140 — Durable Joint Engine API Run Acceptance Registry

## Ergebnis

Schreibt Modus 0600, fsynct Marker und Registerverzeichnis und ersetzt niemals ein bestehendes Ziel.

## Grenze

Symlinks, relative Wurzeln und nichtprivate Verzeichnisse scheitern detailfrei.
