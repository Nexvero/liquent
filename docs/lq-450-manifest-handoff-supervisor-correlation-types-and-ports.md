# LQ-450 — Manifest Handoff Supervisor Correlation Types and Ports

## Ergebnis

LQ-450 konkretisiert die LQ-449-Foundation mit geschlossenen Plattformwerten
und drei minimalen Portgrenzen.

Der Slice implementiert noch keinen Persistenzadapter oder Supervisorservice.

## Eigenes Korrelationsmodul

Die Werte liegen in
`identity.manifest_handoff_supervisor_correlation`.

Das Modul importiert bestehende Claim-, Owner- und Handlewerte, aber keine
Persistenz-, Prozess-, IPC- oder Konfigurationsbibliothek.

Der Import erzeugt keine Backend- oder Prozesswirkung.

## Stabile Identitäten

Fünf neue repr-freie nicht leere Stringwerte modellieren:

- Backendinstanz-ID;
- Prepare-ID;
- Release-ID;
- Terminate-ID;
- terminale Supervisor-Observation-ID.

Der bestehende LQ-446-Handle bleibt die sechste stabile Identität.

## Keine abgeleiteten IDs

Keine Identität wird aus PID, Host, Claim, Owner, Zeit, Pfad oder Dateiname
abgeleitet.

Die Werte tragen keine Authority und keine Prozesssteuerung.

Leere Werte scheitern bei Konstruktion.

Ihre spätere kontrollierte Erzeugung bleibt Adapterabhängigkeit.

## Backendstatus

`ManifestHandoffSupervisorBackendStatus` ist exakt `active` oder `inactive`.

`ManifestHandoffSupervisorBackend` bindet Instanz-ID, Status und aware UTC
Provisionierungszeit.

Der Record ist unveränderlich und gibt die Instanz-ID nicht über `repr` aus.

Ein aktiver Record autorisiert noch keinen Claim.

## Aktuelle Backendauflösung

`CurrentManifestHandoffSupervisorBackend.resolve()` ist parameterlos.

Die Implementierung muss den aktuellen aktiven Backendbestand aus dem System
of Record lesen.

Inaktivität oder neutrale Abwesenheit ergibt `None`.

Technische Unverfügbarkeit bleibt davon getrennt.

## Keine freie Backendwahl

Der Lookup akzeptiert insbesondere keine Backend-ID, URL, Host-, Socket-,
Container- oder Produktwahl.

Auch SessionPrincipal, Rolle, Allowboolean und Authoritysnapshot fehlen.

Der Caller kann dadurch keine inaktive oder fremde Instanz auswählen.

Konkrete Provisionierung und Statusmutation bleiben separat.

## Getrennte Prepare-Requests

`ReserveManifestHandoffWriterPreparation` bindet Prepare-ID,
Backendinstanz-ID, Execution-Claim und Execution-Owner.

`ReserveManifestHandoffRecoveryPreparation` bindet dieselben
Korrelationsrollen mit Recovery-Claim und Recovery-Owner.

Es gibt keinen generischen Request mit nullable Claimfeldern oder
caller-gelieferter Capability.

## Prepare-Records

Die korrespondierenden `Reserved...Preparation`-Records ergänzen ausschließlich
die serverseitige aware UTC Reservierungszeit.

Alle IDs und Owner bleiben repr-frei.

Writer- und Recoverytypen sind nicht austauschbar.

Eine Reservierung startet keinen Prozess und öffnet kein Gate.

## Handle-Request

`BindManifestHandoffSupervisorHandle` enthält ausschließlich Prepare-ID,
Backendinstanz-ID und den bestehenden opaken Handle.

`BoundManifestHandoffSupervisorHandle` ergänzt die serverseitige aware UTC
Bindungszeit.

Der Request trägt keinen PID-, Gate-, Prozess- oder Outcomezustand.

Backend und Prepare müssen später persistent exakt zusammenpassen.

## Release-Request

`RecordManifestHandoffSupervisorRelease` bindet stabile Release-ID und Handle.

`RecordedManifestHandoffSupervisorRelease` ergänzt die serverseitige aware UTC
Anforderungszeit.

Der Record behauptet weder angenommene noch ausgeführte Gatewirkung.

Physische Freigabe bleibt beim externen Supervisorjournal.

## Terminate-Request

`RecordManifestHandoffSupervisorTermination` bindet stabile Terminate-ID und
Handle.

Der gespeicherte Record ergänzt ausschließlich die serverseitige
Anforderungszeit.

Es gibt kein Signal-, Timeout-, PID- oder Erfolgsfeld.

Eine persistierte Anfrage ist kein terminaler Fakt.

## Terminal-Request

`RecordManifestHandoffSupervisorTerminalObservation` bindet stabile terminale
Observation-ID und Handle.

Der gespeicherte Record ergänzt die serverseitige aware UTC
Korrelationszeit.

Er enthält keinen freien Exitcode, stdout, stderr oder Caller-Outcome.

Die direkte geschlossene Prozessobservation kommt weiterhin vom Supervisor.

## Strikte Konstruktion

Jeder Request und Record prüft seine exakten Domainklassen.

Strings können nicht anstelle typisierter IDs eingesetzt werden.

Alle gespeicherten Zeiten müssen aware UTC sein.

Naive oder nicht-UTC Zeiten scheitern fail-closed.

## Repr-Grenze

