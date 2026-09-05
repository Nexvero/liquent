# LQ-808 — Instrumented Engine API Owned Process Run

## Umsetzung

`OwnedManifestHandoffSupervisorEngineApiProcessRun` besitzt nun eine exakte
`ManifestHandoffSupervisorEngineApiProcessStatus`-Instanz. Für bestehende direkte
Composition wird wirkungsfrei eine eigene Instanz erzeugt; die vollständige
Proxycomposition injiziert ihre explizite gemeinsame Instanz.

Der Run setzt Status ausschließlich an den bereits vorhandenen kontrollierten
Grenzen. Listenercleanup bleibt unverändert best-effort und entscheidet weiterhin
über Erfolg oder detailfreie technische Nichtverfügbarkeit.

Ein Fehler versucht genau einen Übergang nach `failed`. Ist der Status wegen
eines vorherigen Vertragsbruchs bereits terminal, wird dessen ursprüngliche
Terminalität nicht überschrieben.

## Nicht umgesetzt

Der Status wird noch nicht durch einen Healthtransport publiziert. Signal-
Install/Restore, Paketscript, Deployment und Restartpolicy bleiben separat.
