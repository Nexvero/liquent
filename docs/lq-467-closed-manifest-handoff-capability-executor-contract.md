# LQ-467 — Closed Manifest Handoff Capability Executor Contract

## Ergebnis

LQ-467 definiert die einzige Grenze, an der Writer- oder Recoveryfähigkeit nach
dem Gate tatsächlich ausgeführt werden darf.

Der Slice implementiert noch keinen Executor und führt keine Capability aus.

## Zwei getrennte Requests

Writer und Recovery besitzen verschiedene Execution-Requesttypen.

Es gibt keinen freien Profil-, Capability- oder Operationsstring.

Der konkrete Requesttyp bestimmt den zulässigen Executorpfad.

Cross-Profile-Aufrufe scheitern bereits bei Konstruktion.

## Released ist zwingend

Jeder Execution-Request verlangt exakt einen
`ReleasedManifestHandoffSupervisorGateWrapper`.

Ready oder ein akzeptiertes Token sind keine zulässigen Ersatzwerte.

Damit ist ein dauerhaft publiziertes Consumed-Ack typseitige Voraussetzung.

Es gibt keinen alternativen Allowpfad.

## Prepared ist zwingend

Writer verlangt den bestehenden vorbereiteten Writerprozess.

Recovery verlangt den bestehenden vorbereiteten Recoveryprozess.

Der vorbereitete Handle muss exakt dem Handle der ursprünglichen Gatebindung
entsprechen.

Ein Released-Marker eines anderen Jobs kann nicht wiederverwendet werden.

## Capabilityrequest

Zusätzlich wird der bestehende geschlossene Writer- beziehungsweise
Recovery-Supervisorrequest gebunden.

Er trägt Claim, Owner, Scopebinding und Manifestnamen.

Der Executorvertrag ergänzt keine freien Pfade, Commands oder Argumente.

Die vorhandenen Requestkonstruktoren validieren ihre vollständige Form erneut.

## Claimbindung

Claim-ID des vorbereiteten Prozesses muss exakt der Claim-ID des
Capabilityrequests entsprechen.

Ein anderer Claim kann nicht unter demselben Gate ausgeführt werden.

Claimwerte bleiben repr-frei.

Der Executor erzeugt oder erneuert keinen Claim.

## Ownerbindung

Owner-ID des vorbereiteten Prozesses muss exakt der Owner-ID des
Capabilityrequests entsprechen.

Ein fremder Worker oder Serviceowner kann den vorbereiteten Prozess nicht
übernehmen.

Ownerwerte bleiben repr-frei.

Aktuelle Claim-/Ownergültigkeit wird später vor Servicefreigabe erneut geprüft.

## Profilbindung Writer

Writerexecution verlangt das feste Writerprofil in der ursprünglichen
Gatebindung.

Ein Recovery-Gate kann keinen Writerrequest tragen.

Der Request kann das Profil nicht überschreiben.

Die Profilentscheidung stammt aus der persistierten Runtimecomposition.

## Profilbindung Recovery

Recoveryexecution verlangt das feste Recoveryprofil.

Ein Writer-Gate kann keinen Recoveryrequest tragen.

Recovery bleibt über den bestehenden Request read-only und ohne Writer- oder
Cleanupfähigkeit.

Der Executorvertrag erweitert diese Fähigkeit nicht.

## Writerergebnis

Erfolgreiche Writerexecution liefert einen
`ExecutedManifestHandoffWriterCapability`.

Er enthält den vollständigen Execution-Request und genau einen bestehenden
geschlossenen Writerabschluss.

Outcome-Handle, Claim und Owner müssen erneut der Vorbereitung entsprechen.

Freie Ergebnisformen sind ausgeschlossen.

## Recoveryergebnis

Recovery liefert entsprechend einen geschlossenen Recoveryabschluss.

Handle, Claim und Owner werden erneut vollständig verglichen.

Writeroutcomes sind im Recoveryresultat typseitig unmöglich.

Die bestehende Kind-/Faktenmatrix bleibt unverändert wirksam.

