# LQ-469 — Asynchronous Capability Outcome Inspect and Wait Contract

## Ergebnis

LQ-469 definiert read-only Inspect- und Wait-Grenzen für eine bereits
freigegebene Capabilityausführung.

Der Slice implementiert noch keinen Adapter, Poller oder Supervisorservice.

## Ausgangspunkt

LQ-468 kann nur einen unmittelbar terminalen Releaseausgang akzeptieren.

Ein Running-Ausgang beweist mögliche fortdauernde Capabilitywirkung und darf
nicht als technischer Endzustand verloren gehen.

LQ-469 modelliert deshalb direkte spätere Beobachtung ohne zweiten Release.

Die ursprüngliche LQ-467-Executionbindung bleibt unverändert erhalten.

## Zwei Inspectionrequests

Writer und Recovery besitzen getrennte Inspectionrequesttypen.

Jeder Request enthält ausschließlich den bereits vollständig validierten
profilspezifischen Executionrequest.

Handle, Claim, Owner, Gate und Capabilityrequest werden nicht erneut frei
angeliefert.

Es gibt keinen generischen Profil- oder Operationsparameter.

## Keine neue Freigabe

Inspection akzeptiert weder Ready noch Token noch einen neuen Released-Marker.

Sie trägt dieselbe bereits freigegebene Execution weiter.

Der Port besitzt keine Release- oder Startmethode.

Beobachtung kann keine zweite Capabilitywirkung autorisieren.

## Writer Running

Eine nichtterminale Writerbeobachtung besteht aus Inspectionrequest und
`RunningManifestHandoffWriterProcess`.

Handle, Claim und Owner müssen exakt der Prepared-Bindung der Execution
entsprechen.

Ein Running-Record eines anderen Jobs wird nicht adoptiert.

Running behauptet noch keinen Writeroutcome.

## Recovery Running

Recovery verwendet den getrennten bestehenden Running-Recoverytyp.

Auch hier werden Handle, Claim und Owner vollständig verglichen.

Writer-Running kann nicht als Recoverybeobachtung konstruiert werden.

Recovery bleibt ohne Writer- oder Cleanupautorität.

## Terminal Writer

Eine terminale Writerbeobachtung ist direkt der bestehende
`ExecutedManifestHandoffWriterCapability`.

Damit gelten erneut die LQ-467-Prüfungen von Handle, Claim, Owner und
profilspezifischem Outcome.

Es wird kein zweiter terminaler Wrappertyp eingeführt.

Der Record ist Eingang für das spätere Terminal-Envelope.

## Terminal Recovery

Recovery verwendet entsprechend den bestehenden Executed-Recoveryrecord.

Writeroutcomes bleiben typseitig ausgeschlossen.

Die geschlossene Recovery-Kind-/Faktenmatrix bleibt vollständig wirksam.

Terminalität behauptet noch keine Engine-Terminalbeobachtung.

## Outcomeunion

Writerinspection liefert ausschließlich Running oder Executed-Writer.

Recoveryinspection liefert ausschließlich Running oder Executed-Recovery.

Prepared, Ready, Token, Konflikt, freie Statuswerte und `None` gehören nicht
zur Union.

Unbekannter erwarteter Bestand ist technische Unverfügbarkeit.

## Inspectionport

`ManifestHandoffSupervisorCapabilityOutcomeInspection` besitzt genau
`inspect_writer_outcome` und `inspect_recovery_outcome`.

Jeder Aufruf ist read-only und adressiert dieselbe persistente Prozessbindung.

Der Port startet, released und terminiert nichts.

Er liefert unmittelbar Running oder Executed.

## Waitport

`ManifestHandoffSupervisorCapabilityOutcomeWait` besitzt getrennte Writer- und
Recoverymethoden.

Wait liefert ausschließlich den jeweiligen terminalen Executed-Record.

Eine konstruktiv konfigurierte spätere Implementation darf intern begrenzt
warten.

Der Request enthält keinen Timeout, Pollintervall oder Clockwert.

## Timeoutsemantik

