# LQ-289 — Persistent Research Worker Foundation Contract

## Ergebnis

LQ-289 auditiert den in Compose referenzierten, aber nicht implementierten
`liquent-research-worker` und entscheidet den kleinsten sicheren Vertrag für
einen späteren langlebigen Research-Worker.

Der Slice implementiert noch keinen Command, Queueadapter, Port, Schema,
Migration, Prozessloop oder Compose-Aktivierung.

## Aktueller Zustand

Research-Jobs werden heute durch die Control Plane synchron gestartet.

`start_research_job` registriert ein `InMemoryResearchJob` und führt den Runner
im selben Prozess unmittelbar aus.

`InMemoryResearchJobs` ist ein lokales Objekt. Sein Inhalt ist weder zwischen
Control Plane und Worker geteilt noch nach Prozessneustart erhalten.

Die vorhandenen READY/RUNNING/SUCCEEDED/FAILED-Transitions schützen den lokalen
Objektlebenszyklus, bilden aber keine persistente Queue und keinen
Mehrprozess-Claim.

## Festgestellter Blocker

Ein `liquent-research-worker`, der lediglich dieselben In-Memory-Objekte lädt,
könnte keine von der Control Plane angenommenen Jobs sehen.

Polling einer nicht vorhandenen Tabelle, erneute Ausführung caller-gelieferter
Requests oder Scannen lokaler Artifactverzeichnisse wären ungeschützte
Ersatzmechanismen.

Vor einem Entry Point sind deshalb persistente Jobannahme, atomarer Claim,
stabile Ausführungsevidence und Restart-Recovery erforderlich.

## Prozessrolle

Der spätere Research-Worker ist ein langlebiger interner Prozess für
deterministische Research-/Backtesting-Jobs.

Er ist keine HTTP-Route, Browser-Session, Publication-Worker, Scheduler für
Releaseprozesse, Tradingengine oder allgemeine Codeausführungsplattform.

Er besitzt keine Publisher-, Registry-, OIDC-, Membership-Management- oder
Deploymentauthority.

## Persistente Jobidentität

Jeder angenommene Job benötigt eine stabile, nicht wiederverwendbare `JobId`.

Der persistente Job bindet unveränderlich mindestens:

- Workspace-ID;
- annehmende User-ID als Actorreferenz;
- validierten Experiment-Snapshot;
- stabile Strategy-/Runner-Auswahl aus kontrollierter Konfiguration;
- Erstellungszeit und initiale Jobrevision;
- erwartete Ergebnis- und Artifactklasse.

Session-ID, CSRF-Token, Cookie, Membershiprolle und caller-gelieferte
Allow-Entscheidung werden nicht in den Workerauftrag kopiert.

## Autorisierung bleibt vor der Queue

Die Control Plane prüft beim Annehmen weiterhin aktuelle Session, CSRF,
Workspace, aktive Membership und `research:write`.

Der Worker erhält keinen SessionPrincipal und darf eine User-ID nicht als
Authority interpretieren.

Die Jobannahme muss atomar eine autorisierte persistente Arbeitseinheit
erzeugen. Ohne Commit darf dem Browser kein angenommener Job bestätigt werden.

Ob ein bereits angenommener Job nach späterem Membershipentzug noch ausgeführt
oder neutral storniert wird, benötigt vor Implementierung eine explizite
Policyentscheidung. LQ-289 erfindet keinen Grace-Zeitraum.

## Geschlossener Snapshot

Der Worker führt ausschließlich den persistierten, bereits validierten
Experiment-Snapshot aus.

Er akzeptiert keine Python-Importpfade, Shellbefehle, URLs, freie Dateipfade,
Pickles, Module, Rollen, Limits oder Strategyparameter aus Prozessargumenten.

Runner und Datenquelle werden durch eine geschlossene interne Resolvergrenze
aus dem Snapshot bestimmt.

Der Worker lädt keine Browserdaten und entdeckt keine Jobs aus Artifacts.

## Jobzustände

Der persistente Mindestlebenszyklus unterscheidet:

- `ready`: committet und noch nicht geclaimt;
- `running`: genau einem aktuellen Claim zugeordnet;
- `succeeded`: Ergebnis und notwendige Artifactreferenzen atomar bestätigt;
- `failed`: detailarme terminale fachliche oder technische Ausführung beendet;
- `cancelled`: nur nach einem später explizit autorisierten Vertrag.

Die konkreten Statusnamen sind noch keine Schemaentscheidung. Ihre
beobachtbaren Bedeutungen sind jedoch getrennt zu erhalten.

## Atomarer Claim

Ein Worker darf genau einen `ready` Job atomar claimen.

Der Claim bindet mindestens stabile Worker-Identität, Claim-/Lease-Identität,
Jobrevision und Claimzeit.

Zwei Prozesse dürfen denselben Job nicht gleichzeitig als ausführbar
beobachten. Eine Datenbankauswahl vor dem Claim ist keine Authority zum
Ausführen.

Die konkrete SQL-, Lock-, Queue- oder Portform wird im Persistenzslice
entschieden und auf PostgreSQL mit unabhängigen Verbindungen geprüft.

## Lease und Heartbeat

Ein langlebiger Prozess benötigt eine begrenzte Lease, weil Container,
Host oder Prozess während RUNNING verschwinden können.

Heartbeat darf nur die eigene aktuelle Lease verlängern. Stale Worker oder
fremde Claim-ID dürfen keine Lease, Revision oder Resultate verändern.

Lease-Dauer, Heartbeatintervall und Clocktoleranz werden explizite validierte
Processkonfiguration, keine Jobfelder.

Clockfehler oder rückwärts laufende monotone Zeit scheitern fail-closed.

