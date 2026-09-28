# LQ-517 — Explicit Opt-In Supervisor Control-Directory Cleanup Composition

## Ergebnis

LQ-517 implementiert eine explizite Factory für die kontrollierte
Control-Directory-Cleanup-Kette.

Der erzeugte Graph bleibt nach dem Aufbau vollständig inert.

## Explizites Opt-in

Nur ein bewusster Aufruf von
`compose_manifest_handoff_supervisor_control_directory_cleanup` konstruiert
die Cleanupgrenzen.

Modulimport, Appstart, Lifespan und bestehende Supervisorcomposition rufen die
Factory nicht auf.

## Kontrollierte Eingänge

Die Factory verlangt eine bereits konfigurierte SQLAlchemy-Engine, eine
geschlossene Backendinstanz-ID und einen absoluten privaten Control-Root.

Eine optionale konstruktive Clock kann für alle zeitabhängigen Adapter geteilt
werden.

Keiner dieser Werte kann aus einem Cleanuprequest ersetzt werden.

## Datenbankeigentum

Die injizierte Engine bleibt Eigentum des Callers.

Die Composition schließt oder disposed sie nicht.

Beim Aufbau wird keine Verbindung geöffnet, keine Abfrage ausgeführt und keine
Transaktion begonnen.

## Root-Eigentum

Der absolute Root wird bereits kontrolliert und extern besessen übergeben.

Die Factory erstellt, öffnet, prüft, chmodded oder entfernt beim Aufbau kein
Verzeichnis.

Alle späteren lokalen Grenzen erhalten exakt denselben Root.

## Backendbindung

Die Backendinstanz-ID liegt bereits als geschlossenes internes Value Object
vor.

Sie wird unverändert an den persistenten Journaladapter gebunden.

Die Composition erzeugt, rotiert oder errät keine Backendidentität.

## Gemeinsame Persistenz

Directory-Lifecycle, Cleanup-Attempts, Runtimeartefakte und Journal werden aus
derselben Engine konstruiert.

Es gibt keinen In-Memory-, Test- oder zweiten Datenbankfallback.

Execution und Reconciliation beobachten damit dieselbe persistente Wahrheit.

## Aktuelle Clearance-Auflösung

Die read-only Clearance-Auflösung teilt Directory-, Decision- und
Journaladapter mit dem übrigen Graphen.

Writer- und Recoveryjournal werden ausschließlich über die stabile Backend-ID
des konstruierten Journaladapters gelesen.

Keine Clearance wird beim Factoryaufbau aufgelöst oder erzeugt.

## Clearance-Erzeugung

Das Bundle exportiert die bestehende atomare LQ-508-Clearance-Erzeugung als
separaten kontrollierten Einstieg.

Sie bleibt der einzige Einstieg, der aus Principal und aktuellem Request einen
Started-Attempt samt positiver Clearance erzeugen darf.

Die Composition umgeht weder Principalbindung noch aktuelle Foundation-,
Management-, Hold-, Recovery-, Reference- oder Terminalprüfungen.

## Gemeinsamer Codec

Genau ein kanonischer Control-Artefaktcodec wird für Preflight, physische
Wirkung und read-only Reconciliation konstruiert.

Ein Request kann keinen Codec, Dateinamen oder Byteencoder injizieren.

## Preflight

Der LQ-512-Preflight erhält den gemeinsamen Root sowie aktuelle Attempt-,
Clearance- und Artefaktlookups.

Er bleibt read-only und wird erst durch einen expliziten Executionaufruf
aktiviert.

## Write Claim

Der LQ-511-Claimadapter verwendet dieselbe Engine und dieselbe Clock wie der
Attemptstore.

Sein historischer Claimlookup wird zugleich an beide lokalen post-claim
Grenzen gebunden.

Die Factory beansprucht beim Aufbau keinen Attempt.

## Physische Wirkung

Die LQ-513-Grenze erhält Root, historischen Claimlookup, aktuellen
Directorylookup, aktuellen Artefaktlookup und gemeinsamen Codec.

Sie ist ausschließlich in die kontrollierte Execution eingesetzt.

Reconciliation erhält keinen Zugriff auf ihre Remove-Methode.

## Execution

