# LQ-452 — Durable Manifest Handoff Supervisor Journal Contract

## 1. Ergebnis

LQ-452 definiert die autoritative interne Journal- und Zustandsgrenze des
controllerunabhängigen Manifest-Handoff-Supervisors.

Der Slice implementiert noch kein Journal, keinen Service und keinen Prozess.

## 2. Rolle des Journals

Das Supervisorjournal ist die einzige autoritative Quelle für direkte
Prepare-, Gate-, Lauf-, Terminierungs- und Terminalbeobachtungen.

Die LQ-449-Plattformtabellen korrelieren diese Fakten, ersetzen sie aber nicht.

PID, Prozesslisting, Pipezustand, Timeout und Dateiabwesenheit sind keine
Journalfakten.

## 3. Feste Backendinstanz

Jeder Journalbestand gehört genau einer stabilen Backendinstanz-ID.

Die ID wird beim kontrollierten Serviceaufbau gebunden und nicht pro Request
gewählt.

Ein Journalbestand einer anderen Instanz wird weder importiert noch adoptiert.

Backendinstanz-IDs werden nicht wiederverwendet.

## 4. Zwei feste Fähigkeiten

Das Journal kennt ausschließlich `writer` und `recovery`.

Writer bezeichnet genau den kontrollierten LQ-426-Prozess.

Recovery bezeichnet genau den read-only LQ-427-Reconciler.

Es gibt keine generische Command-, Shell- oder Pluginfähigkeit.

## 5. Unveränderliche Jobbindung

Prepare-ID, Backendinstanz, Capability, Claimkorrelation, Ownerkorrelation und
opaker Handle bilden eine unveränderliche Jobbindung.

Der Service darf keinen Bestandteil nachträglich ersetzen.

Ein Handle gehört höchstens einer Prepare-ID.

Eine Prepare-ID erzeugt höchstens einen physischen Kindprozess.

## 6. Zustandsfolge

Die einzige vorwärts gerichtete Zustandsfolge lautet:

1. `prepare_registered`;
2. `launch_committed`;
3. `prepared_gated`;
4. optional `release_committed`;
5. optional `running`;
6. optional `termination_requested`;
7. `terminal_observed`.

Zustände werden nicht zurückgesetzt oder überschrieben.

## 7. Append-orientierte Historie

Jeder Übergang ist ein eigener historiesicherer Fakt mit stabiler Identität
und serverseitiger aware UTC Zeit.

Ein frei mutierbares `current_state` ist nicht die normative Historie.

Eine Projektion darf den aktuellen Zustand aus gültigen Fakten ableiten.

Widersprüchliche oder lückenhafte Folgen bleiben technisch unverfügbar.

## 8. Prepare-Registrierung

Vor jeder Prozessanlage journalisiert der Service die vollständige
unveränderliche Preparebindung.

Er bestätigt dem Client zu diesem Zeitpunkt noch keinen vorbereiteten
Prozess.

Ein Crash nach Registrierung wird mit derselben Prepare-ID aufgelöst.

Eine neue Prepare-ID darf den registrierten Job nicht ersetzen.

## 9. Launch-Commit

Vor der physischen Prozessanlage entsteht genau ein stabiler Launch-Commit.

Der Launchmechanismus muss denselben Commit idempotent erkennen oder seine
Nichtwirkung autoritativ belegen.

Ein unklarer Launch wird nicht durch einen zweiten Spawn beantwortet.

Ohne eindeutige Auflösung bleibt der Job fail-closed.

## 10. Start-Gate

Der Kindprozess beginnt in einem Supervisorwrapper vor jedem Writer- oder
Reconcilerzugriff.

Der Wrapper bindet sich an Handle und einmaligen Gatekanal.

Er führt keine Capability aus, bevor das Gate autoritativ freigegeben wurde.

Ein bloß gestarteter normaler Writer erfüllt diese Grenze nicht.

## 11. Prepared-gated

`prepared_gated` darf erst appendiert werden, nachdem der Service den lebenden
Kindprozess direkt am richtigen Gate beobachtet hat.

Die Beobachtung bindet Handle, Prepare-ID und Capability.

Erst dieser Fakt darf ein LQ-446-Prepared-Ergebnis speisen.

Eine Jobdefinition oder PID allein genügt nicht.

## 12. Prepare-Retry

Ein exakter Retry derselben Prepare-ID liefert dieselbe Handlebindung und den
höchsten gültigen Journalzustand.

Vor `prepared_gated` darf er keinen vorbereiteten Erfolg behaupten.

Abweichende Claim-, Owner- oder Capabilitywerte sind Konflikt.

Retry startet niemals einen zweiten Prozess.

## 13. Prepare-Unknown

Nach Kommunikationsverlust fragt der Client ausschließlich dieselbe
Prepare-ID read-only ab.

Autoritativ belegte Nichtwirkung vor Launch kann neutral sein.

Registrierter, launch-committeter oder mehrdeutiger Bestand bleibt gebunden.

Fehlende Auflösung eines erwarteten Jobs ist technische Unverfügbarkeit.

## 14. Release-Voraussetzung

