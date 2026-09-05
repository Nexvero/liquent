# LQ-696 — Supervisor Appfactory Health and Close Composition

## Umsetzung

`create_app` akzeptiert drei neue gekoppelte Argumente für Prozess, Probe und
Eigentümerschaft.

## Fail-fast

Jede unvollständige Kombination, geschlossene Settings, fehlende explizite
Engine, fremder Probe oder gemischte externe Healthinstanz wird vor Aufbau der
App abgelehnt.

Es gibt keinen Settings-only- oder Health-only-Erfolg.

## Readiness

Der neue Probe übersetzt die unveränderliche Kandidatenaussage in
`manifest_handoff_supervisor_not_ready`.

Unerwartete technische Probefehler werden detailfrei als
`manifest_handoff_supervisor_unavailable` sichtbar.

## Lifecycle

Nach `mark_stopping` wird der besessene Supervisorprozess auch dann geschlossen,
wenn weitere Ressourcen eigene Cleanupwege besitzen.

Die explizite Datenbank-Engine wird nicht disponiert.

## Unverändert

Routen, Appzustand und öffentliche Supervisoroperationen werden nicht erweitert.
