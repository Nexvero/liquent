# LQ-408 — Owner-controlled PostgreSQL Volume Disposition and Deletion Operational Handoff Contract

## Zweck

LQ-408 definiert den Vertrag für ein zusammenhängendes Betreiber-Runbook der
vollständigen PostgreSQL-Volume-Disposition- und -Deletion-Kette.

Der Slice implementiert kein Runbook, keinen Command, keinen
Autorisierungsgenerator, keinen Claim, keine Evidence und keine
Ressourcenmutation.

## Prozesscharakter

Volume-Disposition und -Deletion bleiben explizit gestartete, beaufsichtigte
und kurzlebige Offline-Prozesse.

Das Runbook darf keine Queue, Schleife, Scheduler-, Service-, CI-, Deployment-
oder HTTP-Automatisierung beschreiben.

Jeder positive Ausgang beendet genau einen Schritt und benötigt eine neue
bewusste Betreiberentscheidung vor dem nächsten Schritt.

Das Runbook ist keine Authority und darf keine fehlende Autorisierung oder
System-of-Record-Entscheidung ersetzen.

## Dediziertes Prozesskonto

Alle Commands laufen unter einem dedizierten nicht interaktiven Prozesskonto.

Dieses Konto besitzt nur notwendige Leserechte auf Docker-Binary, Lineage-,
Retention-, Hold-, Recovery- und Autorisierungsdateien sowie owner-only Zugriff
auf das gebundene Evidenceverzeichnis.

Es besitzt keine OIDC-, Research-, Release-, Deployment-, Backup- oder
allgemeinen Infrastruktur-Credentials.

Besitz des Prozesskontos gewährt keine Disposition-, Lösch-, Inspector-,
Finalisierungs- oder Handoff-Authority.

## Rollen und Vier-Augen-Grenze

Das Runbook muss mindestens benennen:

- Environment Owner für Host, Run, Projekt und Evidencewurzel;
- Policy Owner für Retention-, Hold- und Recoveryentscheidungen;
- Authorizer für jede neue owner-only Autorisierung;
- getrennten Executor für genau einen ausgewählten Command;
- getrennten Reviewer gemäß jeweiligem Operatorvertrag;
- Evidence-Retention Owner;
- Incident Owner.

Keine Rollenbezeichnung, Gruppenmitgliedschaft oder Kontoinhaberschaft ist ein
Allow-Boolean.

Executor, Authorizer und Reviewer bleiben getrennt, wo der jeweilige Vertrag
drei Identitäten verlangt.

## Gebundener Environmentlauf

Vor dem ersten Command muss das Runbook einen einzelnen opaque Run und dessen
Environmentbindung dokumentieren.

Docker-Binary, Projektname, Source-Commit, immutable Image-Referenz,
Compose-SHA-256, exakte Volumeidentität und Evidenceverzeichnis müssen
denselben freigegebenen Run beschreiben.

Runtime-Cleanup-Finalization, Lineage, Retention, Legal Hold und Recoveryfakten
müssen bytegenau zu dieser Bindung gehören.

Mutable Tags, relative Pfade, ungeprüfte Symlinks, alternative Projektwerte
oder Environment-Fallbacks sind ausgeschlossen.

Ein Host- oder Pfadwechsel benötigt eine neue environmentbezogene Prüfung und
darf nicht still als Retry gelten.

## Voraussetzungen vor Disposition

Das Runbook muss vor LQ-390 mindestens bestätigen:

- terminalen Runtime-Cleanup mit erhaltenem rungebundenem Volume;
- vollständige unveränderte Lineageartefakte;
- aktuelle Retentionentscheidung aus dem System of Record;
- aktuellen eindeutigen Legal-Hold-Zustand;
- erforderliche Backup- und Restorebestätigung;
- keine gebundene spätere Nutzung des Volumes;
- private sichere Evidencewurzel mit ausreichendem Speicher;
- benannte Authority-, Evidence- und Incidentverantwortung.

Das Runbook darf keine dieser Tatsachen aus Dateinamen, Tickettext,
Callerbehauptung oder Dockerabwesenheit ableiten.

Fehlende, widersprüchliche oder technisch unklare Voraussetzung stoppt vor
Disposition und Mutation.

## Private Dateigrenze

Alle Autorisierungen, Claims und Evidence müssen regulär, owner-held,
single-link und mit Modus `0400` oder `0600` behandelt werden, soweit der
jeweilige Operatorvertrag nichts engeres verlangt.

