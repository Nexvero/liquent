# LQ-445 — Controlled Manifest Handoff Supervisor Contract

## 1. Ergebnis

LQ-445 definiert den kontrollierten Supervisor- und Prozessende-Adaptervertrag
für claimed Writer- und Recoveryausführungen.

Der Slice implementiert noch keinen Prozessadapter, Typ, Port oder Composer.

## 2. Ausgangslage

LQ-443 persistiert genau einen Execution-Owner, einen claimgebundenen
`writer_started`-Fakt und terminale Execution-Endnachweise.

LQ-444 persistiert autorisierte Recovery-Owner, claimgebundene
Reconciliationobservationen und terminale Recovery-Endnachweise.

Noch fehlt eine kontrollierte Prozessgrenze, deren direkte Beobachtung diese
Owner- und Endfakten autoritativ speisen darf.

CLI-Exitcodes, Callerbehauptungen und PID-Dateien reichen dafür nicht.

## 3. Sicherheitsziel

Der Supervisor muss sicherstellen, dass jeder Execution- oder Recovery-Claim
höchstens einen konkret gebundenen Kindprozess besitzt.

Kein Writer darf vor durablem claimed Start Dateizugriff ausführen.

Recovery darf ausschließlich den read-only Reconciler ausführen.

Ein terminaler Endfakt darf erst entstehen, wenn der konkret gebundene Prozess
nachweislich keine weitere Wirkung erzeugen kann.

## 4. Zwei getrennte Prozessfähigkeiten

Der spätere Adapter besitzt getrennte Operationen für:

- genau einen LQ-426-Writerprozess;
- genau einen LQ-427-Reconciliationprozess.

Es gibt keinen generischen `run(command, args, env)`-Port.

Writer und Reconciler sind feste kontrollierte Fähigkeiten, keine
caller-gelieferten Programme.

Cleanup, Shell, Build, Git und Deployment sind keine Supervisorfähigkeit.

## 5. Keine freie Kommandooberfläche

Der Caller darf weder ausführbaren Pfad, Modulnamen, Shellstring,
Arbeitsverzeichnis noch Environmentmap liefern.

Es gibt kein `shell=True`, keine Stringinterpolation und keine Suche über
`PATH` aus untrusted Eingaben.

Die konkrete ausführbare Identität wird beim Adapteraufbau kontrolliert und
unveränderlich gebunden.

Ein Prozessaufruf kann diese Bindung nicht überschreiben.

## 6. Kontrollierter Execution-Owner

Vor dem Execution-Claim erzeugt die kontrollierte Composition eine stabile
Execution-Owner-ID und bindet sie an genau einen Supervisorstartversuch.

Die ID ist kein PID-, Host-, Container- oder Zeitwert.

Der Supervisor akzeptiert keine freie Owner-ID aus einer HTTP-, CLI- oder
Sessiongrenze.

SessionPrincipal identifiziert nur den Actor und ist kein Prozessowner.

## 7. Startgesperrter Kindprozess

Der Writerkindprozess muss in einem Zustand entstehen, in dem er noch keinen
Source- oder Zielzugriff ausführen kann.

Er wartet auf eine kontrollierte einmalige Freigabe des Supervisors.

Ein bloßes Starten des normalen Writers und nachträgliches Persistieren von
`writer_started` ist verboten.

Der Start-Gate muss vor jedem möglichen Writercode wirksam sein.

## 8. Execution-Reihenfolge

Für einen neuen Writer gilt exakt:

1. Attempt persistent reservieren;
2. Execution-Claim für kontrollierten Owner erwerben;
3. startgesperrten Kindprozess genau einmal anlegen;
4. dessen Existenz und Gatezustand direkt bestätigen;
5. `start_claimed_execution` mit Claim, Owner und Observation-ID durable
   bestätigen;
6. erst danach das Gate genau einmal freigeben;
7. direkten Prozessausgang abwarten und Writerobservation sichern;
8. terminalen Execution-Endfakt sichern.

Kein Schritt darf aus Callerstatus oder Timeout übersprungen werden.

## 9. Warum der Gatezustand erforderlich ist

Würde `writer_started` vor Prozessanlage persistiert, könnte unklar bleiben,
ob überhaupt ein Prozess existierte.

