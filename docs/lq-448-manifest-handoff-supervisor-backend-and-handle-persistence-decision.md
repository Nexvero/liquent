# LQ-448 — Manifest Handoff Supervisor Backend and Handle Persistence Decision

## 1. Ergebnis

LQ-448 trifft die in LQ-447 offengelassene Backend- und
Handlepersistenzentscheidung.

Die gewählte Grenze ist ein dedizierter controllerunabhängiger
Supervisorservice mit eigenem durablem Journal.

Die Anwendungscomposition ist Client dieser Grenze und besitzt den
Kindprozess nicht selbst.

## 2. Verbindliche Architektur

Die Lösung besteht aus zwei getrennten persistenten Quellen:

- das Manifest-Handoff-Registry bindet fachlichen Claim, Owner, Capability
  und stabile Operationsidentitäten;
- das Supervisorjournal bindet den opaken Jobhandle an Gatezustand,
  Prozesszustand und direkte terminale Observation.

Keine Quelle darf die Fakten der anderen aus lokalen Annahmen ersetzen.

## 3. Warum ein eigener Supervisorservice

Ein dedizierter Dienst überlebt den Verlust eines einzelnen
Anwendungscontrollers und bleibt über eine feste kontrollierte Grenze
inspizierbar.

Er besitzt Prozessanlage, Start-Gate, Freigabe, Inspektion und Terminierung.

Er ist kein allgemeiner Remote-Commandrunner.

Seine feste Fähigkeit ist ausschließlich Writer oder read-only Reconciler.

## 4. Controllerunabhängigkeit

Der ursprüngliche Composer ist nach erfolgreicher Anfrage für die weitere
Auflösung entbehrlich.

Ein neuer Composer kann dieselbe intern persistierte Operationsidentität an
denselben Supervisorbackendbestand richten.

Kein in-memory Clientobjekt ist normative Quelle.

Clientverlust ändert weder Jobidentität noch Gate- oder Terminalzustand.

## 5. Serviceverlust

Auch ein Neustart des Supervisordienstes darf die Journalbindung nicht
verlieren.

Der Dienst muss sein Journal vor jeder bestätigten physischen Wirkung durable
sichern oder dieselbe Wirkung anhand derselben ID eindeutig auflösen können.

Kann er einen erwarteten Job nach Neustart nicht autoritativ auflösen, bleibt
der Ausgang technisch unverfügbar.

Er darf daraus kein terminales Ende ableiten.

## 6. Supervisorjournal als Prozessquelle

Das Journal ist die autoritative Quelle für:

- Backendinstanz und opaken Jobhandle;
- feste Writer- oder Recoveryfähigkeit;
- Prepare-ID und bestätigten startgesperrten Zustand;
- Release-ID und einmaligen Gatezustand;
- Terminate-Request-ID und deren Annahmestatus;
- laufende direkte Beobachtung;
- terminale Observation-ID und geschlossenes Ergebnis.

PID, Container-ID oder Service-Manager-ID können intern vorkommen, verlassen
diese Grenze aber nicht als Autoritätsfakt.

## 7. Registry als Korrelationsquelle

Das Manifest-Handoff-Registry bleibt die autoritative Quelle für:

- Attempt und Scopebinding;
- Execution- oder Recovery-Claim;
- den zugehörigen Owner;
- Writer- oder Recoveryfähigkeit;
- intern erzeugte Prepare-, Release- und Terminate-ID;
- Backendinstanz-ID und opaken Supervisorhandle;
- terminale Supervisor-Observation-ID nach erfolgreicher Korrelation.

Es erfindet keinen Gate- oder Prozessstatus.

## 8. Geteilte Zuständigkeit

Der Supervisor entscheidet nicht, ob ein fachlicher Claim autorisiert ist.

Das Registry entscheidet nicht, ob ein konkreter Prozess noch wirkt.

Die Composition darf nur Fakten verbinden, wenn Claim, Owner, Capability,
Backendinstanz, Handle und Operationsidentität vollständig übereinstimmen.

