# LQ-780 — Owned Engine API Signal Stop Source

## Umsetzung

`OwnedManifestHandoffSupervisorEngineApiSignalStopSource` hält Aktivstatus,
Stopzustand, ursprüngliche Handler und die tatsächlich installierte Teilmenge.

Konstruktion und `requested` lesen oder verändern keine globalen Signalhandler.
`install` validiert den Main Thread, erfasst beide Originale und installiert eine
gebundene minimale Handlermethode.

`restore` bearbeitet die installierte Liste rückwärts und versucht immer alle
Einträge. Der interne aktive Zustand wird auch bei Restorefehler beendet.

## Detailfreiheit

Thread-, Get-, Set-, Rollback- und Restorefehler werden auf die bestehende
detailfreie technische Nichtverfügbarkeit reduziert.

## Nicht umgesetzt

Kein Signalversand, Wakeup-FD, Listenerclose, Acceptinterrupt, Thread,
Prozessentrypoint oder Run-Composition wird ergänzt.
