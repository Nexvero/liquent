# LQ-442 — Persistent Manifest Handoff Ownership and Recovery Foundation

## Ergebnis

LQ-442 ergänzt Revision `20260824_0029` linear nach
`20260819_0028`.

Die Revision schafft leere persistente Foundations für Execution-Ownership,
Leasehistorie, terminale Prozessnachweise, Recoveryauthority und
claimgebundene Recoveryobservationen.

Der Slice implementiert noch keinen Datenbankadapter oder Prozessaufruf.

## Additive Revision

Revision 0029 verändert keine bestehende LQ-431-Tabelle und erweitert keine
vorhandene Observationkind-Liste.

Sie erzeugt ausschließlich neue Tabellen und einen partiellen eindeutigen
Index.

Es gibt keinen Seed, Backfill, Import oder erfundenen Bestandsclaim.

Der Head ist danach eindeutig `20260824_0029` bei 29 linearen Migrationen.

## Recoveryauthority

`manifest_handoff_recovery_authorities` bindet Scope und User an explizit
aktiven oder inaktiven Recoverystatus.

Scope und User referenzieren die bestehenden stabilen Systeme-of-Record.

Die Tabelle ist getrennt von Registryreservierungsauthority, ordinary
Membership und Researchpermissions.

Sie enthält keine Rolle und keinen freien Allow-Wert.

## Execution-Claims

`manifest_handoff_execution_claims` hält:

- stabile Claim-ID;
- genau ein bestehendes Attempt;
- den initial autorisierten Actor;
- kontrollierten Execution-Owner;
- serverseitige Claimzeit;
- initiales Leaseende.

Attempt-ID ist dauerhaft eindeutig, sodass ein Attempt niemals einen zweiten
Execution-Claim oder Writerowner erhält.

Claim- und Owner-ID müssen vorhanden sein; Leaseende liegt strikt nach der
Claimzeit.

## Warum Execution-Claims nicht freigegeben werden

Die Tabelle besitzt keinen Status, kein `released_at` und keine partielle
Wiederverwendungsregel.

Terminales Prozessende wird separat append-only belegt.

Auch nach Ende, Reconciliation oder Dateilöschung bleibt die Attemptbindung
dauerhaft verbraucht.

Damit kann Recovery niemals zum zweiten Writerstart werden.

## Leasehistorie

`manifest_handoff_execution_lease_renewals` speichert jede Renewal mit einer
eigenen stabilen Renewal-ID.

Claim, Owner, serverseitige Renewalzeit und positives neues Leaseende bleiben
erhalten.

Die Foundation korrigiert damit eine in LQ-441 noch offene Persistenzlücke:
Ohne Renewal-ID wäre ein unklarer Heartbeatcommit nicht exakt retrybar und
Heartbeat-Historie nicht nichtwiederverwendbar identifizierbar.

Leasezeilen autorisieren weiterhin weder Recovery noch Takeover.

## Claimed Starts

`manifest_handoff_execution_starts` bindet genau einen Execution-Claim an
genau eine bestehende Observation-ID und den kontrollierten Owner.

Claim-ID ist Primärschlüssel; Observation-ID ist ebenfalls eindeutig.

Der spätere Adapter muss atomar sicherstellen, dass die Observation
`writer_started` ist, zum selben Attempt gehört und der Claimowner aktuell
passt.

Die reine Foreign-Key-Struktur erfindet diese semantische Entscheidung nicht.

## Execution-Endnachweise

`manifest_handoff_execution_ends` hält eine stabile End-ID, genau einen Claim,
Owner, terminale Art und serverseitige Endzeit.

Je Execution-Claim ist höchstens ein terminaler Fakt zulässig.

Die Arten sind auf `outcome_secured`, `outcome_unknown` und
`start_not_confirmed` begrenzt.

Exitcode, Signal, PID, Host und Fehlermeldung werden nicht gespeichert.

## Recovery-Claims

`manifest_handoff_recovery_claims` bindet:

- stabile Recovery-Claim-ID;
- Attempt;
- konkreten Execution-Endnachweis;
- aktuell autorisierten Actor;
- kontrollierten Recovery-Owner;
- serverseitige Claimzeit;
- optionales terminales Ende des Recoveryowners.

