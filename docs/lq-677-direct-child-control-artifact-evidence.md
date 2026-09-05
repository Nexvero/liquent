# LQ-677 — Direct Child Control Artifact Evidence

## Ergebnis

Ausführbare Evidenz belegt die direkte Directorybindung und unveränderte
Atomizität.

## Publish und Read

Ein kanonisches Ready-Artefakt wird unter dem festen Rollennamen publiziert und
über dieselbe gebundene ID byteidentisch gelesen.

Keine temporäre Datei bleibt zurück.

## Retry und Konflikt

Byteidentischer Retry bewahrt Inode und Mtime und führt keinen Rewrite aus.

Ein divergenter Record mit derselben Rolle liefert den bestehenden detailfreien
Artefaktkonflikt.

## Directorygrenzen

Falsche ID scheitert vor Dateizugriff.

Child-Directory mit falschem Modus sowie Symlink werden abgewiesen.

Ein Parent mit Modus 0755 verhindert die direkte Childprüfung nicht, weil nur
der gebundene Directorydescriptor die private Artefaktgrenze bildet.

## Oberfläche

Repräsentation enthält weder Pfad noch ID.

Delete-, Cleanup-, Overwrite- und Prozessmethoden fehlen konstruktiv.
