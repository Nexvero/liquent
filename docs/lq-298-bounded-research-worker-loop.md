# LQ-298 — Bounded Research Worker Loop

## Ergebnis

LQ-298 implementiert `ResearchWorkerLoop` als seriellen langlebigen Loop um
den kontrollierten LQ-295-Einzeljobprozessor.

Der Loop akzeptiert eine stabile Worker-ID, eine validierte Wait-/Backoffpolicy,
eine kontrollierte Jitterquelle sowie extern besessene Stop- und Waitgrenzen.

Er installiert keine Signale, liest keine Umgebung und startet keinen Thread
oder Prozess.

## Genau ein aktiver Job

Der Loop ruft `ProcessOneResearchJob.process` ausschließlich seriell auf.

Ein neuer Claim beginnt erst, nachdem der vorherige Aufruf vollständig mit
Erfolg, Fehler, Claimverlust oder technischer Nichtverfügbarkeit zurückgekehrt
ist. Es gibt keinen Threadpool, Prefetch, Batchclaim oder parallelen Heartbeat.

Die maximale interne Jobkonkurrenz ist damit strukturell eins.

## Stop-Semantik

Vor jedem neuen Einzeljobaufruf wird die extern besessene Stopgrenze geprüft.
Ist Stop bereits angefordert, entsteht kein Claim und der Loop kehrt neutral
mit seinen bisherigen Zählern zurück.

Jedes Warten ist über die injizierte `wait(timeout)`-Grenze unterbrechbar. Ein
Stop während Idle oder Backoff beendet den Loop vor einem weiteren Claim.

Ein Stop während synchroner Jobausführung bricht Runner oder Artifactwrite
nicht unkontrolliert ab. Der aktuelle Einzeljob darf seinen claimgebundenen
Abschluss versuchen; danach wird kein neuer Job begonnen.

## Idle-Warten

`idle` ist ein gesunder Queuezustand.

Der Loop wartet die positive begrenzte Idle-Dauer und pollt niemals ohne Pause.
Er erzeugt dabei weder Fehler noch Jobstatusmutation und führt kein internes
Logging pro leerem Poll ein.

## Technischer Backoff

Detailfreie Persistenz-, Processing- und Artifact-Nichtverfügbarkeit werden
gezählt und führen zu exponentiellem Backoff.

Der Backoff startet bei einem positiven Initialwert, verdoppelt sich und wird
am expliziten Maximum begrenzt. Nach einem gesunden Ergebnis einschließlich
`idle` wird er auf den Initialwert zurückgesetzt.

`claim_lost` wartet ebenfalls begrenzt, bevor ein neuer Claim versucht wird.
Der Loop erfindet keine Recovery oder Requeueentscheidung.

## Kontrollierter Jitter

Vor jedem Idle- oder Backoff-Wait wird genau ein Jitterwert innerhalb des
konfigurierten Bereichs bezogen.

Negative, nichtnumerische oder oberhalb des Maximums liegende Werte scheitern
fail-closed. Der Loop verwendet keine globale Zufallsquelle und akzeptiert
keinen Jitter aus einem Job oder Browserrequest.

## Ergebnis und Beobachtbarkeit

Nach Stop liefert `ResearchWorkerLoopResult` ausschließlich Zähler für:

- erfolgreich abgeschlossene Jobs;
- kontrolliert fehlgeschlagene Jobs;
- verlorene Claims;
- technische Nichtverfügbarkeit.

Das Ergebnis enthält keine Job-, User-, Workspace-, Claim-, Lease-, Pfad-,
Exception- oder Infrastrukturdetails.

## Policyvalidierung

Idle- und initiale technische Waitdauer müssen positiv sein. Maximum darf den
Initialwert nicht unterschreiten; Jittermaximum und alle Werte müssen endlich
nichtnegativ sein.

Ungültige Policy scheitert beim Objektaufbau vor Claim, Wait oder
Ressourcenzugriff.

## Nicht enthalten

LQ-298 implementiert keine Signalhandler, Processkonfiguration,
Worker-ID-Quelle, Readiness/Liveness, Logging, Telemetrie, Recovery,
Cancellation, CLI, Entry-Point, Compose- oder Production-Aktivierung.

Schema und Migration-Head bleiben `20260819_0027`; Bundle und Entry Points
bleiben unverändert.

Die vollständige lokale Suite besteht mit 3368 Tests, 98 erwarteten
PostgreSQL-Skips und 615 bestehenden Warnungen.

## Implementierungsfolge

LQ-299 sollte die geschlossene Research-Worker-Processkonfiguration und stabile
owner-kontrollierte Worker-ID-Quelle entscheiden und implementieren.

Danach kann ein Entry-Point Signalhandling, Composition, Readiness und den
LQ-298-Loop kontrolliert verbinden.