Release akzeptiert ausschließlich den bereits gebundenen Handle und die
stabile LQ-450-Release-ID.

Die Plattformcomposition muss zuvor die Releasekorrelation und bei Writer den
claimed-Start-Fakt durable gesichert haben.

Das Journal prüft keine Session oder Authority.

Es akzeptiert keine caller-gelieferte Allowentscheidung.

## 15. Release-Commit

Vor physischer Gatewirkung bindet das Journal die Release-ID unveränderlich an
Job und Gate.

Eine andere Release-ID für denselben Handle ist Konflikt.

Dieselbe ID darf nur den bestehenden Übergang fortsetzen oder auflösen.

Es gibt höchstens einen physischen Gateverbrauch.

## 16. Atomare Gategrenze

Journal und Gateprimitive müssen ein Protokoll bilden, das nach Servicecrash
zwischen Commit und Wirkung keine zweite Freigabe erzeugt.

Der Gatewrapper konsumiert die stabile Release-ID höchstens einmal.

Ein bereits konsumierter Token bleibt historiesicher erkennbar.

Ein Boolean oder flüchtiger Pipewrite allein genügt nicht.

## 17. Release-Unknown

Nach unklarem Release liest der Service denselben Job und dieselbe Release-ID.

Er unterscheidet direkt `prepared_gated`, `release_committed`, `running` und
`terminal_observed`.

Er erzeugt keine neue Release-ID und keinen neuen Gatekanal.

Unauflösbarkeit bleibt unknown und öffnet keinen zweiten Prozess.

## 18. Running

`running` bedeutet direkte Beobachtung nach konsumierter Gatefreigabe.

Der Zustand ist nicht terminal und autorisiert keinen fachlichen Erfolg.

Ein laufender Prozess kann nach Kommunikations- oder Controllerverlust weiter
wirken.

Leaseablauf ändert diesen Fakt nicht.

## 19. Read-only Inspect

Inspect adressiert exakt Backendinstanz und opaken Handle.

Es gibt ausschließlich die höchste konsistente geschlossene Projektion zurück.

Inspect startet, released, signalisiert und adoptiert nichts.

Eine fremde oder beliebige ID gibt keine Bestandsdetails aus.

## 20. Terminierungsanforderung

Terminate akzeptiert eine stabile Terminate-ID für genau einen gebundenen Job.

Vor Signalwirkung wird `termination_requested` durable appendiert.

Exakter Retry derselben ID löst nur den vorhandenen Request auf.

Eine zweite Terminate-ID für denselben Job ist Konflikt.

## 21. Terminierung ist nicht terminal

Signalversand, Signalannahme, Timeout und Wrapperabbruch sind keine terminale
Observation.

Der Job kann nach `termination_requested` weiterhin `prepared_gated`,
`release_committed` oder `running` sein.

Der Service muss weiter direkt beobachten.

Recovery bleibt bis `terminal_observed` gesperrt.

## 22. Terminale Beobachtung

`terminal_observed` wird genau einmal nach direktem belegtem Ende des gebundenen
Kindprozesses appendiert.

Der Fakt besitzt eine stabile vom Supervisor erzeugte Observation-ID.

Er bindet Handle, Capability, Endzeit und geschlossenes Ergebnis.

Nach diesem Fakt kann derselbe Prozess keine weitere Wirkung erzeugen.

## 23. Direkter Endnachweis

Der Supervisor muss den Prozess selbst besitzen oder über eine
controllerunabhängige primitive Quelle direkt terminal beobachten.

PID-Abwesenheit, EOF, Lockverlust, Service-Neustart und abgelaufene Dauer
reichen nicht.

Ein verlorener Kindprozess ohne direkte Observation bleibt unverfügbar.

Das Journal erfindet kein Ende zur Freigabe von Recovery.

## 24. Geschlossene Writerergebnisse

Writerterminalität verwendet exakt die fünf LQ-446-Arten.

Nur `manifest_handed_off` trägt Filename und Manifestfakten.

Alle anderen Writerarten tragen weder Filename noch Fakten.

Commit- und Stagingfreigaben bleiben immer false.

## 25. Geschlossene Recoveryergebnisse

Recoveryterminalität verwendet exakt fünf LQ-427-Arten plus unknown.

Fakten und Filename folgen der LQ-446-Matrix.

Writer- und Cleanupfreigabe bleiben immer false.

Recovery führt keine Dateimutation aus.

## 26. Begrenzte Ergebnisdaten

Das Journal nimmt nur geschlossene typisierte Ergebnisfelder an.

Nachrichtengröße, Filename und Fakten sind streng begrenzt und validiert.

Freies stdout, stderr, Traceback, Environment und Exceptiontext werden nicht
als Domainresultat gespeichert.

Ungültige Payload bleibt outcome unknown oder technische Unverfügbarkeit.

## 27. Service-Neustart

Nach Neustart rekonstruiert der Service jeden Job ausschließlich aus Journal
und seiner kontrollierten Prozessprimitive.

Er wiederholt keinen Spawn und keine Gatewirkung aus Vermutung.

Nichtterminaler Bestand wird weiter beobachtet.

