# LQ-2639 — Bootstrap Parent Deployment Config Load

## Beobachtung

Der erste bestätigte Initial-Bootstrap-Versuch endete nach erfolgreichem
Preflight und vor seiner ersten Mutation. `DEPLOY_STATE_DIR` war im
Bootstrap-Prozess nicht gesetzt. Der als separates Programm aufgerufene
Preflight lädt die private Deployment-Konfiguration nur in seinen eigenen
Prozess und kann diese Werte nicht an den aufrufenden Prozess zurückgeben.

Der Abbruch erfolgte vor Run-Verzeichnis, Imageänderung, Netzwerkerzeugung,
Containerstart, Migration oder Host-nginx-Handoff. Der bestehende Hostdienst
blieb aktiv; ein Rollback war nicht erforderlich.

## Korrektur

Der Bootstrap lädt die validierte Deployment-Konfiguration nun selbst direkt
nach Root- und Bestätigungsgate. Erst danach ruft er den weiterhin
eigenständigen read-only Preflight auf. Eine Regression bindet diese Reihenfolge
vor Image-Pull und jeder mutierenden Handlung.

## Grenze

Die Korrektur verändert keine Konfigurationswerte und lockert keinen
Preflight. Sie startet selbst keinen Dienst und wiederholt den Bootstrap erst
nach erneutem integriertem Reviewstand. Die ursprüngliche explizite
`INITIALIZE-STAGING`-Bestätigung bleibt Voraussetzung jedes Versuchs.
