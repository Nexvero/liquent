# LQ-447 — Local Manifest Handoff Supervisor Feasibility Decision

## 1. Ergebnis

LQ-447 prüft, ob der in LQ-446 angekündigte lokale startgesperrte
Prozessadapter den LQ-445-Sicherheitsvertrag mit dem aktuellen Bestand
korrekt erfüllen kann.

Das Ergebnis ist fail-closed: Ein einfacher lokaler Adapter wird nicht
implementiert.

Vor Prozesscode fehlen eine controllerverlustfest auflösbare Supervisorgrenze
und persistente Handle-/Gate-/Terminalfakten.

## 2. Kein folgenloser Implementierungsaufschub

Die Entscheidung verhindert eine konkrete Sicherheitsverletzung.

Ein Adapter, der nur ein in-memory `Popen`-, PID- oder Forkobjekt hält, würde
nach Controllerverlust weder den ursprünglichen Prozess sicher identifizieren
noch dessen Ende autoritativ belegen können.

Er könnte dadurch parallele Recovery oder einen zweiten Prozess indirekt
öffnen.

LQ-447 schreibt deshalb keinen scheinbar funktionierenden, aber nicht
recoveryfähigen Supervisor.

## 3. Anforderungen aus LQ-445

Der spätere Supervisor muss gleichzeitig garantieren:

- genau einen Prozess je Claim/Ownerbindung;
- startgesperrten Prozess vor jeder Dateiwirkung;
- genau eine Gatefreigabe nach durablem claimed Start;
- read-only Statusauflösung nach Controllerneustart;
- direkten terminalen Nachweis ohne PID-, Timeout- oder Leaseannahme;
- keinen zweiten Writer- oder Reconcilerstart bei Unsicherheit;
- bounded IPC und feste Prozessfähigkeit ohne freie Commands.

Keine dieser Anforderungen darf als Best-effort behandelt werden.

## 4. Aktueller Persistenzbestand

Revision `20260824_0029` speichert Execution- und Recovery-Claims sowie deren
terminalen fachlichen Endnachweis.

Sie speichert jedoch keinen Supervisorhandle, keine Backendinstanz, keinen
Gatezustand, keine Releaseentscheidung und keine direkte Prozessbeobachtung.

LQ-443 und LQ-444 können deshalb nur Fakten annehmen, die eine andere
kontrollierte Quelle bereits sicher erzeugt hat.

Sie ersetzen die fehlende Prozessquelle nicht.

## 5. Warum `subprocess.Popen` allein nicht genügt

Ein `Popen`-Objekt lebt ausschließlich im Controllerprozess.

Nach dessen Absturz geht die sichere Zuordnung zwischen Claim, Owner, Handle,
Gatepipe und Kindprozess verloren.

Ein neuer Controller kann das alte Objekt nicht inspizieren.

Ein PID-basierter Wiederaufbau wäre wegen PID-Reuse und fremder Prozesse nicht
autoritativ.

## 6. Warum PID plus Startzeit nicht genügt

PID und beobachtete Startzeit sind Plattformmetadaten, keine stabile
Prozessidentität des Systems of Record.

Sie können fehlen, anders formatiert sein oder nach Namespace-/Hostwechsel
nicht vergleichbar bleiben.

Selbst eine scheinbar passende PID beweist weder Claimbindung noch
Gatezustand.

Ein fehlender PID-Eintrag beweist kein terminales Ende.

## 7. Warum eine PID-Datei nicht genügt

Eine PID-Datei kann veralten, ersetzt oder nach Crash unvollständig sein.

Sie besitzt keine atomare Bindung an Execution-/Recovery-Claim und
Supervisorbackend.

Dateiabwesenheit oder ein gelöschtes Lockfile beweist nicht, dass kein Prozess
mehr Dateiwirkung erzeugen kann.

Eine PID-Datei wird daher nicht als Handlepersistenz eingeführt.

## 8. Warum ein Lockfile nicht genügt