Eine Teilübereinstimmung ist kein Erfolg.

## 9. Backendinstanz-ID

Jede kontrollierte Supervisorinstallation besitzt eine stabile intern
provisionierte Backendinstanz-ID.

Sie ist kein Hostname, Socketpfad, Deploymentname oder Netzwerkziel.

Ein Handle ist nur zusammen mit dieser Instanz-ID eindeutig.

Eine Instanz-ID wird nach Austausch oder Verlust nicht neu zugewiesen.

## 10. Opaker Jobhandle

Der LQ-446-Handle bezeichnet genau einen Supervisorjob innerhalb genau einer
Backendinstanz.

Er wird vom Supervisor kontrolliert erzeugt und niemals vom Caller gewählt.

Er wird nicht aus PID, Zeit, Claim oder Dateipfad rekonstruiert.

Ein Handle wird nach Jobende nicht wiederverwendet oder reassigned.

## 11. Prepare-ID

Vor dem ersten Prepare erzeugt die kontrollierte Composition genau eine
stabile Prepare-ID.

Der Supervisor bindet diese ID atomar an Capability, Claimkorrelation,
Ownerkorrelation und den neu erzeugten Jobhandle.

Ein exakter Retry liefert dieselbe Bindung.

Divergente Parameter unter derselben Prepare-ID sind Konflikt.

## 12. Prepare-Wirkung

Eine bestätigte Preparewirkung bedeutet, dass der feste Kindprozess existiert
und vor jeder Writer- oder Reconcilerfähigkeit am Supervisor-Gate wartet.

Eine bloß reservierte Datenbankzeile oder konfigurierte Jobdefinition reicht
nicht.

Der Supervisor bestätigt Prepare erst nach direkter Gatebeobachtung.

Vorher bleibt der Ausgang unknown oder detailfrei technisch unverfügbar.

## 13. Persistenzreihenfolge für Prepare

Die Registrykorrelation wird mit Prepare-ID und festem fachlichem Kontext
reserviert, bevor eine Backendwirkung angefragt wird.

Nach Backendbestätigung wird exakt der zurückgegebene Instanz-/Handlebezug an
diese Reservierung gebunden.

Ist der Commit unklar, wird nur dieselbe Prepare-ID read-only oder idempotent
aufgelöst.

Ein zweites Prepare mit neuer ID ist verboten.

## 14. Claimed Start bleibt fachliche Grenze

Der vorbereitete gated Prozess besitzt noch keine Dateiwirkungsfähigkeit.

Erst LQ-443 darf den claimed Writerstart fachlich sichern.

Der Supervisorhandle ersetzt weder Execution-Claim noch aktuelle Authority.

Recovery bleibt an den aktuellen LQ-444-Recoveryclaim gebunden.

## 15. Release-ID

Nach durablem claimed Start adressiert die Composition das Gate mit genau der
vorher intern erzeugten Release-ID.

Der Supervisor bindet die ID unveränderlich an Backendinstanz, Handle,
Prepare-ID und Gate.

Dieselbe ID kann unknown auflösen, aber keine zweite physische Freigabe
erzeugen.

Eine andere Release-ID für denselben Job ist Konflikt.

## 16. Durable Gatewirkung

Der Supervisor journalisiert die einmalige Releaseentscheidung so, dass ein
Neustart sie weder vergisst noch erneut ausführt.

`prepared` und `released` sind historiesichere Zustände.

Ein freies Boolean ohne Operationsbindung genügt nicht.

Unknown bleibt gesperrt, bis derselbe Journaleintrag aufgelöst ist.

## 17. Inspektion

Inspect ist read-only und adressiert ausschließlich die persistierte
Backendinstanz-/Handlebindung.

Es liefert nur einen geschlossenen LQ-446-Zustand.

Es adoptiert keinen gefundenen Prozess und erzeugt keinen neuen Job.

Fehlender erwarteter Bestand ist nicht neutraler Prozessabschluss.