Unvereinbarer Journal-/Prozessbestand bleibt fail-closed.

## 28. Keine Prozessadoption

Ein im OS, Containerdienst oder Service-Manager gefundener fremder Prozess
wird nicht an einen Journaljob gebunden.

PID-, Name-, Commandline- oder Pfadähnlichkeit reicht nicht.

Eine verlorene Handlebindung wird nicht repariert oder überschrieben.

Bestandsverankerung bleibt separat.

## 29. Neutralität

Eine autoritativ nie registrierte Prepare-ID kann neutral fehlen.

Ein unbekannter beliebiger Handle kann ohne Details neutral abgelehnt werden.

Ein erwarteter, journalisierter, aber nicht auflösbarer Job ist nicht neutral.

Neutralität autorisiert keine neue ID oder Prozesswirkung.

## 30. Detailfreie technische Unverfügbarkeit

Journalbeschädigung, lückenhafte Historie, unauflösbarer erwarteter Job,
mehrdeutige Gatewirkung und ungesichertes terminales Ergebnis bleiben
detailfreie technische Unverfügbarkeit.

PID-, Host-, Socket-, Signal-, Pfad- und Produktdetails verlassen die Grenze
nicht.

LQ-452 benennt keinen neuen Exceptiontyp.

## 31. Konflikte

Divergente Wiederverwendung von Prepare-, Handle-, Release-, Terminate- oder
Terminal-ID ist detailfreier Konflikt.

Es gibt kein Rebind, Last-write-wins, Adopt oder Zurücksetzen.

Konflikt erzeugt keine physische Wirkung.

Der bestehende Job bleibt unverändert gebunden.

## 32. Authentisierte Servicegrenze

Nur der kontrollierte Plattformclient darf Journaloperationen adressieren.

Das Protokoll ist versionsgebunden und beschränkt Requestgrößen.

Authentisierung ersetzt keine fachliche Claimentscheidung.

Konkretes Transport- und Credentialformat bleibt separat.

## 33. Ressourcenbegrenzung

Prozessdauer, IPC-Größe, Diagnoseoutput, Deskriptoren und parallele Jobs
benötigen kontrollierte feste Obergrenzen.

Grenzen stammen aus Servicekonfiguration, nicht aus Operationsrequests.

Überschreitung kann Terminierung anfordern, aber kein Ende erfinden.

Konkrete Werte bleiben Implementierungsentscheidung.

## 34. Retention

Jobbindung und alle Übergangsidentitäten bleiben mindestens so lange erhalten,
wie Prozesszuordnung, Unknown-Auflösung, Recovery, Parallelitätsausschluss oder
Audit davon abhängen.

OS-Ressourcen dürfen erst nach `terminal_observed` freigegeben werden.

Stabile IDs und Terminalfakten werden nicht wiederverwendet.

Eine konkrete Frist bleibt separat.

## 35. Keine Schemaentscheidung

LQ-452 entscheidet keine Tabelle, Datei, Embedded Database, Logengine oder
Transaktionsbibliothek für das Journal.

Es ergänzt keine Migration, Domainklasse oder Portsignatur.

Head bleibt `20260824_0030` mit 30 linearen Migrationen.

Die Journalfoundation folgt separat.

## 36. Keine Implementation oder Wiring

Der Slice implementiert keinen Service, Wrapper, Prozessadapter, Gatekanal,
IPC-Transport oder Client.

Er startet, released, inspiziert, signalisiert oder beendet keinen Prozess.

Es gibt kein CLI-, Compose-, CI-, Deployment- oder Production-Wiring.

LQ-439 und LQ-451 bleiben unverändert.

## 37. Tests

Fokussierte statische Tests belegen:

- unveränderliche Jobbindung und lineare append-orientierte Zustandsfolge;
- Prepare-Registrierung und Launch-Commit vor Prozessanlage;
- direkte `prepared_gated`-Beobachtung;
- einmalige Release-ID und atomare Gategrenze;
- read-only Inspect und Unknown-Auflösung ohne zweite Wirkung;
- Terminierungsrequest getrennt von terminaler Observation;
- direkte geschlossene Writer-/Recoveryergebnisse;
- Neustart ohne Spawn-, Gate- oder Prozessadoption;
- neutrale Abwesenheit getrennt von technischer Unverfügbarkeit;
- keine Schema-, Prozess-, Port- oder Wiringentscheidung;
- unveränderten Head 0030;
- Roadmap- und Folgeslicebindung.

## 38. Nichtziele

LQ-452 implementiert kein Supervisorjournal und wählt keine Journalengine.

Er entscheidet kein Wireformat, Service-Manager-Produkt, Gateprimitive,
Executable oder Sandboxprofil.

Serviceprozess, Clientadapter, Plattformcomposition, Bestand, Cleanup und
finale Retention bleiben separat.

## 39. Nächster Slice

LQ-453 sollte geschlossene Journalidentitäten, Zustandswerte, Requests,
Resultate und getrennte Writer-/Recoveryjournalports definieren.

Persistenzfoundation und Serviceimplementation folgen danach separat.
