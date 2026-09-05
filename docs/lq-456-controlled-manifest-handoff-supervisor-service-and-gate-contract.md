# LQ-456 — Controlled Manifest Handoff Supervisor Service and Gate Contract

## 1. Ergebnis

LQ-456 definiert den kontrollierten Serviceprozess und die physische
Start-Gate-Grenze auf dem persistenten LQ-455-Journal.

Der Slice implementiert noch keinen Service, Wrapper oder Kindprozess.

## 2. Serviceeigentum

Der Supervisorservice besitzt alle Writer- und Recoverykindprozesse.

Anwendungscontroller sind ausschließlich authentisierte Clients.

Clientverlust beendet, übernimmt oder dupliziert keinen Job.

Der Service bleibt an genau eine stabile Backendinstanz gebunden.

## 3. Kein allgemeiner Prozessdienst

Der Service kennt nur den festen Writer und den read-only Reconciler.

Requests enthalten kein Executable, Command, Args, Env, cwd oder Shell.

Cleanup, Git, Build, Deployment und beliebige Programme sind ausgeschlossen.

Prozessprofile werden beim Serviceaufbau fixiert und validiert.

## 4. Startreihenfolge

Für einen neuen Job gilt zwingend:

1. Journaljob persistent registrieren;
2. Launch-Commit persistent appendieren;
3. genau einen Wrapperprozess anlegen;
4. direkten gebundenen Gatehandshake empfangen;
5. `prepared_gated` persistent appendieren;
6. erst danach Prepared an den Client liefern.

Keine Prozessanlage findet vor Launch-Commit statt.

## 5. Wrapper vor Capabilitycode

Der Kindprozess startet in einem minimalen kontrollierten Wrapper.

Der Wrapper lädt oder importiert noch keinen Writer- oder Reconcilerpfad,
bevor das Gate konsumiert ist.

Source und Target werden vor Gatefreigabe nicht geöffnet oder aufgelöst.

Der Gatehandshake erfolgt vor jeder Capabilitywirkung.

## 6. Gebundener Gatehandshake

Der Handshake bindet Backendinstanz, Handle, Launch-Commit und Capability.

Er ist begrenzt, versioniert und authentisiert.

Ein Handshake eines fremden oder bereits gebundenen Prozesses wird nicht
adoptiert.

PID oder Parentbeziehung allein beweist keine Bindung.

## 7. Gateprimitive

Die Gateprimitive besitzt genau zwei irreversible Zustände: wartend und mit
einer konkreten Release-ID konsumiert.

Sie kann höchstens eine Release-ID konsumieren.

Der konsumierte Wert bleibt nach Service- oder Clientverlust auflösbar.

Ein flüchtiger Pipewrite oder frei setzbares Boolean genügt nicht.

## 8. Release-Reihenfolge

Für Release gilt zwingend:

1. exakt gebundenen Prepared-Job inspizieren;
2. LQ-455-Release-Commit mit stabiler Release-ID appendieren;
3. dieselbe Release-ID an die Gateprimitive adressieren;
4. direkten einmaligen Konsum beobachten;
5. `running` mit stabiler Observation-ID appendieren;
6. Running oder bereits Terminal an den Client liefern.

Gatewirkung vor durablem Release-Commit ist verboten.

## 9. Release-Unknown

Nach Kommunikations- oder Serviceverlust wird ausschließlich dieselbe
Release-ID aufgelöst.

Journal und Gateprimitive werden read-only korreliert.

Der Service erzeugt weder neue Release-ID noch neuen Gatekanal.

Mehrdeutigkeit bleibt fail-closed und erzeugt keine zweite Wirkung.

## 10. Physische Einmaligkeit

Journal-Commit allein ist noch keine Gatewirkung.

Gatekonsum allein ohne passenden Journal-Commit ist ungültiger technischer
Bestand.

Der Service muss beide Fakten über dieselbe Release-ID zusammenführen.

Nur ein direkt belegter Konsum darf Running speisen.

## 11. Process input

Der Wrapper erhält ausschließlich die beim Journaljob fixierte Binding und den
Handoffnamen.

