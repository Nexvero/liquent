# LQ-2635 — Initial Staging Runtime Input Gate

## Problem

Ein erfolgreich gerendertes Compose-Modell beweist nicht, dass dessen
Laufzeitdatei und dateibasierte Secrets auf dem Zielhost tatsächlich vorhanden
und befüllt sind. Ohne einen frühen Gate könnte PostgreSQL oder die Control
Plane deshalb erst nach Beginn des mutierenden Bootstrap-Laufs scheitern.

## Vertrag

Der Initial-Preflight verlangt die private, nicht leere `runtime.env` neben der
konfigurierten Basis-Compose-Datei. Das Secret-Verzeichnis muss ein absoluter,
nicht auf `/` zeigender Hostpfad sein. `database_url` und `postgres_password`
müssen darin jeweils als private, nicht leere reguläre Datei vorhanden sein.
Inhalte werden weder interpretiert noch ausgegeben.

Die Prüfung bleibt vor jeder Bootstrap-Mutation. Fehlende, leere, verlinkte
oder für Gruppe beziehungsweise andere Benutzer lesbare Eingaben führen zu
einer detailarmen Ablehnung.

## Grenze

Die drei Research-Worker-Hosteingaben sind bewusst kein Initial-Bootstrap-Gate:
dieser Lauf startet nur PostgreSQL, Migration und Control Plane. Worker-ID,
Worker-Konfiguration und Forschungsdaten erhalten vor einer späteren
Worker-Aktivierung einen eigenen Readiness-Gate. Der Slice erzeugt keine
Secrets und startet keinen Dienst. Das erst mit Grafana benötigte
Administratorpasswort bleibt ebenfalls dessen späterem Aktivierungsgate
vorbehalten.
