# LQ-386 — Owner-controlled Runtime Cleanup Operational Handoff Contract

## Zweck

LQ-386 definiert den Vertrag für ein zusammenhängendes Betreiber-Runbook der
vollständigen Runtime-Cleanup-Kette.

Der Slice implementiert kein Runbook, keinen Command, keinen
Autorisierungsgenerator, keinen Claim, keine Evidence und keine
Ressourcenmutation.

## Prozesscharakter

Runtime-Cleanup bleibt ein explizit gestarteter, beaufsichtigter und
kurzlebiger Offline-Prozess.

Das Runbook darf keine Queue, Schleife, Scheduler-, Service-, CI-, Deployment-
oder HTTP-Automatisierung beschreiben.

Jeder positive Ausgang beendet genau einen Schritt und benötigt eine neue
bewusste Betreiberentscheidung vor dem nächsten Schritt.

Ein Runbook ist keine Authority und darf keine fehlende Autorisierung ersetzen.

## Dediziertes Prozesskonto

Alle Cleanup-Commands laufen unter einem dedizierten nicht interaktiven
Prozesskonto.

Dieses Konto besitzt nur die notwendigen Leserechte auf Docker-Binary,
Compose-, Runtime-, Image- und Autorisierungsdateien sowie owner-only Zugriff
auf das gebundene Evidenceverzeichnis.

Es besitzt keine OIDC-, Research-, Release-Publication-, Deployment- oder
allgemeinen Infrastruktur-Credentials.

Besitz des Prozesskontos gewährt keine Cleanup- oder Finalisierungsautorität.

## Gebundener Environmentlauf

Das Runbook muss vor dem ersten Command einen einzelnen opaque Run und dessen
Environmentbindung dokumentieren.

Docker-Binary, Compose-Datei, Runtime- und Image-Environment, Projektname,
Source-Commit, immutable Image-Digest und Evidenceverzeichnis müssen denselben
freigegebenen Run beschreiben.

Mutable Tags, relative Pfade, ungeprüfte Symlinks, alternative Compose-Dateien
oder Environment-Fallbacks sind ausgeschlossen.

Ein späterer Host- oder Pfadwechsel benötigt eine neue environmentbezogene
Prüfung und darf nicht still als Retry gelten.

## Private Dateigrenze

Alle Autorisierungen, Claims und Evidence müssen regulär, owner-held,
single-link und mit Modus `0400` oder `0600` behandelt werden, soweit der
jeweilige Operatorvertrag nichts engeres verlangt.

Das Runbook muss `umask 077`, private absolute Arbeitsverzeichnisse und sichere
Übergabe ohne Shell-History, Chat, Ticket, Log oder Environmentvariable
verlangen.

Unsichere Rechte, Eigentümer, Links oder Dateitypen sind technische
Nichtverfügbarkeit und dürfen nicht durch breitere Rechte repariert werden.

Keine private ID, kein Hash und kein interner Pfad gehört in öffentliche
Statusmeldungen.

## Autorisierungsmaterial als Handoff

Jeder mutierende, inspizierende und finalisierende Command benötigt seine
eigene vorab bereitgestellte owner-only Autorisierungsdatei.

Das Runbook muss für jeden Schritt benennen:

- welche vorherige Autorisierung und Evidence als System-of-Record-Basis gilt;
- welche IDs und Hashes bytegenau übernommen werden;
- welche neue nicht wiederverwendbare ID erforderlich ist;
- welche getrennten Executor- und Autorisiereridentitäten gelten;
- welches aktuelle UTC-Fenster freigegeben wurde;
- wer das Material bereitstellt, prüft und an das Prozesskonto übergibt.

Es darf keine freie JSON-Erfindung, Test-Fixture-Kopie oder Python-REPL-
Abkürzung empfehlen.

## Keine Autorisierungserzeugung durch Executor

Das Prozesskonto darf seine eigene mutierende oder finalisierende
Autorisierung nicht erzeugen oder erweitern.

Der Executor darf Hashes für die technische Übergabe prüfen, aber keine
fehlenden Authority-Fakten ergänzen.

Eine neue Autorisierung verlängert keine historische Gültigkeit und repariert
keine beschädigte Evidence.