Die LQ-515-Composition teilt denselben Attemptstore für aktuelle Auflösung,
Absent-Abschluss und unmittelbare Outcome-Persistenz.

Preflight, Claim und physische Wirkung werden in ihrer bereits geschlossenen
Reihenfolge verdrahtet.

LQ-517 ergänzt keinen alternativen oder wiederholenden Wirkungspfad.

## Read-only Reconciliation

Die LQ-516-Grenze erhält denselben Root, Attemptstore, Claimlookup,
Directorylookup, Artefaktlookup und Codec.

Sie besitzt nur die Inspectionmethode und kann keinen Remove auslösen.

Die High-Level-Reconciliation persistiert Unknown-Sicherung und terminale
Klassifikation über denselben Attemptstore wie Execution.

## Exportierte Oberfläche

Das Ergebnisbundle exportiert genau drei kontrollierte Einstiege:
Clearance-Erzeugung, Execution und Reconciliation.

Low-Level-Directory-, Runtime-, Journal-, Clearance-, Claim- und
Dateisystemadapter werden nicht separat zurückgegeben.

## Keine Authority-Abkürzung

Die Factory akzeptiert keinen SessionPrincipal, User, Workspace, Scope,
Membership-, Rollen-, Permission- oder Allowwert.

Sie cached keine Authority und erteilt selbst keine Cleanupfähigkeit.

Authority und Zielbindung werden weiterhin erst durch die persistente
Clearance-Erzeugung aus dem System of Record entschieden.

## Keine automatische Auswahl

Die Composition listet keine retired Directories und wählt keinen Kandidaten.

Attempt-, Directory- und Actorbindung müssen aus dem expliziten kontrollierten
Aufruf stammen und werden an den bestehenden Grenzen erneut geprüft.

Es gibt keine oldest-first-, TTL-, Queue- oder Sweepentscheidung.

## Kein Batchcleanup

Das Bundle besitzt keine Listen-, Schleifen-, Fan-out- oder Batchmethode.

Ein Executionaufruf betrifft weiterhin exakt einen bereits gestarteten
Attempt und ein Directory.

## Keine Zeitsteuerung

Es werden kein Scheduler, Timer, Thread, Worker, Signalhandler oder
Backgroundtask registriert.

Die optionale Clock ist nur eine konstruktive Abhängigkeit bestehender Adapter.

Ihr Wert wird beim Aufbau nicht gelesen.

## Keine Transportsichtbarkeit

LQ-517 ergänzt keine HTTP-Route, CLI, Adminaktion, Startuphook oder
Appfactory-Option.

Das Bundle wird nicht in bestehende Productionverdrahtung eingesetzt.

Ein späterer Operatoradapter muss es ausdrücklich besitzen und aufrufen.

## Aufbaufehler

Falsche Engine-, Backend-, Root- oder Clockwerte scheitern vor Rückgabe über
die bestehende detailfreie technische Unverfügbarkeitsgrenze.

Bestehende technische Unverfügbarkeit wird unverändert weitergereicht.

Andere unerwartete Konstruktionsfehler werden detailfrei vereinheitlicht.

## Keine Cleanupwirkung beim Aufbau

Die Factory ruft weder Clearance-Erzeugung, Preflight, Claim, Remove,
Outcome-Persistenz noch Reconciliation auf.

Sie kann deshalb beim Aufbau keine persistente oder physische Cleanupwirkung
auslösen.

## Kein Schema oder Deployment

LQ-517 ergänzt keine Migration, Tabelle, Spalte, SQL-Anweisung, Seedzeile,
Domainausprägung oder Portsignatur.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

Es gibt keine Compose-, Container-, Environment- oder Deploymententscheidung.

## Tests

Fokussierte Prüfungen belegen explizite Eingänge, eine Engine, einen Root,
einen Codec, geteilte Persistenzlookups und die drei kontrollierten Einstiege.

Sie sichern außerdem fehlende Aufbauwirkung, automatische Aktivierung,
Scheduler-, Batch-, Route- und Ressourcenbesitzlogik ab.

## Nächster Slice

LQ-518 sollte den Operator-Wiring-Vertrag für einen einzelnen ausdrücklich
angeforderten Cleanup und dessen getrennte Reconciliation definieren.

Automatische Planung, Directorysuche und Batchcleanup bleiben dabei weiterhin
geschlossen.
