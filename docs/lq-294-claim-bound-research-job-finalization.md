# LQ-294 — Claim-bound Research Job Finalization

## Ergebnis

LQ-294 implementiert den atomaren terminalen Abschluss persistenter
Research-Jobs für Erfolg und detailarmen Ausführungsfehler.

Die additive Migration `20260819_0027` speichert genau ein unveränderliches
Outcome je Job. Sie erzeugt keine Jobs, Claims, Ergebnisse oder Seeds.

## Gemeinsame Claimbindung

Beide Finalizer verlangen exakt Job-ID, erwartete aktuelle Revision,
Worker-ID und Claim-ID.

Nur ein `running` Job mit derselben aktuellen Bindung und einer zum
serverbestimmten Abschlusszeit noch nicht abgelaufenen Lease darf mutieren.

Stale Revision, fremder Worker, falscher Claim, terminaler Job oder
abgelaufene Lease ergeben neutral `None`. Dabei entstehen weder neue Revision
noch Outcome oder Statusänderung.

## Erfolgsabschluss

Erfolg verlangt eine bestehende `BacktestExperimentSummary` und eine immutable
`ArtifactReference` für kanonisches JSON.

Die Artifactreferenz muss einen nicht leeren Schlüssel, exakt einen
kleingeschriebenen SHA-256-Wert, `application/json` und eine positive Bytegröße
tragen. Die Summary muss zur persistierten Experiment-ID des Jobs gehören.

Summary, Artifactbindung, serverbestimmte Abschlusszeit, neue Revision und
Status `succeeded` werden in einer Datenbanktransaktion sichtbar.

Der Artifactinhalt wird vorher über den bestehenden `ArtifactStore` erzeugt.
Ein Write ohne erfolgreichen Datenbankabschluss bleibt unsichtbare
Recoveryevidence und behauptet keinen Job-Erfolg.

## Fehlerabschluss

Der erste kontrollierte Fehlercode ist ausschließlich `execution_failed`.

Persistiert werden keine Exception, Message, Stacktrace, Runnerdetails,
Parameter, Pfade oder Infrastrukturinformationen. Ein fehlgeschlagener Job
trägt weder Summary noch Artifactbindung.

Outcome, neue Revision, Abschlusszeit und Status `failed` committen atomar.

## Unveränderliches Outcome

`research_job_outcomes` besitzt höchstens einen Datensatz je Job und erzwingt
die vollständige Trennung erfolgreicher und fehlgeschlagener Inhalte.

Ein terminaler Retry ist neutral. Erfolg kann nicht in Fehler und Fehler nicht
in Erfolg umgeschrieben werden.

Claim- und Leaseevidence bleibt nach Abschluss erhalten und wird nicht für
einen neuen Job wiederverwendet.

## Worker-Control-Plane

Die bestehende LQ-293-Workergrenze kann Erfolg oder Fehler direkt aus einem
`ClaimedResearchJob` finalisieren. Dadurch werden Job, Revision, Worker und
Claim aus demselben gebundenen Objekt übernommen und nicht einzeln aus
Prozessargumenten konstruiert.

## Technische Fehler

Beschädigte Resultwerte, ungültige Artifactreferenzen, nicht kanonisch
serialisierbare Summarys sowie Datenbank-, Clock- oder Generatorfehler bleiben
detailfreie `ResearchJobStoreUnavailable`.

Sie werden nicht als `execution_failed` persistiert und nicht in neutrales
`None` umgedeutet.

## Nicht enthalten

LQ-294 implementiert keinen ArtifactStore-Adapter, Runner, Resolver,
Heartbeatloop, Recovery, Cancellation, Polling, Signalhandling, CLI, Route,
Workercommand oder Production-Wiring.

Bundle-Gates folgen dem neuen linearen Head `20260819_0027`; Entry-Point- und
Operatormodulanzahl bleiben unverändert.

Die vollständige lokale Suite besteht mit 3336 Tests, 98 erwarteten
PostgreSQL-Skips und 615 Warnungen.

## Implementierungsfolge

LQ-295 kann nun eine kontrollierte einzelne Worker-Ausführung aus Claim,
geschlossenem Resolver, Heartbeat und terminalem Finalizer komponieren.

Der langlebige Prozessloop und seine Production-Aktivierung bleiben danach
separate Slices.