Das Runbook muss `umask 077`, private absolute Arbeitsverzeichnisse und sichere
Übergabe ohne Shell-History, Chat, Ticket, Log oder Environmentvariable
verlangen.

Unsichere Rechte, Eigentümer, Links oder Dateitypen sind technische
Nichtverfügbarkeit und dürfen nicht durch breitere Rechte repariert werden.

Private IDs, Hashes, Ressourcennamen und Pfade gehören nicht in öffentliche
Statusmeldungen.

## Autorisierungsmaterial als Handoff

Jeder Resolver, Preflight, mutierende Operator, Inspector, Finalizer und
terminale Handoff benötigt seine eigene vorab bereitgestellte owner-only
Autorisierungsdatei.

Das Runbook muss je Schritt benennen:

- welche Vorgängerautorisierung und Evidence System-of-Record-Basis ist;
- welche IDs und Hashes bytegenau übernommen werden;
- welche neue nicht wiederverwendbare ID erforderlich ist;
- welche getrennten Identitäten gelten;
- welches aktuelle UTC-Fenster freigegeben wurde;
- wer das Material erstellt, prüft und an das Prozesskonto übergibt.

Freie JSON-Erfindung, Test-Fixture-Kopie, Python-REPL oder nachträgliche
Feldergänzung sind unzulässig.

## Keine Authority-Erzeugung durch Executor

Das Prozesskonto darf keine eigene Autorisierung erzeugen, erweitern oder
erneuern.

Der Executor darf Hashes technisch prüfen, aber keine fehlende Authority,
Rolle, Freigabe oder System-of-Record-Tatsache ergänzen.

Neue Authority verlängert keine historische Gültigkeit und repariert keine
beschädigte Evidence.

Stale, malformed, fremde oder widersprüchliche Autorisierung endet fail-closed
ohne Folgeschritt.

## Verbindliches Command-Inventar

Das spätere Runbook muss diese neun installierten Grenzen dokumentieren:

1. `liquent-disposable-postgres-volume-disposition`;
2. `liquent-disposable-postgres-volume-deletion-preflight`;
3. `liquent-disposable-postgres-volume-delete`;
4. `liquent-disposable-postgres-volume-delete-reconcile`;
5. `liquent-disposable-postgres-volume-delete-finalize`;
6. `liquent-disposable-postgres-volume-delete-continue`;
7. `liquent-disposable-postgres-volume-delete-continue-reconcile`;
8. `liquent-disposable-postgres-volume-delete-continue-finalize`;
9. `liquent-disposable-postgres-volume-delete-terminal-handoff`.

Diese Reihenfolge beschreibt Authority-Abhängigkeiten, nicht die Erlaubnis,
alle Commands nacheinander auszuführen.

Der aktuelle kanonische Ausgang wählt genau eine Route oder einen Abbruch.

## Private Pfadkarte

Das Runbook muss eine private unveränderliche Pfadkarte mindestens für
folgende Artefakte verlangen:

- Docker-Binary, Projekt und Evidencewurzel;
- Lineage-, Retention-, Hold- und Recoverydatei;
- Disposition- und initiale Löschautorisierung;
- ursprüngliche Reconciliation- und Finalization-Autorisierung;
- Continuation-, Continuation-Reconciliation- und
  Continuation-Finalization-Autorisierung;
- terminale neue Reconciliation- und Finalization-Autorisierung;
- Terminal-Handoff-Autorisierung;
- alle entstandenen Claims und Evidencepfade.

Die Pfadkarte ist Auditmaterial und keine Authority.

Sie darf nicht als exportierte Environmentvariablenmenge oder öffentlicher
Anhang umgesetzt werden.

## Stage A — read-only Disposition

LQ-390 wird mit aktuellen gebundenen Clearance- und Lineageartefakten
ausgeführt.

Nur `deletion_review_ready` darf zu einer getrennten Entscheidung über LQ-392
routen.

Retention, Hold, Recovery, spätere Nutzung, Abwesenheit oder Konflikt stoppen
ohne Mutation entsprechend ihrer kanonischen Klasse.

Technische Nichtverfügbarkeit stoppt und eröffnet bei ungeklärter Ursache den
Incidentweg.

Der Resolver erzeugt keine Löschautorisierung.

## Stage B — frischer Preflight

