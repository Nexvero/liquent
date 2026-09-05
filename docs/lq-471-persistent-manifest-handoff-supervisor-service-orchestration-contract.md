# LQ-471 — Persistent Manifest Handoff Supervisor Service Orchestration Contract

## 1. Ergebnis

LQ-471 definiert die verbindliche Orchestrierung des persistenten
Manifest-Handoff-Supervisorservice über die bestehenden Grenzen.

Der Slice implementiert keinen Service und ergänzt keine neue Portsignatur.

## 2. Bestehende Grenzen

Der Service komponiert Backend-/Hand-Korrelationen, Journal, Runtimebinding,
Engine, Control-Artefakte, Gatewrapper, Capabilityexecutor und
Outcomebeobachtung.

Keine einzelne Grenze darf die Fakten einer anderen Grenze erfinden.

Persistenz, Enginezustand und Dateiartefakte bleiben getrennte Systeme of
Record für ihre jeweiligen Fakten.

## 3. Serviceeigentum

Genau eine stabile aktive Backendinstanz besitzt einen Job.

Controllerverlust beendet oder dupliziert keinen Job.

Clients erhalten keine Engine-, Datei- oder Capabilityabhängigkeit.

Der Service ist kein allgemeiner Prozessdienst.

## 4. Stabile Identitäten

Prepare-, Handle-, Launch-, Creation-, Control-Directory-, Artefakt-, Release-,
Terminate- und Observation-IDs werden nicht wiederverwendet.

Retries verwenden exakt dieselben IDs.

Eine neue ID ist kein Reconciliationmechanismus.

IDs erteilen selbst keine Authority oder Prozessfähigkeit.

## 5. Writer- und Recoverytrennung

Writer- und Recoveryflows bleiben von Journalregistrierung bis Terminalrecord
typseitig getrennt.

Writerprofil kann nicht in Recovery umetikettiert werden.

Recovery erhält kein Source-Mount und keine Writer- oder Cleanupfähigkeit.

Cross-Profile-Bestand ist technische Divergenz.

## 6. Prepare-Voraussetzungen

Vor neuer Wirkung löst der Service die aktuelle aktive Backendinstanz und die
exakte bestehende Vorbereitung auf.

Claim, Owner, Scopebinding und Handoffname stammen aus dem bereits
kontrollierten Request.

Ein inaktives Backend oder divergente Vorbereitung scheitert fail-closed.

SessionPrincipal wird nicht an den Service übertragen.

## 7. Prepare-Reihenfolge

Ein neuer Prepareflow hält zwingend diese Reihenfolge ein:

1. Korrelation und Journaljob idempotent registrieren;
2. Launch-Commit dauerhaft appendieren;
3. Container über dieselbe Creation-ID create/reconcile;
4. Runtimebinding dauerhaft speichern;
5. exakt den gebundenen Container einmal starten;
6. Engine-Running und dauerhaftes Ready desselben Handles beobachten;
7. Ready-Artefaktfakten dauerhaft korrelieren;
8. `prepared_gated` im Journal appendieren;
9. erst dann Prepared zurückgeben.

## 8. Keine Wirkung vor Launch-Commit

Engine-Create findet niemals vor durablem Launch-Commit statt.

Ein registrierter Job ohne Launch-Commit besitzt noch keine erlaubte
Prozesswirkung.

Ein unklarer Launch-Commit wird über dieselbe Transition-ID aufgelöst.

Der Service erzeugt keinen zweiten Journaljob.

## 9. Create-Unknown

Nach unklarem Create wird zuerst Runtimebinding nach Handle und Creation-ID
gelesen.

Danach wird Enginebestand ausschließlich über dieselbe Creation-ID
reconciliert.

Exakte Image-, Profil-, Label- und Sicherheitsbindung ist erforderlich.

Unklarer oder divergenter Bestand erzeugt keinen zweiten Container.

## 10. Runtimebinding vor Start

Die unveränderliche Engine-Container-ID muss vor Start dauerhaft an Handle,
Creation, Control-Directory und Image-Digest gebunden sein.

Ein Container ohne persistente Binding darf nicht gestartet werden.

Bindingkonflikt führt zu keiner Enginewirkung.

Name, Label oder PID ersetzen die Container-ID nicht.