Würde der Writer vor `writer_started` laufen, könnte eine Dateiwirkung ohne
durablen Ownershipfakt entstehen.

Der bestätigte startgesperrte Prozess schließt beide Reihenfolgelücken.

Er besitzt einen Prozess, aber noch keine Dateiwirkungsmöglichkeit.

## 10. Start-not-confirmed vor claimed Start

Kann der startgesperrte Prozess nicht eindeutig angelegt oder beobachtet
werden, bleibt `writer_started` aus.

Der Supervisor muss zunächst direkt belegen, dass kein gebundener Kindprozess
mehr wirken kann.

Erst dann darf `record_start_not_confirmed` für den Execution-Claim aufgerufen
werden.

Ein unklarer Launch ohne terminalen Nachweis bleibt fail-closed blockiert.

## 11. Fehler nach claimed Start

Nach durablem claimed Start ist `start_not_confirmed` nicht mehr zulässig.

Bleibt Gatefreigabe, Writerausführung, Prozessausgang oder Outcomesicherung
unklar, endet die direkte Quelle als `outcome_unknown`.

Der Writer wird niemals erneut gestartet.

Recovery benötigt danach den terminalen Prozessnachweis aus LQ-443.

## 12. Einmalige Gatefreigabe

Das Gate kann höchstens einmal und nur für den exakt gebundenen Claim/Owner
freigegeben werden.

Freigabe ist keine wiederholbare Retryoperation.

Ist ihr technischer Ausgang unklar, darf weder eine zweite Freigabe noch ein
zweiter Prozessstart erfolgen.

Der Supervisor wartet beziehungsweise beweist terminales Ende und klassifiziert
den Ausgang danach konservativ unknown.

## 13. Keine Lease-Fencingfiktion

Lease-Renewals dürfen während eines laufenden Executionprozesses als
Livenessfakten erzeugt werden.

Der Supervisor liefert dafür keine Callerzeit und keine Ablaufentscheidung.

Leaseablauf stoppt oder entmachtet den Kindprozess nicht.

Er autorisiert weder Gateübernahme, zweiten Prozess noch Recovery.

## 14. Prozesshandle

Die kontrollierte Prozessgrenze benötigt einen opaken Handle, der genau den
gestarteten Kindprozess bezeichnet.

Der Handle wird nicht aus PID allein rekonstruiert und nicht an untrusted
Caller ausgegeben.

Er muss gegen PID-Reuse, fremde Prozesse und Owner-Reassignment geschützt
sein.

Claim, Owner und Handle bilden eine unveränderliche interne Bindung.

## 15. Controllerverlust

Ein In-Process-`Popen`-Objekt allein genügt nicht als Recoverygrundlage, wenn
der Controller abstürzen kann.

Die spätere konkrete Supervisorgrenze muss den gebundenen Prozess nach
Controllerneustart eindeutig terminal oder weiterhin wirkend beobachten
können.

Alternativ muss sie technisch garantieren und direkt nachweisen, dass der
Kindprozess den Controller nicht überleben kann.

LQ-445 entscheidet keine konkrete Daemon-, Container- oder OS-Technologie.

## 16. Kein PID- oder Hostnachweis

Eine fehlende PID, nicht antwortender Prozess, verschwundene Datei, Hostwechsel
oder Containername beweist kein terminales Ende.

PID-Reuse darf niemals einen neuen Prozess an einen alten Claim binden.

Logs und Process-Listing sind diagnostische Hinweise, keine autoritative
Endquelle.

Nur die kontrollierte Supervisorbindung kann den Endfakt speisen.

## 17. Direkter Writerausgang

Nach Gatefreigabe ruft der Kindprozess ausschließlich den LQ-426-Writer mit
Source, Ziel und Namen aus Binding beziehungsweise persistentem Attempt auf.

Der Caller kann diese Werte nicht ersetzen.

Das direkte typisierte Resultat oder die direkten detailbegrenzten
Writerexceptions werden an die Composition zurückgegeben.

Freies stdout-JSON oder Exitcode allein ist kein Writerfakt.

## 18. Outcome-Sicherung vor Execution-Ende

