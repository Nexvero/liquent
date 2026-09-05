# LQ-440 — Manifest Handoff Execution Ownership and Recovery Contract

## 1. Ergebnis

LQ-440 definiert die fehlende persistente Execution-Ownership- und
Recoverygrenze für gestartete Manifest-Handoffattempts.

Der Slice implementiert noch keine Typen, Ports, Persistenz oder
Prozesssteuerung.

## 2. Ausgangslücke

LQ-439 kann innerhalb eines aktiven Aufrufs genau einen Writer sicher öffnen.

Zwischen bestätigtem `writer_started` und durablem Writerausgang kann dieser
Prozess jedoch enden, hängen oder seine Registryverbindung verlieren.

Revision `20260819_0028` speichert weder Execution-Owner noch Claim, Lease,
Heartbeat oder belegtes Prozessende.

Ein zweiter Prozess kann deshalb heute keine sichere Recoveryberechtigung
ableiten.

## 3. Sicherheitsziel

Zu jedem Attempt darf höchstens ein Writerprozess als aktueller
Execution-Owner gelten.

Kein anderer Prozess darf Writer oder Reconciliation parallel zu einem
möglicherweise noch wirkenden Writer ausführen.

Recovery darf niemals einen zweiten Writerlauf erzeugen.

Sie darf nach belegtem Ende ausschließlich den vorhandenen Dateizustand
frisch beobachten und persistieren.

## 4. Stabile Execution-Identität

Jeder kontrollierte Writerstart benötigt eine intern erzeugte stabile
Execution-Claim-ID.

Sie bindet dauerhaft genau ein Attempt und genau eine kontrollierte
Prozessausführung.

Die ID ist nicht aus Attempt, Scope, Actor, PID, Hostname, Zeit oder Pfad
abgeleitet und wird nie neu vergeben.

Ein Claim kann nicht auf ein anderes Attempt oder einen anderen Prozess
reassigned werden.

## 5. Kontrollierter Execution-Owner

Der Claim bindet einen intern bekannten Execution-Owner aus einer
owner-kontrollierten Prozessgrenze.

Ein freier Callerstring, PID allein, Containername, Hostname oder
SessionPrincipal ist kein hinreichender Ownernachweis.

Der Owner besitzt keine Staging-, Commit-, Publication- oder
Deploymentauthority.

Er bezeichnet ausschließlich die konkrete Verantwortung für diesen einen
Writerprozess.

## 6. Claim vor Writerstart

Eine spätere sichere Composition muss den Execution-Claim nach durablem
Attempt und vor `writer_started` erwerben.

Der Startappend muss eindeutig an denselben Claim gebunden sein.

Nur der Prozess, dem dieser aktive Claim persistent gehört, darf den Writer
öffnen.

Kann Claim oder Claim-Bindung nicht eindeutig bestätigt werden, bleibt der
Writer gesperrt.

## 7. Atomare Eindeutigkeit

Für ein Attempt darf höchstens ein Execution-Claim den Writerstart gewinnen.

Konkurrierende Claimversuche müssen im System of Record serialisiert werden.

Check-then-set im Prozess, PID-Datei, Lockfile oder Dateiabwesenheit genügen
nicht.

Die konkrete Transaktion, Tabelle und Constraintstruktur entscheidet dieser
Vertrag noch nicht.

## 8. Startbezug

`writer_started` ohne eindeutig gebundenen Execution-Claim bleibt für neue
Productionausführung unzureichend.

Bestehende LQ-439-Composition darf daher vor späterem Production-Wiring nicht
einfach unverändert als recoveryfähiger Prozess behandelt werden.

Eine spätere Integration muss Claim und Startbeobachtung gemeinsam in eine
eindeutige Reihenfolge bringen.

Sie darf historische LQ-439-Starts nicht nachträglich einem erfundenen Claim
zuordnen.

## 9. Lease als Livenesshinweis

Ein Claim darf eine serverseitig berechnete begrenzte Lease und Heartbeats
besitzen.

Lease und Heartbeat dienen ausschließlich der Beobachtung, dass ein Owner
kürzlich noch Fortschritt melden konnte.

Der Caller liefert weder aktuelle Zeit noch Ablaufzeit oder bereits
abgelaufenen Status.