## 11. Start

Start adressiert ausschließlich die persistierte Container-ID.

Vor Start wird direkt inspected und ausschließlich created akzeptiert.

Running, exited oder dead lösen keinen blinden Neustart aus.

Startannahme allein erzeugt noch kein Prepared.

## 12. Ready-Korrelation

Prepared verlangt direkte Engine-Running-Beobachtung und ein kanonisches
dauerhaft publiziertes Ready-Dokument.

Handle, Control-Directory, Ready-ID und Gated-Observation-ID müssen vollständig
übereinstimmen.

Die Artefaktfakten werden vor Journal-Gated über LQ-460 gespeichert.

Engine-Running allein oder Ready allein genügt nicht.

## 13. Prepared-Rückgabe

Der Client erhält Prepared erst aus einem Journalview im Zustand
`prepared_gated`.

Runtimebinding und Ready-Korrelation müssen zu demselben Handle auflösbar sein.

Ein transienter Wrapperhandshake reicht nicht.

Prepared erteilt noch keine Capabilityausführung.

## 14. Release-Voraussetzungen

Release verlangt exakt denselben Prepared-Job, aktive Claim-/Ownerbindung und
Journalzustand `prepared_gated`.

Eine vorhandene Release-ID wird read-only aufgelöst und nicht ersetzt.

Ein Termination-requested- oder terminaler Job wird nicht released.

Der Caller kann Inputs, Profil oder Runtime nicht ändern.

## 15. Release-Reihenfolge

Release hält zwingend diese Reihenfolge ein:

1. Prepared-, Runtime- und Ready-Bindung aktuell inspizieren;
2. Release-Commit mit stabiler Release-ID dauerhaft appendieren;
3. kanonisches Release-Token derselben ID atomar publizieren;
4. Token-Artefaktfakten dauerhaft korrelieren;
5. Wrapperkonsum und dauerhaftes Consumed-Ack derselben ID beobachten;
6. Consumed-Fakten dauerhaft korrelieren;
7. direkte Engine-Running-Beobachtung desselben Containers durchführen;
8. `running` mit stabiler Observation-ID appendieren;
9. erst danach den Released-Marker der Capabilitygrenze zuführen.

## 16. Commit vor Token

Release-Token darf niemals vor durablem Release-Commit publiziert werden.

Ein Token ohne exakt denselben Commit ist ungültiger technischer Bestand.

Der Service publiziert kein zweites Token mit neuer Release-ID.

Tokenpublikation erteilt keine allgemeine Authority.

## 17. Token vor Consumed

Consumed muss dasselbe Handle und dieselbe Release-ID wie das kanonisch
gelesene Token tragen.

Der Wrapper publiziert Ack vor Capabilityimport oder -aufruf.

Der Service kann Ack nicht aus Running ableiten.

Ein Ack ohne Token und Commit ist keine Freigabe.

## 18. Running-Reihenfolge

Journal-Running verlangt Release-Commit, persistiertes Token, persistiertes
Consumed-Ack und direkte Engine-Running-Beobachtung.

Keiner dieser vier Fakten ersetzt einen anderen.

Running wird vor tatsächlichem Consumed-Ack niemals appendiert.

Der Running-Observation-ID-Retry bleibt identisch.

## 19. Capabilityausführung

Nur der vollständig korrelierte Released-Marker darf in den LQ-467-Executor
gelangen.

Execution bindet Prepared, Handle, Claim, Owner und unveränderten
Capabilityrequest.

Der Service erzeugt keinen generischen Command oder Environmentwert.

Ein technischer Executorfehler autorisiert keinen zweiten Release oder Start.

## 20. Nichtterminaler Outcome

Liefert die Capabilityprimitive Running, bleibt der Job nichtterminal.

Der Service verwendet ausschließlich LQ-470-Inspect/Wait über dieselbe
Executionbindung.

Wait-Ausschöpfung ist kein Prozessende.

Es wird kein Outcome aus Timeout, PID-Abwesenheit oder Wrapper-EOF erfunden.

## 21. Terminale Voraussetzungen

Terminalisierung verlangt einen vollständig korrelierten geschlossenen
Capabilityoutcome und direkte Enginebeobachtung `exited` oder `dead` derselben
Container-ID.