## 18. Terminate-ID

Jede kontrollierte Terminierungsanforderung besitzt eine stabile intern
erzeugte Terminate-ID.

Der Supervisor bindet sie an genau einen bestehenden Job.

Retry derselben ID löst nur den bestehenden Anforderungsstatus auf.

Signalannahme oder Requestcommit ist noch kein terminales Ende.

## 19. Terminale Observation

Der Supervisor erzeugt genau eine stabile terminale Observation-ID je
beendetem Job.

Sie bindet Backendinstanz, Handle, Capability und direkt beobachtetes
geschlossenes Ergebnis.

Sie bleibt nach Freigabe von OS-Ressourcen erhalten.

Ein Exitcode, EOF oder verschwundener Prozess ohne Journalkorrelation genügt
nicht.

## 20. Geschlossene Ergebnisse

Writerergebnisse bleiben exakt auf die fünf LQ-446-Arten begrenzt.

Recoveryergebnisse bleiben exakt auf fünf LQ-427-Arten plus unknown begrenzt.

Fakten und Filename erfüllen weiterhin die LQ-446-Matrix.

Das Journal speichert keine freie stdout-, stderr- oder Exceptionpayload als
Domainresultat.

## 21. Keine verteilte Transaktionsfiktion

Registry und Supervisorjournal bilden keine gemeinsame ACID-Transaktion.

Die Composition verwendet stabile IDs und read-only Reconciliation für jede
unklare Grenzwirkung.

Sie führt kein Check-then-create mit neuer ID aus.

Lokaler Erfolg plus Registryfehler autorisiert keine Wiederholung.

## 22. Neutrale Abwesenheit

Eine Prepare-ID, deren Nichtwirkung der Supervisor autoritativ belegt, kann
neutral fehlen.

Eine unbekannte beliebige Caller-ID gibt ebenfalls keine Bestandsdetails aus.

Ein im Registry erwarteter, aber im Backend unauflösbarer Handle ist dagegen
nicht neutral.

Abwesenheit autorisiert keinen neuen Prozess ohne dieselbe reservierte
Prepare-ID.

## 23. Detailfreie technische Unverfügbarkeit

Journalverlust, inkonsistente Gatehistorie, unauflösbare erwartete Handles,
mehrdeutige Terminalbeobachtung und Backendinstanzverlust bleiben detailfreie
technische Unverfügbarkeit.

Host-, PID-, Socket-, Container-, Pfad-, Signal- und Produktdetails verlassen
die Grenze nicht.

LQ-448 benennt keinen neuen Exceptiontyp.

## 24. Konflikte

Abweichende Wiederverwendung von Instanz-, Handle-, Prepare-, Release-,
Terminate- oder Terminal-ID bleibt detailfreier Konflikt.

Es gibt kein Rebind, Adopt, Last-write-wins oder automatisches Ersetzen.

Konflikt startet oder released keinen Prozess.

Der fachliche Claim bleibt fail-closed.

## 25. Backendprotokoll

Die spätere Transportgrenze ist lokal oder privat authentisiert,
versionsgebunden und streng begrenzt.

Sie akzeptiert keine SessionPrincipal-, Rolle-, Allow- oder Authorityfelder.

Sie akzeptiert keine freien Commands, Argumente, Umgebungen oder Pfade.

Konkretes Wireformat, Sockettechnik und Authentisierungsmittel bleiben
Implementierungsentscheidungen späterer Slices.

## 26. Kein konkretes Supervisorprodukt

LQ-448 bindet die Architektur an die semantische Servicegrenze, nicht an
Docker, systemd, launchd, Kubernetes oder eine fremde Supervisordistribution.

Ein Produkt darf später nur gewählt werden, wenn Service, Journal,
startgesperrter Prozess und direkte Terminalbeobachtung gemeinsam nachgewiesen
sind.

Produktverfügbarkeit allein erfüllt den Vertrag nicht.

## 27. Deploymentgrenze