LQ-392 benötigt eine neue aktuelle Löschautorisierung und führt LQ-390 frisch
read-only erneut aus.

Nur `ready` erlaubt eine separate beaufsichtigte Entscheidung für LQ-394.

`rejected`, `investigation_required` oder technische Nichtverfügbarkeit führt
zu keinem Claim und keiner Mutation.

Ein früherer positiver Resolverausgang oder Tickettext ersetzt den Preflight
nicht.

## Stage C — initiale Löschung

LQ-394 wiederholt LQ-392 frisch, legt den ursprünglichen Claim durable an und
prüft die exakte Volumebindung zuletzt read-only.

Er darf genau einen exakten Volume-Remove versuchen und muss anschließend
Abwesenheit exakt bestätigen.

Bestätigter Erfolg schreibt atomare LQ-394-Evidence vor Freigabe des
ursprünglichen Claims und beendet die technische Löschkette direkt.

Eine technisch mehrdeutige Claimfreigabe bei vorhandener Evidence erlaubt nur
den exakten Evidence-Retry desselben LQ-394-Commands.

## Initialer Unknown Outcome

Prozessverlust, Timeout, Nonzero, stderr, verlorene Bestätigung oder
widersprüchliche Nachbeobachtung nach möglichem Remove darf niemals als Erfolg
oder Abwesenheit interpretiert werden.

Der ursprüngliche Claim und alle Eingaben bleiben unverändert erhalten.

Der einzige zulässige nächste technische Schritt ist LQ-396 mit neuer aktueller
Reconciliation-Authority.

Blind-Retry von LQ-394, Ersatzbefehl, manuelles Docker-Remove, Force, Prune und
neue Lösch-ID sind verboten.

## Stage D — ursprünglicher Inspector

LQ-396 schreibt weder Claims, Evidence noch Ressourcen.

Das Runbook muss getrennt routen:

- `final_evidence_present` zur LQ-398-Finalisierung;
- `volume_absent_evidence_missing` zur LQ-398-Finalisierung;
- `volume_present` zur LQ-398-Finalisierung des nichtterminalen Handoffs;
- `not_found` zum neutralen Stop;
- `conflict` zum Incident-Stop;
- technische Nichtverfügbarkeit zum Incident-Stop.

Kein Inspectorausgang allein erlaubt Claimfreigabe oder Mutation.

## Stage E — ursprünglicher Finalizer

LQ-398 benötigt eine neue aktuelle Finalization-Authority und führt LQ-396
frisch aus, sofern keine eigene Finalization-Evidence existiert.

`volume_removal_finalized` und `deletion_evidence_confirmed` beenden die
technische Löschkette nach Evidence-first Freigabe des ursprünglichen Claims.

`continuation_required` lässt den Claim offen und darf ausschließlich zu einer
separaten Entscheidung über LQ-400 routen.

`not_found` stoppt neutral. `investigation_required` und technische
Nichtverfügbarkeit stoppen ohne Folgemutation.

Ein Evidence-Retry wiederholt nur die exakte Claimfreigabe und erreicht weder
LQ-396 noch Docker.

## Stage F — einzige Continuation

LQ-400 benötigt eine neue aktuelle Continuation-Authority und einen separat
vorab gebundenen Unterclaim.

Der Operator führt LQ-398 frisch aus und erreicht Mutation nur bei
`continuation_required`.

Er darf genau einen weiteren exakten Volume-Remove versuchen. Damit ist das
Gesamtbudget von höchstens zwei Removeversuchen ausgeschöpft.

Bestätigter Erfolg schreibt atomare Continuation-Evidence vor Freigabe nur des
Unterclaims. Der ursprüngliche Claim bleibt offen.

Es gibt keinen dritten Remove und keine zweite Continuation.

## Continuation Unknown Outcome

Technische Mehrdeutigkeit nach möglichem LQ-400-Effekt lässt beide Claims
offen und erzeugt keine Continuation-Evidence.

Der einzige zulässige nächste technische Schritt ist LQ-402 mit neuer aktueller
Continuation-Reconciliation-Authority.

Blind-Retry von LQ-400, manuelle Claimfreigabe und alternative Dockerbefehle
sind verboten.

## Stage G — Continuation-Inspector

LQ-402 prüft Continuation-Evidence vor Claims und Docker und bleibt strikt
read-only.

Das Runbook muss getrennt routen:

