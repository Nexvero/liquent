# LQ-2630 — Staging Runtime and Host Interpolation Separation

## Problem

Die drei Hostpfade des Research Workers standen in `runtime.env.example`.
Diese Datei wird über Compose `env_file` an alle Anwendungsrollen übergeben.
Control Plane und Migration hätten dadurch unbekannte `LIQUENT_*`-Variablen
erhalten und wären an der absichtlich strikten Settings-Grenze gescheitert.

## Korrektur

Die drei Werte liegen nun in `images.env.example`. Diese Datei dient bereits
als explizite Compose-Interpolationseingabe und wird nicht als Prozessumgebung
in Container injiziert. Die Pfade bleiben absolute, nicht geheime
Betreiberwerte; Worker-Konfiguration, stabile Worker-ID und Forschungsdaten
werden dadurch weder erzeugt noch aktiviert.

Der Initial-Preflight liest dieselbe operator-owned Datei vor jeder Mutation.
Er bindet das konfigurierte Anwendungsimage exakt an den übergebenen
Releasekandidaten und verlangt für die drei im Basisvertrag enthaltenen
Infrastrukturrollen PostgreSQL, Prometheus und Grafana jeweils einen
vollständigen Registry-SHA-256-Digest. Tags, Platzhalter und fehlende Werte
scheitern fail-closed.

## Grenze

Die Trennung erzeugt keine Laufzeitdateien oder Secrets. Der noch nicht
veröffentlichte Backup-Image-Digest wird nicht durch einen beliebigen
syntaktisch gültigen Ersatz umgangen; LQ-2631 trennt ihn vom Initialstart.