Zusätzlich muss ein kanonisches Terminal-Envelope desselben Handles und der
stabilen Terminal-Observation-ID vorliegen.

Exitcode allein ist kein fachlicher Outcome.

Envelope allein ist kein Runtime-Endnachweis.

## 22. Terminale Reihenfolge

Ein regulärer Terminalflow hält zwingend diese Reihenfolge ein:

1. geschlossenen Executed-Outcome direkt beobachten;
2. Terminal-Envelope kanonisch atomar publizieren;
3. Envelope-Fakten dauerhaft korrelieren;
4. gebundene Engine-Container-ID bis exited/dead beobachten;
5. Envelope erneut kanonisch lesen und mit Outcome korrelieren;
6. profilspezifische Terminaltransition mit derselben Observation-ID appendieren;
7. erst den persistenten Terminalview an Clients liefern.

## 23. Ende ohne Envelope

Engine exited/dead ohne valides Envelope bleibt konservativ technisch
unverfügbar beziehungsweise benötigt den geschlossenen unknown-/unavailable-
Pfad der Capability.

Der Service erfindet keine Fakten oder Dateinamen.

Ein zweiter Capabilitystart bleibt verboten.

Terminaljournal wird erst mit einem gültigen geschlossenen Outcome appendiert.

## 24. Envelope ohne Engineende

Ein valides Envelope bei weiterhin running/created Runtime ist nichtterminal.

Der Service wartet weiterhin auf direkte Engine-Terminalität.

Er appendiert keine Terminaltransition vor exited/dead.

Envelope-Publikation terminiert den Container nicht.

## 25. Terminate-Voraussetzungen

Terminate verlangt stabilen Terminate-ID-Retry und einen nichtterminalen
gebundenen Journaljob.

Claim-/Owner- und Handlebindung werden vor neuer Signalwirkung aktuell geprüft.

Ein bereits terminaler Job erzeugt keine Enginewirkung.

Der Caller liefert weder Signal noch Timeout.

## 26. Terminate-Reihenfolge

Terminate hält zwingend diese Reihenfolge ein:

1. Journal-, Runtime- und Containerbinding direkt inspizieren;
2. `termination_requested` mit stabiler Terminate-ID dauerhaft appendieren;
3. erst danach Stop/Kill derselben persistierten Container-ID anfordern;
4. Annahme nicht als Ende interpretieren;
5. Engine bis exited/dead direkt beobachten;
6. vorhandenen geschlossenen Outcome/Envelope korrelieren oder konservativen
   profilspezifischen unknown-/unavailable-Ausgang bilden;
7. Terminaltransition dauerhaft appendieren.

## 27. Kein Signal vor Journal

Keine Stop-/Kill-Wirkung findet vor durablem Terminate-Journalfakt statt.

Ein unklarer Journalappend wird mit derselben Terminate-ID aufgelöst.

Der Service sendet nicht vorsorglich ein zweites Signal an einen anderen
Container.

Terminate-Annahme bleibt nichtterminal.

## 28. Read-only Inspect

Client-Inspect liest Journal, Runtimebinding, Engine und erforderliche
Artefaktkorrelationen read-only.

Es publiziert kein Token, Ack oder Envelope.

Es startet, released, terminiert und terminalisiert nichts.

Inkonsistenz wird nicht automatisch repariert.

## 29. Restart PREPARE_REGISTERED

Ohne Launch-Commit ist keine Enginewirkung erlaubt.

Nur derselbe Prepareflow darf dieselbe Launch-ID fortsetzen.

Enginebestand unter der Creation-ID wäre Divergenz.

Es wird kein neuer Handle registriert.

## 30. Restart LAUNCH_COMMITTED

Der Service liest Runtimebinding und reconciliert dieselbe Creation-ID.

Fehlt autoritativ jede Create-Wirkung, darf derselbe Createversuch fortgesetzt
werden.

Bestehender exakter Container wird gebunden, inspiziert und nicht blind
gestartet.

Unklarer Bestand bleibt gesperrt.

## 31. Restart PREPARED_GATED

Runtime muss created/running gemäß belegtem Startstand und Ready muss exakt
kanonisch vorhanden sein.

Tokenabwesenheit ist vor Release-Commit neutral.

