# LQ-472 — Persistent Supervisor Service Commands, Results and Ports

## Ergebnis

LQ-472 definiert geschlossene Commands, persistenzgebundene Ergebnisse und
minimale Writer-/Recovery-Serviceports für den LQ-471-Vertrag.

Der Slice implementiert den Service noch nicht.

## Vier Commandformen

Der Service kennt Prepare, Release, Terminate und Inspect.

Writer und Recovery besitzen getrennte Preparetypen.

Release, Terminate und Inspect sind profilneutral, weil sie ausschließlich
einen bereits persistent typisierten Handle adressieren.

Es gibt keinen generischen Operationsstring.

## Writer Prepare

Writer-Prepare bindet die vollständige Writer-Journalregistrierung, Creation-
ID, Control-Directory-ID, Image-Digest und Gate-Startbindung.

Gateprofil muss Writer sein.

Gatehandle muss dem registrierten Handle entsprechen.

Gate-Control-Directory muss der Command-ID entsprechen.

## Recovery Prepare

Recovery verwendet dieselbe geschlossene Form mit
Recovery-Journalregistrierung und festem Recoveryprofil.

Writerregistrierung oder Writerprofil wird abgelehnt.

Der Command erweitert keine Recovery-, Writer- oder Cleanupfähigkeit.

Cross-Profile-Prepare ist unkonstruierbar.

## Vollständige Gateidentitäten

Die Gate-Startbindung trägt Ready-, Consumed- und Terminal-Artefakt-ID sowie
Gated- und Terminal-Observation-ID.

Diese Identitäten sind vor erster Prozesswirkung stabil.

Der Prepare-Retry muss dieselben Werte wiederverwenden.

Ein Service darf sie nach Neustart nicht neu erzeugen.

## Releasecommand

Release bindet ausschließlich Handle, Release-ID, Token-Artefakt-ID und
Running-Observation-ID.

Prozessrequest, Profil, Image und Runtime können bei Release nicht geändert
werden.

Consumed- und Terminal-ID stammen weiterhin aus der ursprünglichen
Gatebindung.

Eine andere Release-ID ist kein Retry.

## Terminatecommand

Terminate enthält nur Handle und stabile Terminate-ID.

Signal, Graceperiod, Timeout und Container-ID sind keine Callerparameter.

Der Service löst die persistente Runtimebinding selbst auf.

Ein Retry verwendet dieselbe Terminate-ID.

## Inspectcommand

Inspect enthält ausschließlich den internen Supervisorhandle.

Es gibt keine Profil-, Backend-, Claim-, Owner- oder Include-Option.

Der Service bestimmt den Jobtyp aus der persistenten Journalregistrierung.

Inspectcommand erteilt keine Wirkung.

## Keine Caller-Authority

Kein Command akzeptiert SessionPrincipal, User-ID, Workspace-ID, Permission,
Managementrolle oder Allowentscheidung.

Der Plattformclient prüft aktuelle Claim-/Owner- und Lifecyclevoraussetzungen
vor neuen Wirkungscommands.

Transportauthentisierung bleibt getrennt.

Service-IDs sind keine allgemeine Authority.

## Writerergebnis

`ManifestHandoffWriterServiceResult` bindet Writer-Journalview,
Runtimebinding und genau einen sichtbaren Writerprozesszustand.

Alle drei müssen denselben Handle tragen.

Claim und Owner des Prozesses müssen dem registrierten Processrequest
entsprechen.

Interne Engine- und Artefaktdetails werden nicht zurückgegeben.

## Recoveryergebnis

Recovery bindet entsprechend Recovery-Journalview, Runtime und
Recoveryprozesszustand.

Writerzustände sind typseitig ausgeschlossen.

Handle, Claim und Owner werden vollständig verglichen.

Die bestehende Recovery-Kind-/Faktenmatrix bleibt wirksam.

## Sichtbare Zustände

`prepared_gated` verlangt exakt Prepared.

`running` verlangt exakt Running.

`termination_requested` bleibt nichtterminal und verlangt ebenfalls Running.

`terminal_observed` verlangt exakt Completed.

## Nicht sichtbare Zwischenzustände

`prepare_registered`, `launch_committed` und `release_committed` sind
orchestrierungsinterne Zwischenzustände.

Sie können nicht als erfolgreicher ServiceResult konstruiert werden.

Der Service reconciliiert sie intern oder bleibt technisch unverfügbar.

Er erfindet für sie keinen Prepared- oder Runningzustand.

## Terminalkonsistenz

Bei `terminal_observed` muss der Prozess exakt dem Ergebnis des Journalviews
entsprechen.

Ein anderer geschlossener Outcome desselben Handles genügt nicht.

Claim und Owner bleiben zusätzlich gebunden.

Last-write-wins ist ausgeschlossen.

## Runtimekonsistenz

Jeder sichtbare Result verlangt eine persistente Runtimebinding desselben
Handles.