Ein direkter Writererfolg oder Writer-unknown wird zunächst über die
quellenspezifische Observationgrenze gesichert.

Ist diese Sicherung eindeutig durable, darf der Supervisorausgang
`outcome_secured` terminalisiert werden.

Bleibt ihr Commit nach exaktem ID-Retry unklar, wird der Prozess als terminal,
aber die Outcomesicherung als `outcome_unknown` erfasst.

Der Writer wird wegen Registryunsicherheit nicht wiederholt.

## 19. Nicht erfolgreiche Writerresultate

`target_not_absent`, `source_not_stable` und definitive
Writerunverfügbarkeit bedeuten einen beendeten Kindprozess, aber noch keinen
gesicherten Manifestzustand.

Die spätere Composition darf frisch reconciliieren, solange sie denselben
laufenden Ownerkontext besitzt und keine parallele Wirkung mehr möglich ist.

Alternativ sichert sie terminal `outcome_unknown` und übergibt an separate
Recovery.

Sie erfindet niemals Writererfolg oder Dateiabwesenheit.

## 20. Kontrollierte Beendigung

Eine owner-kontrollierte Abbruchentscheidung darf nur den exakt gebundenen
Kindprozess adressieren.

Nach Signal oder Abbruchanforderung muss der Supervisor weiterhin auf direkt
belegtes terminales Ende warten.

Das Senden eines Signals allein ist kein Endnachweis.

Nach möglicher Writerwirkung wird kein neuer Writer gestartet.

## 21. Timeout

Eine kontrolliert injizierte Dauer darf eine Beendigungsanforderung auslösen.

Timeout allein erzeugt weder `start_not_confirmed` noch `outcome_unknown` als
terminalen Fakt.

Erst die direkte terminale Prozessbeobachtung öffnet den entsprechenden
Endappend.

Kann Ende nicht belegt werden, bleibt der Claim aktiv und Recovery gesperrt.

## 22. Ressourcenbegrenzung

Die spätere Implementierung benötigt kontrollierte Obergrenzen für
Prozessdauer, Output, geöffnete Handles und IPC-Nachrichten.

Konkrete Werte kommen aus validierter Konstruktorpolicy, nicht aus dem
Aufrufcaller.

Überschreitung führt zur kontrollierten Beendigungssequenz und nicht zu
unbegrenztem Puffern.

Outputdetails werden nicht in Registryfakten übernommen.

## 23. Environment und Secrets

Der Kindprozess erhält nur eine explizite minimale kontrollierte
Environmentallowlist.

Er erbt nicht ungeprüft das gesamte Controllerenvironment.

DSN, Tokens, Credentials und fremde Prozessvariablen werden nicht für Writer
oder Reconciler benötigt und nicht durchgereicht.

Locale und Encoding müssen deterministisch kontrolliert sein.

## 24. Dateideskriptoren

Nicht benötigte Deskriptoren und Handles werden im Kindprozess geschlossen.

Datenbankverbindungen, Listening-Sockets und Controller-IPC außerhalb des
Start-Gates dürfen nicht vererbt werden.

Der Writer erhält keine Registryverbindung und kann Authority nicht selbst
umgehen.

Der Reconciler erhält keine Mutationsfähigkeit.

## 25. Recovery-Owner

Nach autorisiertem LQ-444-Recovery-Claim bindet der Supervisor genau einen
Recovery-Owner an genau einen startgesperrten Reconciliationprozess.

Recovery-Owner-ID und Prozesshandle sind von Execution-Owner und Writerhandle
getrennt.

Ein Executionprozess kann nicht als Recoveryprozess wiederverwendet werden.

Der Recoverycaller kann keinen freien Prozess auswählen.

## 26. Recovery-Reihenfolge

Für Recovery gilt exakt:

1. aktuellen Recovery-Claim durable erwerben;
2. startgesperrten Reconciliationprozess genau einmal anlegen;
3. Existenz und Gatezustand direkt bestätigen;
4. Gate einmalig freigeben;
5. frisches direktes LQ-427-Ergebnis abwarten;
6. Ergebnis claimgebunden über LQ-444 appendieren;
7. terminales Recovery-Ende sichern.