Ein Prozesslock kann bei Prozessende freigegeben werden, liefert aber keinen
historiesicheren terminalen Fakt und keine direkte Outcomequelle.

Netzwerk-, Container- und Filesystemnamespaces können seine Bedeutung
verändern.

Lockverlust ist außerdem keine typisierte Prozessbeobachtung.

LQ-447 verwendet kein Lockfile als Fencingtoken.

## 9. Warum Pipe-EOF nicht genügt

Eine Parent-Liveness-Pipe kann einem Kindprozess signalisieren, dass der
Controller verschwunden ist.

EOF beweist dem neuen Controller jedoch nicht dauerhaft, wann das Kind
endete oder ob es vor seinem Ende noch Dateiwirkung erzeugte.

Der neue Controller besitzt die alte Pipe nicht.

Ohne durable Backendbeobachtung bleibt Recovery weiterhin unbelegt.

## 10. Warum Parent-Death-Signal nicht genügt

Plattformspezifische Parent-Death-Signale können einen Kindprozess beim
Controllerende terminieren.

Signalzustellung allein ist nach LQ-445 kein terminaler Nachweis.

Racefenster bei Parentwechsel, Plattformunterschiede und fehlende durable
Observation bleiben bestehen.

Ein solches Signal kann später Defense-in-depth sein, aber nicht das System of
Record ersetzen.

## 11. Warum Process Group oder Session nicht genügt

Eine eigene Process Group begrenzt Signale auf eine Prozessfamilie.

Sie beweist weder, dass alle Mitglieder terminal sind, noch bindet sie die
Gruppe dauerhaft an Claim und Owner.

Eine wiederverwendete numerische Gruppen-ID wäre kein opaker stabiler Handle.

Kill-Group plus Timeout bleibt eine Aktion, kein Endnachweis.

## 12. Warum ein Threadadapter unzulässig ist

Ein Thread kann keinen echten isolierten Kindprozess und keine kontrollierte
Descriptor-/Environmentgrenze darstellen.

Pythonthreads lassen sich nicht sicher extern terminieren.

Ein hängender Writerthread könnte nach vermeintlichem Timeout weiterwirken.

Ein Threadadapter würde die Prozess- und Terminalverträge semantisch brechen.

## 13. Warum `multiprocessing` allein nicht genügt

Auch ein `multiprocessing.Process` wird standardmäßig nur durch den aktuellen
Controller eindeutig besessen und beobachtet.

Sein Pythonobjekt ist nach Controllerverlust nicht rekonstruierbar.

Daemonflags, Join und Exitcode lösen keine durable Claim-/Handlebindung.

Die API ändert daher das Grundproblem nicht.

## 14. Warum Timeout kein Ersatz ist

Timeout kann höchstens eine kontrollierte Terminierungsanforderung auslösen.

Er beweist nicht, dass das Signal zugestellt, verarbeitet und der Prozess
terminal beendet wurde.

Ein lokaler Adapter darf nach Timeout weder Endfakt noch Recoveryfähigkeit
erfinden.

Ohne beobachtbares Backend bliebe der Claim dauerhaft blockiert.

## 15. Warum In-Memory-Handleindex nicht genügt

Ein Dictionary aus opakem Handle zu `Popen` wäre innerhalb eines Prozesses
hilfreich, aber nicht controllerverlustfest.

Nach Neustart wäre jeder laufende oder bereits terminale Eintrag unbekannt.

Neutral `None` könnte dann fälschlich als fehlender Prozess interpretiert
werden.

LQ-447 führt deshalb keinen nur lokalen Handlecache als normative Quelle ein.

## 16. Erforderliche Supervisorquelle

Vor einem Adapter benötigt das System eine kontrollierte Supervisorquelle,
die unabhängig vom aufrufenden Composer folgende Fakten bewahrt:

- opake stabile Backend-Handle-ID;
- feste Capability Writer oder Recovery;
- Claim- und Ownerbindung;
- startgesperrt vorbereitet;
- Gate einmalig freigegeben oder nicht freigegeben;
- weiterhin laufend oder direkt terminal beobachtet;
- begrenztes typisiertes direktes Ergebnis;
- Backendinstanz beziehungsweise Namespacebindung.

Diese Quelle darf kein untrusted allgemeiner Commandrunner sein.

## 17. Controllerunabhängige Beobachtung

Die Supervisorquelle muss einen Prozess auch nach Verlust des ursprünglichen
Composers anhand desselben opaken Handles inspizieren können.

Sie muss entweder selbst den Prozess besitzen oder einen Plattformdienst
verwenden, dessen Handle nicht durch PID-Reuse reassigned wird.

Ein neuer Controller darf nur read-only denselben bestehenden Handle
auflösen.

Fehlende Auflösung ist technische Unverfügbarkeit, nicht Prozessende.

## 18. Persistente Handlebindung

Claim, Owner, Capability und Backendhandle benötigen eine durable nicht
reassignbare Bindung vor claimed Start beziehungsweise Recoveryfreigabe.

Ein Handle darf höchstens einer Claim-/Owner-/Capabilitykombination gehören.

Ein Claim darf höchstens einen vorbereiteten Supervisorprozess besitzen.

Retry muss dieselbe Bindung liefern; Divergenz bleibt Konflikt.

## 19. Persistenter Gatezustand

Die Entscheidung `prepared_gated` oder `released` muss historiesicher und
eindeutig sein.

Ein unklarer Gatecommit darf keine zweite physische Freigabe auslösen.

Backend und Persistenz müssen dieselbe einmalige Freigabeidentität erkennen.

Ein frei mutierbares Boolean ohne Retryanker reicht nicht.

## 20. Release-Identität

Die Gatefreigabe benötigt eine eigene stabile intern erzeugte Release-ID.

Sie bindet genau Handle, Claim und Owner.

Ein exakter Retry derselben Release-ID darf nur den bestehenden Zustand
auflösen.

Eine andere Release-ID für denselben Handle ist Konflikt und keine zweite
Freigabe.

## 21. Terminale Supervisorobservation

Das Backend benötigt eine stabile terminale Observation-ID, die genau einen
Handle und direkten Prozessausgang bindet.

Sie ist von LQ-443-/LQ-444-End-ID und Manifest-Observation-ID getrennt.

Die Composition kann erst nach diesem direkten Fakt fachliches Execution-
oder Recovery-Ende sichern.

Exitcode allein ist keine ausreichende terminale Payload.

## 22. Outcomegrenze

Writeroutcomes bleiben auf die fünf LQ-446-Arten begrenzt.

Recoveryoutcomes bleiben auf fünf LQ-427-Arten plus unknown begrenzt.

Fakten und Filename müssen die LQ-446-Matrix erfüllen.

Unbekannte, übergroße oder widersprüchliche Backendantworten werden nicht
persistiert.

## 23. Start-Gate-Protokoll

Das gewählte Backend muss direkt bestätigen, dass der Prozess existiert und
vor jeder Capabilitywirkung am Gate wartet.

Diese Bestätigung benötigt einen stabilen Preparefakt.

Erst nach durablem claimed Start wird die einmalige Release-ID angewendet.

Ein Prozess ohne belegten Gatezustand wird nicht freigegeben.

## 24. Atomicity-Grenze

Datenbank und externes Supervisorbackend können nicht ohne Weiteres in einer
gemeinsamen ACID-Transaktion committen.

Die spätere Composition benötigt daher explizite Unknown- und
read-only-Reconciliationregeln für Prepare und Release.

Idempotente Backendoperationen müssen durch stabile IDs gebunden sein.

Check-then-call mit neuer ID nach Fehler ist verboten.

## 25. Prepare-Unknown

Ist unklar, ob Prepare im Backend wirkte, darf kein zweiter Prozess angelegt
werden.