Ein Journalview ohne Runtime wird nicht als Prepared, Running oder Terminal
ausgegeben.

Container-ID und Control-Directory bleiben im internen Runtimewert repr-frei.

Der Result erteilt keine Enginewirkung.

## Writer-Serviceport

Der Writerport besitzt genau `prepare_writer`, `release_writer`,
`terminate_writer` und `inspect_writer`.

Jede Wirkungsmethode akzeptiert genau ihren geschlossenen Command.

Inspect akzeptiert nur den read-only Inspectcommand.

Es gibt keinen Cleanup-, Restart- oder generischen Executepfad.

## Recovery-Serviceport

Recovery besitzt dieselben vier profilspezifisch benannten Operationen.

Prepare akzeptiert ausschließlich Recovery-Prepare.

Alle Ergebnisse sind Recovery-ServiceResults.

Writer- und Recoveryports können unabhängig komponiert werden.

## Neutrale Abwesenheit

Prepare, Release und Terminate dürfen `None` nur für eine autoritativ neutrale
Vorwirkungsentscheidung liefern.

Inspect darf `None` ausschließlich für einen autoritativ unbekannten beliebigen
Handle liefern.

Ein erwarteter Journaljob ohne Runtime, Container, Artefakt oder Outcome ist
nicht neutral.

Unklare Wirkung bleibt technische Unverfügbarkeit.

## Servicekonflikt

`ManifestHandoffSupervisorServiceConflict` ist feldlos und detailfrei.

Er vereinheitlicht sichtbare Cross-System-Divergenz an der Servicegrenze.

Bestehende Journal-, Runtime-, Engine-, Artefakt- und Wrapperkonflikte werden
nicht mit Details transportiert.

Konflikt erzeugt keine Reparatur- oder Cleanupfähigkeit.

## Reprgrenze

Commands, Results und interne IDs tragen sensible Werte repr-frei.

Der Servicekonflikt besitzt keine Felder.

Validierungsfehler nennen keine konkrete Identität oder Infrastruktur.

Runtime-, Artefakt- und Outcomeinhalte werden nicht geloggt.

## Persistenzblocker: Gatebindung

Revision 0032 persistiert Runtimebinding und bereits publizierte
Artefaktkorrelationen.

Die vollständige vorab reservierte Gatebindung aus Prepare wird jedoch noch
nicht als eigener unveränderlicher Record gespeichert.

Insbesondere Consumed- und Terminal-Artefakt-ID müssen nach einem Neustart vor
ihrer ersten Publikation weiterhin exakt auflösbar sein.

## Warum Command-Retry nicht genügt

Ein Client kann nach Servicecrash fehlen oder seinen ursprünglichen Command
nicht erneut senden.

Der Service darf stabile IDs nicht aus transientem Speicher rekonstruieren.

Er darf auch keine neuen Artefakt-IDs erzeugen.

Productionimplementation bleibt deshalb bis zu einer persistenten
Gatebinding-Foundation gesperrt.

## Keine versteckte Ableitung

Gateartefakt-IDs werden nicht aus Handle, Release-ID, Dateiname oder Hash
abgeleitet.

Deterministische Namensableitung wäre keine Persistenz derselben internen
Fakten.

Der Service adoptiert keine zufällig vorhandene Datei als reservierte ID.

Die spätere Foundation muss Eindeutigkeit und Nichtwiederverwendung sichern.

## Spätere Foundation

Ein Folgeslice muss die vollständige Gatebindung an bestehenden Journaljob,
Handle, Profil und Control-Directory dauerhaft binden.

Er muss idempotenten exakten Retry, Divergenzkonflikt und read-only Lookup
bereitstellen.

Er darf keinen Container, kein Artefakt und keine Authority erzeugen.

Konkretes Schema und Migration werden erst in diesem separaten Slice
entschieden.

## Keine Implementation

LQ-472 orchestriert keinen Journal-, Engine-, Datei-, Gate- oder Executoraufruf.

Es startet keinen Thread und besitzt keine Clock oder ID-Quelle.

Commands führen bei Konstruktion keinerlei I/O aus.

Der Serviceadapter folgt erst nach Schließung des Persistenzblockers.

## Kein Schema oder Wiring

LQ-472 ändert keine Tabelle oder Migration.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Seed, Backfill, Serviceimplementation, Entry Point, CLI-,
Route-, Compose- oder Production-Wiring.

## Tests

Fokussierte Tests belegen geschlossene Prepare-/Release-/Terminate-/Inspect-
Commands, Profil-/Handle-/Control-Directory-Bindung, sichtbare
Journal-/Prozessmatrix, Runtime-/Claim-/Owner-/Terminalkonsistenz, minimale
Serviceports und den expliziten Gatebinding-Persistenzblocker.

## Nächster Slice

LQ-473 sollte die persistente unveränderliche Gatebinding-Foundation und ihren
read-only Lookup definieren.

Erst danach folgt die LQ-471-Serviceimplementation.