Die normative Uhr und Dauer kommen aus kontrollierter Konfiguration.

## 10. Lease-Ablauf ist kein Prozessende

Eine abgelaufene Lease beweist weder Crash noch Beendigung des Writers.

Der Prozess kann ohne Registryzugriff weiterlaufen und später noch Final- oder
Tempdateien beeinflussen.

Der LQ-426-Writer besitzt keinen Fencingtoken, den jeder Dateischritt gegen
das Persistenzsystem prüfen könnte.

Deshalb autorisiert Zeitablauf allein weder Claimübernahme, Reconciliation,
Cleanup noch einen zweiten Writer.

## 11. Kein Fencingversprechen

Eine höhere Claimgeneration oder neue Lease kann den alten lokalen
Writerprozess nicht physisch stoppen.

Die Registry darf daher keine theoretische Fencingwirkung behaupten, die der
Dateiadapter nicht durchsetzt.

Ein zukünftiger fence-fähiger Writer wäre ein separater Architekturwechsel.

LQ-440 setzt ihn nicht voraus und öffnet keine Generation-Übernahme.

## 12. Belegtes terminales Prozessende

Recovery benötigt einen durablem Fakt, dass der konkrete gebundene
Writerprozess terminal beendet ist.

Dieser Fakt darf nur aus der direkten kontrollierten Prozessgrenze stammen,
die den Prozess gestartet und dessen Ende beobachtet oder erzwungen hat.

Ein Caller-Boolean `process_ended`, ein Timeout, fehlender PID-Eintrag, Logtext
oder Heartbeatverlust ist kein Nachweis.

Der Prozessadapter muss den terminalen Ausgang direkt und detailbegrenzt
melden.

## 13. Terminale Ausgangsklassen

Mindestens unterscheidbar bleiben:

- normal beendet und direkter Writerausgang bereits gesichert;
- normal beendet, aber Registry-Outcomesicherung unklar;
- kontrolliert beendet oder beendet beobachtet, Ausgang unbekannt;
- Prozessstart nach Claim nie eindeutig bestätigt.

Diese Klassen geben keine Exitcode-, Signal-, PID-, Host- oder Fehlerdetails
an untrusted Caller aus.

Sie erlauben niemals einen Writerretry.

## 14. Unklarer Prozessstart

Wenn nach Claim nicht feststeht, ob der Writerprozess gestartet wurde, gilt
der Dateiausgang als potenziell beeinflusst.

Der Claim darf nicht einfach freigegeben oder neu vergeben werden.

Erst ein kontrollierter Supervisor-Nachweis, dass kein gebundener Prozess
mehr wirken kann, öffnet die Recoveryprüfung.

Ohne diesen Nachweis bleibt das Attempt fail-closed blockiert.

## 15. Recovery-Claim

Nach belegtem terminalem Execution-Ende erwirbt ein Recoveryprozess einen
separaten intern erzeugten stabilen Recovery-Claim.

Der Recovery-Claim bindet exakt Attempt, beendeten Execution-Claim und den
kontrollierten Recovery-Owner.

Er ist keine Umschreibung des Execution-Claims und keine Writerauthority.

Höchstens ein aktueller Recovery-Claim darf die nächste frische Beobachtung
für diesen Endnachweis besitzen.

## 16. Recovery-Authority

Der Recoveryinitiator muss aktuell aktiv sein und eine explizite
scopegebundene Manifest-Handoff-Recoveryfähigkeit besitzen.

SessionPrincipal identifiziert nur den Actor und erteilt diese Fähigkeit
nicht.

Ordinary Membership, Researchpermission, Registryreservierungsfähigkeit oder
ein caller-gelieferter Rollenname ersetzt die Recoveryfähigkeit nicht.

Actor, Scope, Attempt und Fähigkeit werden aktuell aus dem System of Record
gebunden.

## 17. Revocation

Entzug vor Erwerb des Recovery-Claims verhindert die Recoveryentscheidung.

Entzug nach eindeutig erworbenem Recovery-Claim verhindert nicht die
mechanische Sicherung der bereits direkt beobachteten Dateifakten.

Er autorisiert keinen weiteren Claim, Writer, Cleanup oder neue
Recoverygeneration.

Jede spätere Entscheidung liest aktuelle Aktivität und Fähigkeit neu.