Writer erhält Source und Target; Recovery darf ausschließlich Target und Namen
verwenden.

Registryverbindung, Session, Authority und Plattformcredentials werden nicht
vererbt.

Der Caller kann Inputs bei Release nicht verändern.

## 12. Minimales Environment

Der Service baut eine feste minimale Environmentallowlist.

Encoding und Locale sind deterministisch.

Ungeprüfte Controller- oder Service-Secrets werden nicht vererbt.

Nicht benötigte Deskriptoren und Sockets werden geschlossen.

## 13. Direkte Resultatgrenze

Der Wrapper liefert genau einen begrenzten geschlossenen LQ-446-Ausgang.

Freies stdout, stderr, JSON, Pickle oder Exceptiontext ist kein Domainresultat.

Unbekannte, übergroße oder widersprüchliche Antworten werden nicht als Erfolg
interpretiert.

Writer- und Recoveryresultate bleiben getrennt.

## 14. Terminale Reihenfolge

Nach direktem Prozessende validiert der Service das geschlossene Resultat.

Dann appendiert er genau eine Terminaltransition mit stabiler Observation-ID
und direkt beobachteter Endzeit.

Erst der persistierte Terminalview wird an Clients geliefert.

OS-Ressourcen dürfen erst danach freigegeben werden.

## 15. Ende ohne gültiges Resultat

Direktes Ende ohne gültige Payload wird konservativ auf den geschlossenen
unknown-/unavailable-Ausgang der jeweiligen Capability abgebildet.

Es werden keine Fakten oder Filename erfunden.

Der terminale Prozessnachweis bleibt trotzdem direkt und persistent.

Ein neuer Writerstart bleibt verboten.

## 16. Terminierung

Vor jeder Signalwirkung appendiert der Service den stabilen
Termination-requested-Fakt.

Danach adressiert er ausschließlich den gebundenen Job.

Signalannahme, Timeout und Wrapper-EOF sind nicht terminal.

Der Service beobachtet weiter bis zum direkten Ende.

## 17. Timeout

Eine feste kontrollierte Dauer darf Terminierung auslösen.

Die Dauer ist Servicepolicy und kein Requestparameter.

Timeout erzeugt weder Terminaltransition noch Recoveryfreigabe.

Kann Ende nicht belegt werden, bleibt der Job nichtterminal.

## 18. Service-Neustart

Beim Start liest der Service alle nichtterminalen Journaljobs.

Er startet keinen davon erneut.

Er korreliert sie ausschließlich mit seiner stabilen Prozess- und
Gateprimitive.

Unauflösbarer erwarteter Bestand bleibt technische Unverfügbarkeit.

## 19. Restart nach Registrierung

Ein Job nur in `prepare_registered` hat noch keinen Launch-Commit und keine
Prozesswirkung.

Nur derselbe kontrollierte Prepareflow darf ihn mit der registrierten
Launch-ID fortsetzen.

Ein Job mit Launch-Commit darf niemals blind erneut gespawnt werden.

Launch-Unknown benötigt direkte primitive Auflösung.

## 20. Restart nach Gated

Ein direkt weiterhin wartender gebundener Wrapper bleibt Prepared.

Ein konsumiertes Gate ohne Runningtransition wird über dieselbe Release-ID
aufgelöst.

Ein verschwundener Wrapper ist nicht automatisch terminal.

Ohne direkten Endnachweis bleibt der Job gesperrt.

## 21. Restart nach Running

Ein weiterhin wirkender Prozess bleibt Running.

Ein direkt terminal beobachteter Prozess wird mit derselben Jobbindung
terminalisiert.

PID-Abwesenheit, Lockverlust oder fehlende IPC-Verbindung reichen nicht.

Der Service adoptiert keinen ähnlich aussehenden Prozess.

## 22. Read-only Inspect

Inspect liest Journal und direkte primitive Beobachtung, mutiert aber nichts.

Es liefert nur einen konsistenten LQ-446-Zustand.

Inkonsistenz wird nicht durch automatische Reparatur verborgen.

Inspect erzeugt weder Spawn, Gatekonsum, Signal noch Terminalfakt.

## 23. Authentisierte Clientgrenze