Der Retry verwendet dieselbe Prepare-/Handleidentität und fragt read-only den
Backendbestand.

Kann der ursprüngliche Prozess nicht eindeutig aufgelöst werden, bleibt der
Claim blockiert.

`start_not_confirmed` erfordert weiterhin direkten terminalen Nachweis.

## 26. Release-Unknown

Ist unklar, ob das Gate freigegeben wurde, darf Release nicht mit einer neuen
ID wiederholt werden.

Read-only Backendinspection muss prepared, running oder terminal unterscheiden.

Prepared kann nur mit exakt derselben Release-ID erneut adressiert werden.

Unauflösbarkeit bleibt unknown und öffnet keine Recovery.

## 27. Terminierung

Terminierung benötigt ebenfalls eine stabile intern erzeugte Request-ID, wenn
das Backend ihren Ausgang idempotent auflösen soll.

Ein Caller-Signal oder freie Prozessauswahl bleibt verboten.

Nach Terminierungsanforderung ist running weiterhin möglich.

Nur die terminale Backendobservation speist später den Endfakt.

## 28. Backendpolicy

Executable, Argumentform, minimale Environmentallowlist, Working Directory,
Outputlimit, Laufzeitgrenze und Terminierungsstrategie werden beim
Backendaufbau validiert und fixiert.

Kein LQ-446-Aufruf kann diese Policy überschreiben.

Writer- und Reconcilerpolicy bleiben getrennt.

Cleanup ist keine Backendfähigkeit.

## 29. Kandidatenklassen

Technisch denkbar sind ein dedizierter lokaler Supervisordienst, ein
controllerunabhängiger Container-/Jobdienst oder ein OS-Service-Manager mit
stabiler Jobidentität und read-only Status-API.

LQ-447 wählt noch keinen Kandidaten.

Die Auswahl muss alle Anforderungen nachweisen, nicht nur Prozesse starten
können.

Ein vorhandenes Tool wird nicht allein wegen Verfügbarkeit übernommen.

## 30. Keine stille Plattformbindung

Eine Linux-only Parent-Death-Lösung darf nicht als portabler lokaler Adapter
ausgegeben werden.

macOS-, Linux- und Containersemantik unterscheiden sich bei Process Groups,
Namespaces und Parentwechsel.

Eine spätere Plattformbindung muss explizit sein und fail-fast außerhalb ihrer
belegten Umgebung scheitern.

LQ-447 setzt keine solche Bindung voraus.

## 31. Kein Fallback

Fehlt das ausgewählte Supervisorbackend, darf Production nicht auf
in-memory `Popen`, Thread, PID-Datei oder direkten Writeraufruf zurückfallen.

Unvollständige Composition scheitert beim Aufbau.

Neutraler Backendbestand wird nicht aus Dateiabwesenheit rekonstruiert.

Der bestehende LQ-439-Direktcomposer bleibt ohne Production-Wiring.

## 32. Authority

Die Supervisorquelle erteilt keine Execution- oder Recoveryauthority.

LQ-443 claimed Start und LQ-444 Recoveryclaim bleiben die aktuellen
Authoritygrenzen.

Backendhandle, PID, Jobstatus und Gatezustand ersetzen diese Entscheidungen
nicht.

Revocation wirkt weiterhin auf jede spätere Claim-/Startentscheidung.

## 33. Neutrale Abwesenheit

Ein nachweislich nicht angelegter Prepareversuch kann neutral enden, sofern
das Backend dessen Nichtwirkung autoritativ bestätigt.

Ein fremder oder bereits terminaler Handle kann neutral sein, ohne Details
auszugeben.

Unauflösbarer erwarteter Handle ist dagegen technische Unverfügbarkeit.

Neutralität autorisiert keinen neuen Prozess.

## 34. Detailfreie technische Unverfügbarkeit

Verlorene Handlebindung, unklare Backendinstanz, mehrdeutige Gatewirkung,
unauflösbarer Prozess und beschädigte Outcomehistorie bleiben detailfreie
technische Unverfügbarkeit.