Stale, malformed, fremde oder widersprüchliche Autorisierung endet fail-closed
ohne Folgeschritt.

## Verbindliche Command-Reihenfolge

Das spätere Runbook muss die 16 installierten Cleanup-Grenzen in ihrer
Authority-Reihenfolge dokumentieren:

1. `liquent-disposable-postgres-cleanup-preflight`;
2. `liquent-disposable-postgres-runtime-cleanup`;
3. `liquent-disposable-postgres-cleanup-reconcile`;
4. `liquent-disposable-postgres-cleanup-finalize`;
5. `liquent-disposable-postgres-cleanup-continue`;
6. `liquent-disposable-postgres-cleanup-continue-reconcile`;
7. `liquent-disposable-postgres-cleanup-continue-finalize`;
8. `liquent-disposable-postgres-cleanup-recontinue`;
9. `liquent-disposable-postgres-cleanup-recontinue-reconcile`;
10. `liquent-disposable-postgres-cleanup-recontinue-finalize`;
11. `liquent-disposable-postgres-cleanup-chain-continue`;
12. `liquent-disposable-postgres-cleanup-chain-reconcile`;
13. `liquent-disposable-postgres-cleanup-chain-finalize`;
14. `liquent-disposable-postgres-cleanup-generation-continue`;
15. `liquent-disposable-postgres-cleanup-generation-reconcile`;
16. `liquent-disposable-postgres-cleanup-generation-finalize`.

Disposition und vorgelagerte PostgreSQL-Reconciliation müssen als separate
Voraussetzungen referenziert werden.

## Kein linearer Blindlauf

Die nummerierte Liste ist ein Inventar, kein Skript, das alle Commands
nacheinander ausführt.

Nach jedem Ausgang muss das Runbook genau eine zulässige Route oder einen
Abbruch benennen.

Nicht benötigte Continuation-Stufen werden nicht vorsorglich aufgerufen.

Terminaler Zustand führt nicht durch weitere Continuations, sondern zu einer
separaten aktuellen LQ-343-Entscheidung.

## Preflight und initialer Cleanup

Der Preflight muss vor jeder neuen initialen Cleanup-Autorisierung frisch
ausgeführt werden.

Nur sein geschlossener positiver Ausgang darf den separat autorisierten
initialen Cleanup erreichen.

Ablehnung, Abwesenheit, Konflikt oder technische Nichtverfügbarkeit führt zu
keiner Mutation.

Der initiale Cleanup legt seinen Claim vor der ersten Mutation evidence-sicher
an und darf das Datenvolume nicht entfernen.

## Unknown Outcome

Ab dem ersten möglichen Ressourcenwrite darf Prozessverlust, Timeout oder
technischer Fehler niemals als Abwesenheit oder Erfolg interpretiert werden.

Der aktuelle Claim und sämtliche Eingabeartefakte werden unverändert erhalten.

Das Runbook muss als einzigen nächsten technischen Schritt den passenden
read-only Inspector nennen.

Blind-Retry des mutierenden Commands, Ersatzbefehl, manuelles Docker-Remove,
Compose-Down und neue ID sind verboten.

## Read-only Inspector-Routing

Jeder Inspector benötigt eine eigene aktuelle Autorisierung und dieselben
historischen System-of-Record-Artefakte wie der betroffene Versuch.

Der Inspector schreibt oder entfernt keine Claims, Evidence oder Ressourcen.

Das Runbook muss `not_found`, Fortschritt, unveränderten Präfix, terminalen
Präfix, `conflict` und technische Nichtverfügbarkeit getrennt routen.

Kein Inspectorausgang allein erlaubt Claimfreigabe oder Mutation.

## Evidence-first Finalizer-Routing

Finalisierung benötigt eine weitere neue aktuelle Autorisierung.

Ohne vorhandene eigene Finalization-Evidence führt der Finalizer seinen
Inspector frisch aus.

Nur geschlossene finalisierbare Zustände schreiben Evidence; erst deren
atomare Anlage und Rücklesung erlaubt Freigabe ausschließlich des aktuellen
Claims.

Neutrale oder konfliktbehaftete Ausgänge lassen Evidence und Claim unverändert.

## Evidence-Retry