Nur der kontrollierte Plattformclient kann Prepare, Release und Terminate
adressieren.

Inspect fremder IDs gibt keine Existenz- oder Prozessdetails aus.

Transportauthentisierung ist keine fachliche Authority.

SessionPrincipal oder Rollen werden nicht an den Service übertragen.

## 24. Bounded IPC

Handshake-, Gate- und Resultatnachrichten besitzen feste Versions- und
Größenlimits.

Unbekannte Felder, doppelte Werte und trailing Daten scheitern fail-closed.

Reads und Writes sind zeitlich begrenzt, ohne Timeout als Ende zu behandeln.

Konkretes Wireformat bleibt separat.

## 25. Ressourcenlimits

Parallele Jobs, Laufzeit, IPC-Bytes, Diagnoseoutput, Speicher und Deskriptoren
haben feste konstruktive Obergrenzen.

Überschreitung führt zur kontrollierten Terminierungssequenz.

Limits erweitern keine Capability.

Konkrete Werte bleiben Deploymentpolicy.

## 26. Neutrale Abwesenheit

Eine autoritativ nie registrierte beliebige ID kann neutral fehlen.

Ein erwarteter Journaljob ohne primitive Auflösung ist nicht neutral.

Ein Capabilitymismatch wird ohne fremde Details abgelehnt.

Neutralität autorisiert keinen Spawn oder Retry mit neuer ID.

## 27. Detailfreie technische Unverfügbarkeit

Journal-/Primitive-Divergenz, mehrdeutiger Launch oder Gatekonsum,
unauflösbarer erwarteter Prozess und ungültige IPC bleiben detailfreie
technische Unverfügbarkeit.

PID-, Host-, Socket-, Signal-, Pfad- und Produktdetails verlassen die Grenze
nicht.

LQ-456 benennt keinen neuen Exceptiontyp.

## 28. Konflikte

Divergente Prepare-, Launch-, Handle-, Release-, Terminate- oder Terminal-ID
bleibt detailfreier Konflikt.

Konflikt löst keine physische Wirkung aus.

Es gibt kein Rebind, Adopt, Reset oder Last-write-wins.

Der bestehende Job bleibt unverändert.

## 29. Retention

Journal-, Gate- und direkte Terminalfakten bleiben mindestens erhalten, wie
Unknown-Auflösung, Prozesszuordnung, Recovery oder Audit davon abhängen.

Handle und Operations-IDs werden nicht wiederverwendet.

Diagnoseoutput darf früher begrenzt entfernt werden.

Eine konkrete Frist bleibt separat.

## 30. Keine Primitive-Auswahl

LQ-456 entscheidet noch keine konkrete Gate-, Spawn-, Reaper-, Container-,
Service-Manager- oder IPC-Technologie.

Eine spätere Auswahl muss Restart, Einmaligkeit und direkte Terminalbeobachtung
nachweisen.

Produktverfügbarkeit allein genügt nicht.

## 31. Keine Implementation

Der Slice ergänzt keine Typen, Ports, Tabellen, Migrationen oder Adapter.

Head bleibt `20260824_0031` mit 31 linearen Migrationen.

Er startet oder beendet keinen Prozess und verändert keine Datei.

Es gibt kein CLI-, Compose-, CI-, Deployment- oder Production-Wiring.

## 32. Tests

Fokussierte statische Tests belegen Serviceeigentum, Journal-vor-Wirkung,
Wrapper-vor-Capability, gebundenen Gatehandshake, Einmal-Release, direkte
Terminalbeobachtung, Restart ohne Respawn/Adoption, bounded IPC und fehlende
Schema-/Prozess-/Wiringentscheidung.

## 33. Nichtziele

LQ-456 implementiert keinen Serviceprozess, Wrapper, Gatekanal,
Prozessprimitive, Transport oder Plattformcomposer.

Bestand, Cleanup und finale Retention bleiben separat.

## 34. Nächster Slice

LQ-457 sollte die konkrete lokale Prozess- und Gateprimitive auswählen und
ihre Controller-/Serviceneustart-Eigenschaften fail-closed nachweisen.

Erst danach darf der Supervisorservice implementiert werden.
