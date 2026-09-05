# LQ-695 — Atomic Supervisor Appfactory Lifecycle Contract

## Ziel

Die HTTP-Appfactory erhält eine atomare Übergabegrenze für Kandidatenprozess,
Readinessbeitrag und Lifecycleeigentum.

## Atomare Gruppe

Gemeinsam erforderlich sind:

- exakt ein typisierter Kandidatenprozess
- exakt dessen typisierter Readinessprobe
- explizite Prozesseigentümerschaft
- vollständige Supervisor-Settings
- eine explizit übergebene Datenbank-Engine

Eine Teilgruppe scheitert beim Factory-Aufbau vor Lifespanstart.

## Identitätsbindung

Der Probe muss objektidentisch an den übergebenen Prozess gebunden sein.

Ein Probe eines anderen Graphen darf Readiness nicht bestätigen oder sperren.

## Health

Die Factory komponiert Datenbank- und Supervisorprobe in genau einen
process-eigenen `ProcessHealth`.

Eine fremd injizierte Healthinstanz darf nicht mit automatischer
Supervisorcomposition gemischt werden.

## Shutdown

Der Lifespan markiert zuerst stopping und schließt danach den besessenen
Supervisorprozess genau einmal.

OIDC-Client und app-eigene Datenbank-Engine folgen ihren bestehenden
Eigentumsregeln; eine explizite Engine bleibt fremd besessen.

## Productionstatus

Der Kandidatenprobe bleibt not-ready, solange das Prozessobjekt
`production_ready=false` meldet.

Entrypoint und Deployment wählen diese Grenze noch nicht aus.
