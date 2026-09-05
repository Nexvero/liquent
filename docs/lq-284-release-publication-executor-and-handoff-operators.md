# LQ-284 — Release Publication Executor and Handoff Operators

## Ergebnis

LQ-284 schließt die in LQ-282 festgelegten owner-only Prozessgrenzen für:

- persistente Registrierung eines technischen Publication-Executors;
- autorisierten Publication-Handoff vor dem bestehenden LQ-275-Worker.

Beide Operatoren sind kurzlebige Offline-Prozesse. Sie sind keine Route, kein
Startup-Hook, Scheduler, CI-Schritt oder automatischer Promotion-Nachlauf.

## Executor-Operator

Der neue Entry Point lautet:

```text
liquent-release-publication-executor register
```

Er akzeptiert ausschließlich `--database-url-file` und `--request`.

Die kanonische owner-only Requestdatei enthält exakt die stabile
`registration_id`.

Sie enthält keine Executor-ID, Rolle, Allow-Entscheidung, Authority,
Workspace-, Channel-, Host- oder Credentialbehauptung.

Nach exakter Migration-Readiness komponiert der Prozess den persistenten
LQ-283-Adapter mit dem kryptografisch sicheren internen Executor-ID-Generator.

## Registrierungsergebnis

Erfolg und exakter Retry liefern kanonisches JSON mit ausschließlich:

- `outcome` gleich `registered`;
- Registration-ID;
- intern erzeugter Executor-ID.

Der Retry derselben Registration-ID gibt dieselbe persistierte Executor-ID aus.
Der Operator erzeugt weder Handoff noch Execution oder Attempt.

## Handoff-Operator

Der neue Entry Point lautet:

```text
liquent-release-publication-handoff
```

Er akzeptiert ausschließlich `--database-url-file` und `--request`.

Die kanonische Requestdatei enthält exakt:

- Handoff-ID und Publication-Decision-ID;
- identifizierende Publisher-Authority-ID;
- Channel-ID und erwartete Channel-Revision-ID;
- absolute Pfade zu Bundle, detached SSHSIG und Promotion-Evidence;
- stabile neue Execution-ID.

Die Execution-ID wird noch nicht persistiert. Sie bleibt im bewahrten Request
stabil und wird erst beim LQ-254-Worker-Preflight gebunden.

## Geschlossene Handoff-Grenze

Der Request akzeptiert keine Rollen, Allow-Entscheidungen, Executor-ID,
Registry-, Signer-, Key-, Hash-, Provider-, Attempt- oder Statusbehauptungen.

Die Publisher-ID identifiziert den Actor, erteilt allein aber keine Authority.
Der bestehende LQ-251-Adapter prüft Current-Registry, aktive Policy, Signer,
Key, Channel-Revision und Publisher-Mitgliedschaft erneut aus dem System of
Record.

Promotion-Evidence und detached Signatur werden erneut gegen die aktuelle
Registryprojektion geprüft.

## Verifier-Identität

Die Handoff-Composition bindet die prozessfeste technische Verifier-ID
`liquent-release-publication-handoff-v1`.

Sie ist keine Authority und kein caller-gesteuertes Requestfeld. Für einen
erfolgreichen Handoff muss die bewahrte Promotion-Evidence mit derselben
operativ gebundenen Verifier-Identität erzeugt worden sein.

Eine abweichende Evidence bleibt neutral nicht akzeptiert.

## Sichere Dateigrenze

Database-URL, Request und alle drei Artifactquellen werden über die bestehende
LQ-275-Dateigrenze geprüft:

- absoluter Pfad;
- reguläre symlinkfreie Datei;
- Eigentum des effektiven Prozessnutzers;
- genau ein Hardlink;
- Modus `0400` oder `0600`;
- begrenzte Größe;
- `O_NOFOLLOW`, `O_CLOEXEC` und Descriptorprüfung.

Kanonische JSON-Requests verbieten doppelte, zusätzliche oder nichtkanonische
Felder. Der Operator verändert keine Dateirechte.

## Handoff-Ergebnis

Ein erfolgreicher neuer oder exakt wiederholter Handoff liefert nur:

- `outcome` gleich `accepted`;
- Handoff-, Decision-, Channel- und Channel-Revision-ID;
- unveränderte Execution-ID aus dem bewahrten Request.

Lokale Pfade, Hashes, Registryinventar, Signer und Keys werden nicht ausgegeben.

Die fünf Worker-Felder bleiben aus Request und Ergebnis eindeutig ableitbar.
LQ-284 materialisiert jedoch keine Worker-Datei und startet den Worker nicht.

## Exit-Vertrag

Beide Operatoren verwenden Exit `0` für Erfolg und Exit `2` für ungültigen
Input.

Der Handoff-Operator verwendet zusätzlich:

- Exit `3` für detailfreien ID-/Binding-Konflikt;
- Exit `4` für detailfreie technische Nichtverfügbarkeit;
- Exit `5` mit `not_accepted` für neutrale aktuelle Ablehnung.

Der Executor-Operator verwendet Exit `4` für detailfreie technische
Nichtverfügbarkeit. Seine geschlossene additive Registrierung besitzt keine
neutrale fachliche Ablehnung.

## Readiness und Ressourcen

Jeder Prozess baut genau eine Engine, prüft den exakten Migration-Head und
disposed die besessene Engine in jedem Pfad.

Kein Operator migriert, seedet Authority-Fakten, öffnet Providerzugriff oder
führt automatische Folgeschritte aus.

## Operational Bundle

Das Bundle erwartet jetzt additiv:

- 20 Console Entry Points;
- 19 Operatormodule;
- weiterhin 25 lineare Migrationen mit Head `20260819_0025`.

## Bewusst nicht enthalten

LQ-284 implementiert keinen Executor-Lifecycle, Handoff-Withdrawal, Channel-
oder Publisher-Lifecycle, Scheduler, Service, Provider-SDK, Deployment-Wiring,
automatischen Worker-Start oder automatische Retry-Schleife.

Registration-, Handoff- und Execution-IDs bleiben nicht wiederverwendbare
Fakten. Request- und Ergebnisdateien müssen mindestens für die referenzierenden
Publication-, Incident- und Auditzeiträume bewahrt werden.

## Nächster Slice

LQ-285 sollte den nun geschlossenen operativen Ablauf als End-to-End-Audit und
Runbook-Handoff prüfen, ohne neue Authority- oder Providerwirkung einzuführen.