Existiert exakte Finalization-Evidence, darf der gleiche Finalizer mit
unveränderten Inputs erneut aufgerufen werden, um eine mehrdeutige
Claimfreigabe abzuschließen.

Dieser Retry überspringt Inspector und Docker.

Das Runbook muss vor dem Retry dieselbe Finalization-ID, Autorisierungsdatei,
Evidence und Claimbindung verlangen.

Eine neue ID oder neue Autorisierung ist kein Retry derselben Freigabe.

## Continuation-Routing

Teilfortschritt wird nur über die spezifische nächste Continuation fortgesetzt,
die den jüngsten finalisierten Ausgang bindet.

Erste Continuation, Recontinuation und Chained Continuation bleiben
unterscheidbare historische Stufen.

Eine abgeschlossene Stufe darf nicht durch Wiederholung derselben älteren
Autorisierung übersprungen werden.

Jede Continuation besitzt nur das minimal verbleibende Network-Budget.

## Generation eins und zwei

Generation eins folgt ausschließlich auf nichtterminale LQ-362-Evidence und
verwendet keine Generation-Lineage-Optionen.

Generation zwei folgt ausschließlich auf nichtterminale Generation-1-Evidence
und verlangt genau die beiden direkten Vorgängerdateien.

Das Runbook muss die einzelnen Vorgängeroptionen und deren Reihenfolge exakt
zeigen.

Alternative, zusätzliche oder gemischte Lineage-Eingaben bleiben verboten.

## Generation drei bis 17

Ab Generation drei müssen zwei gleich lange wiederholbare Optionsfolgen die
Continuation- und Finalisierungsautorisierungen der Generationen eins bis
`n - 1` in aufsteigender Reihenfolge transportieren.

Das Runbook muss erklären, dass gleich positionierte Pfade ein Paar bilden und
Dateinamen keine Reihenfolge beweisen.

Höchstens 16 historische Paare sind zulässig. Generation 17 ist die positive
Obergrenze; Generation 18 bleibt fail-closed.

Es gibt kein Paging, Abschneiden oder caller-konfigurierbares Limit.

## Lineage-Retention

Alle Generation-Continuation-, Reconciliation- und
Finalisierungsautorisierungen sowie sämtliche Evidencegenerationen bleiben
bytegenau und unterscheidbar erhalten.

Das Runbook muss für jede Generation eine unveränderliche Inventarliste aus
ID, Dateipfad und SHA-256 im privaten Evidencekontext verlangen.

Diese Inventarliste ist Auditmaterial und keine Authority.

Historische Dateien dürfen nicht umbenannt, überschrieben oder durch Kopien mit
anderer Link- oder Eigentumsbindung ersetzt werden.

## Terminaler Handoff an LQ-343

Nur `generation_continuation_evidence_confirmed` und
`runtime_removal_ready_for_cleanup_finalization` dürfen zum Cleanup-Abschluss
routen.

Das Runbook muss eine neue aktuelle LQ-343-Autorisierung verlangen und darf
keinen Generation-Ausgang als LQ-343-Zustand übernehmen.

LQ-343 führt LQ-341 frisch aus, schreibt eigene Cleanup-Finalization-Evidence
und gibt danach ausschließlich den ursprünglichen LQ-339-Claim frei.

Die gesamte Generation-Lineage bleibt außerhalb seines Schreibumfangs.

## Geschlossene Ausgangsklassen

Das Runbook muss Ergebnisse mindestens in folgende Klassen trennen:

- positiver Abschluss des aktuellen Einzelschritts;
- nichtterminal finalisierter Versuch mit zulässiger nächster Continuation;
- terminal finalisierter Versuch mit möglichem LQ-343-Handoff;
- neutrale Abwesenheit ohne Autorität;
- explizite Ablehnung ohne Mutation;
- Konflikt oder `investigation_required`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Keine Klasse darf allein aus Exitcode, fehlendem stdout oder Prozessverlust
erraten werden.

## Incident-Stopregeln

Bei Exitcode 2, beschädigter Evidence, fremdem Claim, Hashabweichung,
Hostverlust, falschem Eigentümer, unbekannter Generation oder `conflict` muss
der Ablauf stoppen.

