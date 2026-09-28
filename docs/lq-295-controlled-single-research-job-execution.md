# LQ-295 — Controlled Single Research Job Execution

## Ergebnis

LQ-295 implementiert `ProcessOneResearchJob` als begrenzte Ausführung von
höchstens einem persistenten Research-Job.

Der Use Case claimt, erneuert die Lease, löst ausschließlich den persistierten
Snapshot auf, führt genau einen kontrollierten Backtest aus, schreibt ein
immutable JSON-Artifact und finalisiert claimgebunden.

## Höchstens ein Job

`process` akzeptiert nur eine stabile `ResearchWorkerId`.

Eine leere Queue liefert `idle`. Es findet dann weder Resolver-, Runner-,
Artifact- noch Finalizerzugriff statt.

Der Use Case enthält keinen Loop, Batch, Thread, Prozesspool oder parallele
Ausführung.

## Claim und Heartbeat vor Ausführung

Nach dem Claim wird dessen Lease genau einmal vor Resolver- und Runnerzugriff
erneuert. Die neue Revision und Ablaufzeit ersetzen die ursprüngliche
Claimbindung für jede spätere Finalisierung.

Scheitert der Heartbeat neutral, wird der Runner nicht gestartet und
`claim_lost` zurückgegeben.

LQ-295 startet keinen parallelen Heartbeatthread. Dauert die synchrone
Ausführung über die erneuerte Lease hinaus, verweigert der LQ-294-Finalizer den
Abschluss neutral. Das Resultat wird dann nicht als Erfolg sichtbar.

## Geschlossener Resolver

Der Resolver erhält exakt den bereits persistierten und beim Claim
rekonstruierten `ExperimentSnapshot`.

Workerargumente können keine Datasetreferenz, Strategyversion, Parameter,
Importpfade, URLs, Shellbefehle, Rollen oder Authoritywerte ergänzen.

Resolver- und Runnerfehler werden ohne deren Detail als kontrollierter
`execution_failed`-Abschluss versucht.

## Deterministisches Resultat

Der bestehende reine Researchpfad erzeugt eine `BacktestExperimentSummary`.
Ihre Experiment-ID muss dem persistierten Snapshot entsprechen; andernfalls
wird kein Artifact geschrieben und der Job detailarm fehlgeschlagen.

Nicht endliche Metriken werden über die bestehende Evidenceprojektion als
JSON-`null` dargestellt. JSON ist UTF-8, kompakt und nach Schlüsseln sortiert.

## Immutable Artifact

Der Artifactschlüssel enthält nicht die Job-ID selbst, sondern deren SHA-256-
Ableitung unter einem kontrollierten `research/.../result.json`-Präfix.

Der bestehende `ArtifactStore` erhält nur Schlüssel, kanonische Bytes und
`application/json`. Erst dessen immutable Referenz wird an den atomaren
LQ-294-Erfolgsfinalizer übergeben.

Artifact- oder Serialisierungsfehler werden detailfrei als
`research_job_processing_unavailable` gemeldet. Sie werden nicht als
Runnerfehler persistiert; der Job bleibt mit Claim-/Leaseevidence recoverbar.

Ein erfolgreiches Artifact bei anschließend verlorenem Claim bleibt
Recoveryevidence, erzeugt aber keinen sichtbaren Job-Erfolg.

## Rückgabe

Der Use Case unterscheidet ausschließlich:

- `idle`: kein Job geclaimt;
- `succeeded`: Artifact und persistentes Erfolgsoutcome vollständig committet;
- `failed`: kontrollierter Fehler terminal committet;
- `claim_lost`: Heartbeat oder Finalisierung besaß keine aktuelle Authority.

Keine Variante enthält Exceptions, Runnerdetails, Pfade, Memberships oder
Leaseinternas.

## Nicht enthalten

LQ-295 implementiert keinen konkreten ArtifactStore, langlebigen Loop,
Pollintervall, Jitter, Signalhandling, Recovery, Cancellation, CLI,
Entry-Point, HTTP-Route, Compose- oder Production-Wiring.

Schema und Migration-Head bleiben `20260819_0027`; Bundle-Gates und
Entry-Point-Anzahl bleiben unverändert.

Die vollständige lokale Suite besteht mit 3340 Tests, 98 erwarteten
PostgreSQL-Skips und 615 bestehenden Warnungen.

## Implementierungsfolge

LQ-296 sollte einen owner-kontrollierten immutable lokalen Research-
ArtifactStore mit atomarem Create, Hashprüfung und sicherer Pfadgrenze
implementieren.

Danach können Workerloop, Prozesskonfiguration und Runtime-Aktivierung getrennt
entschieden werden.
