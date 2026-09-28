# LQ-297 — Complete Single Research Worker Composition

## Ergebnis

LQ-297 komponiert den vollständigen Pfad für die Verarbeitung genau eines
persistent angenommenen Research-Jobs.

`ResearchWorkerComposition` enthält die gemeinsame persistente Job-Composition
und einen `ProcessOneResearchJob`, der deren Worker-Control-Plane verwendet.

Der Slice baut ausschließlich Objekte. Er startet keinen Job, Worker, Loop,
Thread, Prozess oder Netzwerkzugriff.

## Injizierte Grenzen

`compose_research_worker` verlangt explizit:

- eine extern besessene Datenbank-Engine;
- einen geschlossenen `ResearchRunnerResolver`;
- einen extern besessenen `ArtifactStore`;
- getrennte Generatoren für Job-, Revision- und Claimidentitäten;
- eine positive Lease-Dauer;
- optional eine kontrollierte UTC-Clock.

Keine Abhängigkeit wird aus Umgebungsvariablen, globalem Zustand, Defaultpfad,
Importnamen oder Browserinput entdeckt.

## Genau eine persistente Wahrheit

Composition erzeugt exakt einen `DatabaseResearchJobs`.

Dieselbe Instanz trägt Browser-Acceptance, autorisierten Lookup, Worker-Claim,
Heartbeat sowie Erfolg- und Fehlerfinalisierung.

`ProcessOneResearchJob` verwendet exakt die daraus gebaute
`PersistentResearchWorkerControl`. Es gibt keinen zweiten Store,
In-Memory-Fallback, Queuecache oder abweichenden Finalizer.

## Side-Effect-freier Aufbau

Der Aufbau öffnet keine Datenbankverbindung und liest keine Migration oder
Queue. Er ruft weder Clock noch ID-Generator, Resolver oder ArtifactStore auf.

Insbesondere wird beim Aufbau kein Claim erzeugt, kein Snapshot aufgelöst, kein
Runner gestartet, kein Artifact gelesen oder geschrieben und kein Jobstatus
verändert.

Ungültige Leasedauer scheitert vor jedem Zugriff auf injizierte Ressourcen.

## Ressourcenbesitz

Engine, Resolver, ArtifactStore, Generatoren und Clock bleiben vollständig im
Besitz des Callers.

Die Composition bietet kein `close`, disposed keine Engine und schließt keine
Datei- oder Netzwerkressource. Ein späterer Prozess-Owner muss Lebenszyklus und
Shutdown explizit koordinieren.

## Ausführungsgrenze

Erst ein expliziter Aufruf von `composition.processor.process(worker_id)`
betritt den in LQ-295 definierten Einzeljobpfad.

Die stabile Worker-ID ist keine Session, Membership oder Permission. Aktuelle
Researchauthority wird weiterhin atomar beim LQ-292-Claim entschieden.

## Fehlergrenzen

Composition führt keine neue technische Exception ein.

Persistenz-, Resolver-, Runner-, Artifact- und Finalizerfehler behalten die
jeweils bereits geschlossenen LQ-292- bis LQ-296-Grenzen. Der Aufbau fängt keine
Fehler vorweg und erzeugt keine falsche Readinessbehauptung.

## Nicht enthalten

LQ-297 implementiert keine Konfigurationsquelle, Migration-Readiness,
Worker-ID-Persistenz, Polling, Backoff, Jitter, Signalhandling, Grace Period,
Recovery, CLI, Entry-Point, Compose- oder Production-Aktivierung.

Schema und Head bleiben `20260819_0027`; Bundle, Operatoranzahl und Entry Points
bleiben unverändert.

Die vollständige lokale Suite besteht mit 3355 Tests, 98 erwarteten
PostgreSQL-Skips und 615 bestehenden Warnungen.

## Implementierungsfolge

LQ-298 sollte den langlebigen Research-Worker-Loop mit begrenztem Warten,
fail-closed Stop-Semantik und genau einem aktiven Job entscheiden und
implementieren, noch ohne CLI- oder Compose-Aktivierung.

Danach können Processkonfiguration, stabiler Worker-Identifier und
owner-kontrollierter Entry-Point separat folgen.