Es gibt keinen Writer- oder Cleanupschritt.

## 27. Recovery start-not-confirmed

Kann der startgesperrte Reconciliationprozess nicht eindeutig angelegt werden,
muss der Supervisor zuerst belegen, dass kein Prozess mehr laufen kann.

Dann darf `record_start_not_confirmed` den Recovery-Claim terminalisieren.

Ein späterer autorisierter Versuch benötigt neue Claim-, Owner-, Handle- und
Endidentitäten sowie eine neue frische Beobachtung.

Alte Resultate werden nicht übernommen.

## 28. Recovery outcome-secured

Ein direktes LQ-427-Ergebnis wird genau einmal auf die passende der fünf
LQ-444-Appendmethoden abgebildet.

Nach eindeutigem Observationcommit und terminalem Prozessende wird
`record_outcome_secured` verwendet.

Ein unklarer Append wird nur mit derselben Observation-ID und denselben Fakten
retried.

Der Reconciler wird wegen Commitunsicherheit nicht erneut ausgeführt.

## 29. Recovery outcome-unknown

Endet der Reconciliationprozess ohne verlässlich typisiertes Ergebnis oder
bleibt die Outcomesicherung unklar, wird nach terminalem Prozessnachweis
`record_outcome_unknown` verwendet.

Es wird keine Observation erfunden.

Ein späterer Recovery-Claim muss frisch reconciliieren.

Writer und Cleanup bleiben verboten.

## 30. Reconciler ist read-only

Der Recoverykindprozess erhält ausschließlich Zielbinding und persistenten
Handoffnamen.

Er darf keine Source-, Temp-, Final- oder Registrydatei verändern.

Der Supervisor interpretiert Reconciliation nicht als Cleanupfreigabe.

Pending-cleanup bleibt ein beobachtetes Resultat ohne Mutationserlaubnis.

## 31. Typisierte IPC

Start-Gate, Startbestätigung, direkte Resultate und terminale Beobachtung
benötigen eine geschlossene begrenzte IPC-Darstellung.

Unbekannte Felder, doppelte Schlüssel, übergroße Nachrichten, zusätzliche
Outcomes und inkonsistente Fakten scheitern fail-closed.

Die spätere Typentscheidung darf keine freie JSON-Payload oder generische
Commandantwort öffnen.

LQ-445 legt noch kein konkretes Wireformat fest.

## 32. Exakte Prozessretrygrenze

Ein unklarer Supervisorstart wird niemals durch einen zweiten Start mit
demselben oder neuem Handle "probiert".

Read-only Statusprüfung adressiert ausschließlich die ursprüngliche stabile
Handlebindung.

Erst direkt belegtes terminales Ende kann den Claim abschließen.

Execution-Claims werden trotzdem nie wiederverwendet; Recovery benötigt neue
Claims gemäß LQ-444.

## 33. Authority und Revocation

Claim und claimed Writerstart lesen aktuelle Authority über LQ-443; der
Recovery-Claim liest aktuelle Recoveryauthority über LQ-444.

Der Supervisor akzeptiert keine Authorityparameter.

Revocation vor diesen Grenzen verhindert den Prozessstart beziehungsweise die
Gatefreigabe.

Nach Gatefreigabe bleibt mechanische Outcome- und Endesicherung zulässig, ohne
neue Fähigkeit zu erteilen.

## 34. Neutrale Ablehnung

Fehlender Claim, fremder Owner, fehlende aktuelle Startfreigabe oder bereits
terminaler Prozess endet neutral und ohne neuen Prozess.

Neutralität gibt keinen Handle, PID, Actor, Scope, Pfad oder Prozessstatus
eines fremden Claims aus.

Sie wird nicht in technischen Fehler oder freien Claim umgedeutet.

Kein neutraler Ausgang autorisiert Writer, Reconciler oder Cleanup.

## 35. Detailfreie technische Unverfügbarkeit

Beschädigte Claim-/Handlebindung, mehrdeutige Prozessbeobachtung, unklare
Gatefreigabe, IPC-Verletzung und Infrastrukturfehler bleiben getrennte
detailfreie technische Unverfügbarkeit.