Erreicht eine spätere Waitimplementation innerhalb ihrer festen Policy keinen
terminalen Record, bleibt das Ergebnis technische Unverfügbarkeit.

Timeout liefert weder `None` noch Running noch einen erfundenen Outcome.

Der Port gibt keine Dauer oder Anzahl Versuche aus.

Ein späterer Aufruf muss dieselbe Execution inspectieren und darf nicht erneut
releasen.

## Fehlender Bestand

Ein erwarteter fehlender Supervisorprozess ist nicht neutral.

Abwesenheit beweist weder nie erfolgten Start noch Terminalität.

Name, PID, Claim oder Artefaktdatei dürfen keinen Ersatzprozess adoptieren.

Recovery und Terminaljournal bleiben gesperrt, bis direkte Fakten vorliegen.

## Prepared nach Release

Prepared ist nach nachgewiesenem Released kein gültiger Outcomezustand.

Eine solche Beobachtung ist divergent oder technisch unvollständig.

Sie wird nicht als Running normalisiert.

Der Vertrag bietet keinen zweiten Releaseversuch zur Reparatur.

## Konflikt und Divergenz

Cross-Handle-, Cross-Claim- und Cross-Owner-Running scheitert bereits im
Domainkonstruktor.

Falsche Profil- oder Ergebnistypen sind ebenfalls unkonstruierbar.

LQ-469 benennt keinen neuen Konflikttyp.

Technische Adapterfehler bleiben an der bestehenden detailfreien Grenze.

## Terminalfolge

Executed wird anschließend in einen LQ-465-Complete-Request überführt.

LQ-466 publiziert daraus das kanonische Terminal-Envelope.

Der Supervisorservice muss zusätzlich direkte Engine-Terminalität beobachten.

Erst die persistente Journalkorrelation bildet den Plattformabschluss.

## Keine Engineannahme

Capability-Running ist nicht identisch mit Docker-Running.

Capability-Executed ist nicht identisch mit Docker exited oder dead.

Der Outcomeport besitzt keine Runtime-Container-ID oder Engineoperation.

Enginebeobachtung bleibt LQ-461/LQ-462-Verantwortung.

## Keine Gateartefaktwirkung

Inspect und Wait lesen oder schreiben kein Ready, Token, Ack oder Envelope.

Sie erzeugen keinen Released-Marker.

Gateartefakte bleiben unveränderliche vorgelagerte Belege.

Outcome-Beobachtung verändert keine Control-Datei.

## Keine Authority

Requests akzeptieren keine SessionPrincipal, User-ID, Workspace-ID,
Permission, Managementrolle oder Allowentscheidung.

Released ist kein allgemeiner Authoritysnapshot.

Aktuelle Claim-/Owner-, Terminate- und Plattformvoraussetzungen prüft später
der Supervisorservice vor seiner nächsten Wirkung.

## Keine freien Prozessparameter

Es gibt kein Command, Args, Env, cwd, PID, Signal, Shell oder Timeout.

Der beobachtete Prozess ist ausschließlich durch die bestehende Execution
gebunden.

Caller können keinen anderen Executor oder Prozess auswählen.

Der Slice importiert keine Prozessbibliothek.

## Kein Schema oder Wiring

LQ-469 ändert keine Tabelle, Migration oder Persistenzsignatur.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Adapter, Poller, Thread, Entry Point, Service-, CLI-, Compose-
oder Production-Wiring.

## Tests

Fokussierte Tests belegen getrennte Inspectionrequests, Released-Execution als
einzige Bindung, Running-Handle-/Claim-/Ownerprüfung, geschlossene
Running-/Executed-Unions, terminal-only Wait und fehlende Release-, Timeout-
oder Authorityparameter.

## Nächster Slice

LQ-470 sollte Inspection und konstruktiv begrenztes Wait über die vorhandenen
kontrollierten Supervisor-Inspectmethoden implementieren, ohne Release,
Terminate oder zweiten Start.

Persistente Supervisorservice-Composition folgt danach separat.
