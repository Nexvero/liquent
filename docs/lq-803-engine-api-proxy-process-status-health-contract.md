# LQ-803 — Engine API Proxy Process Status and Health Contract

## Ziel

Der Proxy erhält ein strukturiertes, threadsicheres und detailbegrenztes
Prozessstatusmodell, bevor eine externe Health- oder Deploymentgrenze geöffnet
wird.

## Phasen

Der normale monotone Pfad ist `initial`, `starting`, `serving`, `stopping`,
`stopped`. `failed` ist von jedem nichtterminalen Zustand erreichbar.

Übersprungene, wiederholte oder rückwärts gerichtete Übergänge scheitern
fail-closed. `stopped` und `failed` sind terminal und nicht wiederverwendbar.

## Snapshot

Jeder unveränderliche Snapshot enthält ausschließlich Phase, live, ready,
terminal und einen festen öffentlichen Grund.

Nur `serving` ist ready. Nichtterminale Phasen sind live; terminale Phasen sind
nicht live. Pfade, IDs, Settings, Austauschzahlen, Exceptions und Hostdetails
werden nicht veröffentlicht.

## Concurrency

Lesen und Übergänge werden durch genau einen internen Lock serialisiert. Bei
konkurrierendem Übergang kann nur ein Caller gewinnen.

## Grenzen

Kein Listenerhook, Runinstrumentierung, HTTP-Endpoint, Logging, Deployment oder
Productionclaim wird in diesem Slice ergänzt.