Executable-, OS-, Container-, PID-, Signal-, Environment- und Pfaddetails
verlassen die Grenze nicht.

LQ-445 benennt keinen neuen Exceptiontyp oder Transportstatus.

## 36. Konflikte

Divergente Wiederverwendung stabiler Owner-, Handle-, Observation- oder
Endidentitäten bleibt ein detailfreier Konflikt.

Der Supervisor überschreibt keine bestehende Bindung.

Es gibt kein Last-write-wins, Rebind oder automatisches Ersetzen eines
vermeintlich toten Prozesses.

Konflikt startet keinen Prozess.

## 37. Retention

Claim-, Owner-, Handlebindungs-, Start- und terminale Supervisorfakten müssen
mindestens so lange erhalten bleiben, wie Prozesszuordnung,
Parallelitätsausschluss, Unknown-Recovery oder Audit davon abhängen.

PID und OS-Ressourcen dürfen nach terminalem Ende freigegeben werden, aber die
stabile historische Bindung bleibt erhalten.

LQ-445 legt keine konkrete Frist oder Persistenztechnik für Handles fest.

Manifestdateiretention bleibt separat.

## 38. Bestandsattempts

Attempts ohne Execution-Claim oder ohne kontrollierte Supervisorbindung werden
nicht automatisch als terminal eingestuft.

Ein vorhandenes `writer_started`, aktuelle Dateiabwesenheit oder altes PIDlog
erzeugt keinen Handle- oder Endnachweis.

Bestandsverankerung benötigt weiterhin einen separaten owner-kontrollierten
Slice.

Der Supervisorvertrag führt keinen Backfill aus.

## 39. Keine Implementierungsentscheidung

LQ-445 entscheidet keine Subprocess-, Daemon-, Container-, cgroup-, Socket-
oder Orchestratorbibliothek.

Er entscheidet kein Wireformat, Executable, Timeoutwert, Signal oder
Sandboxprofil.

Es gibt keine neue Tabelle, Spalte, Migration, Domainklasse, Port- oder
Methodensignatur.

Revision und Head bleiben `20260824_0029`.

## 40. Kein Wiring

Der Slice startet, wartet, signalisiert oder beendet keinen echten Prozess.

Er liest keine Datei, kein Environment und kein Prozesslisting.

Es gibt keinen Operator, CLI, Route, Scheduler-, Compose-, CI- oder
Production-Wiringpfad.

LQ-439 wird noch nicht auf claimed Supervisorausführung umgestellt.

## 41. Tests

Fokussierte statische Tests belegen:

- getrennte feste Writer- und Reconcilerfähigkeiten ohne freien Command;
- startgesperrten Prozess vor claimed Writerstart;
- einmalige Gatefreigabe erst nach durablem Start;
- start-not-confirmed nur vor claimed Start und nach terminalem Nachweis;
- unknown statt Writerretry nach unklarer Freigabe oder Outcomesicherung;
- Leaseablauf, Timeout, Signal und PID-Abwesenheit ohne Endwirkung;
- controllerverlustfeste Handlebindung;
- fünf claimgebundene Recoveryoutcomes ohne Writer/Cleanup;
- aktuelle Authority nur an Claim-/Startgrenzen;
- neutrale Ablehnung getrennt von technischer Unverfügbarkeit;
- unveränderte Revision 0029;
- Roadmap- und Folgeslicebindung.

## 42. Nichtziele

LQ-445 implementiert keinen Supervisor, IPC-Kanal, Start-Gate, Prozessrunner,
Writer- oder Reconcilerwrapper und keine Composition.

Scope-/Authority-Bootstrap, Bestandsverankerung, Cleanup und finale
Evidence-Retention bleiben separat.

Staging, Commit, Push, Build, Signatur, Promotion, Publication und Deployment
werden weder ausgeführt noch autorisiert.

## 43. Nächster Slice

LQ-446 sollte geschlossene Supervisor-Handle-, Start-Gate-, Prozessausgangs-
und Request-/Resulttypen sowie getrennte Writer-/Recoveryports definieren.

Konkreter Prozessadapter, claimed Writerintegration, Recoverycomposition,
Bestandsverankerung, Cleanup und Retention bleiben danach separate Slices.