- `continuation_evidence_present` zu LQ-404;
- `volume_absent_evidence_missing` zu LQ-404;
- `volume_present` oder `conflict` zu Incident und Stop;
- `not_found` zum neutralen Stop;
- technische Nichtverfügbarkeit zu Incident und Stop.

Kein LQ-402-Ausgang erlaubt einen weiteren Remove.

## Stage H — Continuation-Finalizer

LQ-404 benötigt eine neue aktuelle Authority und führt LQ-402 frisch aus,
sofern keine eigene Finalization-Evidence existiert.

`continuation_evidence_confirmed` und
`volume_removal_ready_for_deletion_finalization` schreiben eigene atomare
Evidence und geben danach ausschließlich den Unterclaim frei.

Der ursprüngliche Claim bleibt offen und routet erst nach separater Prüfung zu
LQ-406.

`not_found` stoppt neutral. `investigation_required` und technische
Nichtverfügbarkeit stoppen ohne Folgemutation.

Evidence-Retry erreicht weder LQ-402 noch Docker.

## Stage I — terminaler Handoff

LQ-406 benötigt positive LQ-404-Evidence, einen freigegebenen Unterclaim,
einen offenen ursprünglichen Claim, neue aktuelle LQ-396-/LQ-398-Authorities
und eine neue Handoff-Authority.

LQ-398 beobachtet Abwesenheit über LQ-396 erneut read-only, schreibt eigene
atomare Finalization-Evidence und gibt danach den ursprünglichen Claim frei.

Nur `volume_deletion_finalized` bestätigt den terminalen lokalen Abschluss.

`investigation_required` oder technische Nichtverfügbarkeit stoppt ohne
weiteren Versuch.

LQ-406 besitzt keinen eigenen Writer und keine eigene Claimfreigabe.

## Evidence-Retry-Regel

Existiert exakte Operator- oder Finalization-Evidence, darf nur derselbe
zuständige Command mit unveränderten IDs, Autorisierungen und Quellartefakten
erneut aufgerufen werden, um eine mehrdeutige Claimfreigabe abzuschließen.

Dieser Retry überspringt Inspector und Docker.

Eine neue ID, neue Authority oder veränderte Evidence ist kein Retry.

Das Runbook muss vor jedem Retry Evidencehash, Claimpfad und unveränderte
Bindung privat prüfen lassen.

## Geschlossene Ausgangsklassen

Das Runbook muss Ergebnisse mindestens in folgende Klassen trennen:

- positiver Abschluss des aktuellen Einzelschritts;
- terminaler lokaler Löschabschluss;
- neutraler Stop ohne Authority;
- explizite Ablehnung ohne Mutation;
- nichtterminaler Zustand mit genau benanntem Inspector oder Finalizer;
- Conflict oder `investigation_required`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Keine Klasse darf allein aus Exitcode, fehlendem stdout, Ressourcenabwesenheit
oder Prozessverlust erraten werden.

## Incident-Stopregeln

Bei Exitcode 2, malformed Evidence, fremdem Claim, Hashabweichung, Hostverlust,
falschem Eigentümer, `conflict`, `investigation_required`, unerwarteter
Volumeanwesenheit nach LQ-404 oder unbekanntem Ausgang muss der Ablauf stoppen.

Das Runbook muss die vollständige Inputmenge unverändert sichern und einen
environment-owned Incident eröffnen.

Während der Untersuchung sind Docker-Mutationen, Claimlöschung,
Evidence-Reparatur, ID-Neuvergabe, neue Continuation und
Berechtigungsverbreiterung verboten.

Eine Wiederaufnahme benötigt eine explizite Entscheidung aus unveränderten
System-of-Record-Artefakten.

## Evidence-Retention-Prozedur

Das Runbook muss einen benannten betrieblichen Owner für die private
Evidencewurzel verlangen.

Aufzubewahren sind mindestens alle Clearance- und Lineageartefakte,
Autorisierungen, Claims oder deren belegte Freigabe, Operator-Evidence,
Reconciliation- und Finalization-Evidence sowie Incidentaufzeichnungen.

Sicherung muss atomare Dateien und Eigentumsbindung erhalten und darf keine
teilgeschriebenen Temporärdateien als gültige Evidence übernehmen.

Retention endet nicht mit Claimfreigabe, Volumeabwesenheit oder terminalem
LQ-406-Ausgang.

Konkrete Frist, Medium, Rotation und Löschfreigabe bleiben environment-owned
und dürfen nicht durch das Runbook erfunden werden.

