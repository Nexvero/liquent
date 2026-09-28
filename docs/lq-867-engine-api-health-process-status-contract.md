# LQ-867 — Engine API Health Process Status Contract

## Ergebnis

Definiert einen monotonen, threadsicheren Health-Lifecycle von initial bis stopped oder failed.

## Grenze

Nur serving ist ready; stopped und failed sind terminal und nicht live.