Backend-, Prepare-, Handle-, Release-, Terminate-, Terminal-, Claim- und
Owneridentitäten sind in allen neuen Records repr-frei.

Keine ID wird in Fehlermeldungen interpoliert.

Der detailfreie Konflikttyp trägt keine Felder.

Transportlogging bleibt außerhalb dieser Domainwerte.

## Korrelationsstore

`ManifestHandoffSupervisorCorrelationStore` besitzt genau sechs Methoden:

- Writer-Prepare reservieren;
- Recovery-Prepare reservieren;
- Handle binden;
- Releaseanforderung sichern;
- Terminierungsanforderung sichern;
- terminale Observationkorrelation sichern.

Jede Methode akzeptiert genau einen geschlossenen Request.

## Store-Ergebnisse

Ein erfolgreicher Append liefert den entsprechenden persistenten Record.

Neutrale Ablehnung oder Abwesenheit liefert `None`.

Divergente ID-Wiederverwendung liefert den detailfreien
`ManifestHandoffSupervisorCorrelationConflict`.

Technische Unverfügbarkeit bleibt eine separate bestehende Adaptergrenze.

## Read-only Lookup

`ManifestHandoffSupervisorCorrelationLookup` besitzt genau fünf
Auflösungsmethoden für:

- Prepare-ID;
- Handlebindung über Prepare-ID;
- Release-ID;
- Terminate-ID;
- terminale Observation-ID.

Alle Methoden lesen nur exakt die übergebene stabile Identität.

## Unknown-Auflösung

Der Lookup erzeugt keine neue ID und mutiert keinen Bestand.

Prepareauflösung liefert ausschließlich einen Writer- oder Recoveryrecord.

Handleauflösung adoptiert keinen fremden Prozess.

Neutrales `None` wird nicht als terminales Ende interpretiert.

## Keine generische Operationsmethode

Es gibt kein `record(kind, payload)`, `run`, `execute` oder `set_state`.

Der Store akzeptiert keine Dict-, JSON-, Command-, Args-, Env- oder
Statuspayload.

Release, Terminate und Terminal bleiben unterschiedliche Typen und Methoden.

Dadurch kann ein Caller keine Operationsart umetikettieren.

## Keine Authorityparameter

Kein neuer Request oder Port akzeptiert Actor, SessionPrincipal, Rolle,
Permission, Allowboolean oder Authoritysnapshot.

Die fachlichen LQ-443-/LQ-444-Grenzen bleiben unverändert.

Backend- und Korrelationsrecords erteilen keine Writer- oder
Recoveryfähigkeit.

Revocation muss spätere fachliche Entscheidungen weiterhin sperren.

## Keine Prozessparameter

Kein Port akzeptiert Executable, Command, Argumente, Environment,
Arbeitsverzeichnis, Shell, Timeout, Signal oder Clock.

Der Store startet, released, inspiziert oder terminiert keinen Prozess.

Der Lookup liest kein Prozesslisting.

Supervisoroperationen bleiben in den getrennten LQ-446-Ports.

## Retention und Nichtwiederverwendung

Die Typen erlauben kein Rebind oder Überschreiben.

Persistenzadapter müssen die Eindeutigkeiten aus LQ-449 durchsetzen.

IDs bleiben mindestens erhalten, solange Parallelitätsausschluss,
Unknown-Auflösung, Recovery oder Audit davon abhängen.

Eine konkrete Frist bleibt separat.

## Bestandsattempts

Die neuen Typen erzeugen keinen synthetischen Backend-, Prepare- oder
Handlewert für Altattempts.

Lookup-`None` erlaubt keinen Backfill aus PID, Log oder Datei.

Bestandsverankerung bleibt separat owner-kontrolliert.

LQ-439 wird nicht adoptiert.

## Keine Persistenzimplementation

LQ-450 schreibt kein SQL und implementiert keine der sechs LQ-449-Tabellen.

Es ändert keine Tabelle, Spalte oder Migration.

Revision und Head bleiben `20260824_0030`.

Ein Datenbankadapter folgt separat.

## Kein Wiring

Es gibt keinen Supervisorservice, Journaladapter, IPC-Transport oder
Prozesswrapper.

Kein CLI-, Operator-, Route-, Compose-, CI- oder Production-Wiring wird
ergänzt.

Der bestehende Direktcomposer bleibt ohne Production-Fallback.

## Tests

Fokussierte Tests belegen:

- fünf repr-freie stabile IDs und geschlossenen Backendstatus;
- getrennte Writer-/Recovery-Preparetypen;
- strikte ID- und aware-UTC-Konstruktion;
- geschlossene Handle-, Release-, Terminate- und Terminalrequests;
- genau sechs Store- und fünf Lookupmethoden;
- parameterlosen aktuellen Backendlookup;
- keine Authority-, Prozess-, Status- oder Clockparameter;
- detailfreien Konflikt und neutrale `None`-Grenzen;
- unveränderten Head 0030;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-450 implementiert keine ID- oder Clockquelle, Backendprovisionierung,
Persistenzabfrage oder Transaktion.

Supervisorjournal, Serviceprozess, Prozessadapter, Composition, Bestand,
Cleanup und finale Retention bleiben separat.

## Nächster Slice

LQ-451 sollte den persistenten Datenbankadapter für aktuelle Backendauflösung,
sechs idempotente Korrelationsappends und fünf read-only ID-Auflösungen
implementieren.

Supervisorjournal und Prozessservice bleiben danach separat.