## Nichtwiederverwendung

Run-, Disposition-, Lösch-, Reconciliation-, Finalization-, Continuation-,
Handoff- und alle Claim-IDs bleiben dauerhaft innerhalb der erforderlichen
Audit- und Incidentuntergrenze unterscheidbar.

Keine ID, Authority, Claimdatei, Evidence oder Volumeidentität darf unter
neuer Bindung, anderem Scope oder neuer Bedeutung wiederverwendet werden.

Ein fehlender Claim erlaubt keine Pfadübernahme durch einen neuen Vorgang.

Dateinamen oder Alter beweisen weder Abschluss noch Wiederverwendbarkeit.

## Detailarme Kommunikation

Außerhalb des privaten Evidence- und Incidentkontexts dürfen nur kanonischer
Ausgang, Exitklasse, opaque Runreferenz und UTC-Zeit kommuniziert werden.

Interne IDs, Hashes, Pfade, Ressourcennamen, Dateiinhalte, Dockerantworten und
Fehlerdetails bleiben privat.

Technische Nichtverfügbarkeit darf nicht durch stderr-Veröffentlichung oder
ungefilterte Debuglogs aufgeklärt werden.

Das Runbook darf keine Secrets oder Credentials enthalten.

## Verbotene Abkürzungen

Das Runbook muss ausdrücklich verbieten:

- `docker compose down`, `--volumes`, Force und Prune;
- Mount, Export, Volumeinhaltszugriff und SQL als Löschabkürzung;
- Wildcard-, Prefix-, Label- oder Projektgruppenselektion;
- manuellen Volume-Remove außerhalb LQ-394 oder LQ-400;
- dritten Removeversuch oder zweite Continuation;
- manuelle Claimfreigabe oder Evidence-Erstellung;
- Wiederverwendung einer ID unter neuer Bindung;
- Ersetzen oder Umschreiben historischer Authority oder Evidence;
- Erfolg aus lokaler Abwesenheit ohne zuständigen Inspector und Finalizer;
- automatisches Retry, Polling oder Starten des nächsten Commands;
- Zusammenlegen vorgeschriebener Executor-, Authorizer- und Reviewerrollen.

## Terminale Bestätigung

Ein beaufsichtigter Lauf darf lokal nur dann terminal bestätigt werden, wenn:

- LQ-406 kanonisch `volume_deletion_finalized` ausgegeben hat;
- terminale LQ-398-Finalization-Evidence vollständig erhalten ist;
- LQ-404-Finalization-Evidence auf dem Continuation-Pfad erhalten ist;
- Unterclaim und ursprünglicher Claim exakt abwesend sind;
- alle Authority-, Clearance-, Lineage- und Evidencehashes inventarisiert sind;
- kein offener Incident oder technisch unbekannter Zustand besteht.

Claimfreiheit oder Volumeabwesenheit allein genügt nicht.

Der terminale lokale Abschluss startet keine Retentionlöschung und keine
übergeordnete Datenentsorgungsbestätigung.

## Aussagegrenze

Das Runbook darf nach terminalem LQ-406-Abschluss ausschließlich bestätigen,
dass das exakte lokale Docker-Volumeobjekt evidence-first finalisiert wurde.

Backups, Restoreartefakte, Exporte, Snapshots, Replikate, Logs und historische
Evidence bleiben unter eigenen Retention- und Dispositionsgrenzen.

„Alle Daten entsorgt“, „vollständig gelöscht“ oder gleichwertige Aussagen sind
ohne separate übergeordnete System-of-Record-Evidence verboten.

## Nichtziele und Bundle

LQ-408 implementiert kein Runbook, keinen Operator, Entry Point, Test,
Authority-Generator, Writer, Claimrelease, Volume-Remove, Monitoring oder
Deployment.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP- oder Production-Wiring-Änderung.

Bundle-Gates bleiben bei 58 Entry Points, 62 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-409 sollte das beaufsichtigte Volume-Disposition- und -Deletion-Runbook
unter `operations/runbooks` implementieren und statisch auditieren.

Der Nachweis muss Commandinventar, Authority-Materialfluss, alle Routingwege,
Mutationsbudgets, Incidentabbrüche, Evidence-Retention, terminale Bestätigung
und Aussagegrenzen prüfen, ohne Docker oder echte Ressourcen auszuführen.