## Recovery nach Prozessverlust

Eine abgelaufene Lease beweist nicht, dass keine Berechnung oder kein
Artifactwrite stattgefunden hat.

Recovery muss zuerst persistente Job- und Artifactevidence prüfen. Es darf
nicht blind denselben Runner erneut starten.

Deterministische reine Berechnung reduziert Risiken, ersetzt aber keine
idempotente Artifact- und Finalisierungsgrenze.

Ob ein Job erneut geclaimt, neutral failed oder manuell reviewed wird, hängt
von der nachweisbaren Ausführungsphase ab und benötigt einen eigenen Vertrag.

## Ergebnis und Artifacts

Erfolg bindet eine neutrale `BacktestExperimentSummary` und immutable
Artifactreferenzen an Job-ID, Claim und Jobrevision.

Artifactbytes werden über den bestehenden `ArtifactStore`-Port gespeichert;
lokale Pfade oder ungeprüfte Dateien sind kein persistentes Ergebnis.

Jobabschluss und normative Artifactreferenzen müssen so koordiniert sein, dass
kein `succeeded` ohne vollständige Results sichtbar wird.

Ein Artifactwrite ohne bestätigten Jobabschluss bleibt Recoveryevidence und
wird nicht als Erfolg behauptet.

## Fehlergrenze

Fachlich ungültige kontrollierte Inputs dürfen einen detailarmen terminalen
Jobfehler erzeugen.

Datenbank-, Artifact-, Resolver-, Clock- oder Infrastrukturfehler bleiben
technische Nichtverfügbarkeit und dürfen nicht als Research-Ergebnis erscheinen.

Persistierte öffentliche Fehler enthalten keine Exception, Stacktrace, SQL,
DSN, lokalen Pfad, Inputdaten oder internen Strategyzustand.

Ausführliche Diagnose gehört ausschließlich in begrenzte geschützte
Operations-Telemetrie.

## Concurrency und Fairness

Die aktuelle Productionkonfiguration begrenzt Jobkonkurrenz auf genau eins.

Der erste Worker implementiert daher höchstens einen aktiven Claim pro Prozess
und keine interne Thread- oder Prozessparallelität.

Auswahl muss deterministisch und starvation-resistent sein. Workspacequoten,
Prioritäten, Zeitpläne und mehrere Queues bleiben spätere explizite Policies.

## Start und Readiness

Der spätere Command startet nur nach:

- vollständig validierter Productionkonfiguration;
- exakter Migration-Readiness;
- erfolgreicher Composition aller persistenten Ports;
- stabiler technischer Worker-Identität;
- installierten Signal- und Shutdownhandlern.

Readiness bedeutet, dass neue Claims sicher möglich sind. Liveness bedeutet
nur, dass der Prozess seine Schleife weiter ausführen kann.

Ein leerer Queuezustand ist gesund und erzeugt weder Busy Loop noch
Readinessfehler.

## Begrenztes Warten

Der langlebige Loop verwendet server- oder konfigurationsgebundenes begrenztes
Warten mit Backoff und Jitter.

Er pollt nicht ohne Pause, hält keine Datenbanktransaktion während der
Research-Ausführung offen und erzeugt bei leerer Queue keine Logs pro Iteration.

Warteparameter sind Processkonfiguration und können keinen Job, Actor oder
Workspace auswählen.

## Graceful Shutdown

SIGTERM beendet die Annahme neuer Claims sofort.

Ein laufender Job erhält nur die kontrollierte Grace Period aus Compose. Der
Worker versucht Heartbeat und sicheren Abschluss, startet aber keinen zweiten
Job.

Kann er nicht terminal abschließen, bleibt die Lease-/Recoveryevidence erhalten.
Shutdown setzt RUNNING nicht blind auf READY und löscht keine Artifacts.

Exit nach verlorener Datenbank- oder Leaseauthority ist fail-closed.

## Compose-Vertrag

Der bestehende Compose-Service liefert bereits:

- getrennte interne Netze ohne Public-Ingress;
- Migration-Gate-Abhängigkeit;
- CPU-/Memorygrenzen;
- Artifactvolume;
- `60s` Stop-Grace-Period;
- Jobkonkurrenz eins in der Runtimekonfiguration.

Diese Infrastruktur ist notwendig, aber ohne persistente Jobgrenze und Command
nicht hinreichend. Der Stack bleibt nicht runnable.

## Trennung vom Publication-Worker

`liquent-release-publication` ist ein kurzlebiger beaufsichtigter Offline-
Prozess mit Providercredential und eigener persistenter Zustandsmaschine.

Der allgemeine Research-Worker darf diesen Command, dessen Composition,
Credentials, Handoffs oder Providerports weder importieren noch aufrufen.

Research-Artifacts werden nicht automatisch signiert, promoted, veröffentlicht
oder deployt.

## Bewusst nicht entschieden

LQ-289 entscheidet keine Tabelle, Spalte, SQL, Migration, konkrete
Python-Signatur, Queuebibliothek, Portklasse, Lease-Dauer, Pollintervall,
Artifactformat, CLI-Option oder Wiringimplementierung.

Es erzeugt keinen Job, Claim, Lease, Heartbeat, Result, Artifact, Prozess,
Thread, Netzwerkzugriff, Providerzugriff oder Deployment.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit 3413 Tests und 588
bestehenden Warnungen.

## Implementierungsfolge

LQ-290 sollte zuerst den persistenten Research-Job-, Claim- und
Lease-Foundation-Vertrag mit atomarer PostgreSQL-Konkurrenzsemantik entscheiden.

Danach können Annahmeadapter, Artifactabschluss, Worker-Composition und erst
zuletzt der langlebige `liquent-research-worker`-Entry-Point folgen.
