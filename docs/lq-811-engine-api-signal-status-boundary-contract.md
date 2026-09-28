# LQ-811 — Engine API Signal Status Boundary Contract

## Ziel

Der vollständig komponierte Proxy darf `stopped` erst publizieren, nachdem auch
die äußere Signalownership erfolgreich zurückgegeben wurde.

## Aufgeschobene Terminalität

Nur die vollständige Composition aktiviert deferred terminal status. Der innere
Process Run endet nach Listener-Retire in `stopping`.

Erfolgreiches Signal-Restore finalisiert `stopping → stopped`. Restorefehler
finalisiert `stopping → failed`. Installfehler vor dem inneren Run finalisiert
`initial → failed`.

Ein bereits innerlich gesetztes `failed` bleibt beim äußeren Fehlerabschluss
unverändert. Terminale Zustände werden nicht überschrieben.

## Kompatibilität

Direkt konstruierte Process Runs bleiben selbstfinalisierend und akzeptieren
keine äußere Finalisierung. Bestehende isolierte Signal-Run-Doubles ohne deferred
Status behalten ihren bisherigen Ablauf.

## Grenzen

Kein Healthtransport, Logging, Restart, Deployment oder Signalverhaltenswechsel
wird ergänzt.
