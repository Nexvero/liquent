# LQ-2628 — Incremental Pre-Staging Manifest Test Applicability

## Problem

Zwei LQ-424-Regressionen setzten voraus, dass jeder nicht leere Arbeitsbaum
weiterhin den historischen vollständigen Release-Reviewumfang enthält. Nach
dem Merge besteht ein legitimer Folgeslice jedoch nur aus seinen inkrementellen
Dateien. Die Tests versuchten dann `.grype.yaml`, `Dockerfile` und zwei
Secret-Negativfixtures in einem Manifest zu prüfen, das diese Dateien korrekt
nicht enthielt.

## Korrektur

Die allgemeine Prüfung jedes realen Manifestmitglieds und der vollständigen
Review-Section-Abdeckung bleibt unverändert aktiv. Nur die zwei
scope-spezifischen historischen Assertions werden übersprungen, wenn ihr
vollständiger kumulativer Eingabeumfang nicht Teil des aktuellen Manifests ist.

Sobald der historische Scope vollständig vorhanden ist, laufen dieselben
Assertions weiterhin unverändert: Root-Sicherheitseingaben müssen alle
Review-Sections tragen und die PRIVATE-KEY-Markersuche darf exakt die beiden
bekannten Negativfixtures finden.

## Grenze

Produktionscode, Manifestformat, Secret-Erkennung und Reviewklassifikation
werden nicht gelockert. Die Änderung entfernt ausschließlich die falsche
Annahme, ein inkrementeller Post-Merge-Slice müsse Dateien außerhalb seines
Git-Scopes enthalten.
