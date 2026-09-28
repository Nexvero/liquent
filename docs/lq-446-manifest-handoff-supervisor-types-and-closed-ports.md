# LQ-446 — Manifest Handoff Supervisor Types and Closed Ports

## Ergebnis

LQ-446 konkretisiert LQ-445 mit geschlossenen Supervisorwerten und zwei
getrennten minimalen Ports für Writer und Recovery.

Der Slice implementiert noch keinen Prozessadapter oder Composer.

## Eigenes Supervisormodul

Die Werte liegen in `identity.manifest_handoff_supervisor`.

Sie importieren nur bestehende Manifest-Handoff-Domainwerte und keine
Subprocess-, OS-, Container- oder Persistenzbibliothek.

Der Modulimport startet keinen Prozess und liest weder Environment noch
Dateisystem.

Konkrete IPC- und Prozessentscheidungen bleiben separat.

## Opaker Handle

`ManifestHandoffSupervisorHandleId` ist ein stabiler repr-freier nicht leerer
Stringwert.

Er ist weder PID noch Executable-, Host-, Container-, Claim- oder Zeitwert.

Der Handle kann nicht aus einem Prozesslisting rekonstruiert werden.

Seine spätere Erzeugung bleibt kontrollierte Adapterabhängigkeit.

## Writerrequest

`ManifestHandoffWriterSupervisorRequest` bindet ausschließlich:

- Execution-Claim-ID;
- Execution-Owner-ID;
- intern aufgelöste stabile Scopebinding;
- persistenten Handoffnamen.

Claim, Owner und Binding bleiben repr-frei.

Der Request enthält keinen Handle und keine Prozesssteuerung.

## Recoveryrequest

`ManifestHandoffRecoverySupervisorRequest` bindet ausschließlich:

- Recovery-Claim-ID;
- Recovery-Owner-ID;
- intern aufgelöste stabile Scopebinding;
- persistenten Handoffnamen.

Writer- und Recovery-Claimtypen sind nicht austauschbar.

Die Recoverybinding trägt zwar den geschlossenen Scopewert, der spätere
Reconciler darf daraus ausschließlich Zielwurzel und Namen verwenden.

## Verbotene Requestfelder

Beide Requests enthalten insbesondere kein:

- Command, Executable oder Argumentarray;
- Environment oder Arbeitsverzeichnis;
- Shell-, Timeout- oder Signalwert;
- PID, Handleoverride oder Prozessstatus;
- Allow, Rolle, Authoritysnapshot oder SessionPrincipal;
- Outcome, Filename, Digest oder Dateizahl.

Der Caller kann damit keine Prozessfähigkeit erweitern.

## Vorbereiteter Writerprozess

`PreparedManifestHandoffWriterProcess` bindet Handle, Execution-Claim,
Execution-Owner und serverseitige Preparezeit.

`gate_released` ist nicht setzbar und fest `false`.

`writer_authorized` ist ebenfalls fest `false`, weil erst der spätere durable
claimed Start die Composition zur Gatefreigabe berechtigt.

Handle, Claim und Owner bleiben repr-frei.

## Laufender Writerprozess

`RunningManifestHandoffWriterProcess` bindet denselben Handle, Claim und Owner
an die serverseitige Releasezeit.

`gate_released` ist fest `true`, `terminal` fest `false`.

Der Wert ist kein Prozessende und keine Recoveryfreigabe.

Ein Timeout kann weiterhin denselben Runningwert liefern.

## Writerprozess-Outcomes

`ManifestHandoffWriterProcessKind` ist geschlossen auf:

- `manifest_handed_off`;
- `target_not_absent`;
- `source_not_stable`;
- `outcome_unknown`;
- `unavailable`.

Es gibt keinen freien Exitcode- oder Stringoutcome.

Die Werte spiegeln nur direkte LQ-426-Ergebnisse beziehungsweise
detailbegrenzte Prozessunsicherheit.

## Terminaler Writerwert

`CompletedManifestHandoffWriterProcess` bindet Handle, Claim, Owner, Kind und
serverseitige terminale Zeit.

Nur `manifest_handed_off` trägt einen validierten einfachen `.json`-Basename
und `ManifestHandoffFacts`.

Alle anderen Arten verbieten Filename und Fakten.

`terminal` ist fest `true`; Staging- und Commitautorisierung sind fest
`false`.

## Writer-Filename

Der Erfolgsfilename darf keine Slash- oder Backslashkomponente besitzen.

