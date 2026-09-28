# LQ-468 — Controlled Supervisor Capability Executor Adapter

## Ergebnis

LQ-468 implementiert den LQ-467-Executor als konservativen Adapter über die
bestehenden kontrollierten Writer-/Recovery-Supervisorports.

Der Slice ergänzt keine konkrete Writer- oder Recoveryprimitive.

## Bestandsbefund

Das Repository besitzt geschlossene Supervisorwerte und die Ports
`ControlledManifestHandoffWriterSupervisor` sowie
`ControlledManifestHandoffRecoverySupervisor`.

Eine konkrete Implementation dieser beiden Ports ist im aktuellen Bestand
nicht vorhanden.

LQ-468 behauptet deshalb keine ausführbare Productionfähigkeit.

Der Adapter bleibt dennoch eine prüfbare Compositiongrenze für spätere
Implementierungen.

## Zwei Abhängigkeiten

Writer- und Recovery-Supervisor werden getrennt konstruktiv injiziert.

Unvollständige Composition scheitert beim Aufbau detailfrei.

Ein Executionrequest kann keinen anderen Supervisor auswählen.

Die Abhängigkeiten werden nicht aus globalem Zustand aufgelöst.

## Writerdelegation

`execute_writer` akzeptiert ausschließlich den geschlossenen LQ-467-
Writerrequest.

Handle, Claim und Owner stammen ausschließlich aus dessen vorbereitetem
Prozess.

Der Adapter ruft genau einmal `release_writer` mit diesen drei Werten auf.

Der Capabilityrequest selbst liefert keine freien Releaseparameter.

## Recoverydelegation

Recovery folgt derselben Form über genau einen `release_recovery`-Aufruf.

Auch hier stammen Handle, Claim und Owner nur aus Prepared.

Writer- und Recoveryabhängigkeit können nicht vertauscht werden.

Cross-Profile-Bindung ist bereits durch LQ-467 ausgeschlossen.

## Genau ein Releaseversuch

Der Adapter besitzt keine Schleife, keinen Retry und keinen zweiten
Releaseaufruf.

Ein technisch unklarer Ausgang wird nicht durch erneute Capabilitywirkung
aufgelöst.

Released bedeutet Gatefreigabe, nicht Erlaubnis zu beliebig vielen Starts.

Unknown-Reconciliation muss später read-only erfolgen.

## Nur direkter Terminalausgang

Writer wird ausschließlich akzeptiert, wenn der kontrollierte Supervisor
unmittelbar einen `CompletedManifestHandoffWriterProcess` liefert.

Recovery verlangt entsprechend genau den geschlossenen Recoveryabschluss.

Prepared, Running, Konflikt und `None` sind keine terminalen Ergebnisse.

Sie werden nicht normalisiert oder als Erfolg verpackt.

## Running bleibt nichtterminal

Ein Running-Record belegt mögliche fortdauernde Capabilitywirkung.

Der Adapter pollt ihn nicht und erfindet keinen Endzustand.

Er ruft auch nicht automatisch `inspect_writer` oder `inspect_recovery` auf.

Asynchrone direkte Outcome-Beobachtung benötigt einen eigenen Vertrag.

## Kein Terminatefallback

Ein nichtterminaler Releaseausgang löst keine automatische Terminierung aus.

Terminate ist eine separate durable Journal- und Engineentscheidung.

Der Adapter ruft weder `terminate_writer` noch `terminate_recovery` auf.

Fehlerbehandlung erweitert keine Prozessfähigkeit.

## Ergebnisbindung

Ein unmittelbar terminaler Writeroutcome wird über
`ExecutedManifestHandoffWriterCapability` rekonstruiert.

Der LQ-467-Konstruktor vergleicht Handle, Claim und Owner erneut vollständig.

Recovery verwendet denselben Schutz mit seinem profilspezifischen Record.

Divergente Supervisorantworten verlassen die Grenze nicht.

## Kein neutraler Ausgang

Die Executormethoden liefern nur einen vollständig gebundenen Executed-Record.

`None`, Konflikt, Prepared oder Running werden als technische Unverfügbarkeit
behandelt.

Diese Behandlung behauptet nicht, der Prozess habe keine Wirkung entfaltet.

Der Service muss denselben Handle später direkt reconciliieren.

## Fehlergrenze

Abhängigkeits-, Release-, Typ- und Ergebnisbindungsfehler werden über die
bestehende `ManifestHandoffRegistryUnavailable` detailfrei vereinheitlicht.

Konkrete IDs, Zustände und innere Fehler verlassen den Adapter nicht.

LQ-468 benennt keinen neuen Exception- oder Konflikttyp.

Technische Unverfügbarkeit wird nicht in einen fachlichen Outcome umgewandelt.

## Keine Capabilityimplementation

Der Adapter schreibt kein Manifest und reconciliiert kein Target.

Er implementiert weder Writer- noch Recoverylogik.

Er importiert keine private Handoff-Dateioperation.

Die spätere kontrollierte Primitive bleibt eine eigene Abhängigkeit.

## Keine Gateartefaktwirkung

Ready, Token und Consumed wurden bereits vor dem LQ-467-Request typisiert
gebunden.

Der Adapter liest oder schreibt keine Control-Artefakte.

Terminal-Envelope wird erst nach erfolgreichem Executed-Record über LQ-466
publiziert.

Er kann den Released-Marker nicht selbst erzeugen.

## Keine Enginewirkung

Der Adapter erstellt, startet, inspiziert, wartet oder beendet keinen
Dockercontainer.

Er besitzt weder Runtime-Container-ID noch Engineclient.

Engine-Running und Engine-Terminal bleiben Supervisorservice-Fakten.

Es gibt keinen Popen-, Thread- oder Shellfallback.

## Keine Authority

Der Adapter akzeptiert keine Session, User-ID, Workspace-ID, Permission,
Managementrolle oder Allowentscheidung.

Er löst keine aktuelle Plattformauthority auf.

Claim-/Owner-Bindung stammt aus dem bereits validierten Executionrequest.

Revocation und Terminatevoraussetzungen bleiben Sache des Service.

## Keine freien Prozessparameter

Es gibt kein Command, Args, Env, cwd, Timeout, Signal oder PID.

Der Adapter leitet ausschließlich Handle, Claim und Owner an den passenden
bestehenden Supervisorport weiter.

Ein Request kann keinen Entrypoint oder Codepfad wählen.

Die Abhängigkeit ist beim Aufbau festgelegt.

## Repr und Details

Der Adapter-Repr enthält weder Abhängigkeiten noch IDs.

Executionrequests und Outcomes behalten ihre bestehenden repr-freien Werte.

Fehlertexte enthalten keine Supervisorantwort.

Es gibt kein Logging von Capability- oder Dateidetails.

## Kein Schema oder Wiring

LQ-468 ändert keine Tabelle, Migration oder Persistenzsignatur.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Seed, Backfill, konkreten Supervisor, Entry Point, CLI-, Route-,
Compose-, Service- oder Production-Wiring.

## Tests

Fokussierte Prüfungen belegen getrennte Abhängigkeiten, exakt einen
profilspezifischen Releaseaufruf, Prepared-basierte Handle-/Claim-/Ownerwerte,
ausschließlich terminale Akzeptanz, fehlendes Polling/Terminate/Retry und
detailfreie Fehler.

## Nächster Slice

LQ-469 sollte den fehlenden asynchronen Capability-Outcome-Vertrag für direkte
Inspect-/Wait-Reconciliation definieren, ohne zweiten Release oder Start.

Erst danach kann der persistente Supervisorservice sicher komponiert werden.
