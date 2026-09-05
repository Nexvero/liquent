# LQ-519 — Owner-Controlled Single Supervisor Control-Directory Cleanup Operator

## Ergebnis

LQ-519 implementiert den in LQ-518 eingefrorenen kurzlebigen Offline-Operator
für genau ein Supervisor-Control-Directory.

Ein separater Console Entry Point stellt ausschließlich `execute` und
`reconcile` bereit.

## Private Eingänge

Beide Befehle verlangen Dateipfade für Datenbank-URL, Backendinstanz-ID,
Control-Root und kanonischen Request.

Es gibt keinen Environment-, Arbeitsverzeichnis-, In-Memory- oder
Defaultfallback.

Direkte fachliche IDs und Konfigurationswerte sind keine CLI-Argumente.

## Gehärteter Dateileser

Jede Eingabedatei wird mit `O_NOFOLLOW` und `O_CLOEXEC` geöffnet.

Der geöffnete Descriptor muss eine reguläre Datei des effektiven Prozessowners
mit genau einem Hardlink und Modus `0400` oder `0600` zeigen.

Größe, vollständiges Lesen, UTF-8 und NUL-Freiheit werden begrenzt geprüft.

## Exakte Requestform

Der JSON-Decoder weist doppelte Schlüssel zurück.

Execute akzeptiert exakt `actor_user_id` und `directory_id`.

Reconcile akzeptiert exakt `attempt_id` und `directory_id`.

Zusätzliche Authority-, Pfad-, Outcome- oder Wirkungseingaben sind strukturell
nicht möglich.

## Privater Root

Der aus seiner separaten Datei gelesene Root muss absolut, bereits vorhanden,
kanonisch symlinkfrei, owner-kontrolliert und exakt `0700` sein.

Die Operatorgrenze erstellt oder repariert ihn nicht.

Alle LQ-517-Dateisystemadapter erhalten denselben geprüften Root.

## Datenbank und Readiness

Der Operator baut genau eine Engine aus der privaten URL auf.

Vor Composition und fachlicher Wirkung muss der bestehende Readiness-Probe den
exakten Migration-Head bestätigen.

Es findet keine Migration, Schemaerzeugung oder Reparatur statt.

## Enginebesitz

Die Operatorgrenze besitzt ihre Engine und disposed sie in einem `finally`-
Pfad nach Erfolg, neutralem Ausgang, Ablehnung oder Fehler.

LQ-517 bleibt von Ressourcenbesitz frei.

## Execute

Nach validierter Konfiguration und Readiness baut Execute genau eine
LQ-517-Composition auf.

Es erzeugt intern mit kryptografisch starkem Zufall genau eine neue Attempt-ID
und bindet sie an Actor und angegebene Directory-ID.

Die Attempt-ID ist kein Requestfeld.

## Principalbindung

Der Actor wird als `SessionPrincipal` ausschließlich identifiziert.

Der Principal erteilt keine Authority.

Die atomare LQ-508-Grenze prüft Actorbindung und alle aktuellen persistenten
Clearancefakten erneut.

## Clearance vor Wirkung

`create_control_directory_cleanup_clearance` wird genau einmal aufgerufen.

Neutraler Ausgang liefert `not_available`; fachlicher Konflikt liefert
`rejected`.

Nur eine exakt zum erzeugten Request gehörende Clearance erreicht Execution.

## Einmalige Execution

`cleanup_control_directory` wird an genau einer Stelle und ohne Schleife
aufgerufen.

Removed und Already-absent werden mit ihrem geschlossenen Outcome ausgegeben.

Unknown wird als `reconciliation_required` ausgegeben und startet keinen
zweiten Aufruf.

## Reconcile

Reconcile baut dieselbe explizite LQ-517-Composition aus aktuellen privaten
Konfigurationsquellen auf.

Es ruft ausschließlich
`reconcile_control_directory_cleanup` genau einmal für den angegebenen
Attempt-/Directory-Wert auf.

Der Zweig konstruiert keinen Principal, keine Clearance und keinen neuen
Attempt und erreicht keine physische Executionmethode.

## Geschlossene Ergebnisse

Jede normale stdout-Antwort enthält genau Attempt-ID, Directory-ID und Outcome.

Execute kann `removed`, `already_absent`, `reconciliation_required`,
`not_available` oder `rejected` liefern.

Reconcile kann `absent`, `present`, `conflict`, `not_available` oder `rejected`
liefern.

Absolute Pfade und persistente Detailfakten werden nicht ausgegeben.

## Fehlergrenze

Strukturell ungültige Konfiguration oder Requests enden mit dem festen
Input-Rejected-Code und Exitcode 2.

Unsichere private Dateien, Root-, Readiness-, Datenbank-, Codec-, Datei- und
unerwartete Compositionfehler enden mit einem festen detailfreien
Unavailable-Code und Exitcode 4.

Normale geschlossene fachliche Ausgänge verwenden Exitcode 0.

## Keine Authority-Abkürzung

Der Operator akzeptiert keine Rolle, Permission, Capability, Clearance-ID,
Policyrevision oder Allow-/Force-/Override-Entscheidung.

Backend-ID und Root sind getrennte technische Konfiguration und keine
fachlichen Freigaben.

Aktuelle Persistenz entscheidet weiterhin jede Wirkung.

## Keine automatische Reconciliation

Execute ruft Reconcile niemals auf.

Ein `reconciliation_required`-Ausgang muss mit der ausgegebenen Attempt- und
Directory-ID in einem späteren ausdrücklich gestarteten Prozess behandelt
werden.

Der ursprüngliche Attempt wird nicht erneut physisch ausgeführt.

## Keine Discovery oder Batchwirkung

Der Operator besitzt keinen Directorylisten- oder Suchlookup.

Er enthält keine Schleife über Directory-IDs, Queue, Scheduler, Timer, Worker,
Watcher oder Daemonfunktion.

Jeder Prozess behandelt genau einen Befehl und ein angegebenes Directory.

## Keine automatische Aktivierung

Der neue Entry Point ist separat paketiert.

Appfactory, Lifespan, HTTP-Routen, Supervisorservice und bestehende Processes
importieren oder starten ihn nicht.

## Kein Schema

LQ-519 ergänzt keine Migration, Tabelle, Spalte, SQL-Anweisung, Domainklasse
oder Portsignatur.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Statische Prüfungen belegen gehärtete private Dateien, exakte Requestfelder,
Rootschutz, Readiness, eine interne Attempt-ID, Clearance vor einmaliger
Execution, getrennte Reconciliation, Engine-Disposal und den einzelnen
separaten Entry Point.

## Nächster Slice

LQ-520 sollte den Einzel-Operator end-to-end gegen eine wegwerfbare
PostgreSQL-Instanz und einen privaten lokalen Control-Root prüfen.

Automatische Planung, Directorydiscovery und Batchcleanup bleiben geschlossen.