## 18. Ausschließlich read-only Recovery

Recovery ruft ausschließlich den LQ-427-Reconciler mit Binding und Namen aus
dem System of Record auf.

Sie ruft niemals LQ-426 auf und erzeugt, ersetzt, verschiebt oder entfernt
keine Datei.

Die fünf direkten Reconciliationausgänge bleiben unverändert geschlossen.

Cleanup bleibt selbst bei pending-cleanup außerhalb der Recoverycomposition.

## 19. Frische Beobachtung

Jeder Recoveryversuch führt nach Claimgewinn eine neue Dateibeobachtung aus.

Ein Resultat aus Logs, vorherigem Prozessspeicher, Caller-JSON oder einer
älteren Reconciliation darf nicht wiederverwendet werden.

Digest und Dateizahl stammen nur aus den im Reconciler validierten
kanonischen Bytes.

Scopebinding und Handoffname werden nicht vom Caller geliefert.

## 20. Durable Outcomesicherung

Das direkte Reconciliationresult wird über die getrennten LQ-434-Methoden
appendiert.

Observation-ID, Attempt und Fakten werden innerhalb der kontrollierten
Recoverycomposition gebunden.

Ein unklarer Append wird nur mit derselben Observation-ID und denselben Fakten
wiederholt.

Weder Reconciler noch Writer werden wegen eines unklaren Appendcommits im
selben Aufruf erneut ausgeführt.

## 21. Recovery nach Recoveryprozessverlust

Auch ein Recoveryprozess kann nach Beobachtung oder vor Outcomesicherung
enden.

Sein Claim und terminaler Zustand müssen deshalb historiesicher bleiben.

Ein späterer Recoveryversuch benötigt einen neuen kontrollierten Claim und
eine neue frische read-only Beobachtung, nachdem das Ende des vorherigen
Recoveryowners belegt ist.

Er darf keine alte Observation-ID mit neu beobachteten Fakten kombinieren.

## 22. Writerergebnis bereits vorhanden

Ist ein valides `writer_handed_off` bereits durable gesichert, ist keine
Execution-Recovery erforderlich.

Ein terminaler Prozessfakt kann trotzdem für Ownershipaudit erhalten bleiben.

Er erzeugt keine zusätzliche Manifestobservation und keine Cleanupfreigabe.

Die Registryhistorie bleibt maßgeblich, nicht ein Callerstatus.

## 23. Bereits reconciliertes Attempt

Existiert nach dem betreffenden Execution-Ende bereits eine gültige
Reconciliationobservation, endet ein weiterer Recoveryversuch neutral ohne
Dateizugriff.

Er darf keine doppelte Beobachtung allein zur Statusbestätigung appendieren.

Beschädigte oder widersprüchliche Historie ist dagegen technische
Unverfügbarkeit.

## 24. Neutrale Ablehnung

Neutral und ohne Detail endet mindestens:

- unbekanntes oder nicht recoverbares Attempt;
- fehlender aktueller Recovery-Actor oder Capability;
- noch möglicher aktiver Execution-Owner;
- fehlender terminaler Prozessnachweis;
- bereits abschließend gesicherter Ausgang;
- aktuell von einem anderen Recovery-Claim besessene Recovery.

Neutralität gibt keine fremde ID, Historie, Aktivität oder Pfadinformation aus.

## 25. Detailfreie technische Unverfügbarkeit

Beschädigte Claim-/Attemptbindung, unmögliche Historie, unklare
Persistenzcommits und Infrastrukturfehler bleiben getrennte detailfreie
technische Unverfügbarkeit.

Sie werden nicht in freien Claim, Prozessende oder Reconciliationerlaubnis
umgedeutet.

LQ-440 benennt keinen neuen Exceptiontyp und entscheidet keine
Transportabbildung.

## 26. Konflikte

Divergente Wiederverwendung einer Execution-, Recovery- oder
Observation-ID ist ein detailfreier stabiler Konflikt.

Konflikt überschreibt keine bestehende Bindung und öffnet keine Recovery.

Ein Retry ist nur mit derselben ID und exakt denselben intern gebundenen
Fakten zulässig.

Last-write-wins und Upsert sind verboten.

## 27. Konkurrenz

