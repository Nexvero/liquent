# LQ-291 — Research Job Types and Closed Ports

## Ergebnis

LQ-291 führt die stabilen Werte und geschlossenen Ports für persistente
Research-Jobannahme, Claim, Heartbeat und autorisierten Lookup ein.

Der Slice implementiert keine Persistenz, Migration, Queue, Leasepolicy,
Application-Composition, Workerloop, CLI oder Production-Wiring.

## Stabile Identitäten

`ResearchJobAcceptanceId`, `ResearchJobRevisionId`, `ResearchWorkerId` und
`ResearchJobClaimId` sind unveränderliche, nicht leere und repr-geschützte
Werttypen.

Die bestehende `JobId` bleibt die gemeinsame Jobidentität des lokalen und
späteren persistenten Researchpfads. Keine Identität trägt Authority.

## Kontrollierte Ergebnisklasse

`ResearchResultArtifactClass` begrenzt den ersten persistenten Pfad auf die
explizite Klasse `backtest_result_v1`.

Freie Klassenbezeichnungen, Importpfade, Runnernamen, Dateipfade und
serialisierte Pythonobjekte können die Ports nicht passieren.

## Annahmeergebnis

`AcceptedResearchJob` bindet Acceptance-, Job- und Revisionsidentität an Actor,
vollständig validierten Snapshot, kontrollierte Artifactklasse,
serverbestimmten UTC-Zeitpunkt und exakt den Zustand `queued`.

Ein abweichend wiederverwendeter Acceptance-Anker ist als leerer
`ResearchJobAcceptanceConflict` beobachtbar. Das Ergebnis trägt weder
Bestandsdetails noch frühere Eingaben und ist keine neue Exception.

`None` bleibt die neutrale Ablehnung ohne aktuelle Authority.

## Claim-Ergebnis

`ClaimedResearchJob` bindet Job, Revision, Actor, Workspace, Worker, Claim,
Snapshot und Artifactklasse an serverbestimmte Claim- und Leasezeiten.

Der Workspace muss exakt dem Snapshot entsprechen, der Zustand exakt
`running` sein und das Leaseende strikt nach der Claimzeit liegen.

Das Objekt ist technische Ausführungsevidence, keine Membership oder
Researchpermission.

## Heartbeatergebnis

`RenewedResearchJobLease` gibt nur die neue Revision und die unveränderte
Job-/Worker-/Claimbindung mit serverbestimmtem Leaseende zurück.

Es enthält keine caller-gelieferte Zeit, Statusentscheidung oder Authority.

## Browsergeeignete Sicht

`ResearchJobView` enthält Job, Revision, Workspace, Status sowie Annahme- und
Aktualisierungszeit.

Claim-ID, Worker-ID und Leasewerte fehlen strukturell. Ergebnis-, Fehler- und
Artifactdetails bleiben einem späteren Finalisierungsvertrag vorbehalten.

## Geschlossener Acceptance-Port

`AuthorizedResearchJobAcceptance.accept_job` akzeptiert ausschließlich
Acceptance-ID, Actor-User-ID, validierten Snapshot und kontrollierte
Artifactklasse.

SessionPrincipal, Session-ID, CSRF, Rolle, Membership, Permissionliste,
Allow-Boolean, Job-ID, Status, Uhrzeit, Lease und Worker-ID sind keine
Parameter.

Der spätere Adapter muss aktuelle `research:write`-Authority selbst aus dem
System of Record auflösen und exakt identische Retries konvergieren lassen.

## Geschlossener Claim-Port

`ResearchJobClaim.claim_next` akzeptiert ausschließlich eine Worker-ID.

Queueauswahl, Actor, Workspace, Job-ID, Revision, Claim-ID, Status, Priorität,
Uhrzeit und Leaseablauf können nicht vom Worker vorgegeben werden.

`None` bedeutet neutral, dass keine auswählbare Arbeit ausgegeben wurde.

## Geschlossener Heartbeat-Port

`ResearchJobHeartbeat.heartbeat` akzeptiert exakt Job-ID, erwartete Revision,
Worker-ID und Claim-ID.

Der Caller liefert weder `now`, Leaseende, Verlängerungsdauer noch Status.
Stale, fremde, terminale oder abgelaufene Bindungen ergeben später neutral
`None` ohne Mutation.

## Geschlossener Lookup-Port

`AuthorizedResearchJobLookup.get_job` akzeptiert nur Actor-User-ID und Job-ID.

Der Actor wird aus dem authentifizierten Principal übernommen, doch der Port
muss aktuelle `research:read`-Authority für den persistierten Workspace selbst
auflösen. Job-ID und Principal allein gewähren keine Authority.

Unbekannter Job und fehlende aktuelle Leseberechtigung ergeben dasselbe
neutrale `None`.

## Zeit- und Validierungsgrenzen

Alle sichtbaren Zeiten müssen timezone-aware UTC-Werte sein. Aktualisierungszeit
darf nicht vor Annahmezeit liegen.

Die Typen validieren lokale strukturelle Invarianten. Sie behaupten weder, dass
eine Persistenzmutation committet wurde, noch prüfen sie Authority oder
Leaseaktualität gegen eine Uhr.

## Technische Nichtverfügbarkeit

Die Ports definieren keine neue technische Exception.

Adapterfehler dürfen nicht als `None` oder Acceptance-Konflikt ausgegeben
werden. Eine spätere Adaptergrenze muss sie detailfrei vom neutralen Ergebnis
trennen, ohne SQL-, Verbindungs-, Authority-, Job- oder Leaseinformationen
preiszugeben.

## Bewusst nicht entschieden

LQ-291 entscheidet kein Schema, keine Tabelle, Spalte, Constraint, SQL,
Migration, Isolation, Lockstrategie, Lease-Dauer, Generatorcomposition,
Fehlerklasse, Retentiondauer, Queuebibliothek, Finalisierung, Recovery, CLI,
Route, Workerloop oder Wiring.

Es erzeugt und mutiert keine persistente Tatsache und startet keinen Prozess,
Thread oder Netzwerkzugriff.

Migration-Head, Bundle und Compose bleiben unverändert.

Die vollständige lokal ausführbare Suite besteht mit 3327 Tests, 98 erwarteten
PostgreSQL-Skips und 588 bestehenden Warnungen.

## Implementierungsfolge

LQ-292 kann nun Schema, additive Migration und SQLite-/PostgreSQL-Adapter für
Acceptance, Claim, Heartbeat und Lookup implementieren und die atomare
Konkurrenzsemantik gegen PostgreSQL 16 belegen.