## Kein neutrales Ergebnis

Die Executormethoden liefern nach tatsächlichem Aufruf genau einen geschlossenen
Executed-Record.

Sie liefern kein `None`, keinen freien Status und keinen Allowboolean.

Technische Unfähigkeit, einen sicheren Outcome zu bestimmen, bleibt an der
detailfreien technischen Fehlergrenze.

Ein geschlossener Outcome kann weiterhin `outcome_unknown` oder `unavailable`
gemäß bestehender Domainmatrix ausdrücken.

## Keine Retrybehauptung

Der Executorvertrag behauptet nicht, Capabilityausführung sei beliebig
idempotent wiederholbar.

Released erteilt keine zweite Ausführung nach unklarem Prozessausgang.

Runtime-, Journal- und Terminalreconciliation müssen vor jedem späteren
Entscheid read-only korreliert werden.

Ein zweiter Container oder Capabilitystart bleibt ausgeschlossen.

## Terminalfolge

Der Executed-Outcome ist Eingang für den LQ-466-Terminalrequest.

Er wird erst danach kanonisch als Terminal-Envelope publiziert.

Envelope-Publikation und Engine-Terminalbeobachtung bleiben getrennte Fakten.

Der Executor schreibt kein Terminaljournal.

## Port

`ManifestHandoffSupervisorCapabilityExecutor` besitzt genau
`execute_writer` und `execute_recovery`.

Beide Methoden akzeptieren ausschließlich den jeweiligen geschlossenen
Execution-Request.

Es gibt keine generische `execute`, `run`, `shell` oder `call`-Methode.

Die Rückgabetypen sind profilspezifisch.

## Keine Authorityparameter

Der Vertrag akzeptiert keine SessionPrincipal, User-ID, Workspace-ID,
Permission, Managementrolle oder Allowentscheidung.

Released ist ein enger Gatebeleg und keine allgemeine Authority.

Aktuelle persistente Claim-/Owner- und Terminatebedingungen bleiben Aufgabe des
Supervisorservice.

## Keine Prozessparameter

Es gibt kein Command, Args, Env, cwd, Shell, PID, Signal oder Timeout im neuen
Vertrag.

Writer-/Recoveryimplementation und Mountprofil sind konstruktiv festgelegt.

Ein Caller kann keinen anderen Code auswählen.

Der Slice importiert keine subprocess-, Docker- oder Socketbibliothek.

## Keine Dateigrenze

Der Vertrag liest oder schreibt keine Control-Datei.

Codec, Gatewrapper und Executor bleiben getrennte Verantwortlichkeiten.

Scopebinding des bestehenden Capabilityrequests wird nicht als
Control-Directory verwendet.

Terminal-Envelope folgt erst über LQ-466.

## Fehlergrenze

Ungültige Cross-Job-, Cross-Claim-, Cross-Owner- oder Cross-Profile-Bindungen
scheitern bei Konstruktion ohne konkrete Werte in der Meldung.

Technische Executorfehler bleiben über die bestehende detailfreie Grenze.

LQ-467 benennt keinen neuen Exception- oder Konflikttyp.

Es gibt kein Last-write-wins oder automatische Neubindung.

## Kein Schema oder Wiring

LQ-467 ändert keine Tabelle, Migration oder bestehende Persistenzsignatur.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Seed, Backfill, Executoradapter, Entry Point, CLI-, Route-,
Compose-, Service- oder Production-Wiring.

## Tests

Fokussierte Tests belegen Released-Pflicht, Writer-/Recoverytrennung,
Handle-/Claim-/Ownerbindung, profilgebundene Requests, vollständig korrelierte
Outcomes, zwei minimale Portmethoden und fehlende Authority-/Prozessparameter.

## Nächster Slice

LQ-468 sollte die vorhandenen kontrollierten Writer-/Recoveryprimitive hinter
diesem Executorvertrag adaptieren, ohne Supervisorservice oder
Productionentrypoint zu verdrahten.

Servicecomposition und Unknown-Reconciliation folgen separat.