PID-, Host-, Socket-, Service-, Executable- und Pfaddetails verlassen die
Grenze nicht.

LQ-447 benennt keinen neuen Exceptiontyp.

## 35. Konflikte

Divergente Wiederverwendung von Prepare-, Handle-, Release-, Terminate- oder
terminaler Observation-ID bleibt ein detailfreier Konflikt.

Kein Konflikt wird durch neuen Prozess, neue ID oder Überschreiben gelöst.

Last-write-wins und Adopt eines fremden Prozesses sind verboten.

Konflikt hält Claim und Recovery fail-closed.

## 36. Retention

Handle-, Claim-, Owner-, Prepare-, Release-, Terminate- und terminale
Observationbindungen bleiben mindestens so lange erhalten, wie
Parallelitätsausschluss, Endnachweis, Unknown-Recovery oder Audit davon
abhängen.

OS-Ressourcen dürfen nach belegtem Ende freigegeben werden, stabile IDs und
Fakten nicht.

Eine konkrete Frist bleibt separat.

## 37. Bestandsattempts

Bestehende Attempts besitzen keine Supervisorhandlehistorie.

Sie werden nicht automatisch als nie gestartet, terminal oder recoverbar
klassifiziert.

PIDlogs, Dateien und LQ-439-Prozessannahmen erzeugen keinen Backfill.

Bestandsverankerung bleibt ein separater owner-kontrollierter Slice.

## 38. Keine Schemaentscheidung in diesem Slice

Ob Handlefakten im bestehenden Registrysystem, in einem Supervisorservice
oder in beiden mit stabiler Korrelationsidentität liegen, entscheidet LQ-447
noch nicht.

Es wird keine Tabelle, Spalte, Migration, Domainklasse oder Portsignatur
ergänzt.

Revision und Head bleiben `20260824_0029`.

Die Entscheidung muss vor Prozessimplementation fallen.

## 39. Keine Prozessmutation

LQ-447 startet, released, inspiziert, signalisiert oder beendet keinen echten
Prozess.

Es gibt keinen neuen Subprocess-, Fork-, Thread-, Container- oder
Service-Manager-Code.

Keine Manifestdatei wird gelesen oder verändert.

Kein CLI-, Compose-, CI- oder Production-Wiring wird ergänzt.

## 40. Tests

Fokussierte statische Tests belegen:

- fail-closed Entscheidung gegen einfachen lokalen Adapter;
- Unzulänglichkeit von Popen, PID, PID-Datei, Lockfile, Pipe-EOF,
  Parent-Death-Signal, Thread und multiprocessing allein;
- erforderliche controllerunabhängige Supervisorquelle;
- durable Claim-/Owner-/Capability-/Handlebindung;
- stabile Prepare-, Release-, Terminate- und Terminalidentitäten;
- read-only Unknown-Reconciliation ohne zweiten Prozess;
- kein Fallback auf direkten LQ-439-Writer;
- unveränderte Revision 0029 und keine Implementierung;
- Roadmap- und Folgeslicebindung.

## 41. Nichtziele

LQ-447 implementiert bewusst keinen unsicheren lokalen Prozessadapter.

Es wählt noch kein Supervisorprodukt und definiert keine konkrete
Persistenzstruktur, IPC oder Plattformpolicy.

Claimed Writerintegration, Recoverycomposition, Scope-/Authority-Bootstrap,
Bestandsverankerung, Cleanup und finale Evidence-Retention bleiben separat.

## 42. Nächster Slice

LQ-448 sollte die Supervisorbackend- und Handlepersistenzentscheidung treffen
und deren beobachtbare idempotente Prepare-/Release-/Inspect-/Terminategrenzen
konkretisieren.

Erst danach darf ein LQ-446-Prozessadapter implementiert werden.

Claimed Writerintegration, Recoverycomposition, Bestand, Cleanup und Retention
bleiben weiterhin getrennt.