Das Runbook muss die vollständige Inputmenge unverändert sichern und einen
environment-owned Incident eröffnen.

Während der Untersuchung sind manuelle Docker-Mutationen, Claimlöschung,
Evidence-Reparatur, ID-Neuvergabe und Berechtigungsverbreiterung verboten.

Eine Wiederaufnahme benötigt eine explizite Entscheidung aus unveränderten
System-of-Record-Artefakten.

## Evidence-Retention-Prozedur

Das Runbook muss einen benannten betrieblichen Owner für das private
Evidenceverzeichnis verlangen.

Aufzubewahren sind mindestens alle Autorisierungen, Claims oder deren belegte
Freigabe, Continuation-Evidence, Finalization-Evidence, private
Lineage-Inventare und Cleanup-Finalization-Evidence.

Sicherung muss atomare Dateien erhalten und darf keine teilgeschriebenen
Temporärdateien als gültige Evidence übernehmen.

Retention endet nicht mit Claimfreigabe, Runtimeabschluss oder Erreichen der
Generation-Obergrenze.

## Detailarme externe Kommunikation

Außerhalb des privaten Incident- und Evidencekontexts dürfen nur kanonische
Outcomes, Exitklasse, Runreferenz und UTC-Zeit kommuniziert werden.

Interne IDs, Hashes, lokale Pfade, Ressourcennamen, Dateiinhalte und
Fehlerdetails bleiben privat.

Technische Nichtverfügbarkeit darf nicht durch stderr-Veröffentlichung oder
ungefilterte Debuglogs aufgeklärt werden.

Ein Runbook darf keine Secrets enthalten.

## Verbotene Abkürzungen

Das Runbook muss ausdrücklich verbieten:

- `docker compose down`, `--volumes`, Force, Prune und Gruppencleanup;
- manuelle Claimlöschung oder Evidence-Erstellung;
- Wiederverwendung einer ID unter neuer Bindung;
- Ersetzen historischer Autorisierungen oder Evidence;
- Ableitung von Erfolg aus Ressourcenabwesenheit ohne Inspector;
- automatisches Retry, Polling oder Starten des nächsten Commands;
- Zusammenlegen von Executor und Autorisierer;
- Volume-Mount, Volume-Inhaltszugriff oder Volume-Löschung.

## Separate Volume-Disposition

Das Runbook endet nach erfolgreicher LQ-343-Cleanup-Claimfreigabe mit
erhaltenem rungebundenem PostgreSQL-Volume.

Es darf weder Export, Backupfreigabe, Legal Hold, Retentionentscheidung noch
Volume-Löschung als Cleanup-Schritt aufnehmen.

Vollständige Umgebungsentsorgung benötigt einen separaten späteren Vertrag,
separate Authority und eigene Evidence-first-Grenze.

Runtime-Cleanup-Erfolg darf nicht als „Volume entsorgt“ kommuniziert werden.

## Runbook-Abschlusszustand

Ein erfolgreicher Runbookabschluss verlangt mindestens:

- eigene Cleanup-Finalization-Evidence;
- Abwesenheit des exakten LQ-339-Cleanup-Claims;
- Abwesenheit aller untergeordneten Claims;
- unveränderte vollständige Autorisierungs- und Evidence-Lineage;
- nachweislich erhaltenes rungebundenes Datenvolume;
- private Abschlussinventarisierung und benannten Retention-Owner.

Fehlt eines dieser Elemente, ist der operative Ausgang nicht abgeschlossen.

## Nichtziele und Bundle

LQ-386 entscheidet keine konkrete JSON-Vorlage, Signatur, neue Authority,
Funktionssignatur, CLI, Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-,
Compose-, Monitoring- oder Production-Wiring-Änderung.

Es entsteht kein Runbook, Test, Entry Point, Operator, Claim, Evidencewriter
oder Volume-Remover.

Bundle-Gates bleiben bei 49 Entry Points, 53 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-387 sollte `operations/runbooks/disposable-postgres-runtime-cleanup.md`
gemäß diesem Vertrag implementieren und mit einem statischen Audit testen.

Der Slice darf nur Betreiberartefakt, Test und Roadmap ergänzen; Productioncode,
Authority, automatische Ausführung und Volume-Disposition bleiben unverändert.
