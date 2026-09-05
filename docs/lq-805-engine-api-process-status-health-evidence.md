# LQ-805 — Engine API Process Status and Health Evidence

## Lebenszyklusevidenz

Tests belegen alle normalen Phasen und Failure aus jedem nichtterminalen Zustand.
Übersprungene Übergänge sowie jede Wiederverwendung terminaler Zustände werden
abgelehnt, ohne den aktuellen Zustand zu verändern.

## Snapshotevidenz

Phase, live, ready, terminal und feste Gründe werden für den gesamten normalen
Pfad geprüft. Snapshots sind unveränderlich und Status-Repr enthält keine
Lock- oder privaten Details.

## Probe

Die Readinessprojektion wird in jeder Phase geprüft. Fremde Statusobjekte werden
abgelehnt; eine gebrochene Snapshotgrenze liefert detailfrei nicht-ready.

## Concurrency

Acht konkurrierende Startübergänge ergeben exakt einen Gewinner, sieben
Ablehnungen und einen vollständigen `starting`-Zustand.