Der spätere Adapter muss Attempt und Execution-Endnachweis aus derselben
persistenten Kette ableiten.

Caller können weder Attempt noch Endnachweis als Autoritätsbehauptung
durchreichen.

## Genau ein aktiver Recoveryowner

Ein partieller eindeutiger Index erlaubt je Attempt höchstens eine
Recovery-Claimzeile ohne terminales Ende.

Nach direkt belegtem Ende darf später eine neue Recoverygeneration eine neue
Claim-ID erhalten.

Die alte Claim-ID und Historie bleiben erhalten und werden nicht umgeschrieben.

Leaseablauf oder Zeit allein setzt `ended_at` niemals.

## Recovery-Endnachweise

`manifest_handoff_recovery_ends` hält pro Recovery-Claim höchstens einen
stabilen terminalen Fakt.

Die drei geschlossenen Arten entsprechen gesichertem Outcome, unbekanntem
Outcome und nicht bestätigtem Start.

Der zugehörige spätere Adapter muss Endzeile und `ended_at` der Claimzeile in
einer Transaktion konsistent setzen.

Ein caller-gelieferter Boolean oder Timeout darf diese Mutation nicht öffnen.

## Recoveryobservationen

`manifest_handoff_recovery_observations` bindet genau einen Recovery-Claim an
genau eine bestehende Manifestobservation.

Claim-ID ist Primärschlüssel und Observation-ID zusätzlich eindeutig.

Der spätere Adapter muss semantisch auf die fünf LQ-427-Arten begrenzen und
Attempt-/Claimkette atomar validieren.

Die Foundation fügt bewusst keine zweite Outcome-, Digest- oder Dateizahlkopie
hinzu; die bestehende Observation bleibt der Faktenursprung.

## Keine generische Eventpersistenz

Revision 0029 enthält keine freie Payload-, JSON-, Rollen-, Allow- oder
Statusspalte für Events.

Execution- und Recovery-Endarten sind jeweils durch Checks geschlossen.

Writer- und Recoveryobservationen referenzieren bestehende IDs statt
Callerfakten zu duplizieren.

Die späteren Adapter bleiben an die quellenspezifischen LQ-441-Ports gebunden.

## Konkurrenz

Dauerhaft eindeutige Attempt-/Executionbindung verhindert konkurrierende
Writerclaims.

Eindeutige Claim-/Start-/End-/Observationbindungen verhindern
Last-write-wins-Reassignment.

Der partielle Index serialisiert aktive Recoveryowner auf Datenbankebene.

Transaktionsreihenfolge und PostgreSQL-Locking bleiben Aufgabe der späteren
Adapterimplementation.

## Authority und Revocation

Die Foundation speichert Recoveryauthority explizit aktiv oder inaktiv.

Sie erstellt keine Authorityzeile und aktiviert nichts automatisch.

Spätere Claimadapter müssen User, Scope und Capability bei jeder neuen
Entscheidung aktuell lesen.

End- und Outcomesicherung bereits kontrolliert gestarteter Abläufe bleibt eine
mechanische quellenspezifische Grenze.

## Neutrale Abwesenheit

Leere Tabellen bedeuten keine Claims, Ends oder Recoveryauthority.

Sie sind keine technische Störung und erzeugen keine automatische
Recoveryfähigkeit.

Ein fehlender Claim, Endnachweis oder Authorityfakt muss später neutral
fail-closed bleiben.

Dateiabwesenheit füllt keine dieser Tabellen.

## Technische Unverfügbarkeit

Widersprüchliche Claimketten, beschädigte Zeitordnung, mehrdeutige Historie
und Infrastrukturfehler bleiben getrennte detailfreie technische
Unverfügbarkeit.

Die Migration benennt keinen neuen Exceptiontyp.

Constraint- oder Tabellennamen werden nicht an untrusted Caller ausgegeben.

## Retention und Nichtwiederverwendung