Sein Basename vor `.json` muss erneut als `ManifestHandoffName` validieren.

Der spätere Composer prüft zusätzlich die exakte Gleichheit mit dem
persistenten Handoffnamen plus `.json`.

Der Supervisorwert allein darf keinen anderen Namen autorisieren.

## Vorbereiteter Recoveryprozess

`PreparedManifestHandoffRecoveryProcess` bindet Handle, Recovery-Claim,
Recovery-Owner und Preparezeit.

Gate ist fest geschlossen.

Writer- und Cleanupautorisierung sind nicht setzbar und fest `false`.

Der Wert kann nicht als Writerprozess verwendet werden.

## Laufender Recoveryprozess

`RunningManifestHandoffRecoveryProcess` bindet denselben Recoverykontext an die
serverseitige Releasezeit.

Gate ist fest freigegeben, der Prozess aber ausdrücklich nicht terminal.

Writer- und Cleanupautorisierung bleiben `false`.

Der Wert enthält kein vorläufiges Reconciliationresultat.

## Recoveryprozess-Outcomes

`ManifestHandoffRecoveryProcessKind` ist geschlossen auf die fünf direkten
LQ-427-Arten plus `outcome_unknown`.

Es gibt keinen Writer-, Cleanup-, Retry- oder Startfreigabeoutcome.

Technische Reconciler-/IPC-/Prozessunsicherheit wird nur als
`outcome_unknown` sichtbar.

Sie erfindet keine Manifestbeobachtung.

## Terminaler Recoverywert

`CompletedManifestHandoffRecoveryProcess` bindet Handle, Recovery-Claim,
Owner, Kind und serverseitige terminale Zeit.

Temporary-only, handed-off und pending-cleanup tragen Fakten.

Nur handed-off und pending-cleanup tragen zusätzlich den validierten finalen
Filename.

Absent, conflict und outcome-unknown verbieten Filename und Fakten.

## Keine Cleanupfreigabe

Auch ein pending-cleanup-Result setzt `cleanup_authorized` nicht.

Alle vorbereiteten, laufenden und terminalen Recoverywerte halten Writer- und
Cleanupautorisierung unveränderlich `false`.

Der Supervisorport besitzt keine Cleanupmethode.

LQ-428 bleibt außerhalb dieser Grenze.

## Aware UTC

Prepare-, Release- und Endzeiten müssen aware UTC sein.

Sie sind Ergebniswerte einer später injizierten kontrollierten Clock und keine
Requestparameter.

Naive oder nicht-UTC Zeiten werden abgelehnt.

Die Werte treffen keine Lease- oder Timeoutentscheidung.

## Detailfreier Supervisorkonflikt

`ManifestHandoffSupervisorConflict` ist ein leerer unveränderlicher Wert.

Er vereinheitlicht divergente Handle-/Claim-/Ownerbindung ohne Handle, PID,
Pfad oder Prozessdetail auszugeben.

Technische Unverfügbarkeit bleibt separat und erhält in LQ-446 keinen neuen
Exceptionnamen.

## Writer-Supervisorport

`ControlledManifestHandoffWriterSupervisor` bietet ausschließlich:

- `prepare_writer(request)`;
- `release_writer(handle_id, claim_id, owner_id)`;
- `inspect_writer(handle_id, claim_id, owner_id)`;
- `terminate_writer(handle_id, claim_id, owner_id)`.

Es gibt keine generische Run-, Wait- oder Commandmethode.

## Writer prepare

Prepare akzeptiert nur den geschlossenen Writerrequest.

Es liefert einen gated Preparedwert, detailfreien Konflikt oder neutral
`None`.

Ein Handle wird nicht vom Caller geliefert.

Prepare öffnet den Gate nicht und autorisiert den Writer nicht.

## Writer release

Release erhält ausschließlich Handle, Execution-Claim und Execution-Owner.

Es kann prepared, weiterhin running oder terminal sichtbar machen, weil die
technische Gatefreigabe beziehungsweise das begrenzte Warten unklar oder noch
nicht abgeschlossen sein kann.

Es akzeptiert keine Observation-ID oder Authorityentscheidung.

Eine zweite Freigabe darf der spätere Adapter nur als exakten Statusretry
behandeln, niemals als zweite Gatewirkung.

## Writer inspect

Inspect ist read-only und erhält dieselbe stabile Dreifachbindung.

Es liefert nur prepared, running, terminal, Konflikt oder neutral keine
sichtbare Bindung.