Supervisorservice und Journal müssen außerhalb des Lebenszyklus eines
einzelnen Composerprozesses liegen.

Ein Sidecar, der zwingend mit genau diesem Composer stirbt und alle Fakten
verliert, genügt nicht.

Eine gemeinsame Hostplatzierung ist zulässig, aber keine Voraussetzung.

Production darf ohne kontrollierte Supervisorverbindung nicht auf direkten
Writerbetrieb zurückfallen.

## 28. Minimale Privilegien

Der Dienst erhält nur die festen Writer- oder Reconcilerressourcen seiner
konfigurierten Fähigkeit.

Writer und Recovery bleiben getrennte Prozessprofile.

Der Reconciler erhält keine Mutationsfähigkeit.

Registryzugriff und fachliche Authorityprüfung bleiben außerhalb des
Kindprozesses.

## 29. Retention und Nichtwiederverwendung

Backendinstanz-ID, Jobhandle, Operations- und Terminalidentitäten werden nie
für einen anderen Job wiederverwendet.

Ihre Bindungen bleiben mindestens erhalten, solange Claimabschluss,
Parallelitätsausschluss, Unknown-Auflösung, Recovery oder Audit davon
abhängen.

OS-Prozessressourcen und begrenzte Diagnostik dürfen nach belegtem Ende früher
entfallen.

Eine konkrete Frist wird nicht festgelegt.

## 30. Bestandsattempts

Bestehende Attempts ohne Supervisorjournal und Registrykorrelation erhalten
keinen synthetischen Handle.

PID-, Log-, Datei- oder LQ-439-Bestand wird nicht adoptiert.

Sie bleiben für claimed Supervisorstart und Recovery fail-closed.

Ein owner-kontrollierter Bestandsentscheid bleibt separat.

## 31. Keine Schema- oder Portentscheidung

LQ-448 legt die erforderlichen Fakten und Eigentümerschaft fest, aber keine
Tabelle, Spalte, SQL-Anweisung, Migration oder konkrete Journalengine.

Es ergänzt keine Domainklasse und ändert keine LQ-446-Portsignatur.

Revision und Head bleiben `20260824_0029`.

Die additive Persistenzfoundation folgt separat.

## 32. Keine Prozessimplementation

Dieser Slice implementiert keinen Daemon, Kindprozess, Start-Gate,
IPC-Transport oder Clientadapter.

Er startet, released, inspiziert, signalisiert oder beendet keinen Prozess.

Es gibt kein CLI-, Compose-, CI-, Deployment- oder Production-Wiring.

LQ-439 bleibt unverändert und ohne Production-Fallback.

## 33. Tests

Fokussierte statische Tests belegen:

- dedizierten controllerunabhängigen Supervisorservice mit durablem Journal;
- getrennte Prozess- und fachliche Korrelationsquellen;
- stabile Backendinstanz-, Handle-, Prepare-, Release-, Terminate- und
  Terminalidentitäten;
- direkte gated- und terminale Beobachtung ohne PIDfiktion;
- Unknown-Auflösung mit derselben ID ohne zweiten Prozess;
- neutrale Abwesenheit getrennt von technischer Unverfügbarkeit;
- keine Produkt-, Schema-, Port-, Prozess- oder Wiringentscheidung;
- unveränderten Head 0029;
- Roadmap- und Folgeslicebindung.

## 34. Nichtziele

LQ-448 implementiert weder Registry- noch Supervisorjournalpersistenz.

Er wählt keine Datenbank, Queue, Containerengine oder Service-Manager-API.

Prozessadapter, claimed Writerintegration, Recoverycomposition,
Bestandsverankerung, Cleanup und finale Evidence-Retention bleiben separat.

## 35. Nächster Slice

LQ-449 sollte die additive persistente Plattformfoundation für
Backendinstanz-, Handle- und Operationskorrelationen definieren und migrieren.

Das interne Supervisorjournal und seine konkrete Serviceimplementation bleiben
danach separat.