Token oder Ack ohne Release-Commit ist technische Divergenz.

Prepared wird nur aus konsistentem Bestand rekonstruiert.

## 32. Restart RELEASE_COMMITTED

Der Service löst exakt dieselbe Release-ID in Journal, Token und Ack auf.

Fehlendes Token darf mit denselben kanonischen Bytes idempotent publiziert
werden.

Vorhandenes Token ohne Ack lässt den Wrapper gated.

Vorhandenes Ack verlangt direkte Engine-Running-Beobachtung vor Journal-Running.

## 33. Restart RUNNING

Der Service ruft weder Release noch Start erneut auf.

LQ-470 inspiziert dieselbe Executionbindung read-only.

Running bleibt Running; Executed wird mit Envelope und Engineende korreliert.

Fehlender erwarteter Prozess- oder Containerbestand ist nicht neutral.

## 34. Restart TERMINATION_REQUESTED

Dieselbe Terminate-ID und Runtime-Container-ID bleiben verbindlich.

Engine-Running erlaubt erneute idempotente Terminate-Anforderung nur gemäß
geschlossener Enginepolicy, keinen Capabilityrestart.

Engine-Terminal wird mit vorhandenem Outcome/Envelope korreliert.

Abwesenheit ist kein Endnachweis.

## 35. Restart TERMINAL_OBSERVED

Der persistente Terminalview ist endgültig.

Service-Neustart erzeugt keine Engine-, Gate-, Executor- oder Journalwirkung.

Runtime und Artefakte bleiben mindestens bis separater Retentionentscheidung
erhalten.

IDs und Terminalfakten werden nicht wiederverwendet.

## 36. Technische Unverfügbarkeit

Erwarteter fehlender Journal-, Runtime-, Container-, Gate-, Artefakt- oder
Outcome-Bestand ist technische Unverfügbarkeit.

`None` bleibt nur autoritativ neutraler Abwesenheit an der jeweiligen
Vorwirkungsgrenze vorbehalten.

Unklare Wirkung wird nie als Nichtwirkung normalisiert.

Infrastrukturdetails verlassen den Service nicht.

## 37. Konflikte

Journal-, Runtime-, Engine-, Artefakt- und Wrapperkonflikte bleiben getrennte
detailfreie Domainergebnisse, soweit der aufrufende Servicevertrag sie sichtbar
macht.

Der Service überschreibt keine persistente oder physische Divergenz.

Ein Konflikt erweitert keine Retry- oder Cleanupfähigkeit.

Cross-System-Divergenz bleibt fail-closed.

## 38. Authoritygrenze

Transportauthentisierung des Plattformclients ist keine fachliche Authority.

SessionPrincipal, Workspacepermission und Managementrolle werden nicht an den
Supervisorprozess übertragen.

Claim-/Owner- und aktuelle Lifecyclevoraussetzungen werden vor jeder neuen
Wirkung in der Plattformcomposition geprüft.

Persistierte Runtime- oder Gatefakten erteilen keine Authority.

## 39. Ressourcen und Retention

Parallelität, Waitversuche, Pausen, Containerlimits und Artefaktgröße sind
konstruktive Servicepolicy.

Requests können diese Grenzen nicht erhöhen.

Container, Runtimebinding, Journal und Control-Artefakte bleiben mindestens bis
persistierter Terminalkorrelation erhalten.

Cleanup ist keine implizite Serviceoperation dieses Vertrags.

## 40. Keine Implementation

LQ-471 ergänzt keinen Serviceport, Composer, Worker, Thread oder Entry Point.

Es ändert keine Domain-, Persistenz- oder Adaptersignatur.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Seed, Backfill, CLI-, Route-, Compose- oder Production-Wiring.

## 41. Tests

Fokussierte statische Prüfungen belegen Prepare-, Release-, Running-, Terminal-
und Terminate-Reihenfolge, sechs Restartzustände, read-only Inspect,
Cross-System-Fail-closed und fehlende Implementation.

## 42. Nächster Slice

LQ-472 sollte geschlossene Servicecommand- und Ergebniswerte sowie minimale
Writer-/Recovery-Serviceports definieren.

Die Orchestrierungsimplementation und Productioncomposition folgen separat.
