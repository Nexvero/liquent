# LQ-613 — Supervisor Launch File Safety Evidence

## Ergebnis

LQ-613 belegt die LQ-612-Dateigrenze auf einem realen lokalen temporären
Dateisystem.

## Erfolgsnachweis

Publikation erzeugt exakt `launch-binding.json` mit kanonischen Bytes, Modus
`0600` und Linkanzahl eins.

Read rekonstruiert das vollständige Launchdokument.

Keine Pending-Datei bleibt zurück.

## Retries

Ein identischer Retry bewahrt Inode und Änderungszeit und liefert denselben
Published-Nachweis.

Ein divergenter Retry liefert feldlosen Konflikt und verändert kein Byte.

## Abwesenheit und Fehler

Fehlender Bestand liefert `None`.

Unbekannte Directory-ID bleibt detailfrei technisch unverfügbar.

Modi `0644`, `0400` und `0666`, Symlinks und mehrfach verlinkte Dateien werden
abgelehnt.

## Keine Productionevidence

LQ-613 belegt keine Containerlesbarkeit, Dockerlabels, Mounts oder
Prepare-Reihenfolge.

## Nächster Slice

LQ-614 führt den Abschlussaudit gegen Codec, Architektur und Regression aus.