Execution-Claim, Startbindung, terminaler Prozessfakt, Recovery-Claim und
Outcomesicherung benötigen eine persistente eindeutige Reihenfolge.

In-Process-Locks oder ein einzelner Workerprozess sind keine
Korrektheitsgrundlage.

Konkurrierende Recoveryversuche dürfen höchstens einen Claimgewinner haben.

Dateiabwesenheit entscheidet weder Claimfreiheit noch Attemptabschluss.

## 28. Retention und Nichtwiederverwendung

Execution- und Recovery-Claim-IDs sowie ihre Attemptbindungen werden nie für
andere Prozesse oder Attempts wiederverwendet.

Owner-, Start-, Heartbeat-, terminale und Recoveryfakten bleiben mindestens
so lange erhalten, wie Parallelitätsausschluss, Unknown-Auflösung, Audit oder
Nichtwiederverwendung davon abhängen.

Diese Untergrenze überdauert temporäre Leasezeiten und Dateiabwesenheit.

Der Vertrag legt keine konkrete Frist, Tabelle oder Archivstrategie fest.

## 29. Bestandsattempts

Attempts ohne Execution-Claim dürfen nicht automatisch als beendet oder frei
recoverbar gelten.

Eine spätere Einführung benötigt eine separate Bestandsklassifikation und
owner-kontrollierte Verankerung.

Aus `writer_started`, Leasealter oder aktueller Dateitopologie allein wird kein
historischer Prozessnachweis erfunden.

Diese Bestandsverankerung bleibt ein eigener Slice.

## 30. Keine Bootstrapentscheidung

LQ-440 erzeugt keinen initialen Scope, Actor, Claim, Owner oder
Recoveryauthority-Fakt.

Bootstrap bleibt getrennt und darf später initiale Fakten nur unter einem
eigenen atomaren Vertrag erzeugen.

Reguläre Capabilitypersistenz und Mutation werden ebenfalls nicht
vorweggenommen.

## 31. Keine Schema- oder Portentscheidung

Der Slice entscheidet keine Tabelle, Spalte, SQL-Anweisung, Migration,
Constraint, Index, Domainklasse, Port- oder Methodensignatur.

Revision und Head bleiben `20260819_0028`.

Es wird keine vorhandene Observationkind-Liste erweitert.

LQ-439 und die bestehenden Adapter werden in diesem Slice nicht verändert.

## 32. Kein Prozess- oder Production-Wiring

LQ-440 startet, wartet, signalisiert oder beendet keinen Prozess.

Es gibt keinen Supervisoradapter, Operator, CLI, Route, Scheduler, Compose-,
CI- oder Production-Wiringpfad.

Der Vertrag liest kein Dateisystem, Environment, PID-Verzeichnis oder
Containerbackend.

## 33. Tests

Fokussierte statische Tests belegen:

- Claim vor Start und genau einen Execution-Owner;
- Lease-Ablauf ohne Recoveryfreigabe;
- direkten Supervisor-Nachweis des terminalen Prozessendes;
- getrennten Recovery-Claim und aktuelle Recoveryfähigkeit;
- ausschließlich read-only frische Reconciliation;
- Verbot jedes Writerretry und Cleanupaufrufs;
- neutrale Ablehnung getrennt von technischer Unverfügbarkeit;
- Retention, Nichtwiederverwendung und Bestandsgrenze;
- unveränderte Revision 0028;
- Roadmap- und Folgeslicebindung.

## 34. Nichtziele

LQ-440 implementiert keinen Claim, Lease, Heartbeat, Supervisor,
Recoveryadapter, Reconcilerwrapper oder Composer.

Es gibt keine Scope-, Authority-, Bootstrap-, Bestands-, Cleanup- oder
Retentionmutation.

Staging, Commit, Push, Build, Signatur, Promotion, Publication und Deployment
werden weder ausgeführt noch autorisiert.

## 35. Nächster Slice

LQ-441 sollte geschlossene Execution-Ownership-, Prozessende-, Recovery-Claim-
und Request-/Resulttypen sowie minimale quellenspezifische Ports definieren.

Persistenzfoundation, Supervisoradapter, Recoverycomposition,
Bestandsverankerung, Cleanup und finale Evidence-Retention bleiben danach
separate Slices.
