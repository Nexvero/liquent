# LQ-292 — Persistent Research Job Adapters

## Ergebnis

LQ-292 implementiert die LQ-291-Ports als gemeinsame SQLite-/PostgreSQL-
Persistenzgrenze und erweitert den Migration-Head additiv auf `20260819_0026`.

## Persistente Fakten

Die Migration speichert Jobs, unveränderliche Acceptance-/Jobbindungen und
jeweils den aktuellen Claim. Jobs binden Actor, Workspace, kanonischen
Snapshot, kontrollierte Artifactklasse, Status, Revision und serverbestimmte
Zeitpunkte. Sie erzeugt keine Seeds oder Authorityfakten.

## Acceptance

Acceptance löst aktive User-, Workspace- und Membershipfakten sowie
`research:write` innerhalb der Transaktion auf. Exakter Retry rekonstruiert
denselben Job; abweichende Wiederverwendung liefert den detailfreien Konflikt.
Ohne Authority entsteht kein Job.

## Claim und Lease

FIFO-Auswahl erfolgt nach Annahmezeit und Job-ID. PostgreSQL sperrt den
Kandidaten mit `FOR UPDATE SKIP LOCKED`; SQLite trägt den funktionalen lokalen
Pfad. Entzogene queued Jobs werden atomar invalidiert und übersprungen.

Claim-ID, Revision, Claimzeit und Ablauf entstehen innerhalb der kontrollierten
Grenze. Es bleibt keine Transaktion während der Ausführung offen.

Heartbeat vergleicht Job, aktuelle Revision, Worker und Claim. Stale, fremde,
terminale oder abgelaufene Bindungen bleiben neutral und unverändert.

## Autorisierter Lookup

Lookup löst aktive `research:read`- oder durch die bestehende Policy
implizierende `research:write`-Capability bei jedem Aufruf neu auf. Fehlender
Job und fehlende Authority bleiben dasselbe `None`; Claimdetails verlassen die
Grenze nicht.

## Fehler- und Scopegrenze

Technische Fehler werden als detailfreie `ResearchJobStoreUnavailable`
vereinheitlicht. Der Slice implementiert keine Finalisierung, Recovery,
Cancellation, Artifactpersistenz, Queuebibliothek, CLI, Workerloop, Route oder
Production-Wiring.

Die vollständige lokale Suite besteht mit 3329 Tests, 98 erwarteten
PostgreSQL-Skips und 595 Warnungen.

## Implementierungsfolge

LQ-293 kann die kontrollierte Composition von persistenter Control Plane und
Research-Worker entscheiden, ohne Resultfinalisierung vorwegzunehmen.