PID, Signalstatus und freie Processdetails werden nicht ausgegeben.

Inspect startet und released keinen Prozess.

## Writer terminate

Terminate adressiert nur dieselbe Handle-/Claim-/Ownerbindung.

Es liefert weiterhin running, terminal, Konflikt oder neutral `None`.

Ein Signalwert und Timeout sind keine Callerparameter.

Running nach Terminate ist ausdrücklich noch kein terminaler Endnachweis.

## Recovery-Supervisorport

`ControlledManifestHandoffRecoverySupervisor` besitzt dieselben vier
Operationen mit Recovery-spezifischen Request-, Claim-, Owner- und
Zustandstypen.

Es kann keine Writerwerte annehmen oder liefern.

Prepare und Release öffnen ausschließlich die feste read-only
Reconcilerfähigkeit.

Inspect und Terminate erzeugen keine Reconciliationobservation.

## Keine Prozesspolicy im Port

Kein Portparameter heißt Command, Args, Env, cwd, Shell, Timeout, Signal,
Clock, Allow, Rolle oder Authority.

Executablebindung, Gateimplementation, Environmentallowlist,
Ressourcenlimits, Warte- und Terminierungsstrategie sind spätere validierte
Konstruktorabhängigkeiten.

Ein Aufruf kann diese Policy nicht überschreiben.

## Keine terminale Endpersistenz

Supervisorwerte sind direkte Prozessbeobachtungen, noch keine LQ-443-/LQ-444-
Endfakten.

Die spätere Composition ordnet zuerst Outcomeappend und danach den passenden
terminalen Endappend.

Running oder Prepared dürfen niemals als terminal persistiert werden.

Der Supervisorport schreibt keine Registry.

## Keine Authority

Claims und Owners im Request sind Bindungsfakten, keine Authoritysnapshots.

Aktuelle Execution- und Recoveryauthority bleiben bei LQ-443 beziehungsweise
LQ-444.

SessionPrincipal ist kein Requestfeld.

Kein Supervisorresultat autorisiert einen neuen Claim oder Cleanup.

## Retention und Statusretry

Handlebindungen müssen später controllerverlustfest auflösbar sein, solange
Prozessende und Unknown-Recovery davon abhängen.

Die Ports erlauben nur exakte read-only Inspektion derselben stabilen Bindung.

Sie enthalten keine Remove-, Forget-, Rebind- oder Adoptmethode.

Konkrete Handlepersistenz und Retention bleiben Implementierungsentscheidungen.

## Migration und Implementierung

Revision und Head bleiben `20260824_0029`.

LQ-446 ergänzt keine Tabelle, Spalte, SQL-Abfrage, Migration, Seed- oder
Bootstrapdaten.

Es gibt noch keinen Supervisoradapter, IPC-Wireformat oder Prozessstart.

LQ-439 wird nicht verändert.

## Kein Wiring

Der Slice ergänzt keinen Operator, CLI, Route, Scheduler-, Compose-, CI- oder
Production-Wiringpfad.

Es wird kein echter Writer oder Reconciler ausgeführt.

Keine Datei und kein Prozesszustand wird gelesen oder verändert.

## Tests

Fokussierte Tests belegen:

- geschlossene repr-freie Requests ohne Prozesssteuerung;
- nicht überschreibbare gated/running/terminal Zustände;
- exakte Writer-Erfolgsfaktenmatrix;
- sechs geschlossene Recoveryoutcomes;
- keine Writer-/Cleanupauthority in Recoverywerten;
- getrennte Writer-/Recoveryports mit je vier Methoden;
- keine Command-, Zeit-, Signal-, Environment- oder Allow-Parameter;
- leeren detailfreien Supervisorkonflikt;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-446 implementiert keinen Subprocessadapter, Start-Gate, IPC-Parser,
Prozesshandle-Store, Composer oder Supervisorpolicy.

Claimed Writerintegration, Recoverycomposition, Scope-/Authority-Bootstrap,
Bestandsverankerung, Cleanup und finale Evidence-Retention bleiben separat.

Staging, Commit, Push, Build, Signatur, Promotion, Publication und Deployment
werden weder ausgeführt noch autorisiert.

## Nächster Slice

LQ-447 sollte den kontrollierten startgesperrten lokalen Prozessadapter für die
geschlossenen Writer-/Recoveryports implementieren.

Claimed Writerintegration, Recoverycomposition, Bestandsverankerung, Cleanup
und Retention bleiben danach separate Slices.