Execution-Claim-, Renewal-, Start-, End-, Recovery-Claim- und
Recovery-Endidentitäten bleiben dauerhaft an ihre ursprünglichen Fakten
gebunden.

Es gibt kein Cascade-Delete, Upsert, Rebind oder Namensrecycling.

Die Retentionuntergrenze bleibt mindestens so lang wie Parallelitätsausschluss,
Unknown-Auflösung, Audit oder Nichtwiederverwendung davon abhängen.

Eine konkrete Frist oder Archivstrategie wird nicht festgelegt.

## Bestandsattempts

Die Migration erzeugt für vorhandene Attempts keine Execution- oder
Recoveryzeile.

Ein bestehendes `writer_started` wird nicht rückwirkend einem Owner oder
Endnachweis zugeordnet.

Solche Attempts bleiben bis separater owner-kontrollierter
Bestandsverankerung fail-closed für Recovery.

## Domainergänzung

`ManifestHandoffLeaseRenewalId` macht jeden Heartbeat stabil retrybar und
repr-frei.

`ManifestHandoffRecoveryEndId`, `ManifestHandoffRecoveryEndKind` und
`RecordedManifestHandoffRecoveryEnd` schließen die terminale
Recovery-Ownerkette.

Lease- und Recovery-Endwerte bleiben frei von PID-, Host-, Exit- und
Fehlerdetails.

## Portergänzung

Lease-Renewal erhält die intern kontrollierte Renewal-ID als Retryanker.

`ControlledManifestHandoffRecoveryEnd` bietet drei getrennte Methoden für
secured, unknown und start-not-confirmed.

Es gibt weiterhin keinen generischen Kind-, Zeit-, Prozessdetail- oder
Allow-Parameter.

## Migration-Gates

Aktueller Roadmaphead, Readiness-Gate und Release-Bundle-Inventar werden auf
29 Migrationen und `20260824_0029` synchronisiert.

Historische Sliceaussagen zu ihrem damaligen Head bleiben unverändert.

Die Revision ist weiterhin als Package Data erfasst.

## Keine Adapterimplementation

LQ-442 implementiert keinen Claim-, Lease-, Start-, End-, Authority- oder
Recoveryadapter.

Es wird kein SQL außerhalb der Migration ausgeführt und keine Datenbank beim
Import geöffnet.

LQ-439 verwendet den neuen claimed-start-Port noch nicht.

## Kein Prozess- oder Production-Wiring

Der Slice startet, wartet, signalisiert oder beendet keinen Prozess.

Es gibt keinen Supervisor, Reconcilerwrapper, Composer, Operator, CLI, Route,
Scheduler, Compose-, CI- oder Production-Wiringpfad.

Keine Manifestdatei wird gelesen, geschrieben, verschoben oder gelöscht.

## Tests

Fokussierte Tests belegen:

- lineare leere Revision 0029 ohne Seed oder Backfill;
- alle acht Ownership-/Recoverytabellen;
- dauerhaft genau einen Execution-Claim je Attempt;
- positive append-only Lease-Renewals;
- claimgebundenen eindeutigen Writerstart;
- geschlossene terminale Execution- und Recoveryarten;
- explizite Recoveryauthority und höchstens einen aktiven Recoveryowner;
- eindeutige Recoveryobservation ohne Writer-/Cleanupkind;
- stabile Renewal- und Recovery-Endtypen/Ports;
- synchronisierte aktuelle Migration-Gates;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-442 implementiert keine persistente Mutation oder Lookupentscheidung über
die Migration hinaus.

Scope-/Authority-Bootstrap, Supervisoradapter, claimed Composerintegration,
Recoverycomposition, Bestandsverankerung, Cleanup und finale
Evidence-Retention bleiben separat.

Staging, Commit, Push, Build, Signatur, Promotion, Publication und Deployment
werden weder ausgeführt noch autorisiert.

## Nächster Slice

LQ-443 sollte die autorisierte persistente Execution-Claim-, Lease-,
claimed-start- und terminale Execution-Endgrenze implementieren.

Recoveryadapter, Supervisorintegration, Recoverycomposition,
Bestandsverankerung, Cleanup und Retention bleiben danach separate Slices.
