# LQ-385 — Runtime Cleanup Release and Operational Readiness Audit

## Zweck

LQ-385 auditiert den vollständigen Runtime-Cleanup-Komplex nach LQ-327 bis
LQ-384 auf Release- und Betriebsbereitschaft.

Der Audit ist read-only. Er startet keinen Operator, Dockerprozess, Service,
Cleanup, Claimwrite oder Deployment.

## Auditumfang

Geprüft wurden installierte Entry Points, Autorisierungs- und Claimgrenzen,
Unknown-Outcome-Routen, Generation-Lineage, Cleanup-Abschluss, Tests,
Betreiberartefakte, Evidence-Retention und Volume-Disposition.

Der Audit trennt drei Aussagen:

- interne Code- und Vertragsvollständigkeit;
- beaufsichtigte operative Ausführbarkeit;
- vollständige Entsorgung einschließlich Datenvolume.

Keine dieser Aussagen wird aus einer anderen abgeleitet.

## Interne Prozesskette

Die Runtime-Cleanup-Kette besitzt 16 installierte Commands:

1. Cleanup-Preflight;
2. initialer Runtime-Cleanup;
3. Cleanup-Claim-Inspector;
4. Cleanup-Finalizer;
5. erste Continuation;
6. deren Inspector;
7. deren Finalizer;
8. Recontinuation;
9. deren Inspector;
10. deren Finalizer;
11. Chained Continuation;
12. deren Inspector;
13. deren Finalizer;
14. generationengebundene Continuation;
15. Generation-Inspector;
16. Generation-Finalizer.

Disposition und vorgelagerte PostgreSQL-Reconciliation bleiben zusätzliche
Voraussetzungen vor dieser eigentlichen Cleanup-Kette.

## Installierte CLI-Grenzen

Alle 16 Commands sind als Console Entry Points im Paket registriert.

Jeder Command besitzt eine geschlossene Argumentgrenze, detailarme kanonische
Ausgabe und Exitcode 2 bei technischer Nichtverfügbarkeit.

Generation eins und zwei verwenden ihre direkten Vorgängerdateien. Ab
Generation drei transportieren wiederholbare CLI-Optionen eine geordnete,
höchstens 16 Paare lange Lineage.

Kein Command akzeptiert einen freien Zustand, Ausgang, Allow-Bool,
Ressourcennamen oder Mutationsumfang.

## Autoritätsgrenzen

Preflight, Cleanup, jede Continuation, jeder Inspector und jeder Finalizer
besitzen getrennte owner-only Autorisierungen.

Executor und Autorisierer bleiben pro mutierendem oder finalisierendem Schritt
verschieden.

Historische Autorisierungen werden an ihrem ursprünglichen Fenstermittelpunkt
validiert; aktuelle Autorisierungen benötigen ein positives UTC-Fenster von
höchstens einer Stunde.

Kein positiver Ausgang verlängert eine frühere Autorisierung oder startet den
nächsten Command automatisch.

## Claim- und Evidence-Ordnung

Der LQ-339-Cleanup-Claim bleibt bis zur separaten LQ-343-Finalisierung offen.

Jeder untergeordnete Claim wird erst nach eigener atomarer Evidence
freigegeben. Spätere Generationen entfernen keine historischen Claims.

Unknown Outcome lässt den betroffenen Claim offen und erzwingt einen
getrennten read-only Inspector.

Finalizer schreiben ihre eigene Evidence vor Freigabe ausschließlich ihres
aktuellen Claims.

Ein Evidence-Retry überspringt Inspector und Docker und wiederholt nur die
exakte Claimfreigabe.

## Ressourcen- und Volumegrenze

Runtime-Mutation ist auf einzelne intern abgeleitete Container- und
Network-Schritte begrenzt.

Bestätigte Schritte werden nicht wiederholt. Compose-Down, Force, Prune,
Wildcard-, Präfix-, Label- und Gruppencleanup bleiben ausgeschlossen.

Das PostgreSQL-Datenvolume wird in der gesamten Kette ausschließlich read-only
auf unveränderte Runbindung geprüft.

Kein Runtime-Cleanup-Command mountet, öffnet, liest, exportiert oder entfernt
das Volume.

## Vollständiger Cleanup-Handoff

Terminale Generation-Ausgänge führen manuell zum bestehenden LQ-343-
Finalizer.

LQ-343 verlangt eine neue aktuelle Autorisierung und eine frische
LQ-341-Beobachtung; Generation-Evidence ersetzt keine Cleanup-Autorität.

Er schreibt eigene Cleanup-Finalization-Evidence vor Freigabe ausschließlich
des LQ-339-Claims.

LQ-384 belegt diesen Handoff im selben Run und den bytegenauen Erhalt der
gesamten Generation-Lineage.

## Test- und Codebereitschaft

Die fokussierte Generation-/Cleanup-Finalisierungskette besteht mit 77 Tests.

Sie umfasst Generation eins bis vier, positive Generation 17, fail-closed
Generation 18, Unknown Outcome, read-only Reconciliation, Evidence-Retry und
den integrierten LQ-343-Handoff.

Die vollständige Suite besteht mit 3822 Tests, 99 Skips und 615 bestehenden
Warnungen.

Für die implementierte Runtime-Cleanup-Mechanik besteht kein offener Code-,
Vertrags- oder Testblocker.

## Bundle-Bestand

Der aktuelle Gesamtbestand bleibt bei 49 Console Entry Points, 53
Operatormodulen und 27 linearen Migrationen.

Migration-Head bleibt `20260819_0027`.

Runtime-Cleanup benötigt keine zusätzliche Tabelle, SQL-Persistenz oder
Production-App-Wiring.

Die Commands bleiben bewusst owner-kontrollierte Offline-Prozessgrenzen.

## Runtime- und Automatisierungsisolation

HTTP-App und Research-Worker starten keinen Cleanup-Operator.

Compose enthält keinen automatischen Cleanup-Service und keine automatische
Claim-Reconciliation.

CI führt keinen mutierenden Cleanup gegen eine bereitgestellte Umgebung aus.

Diese Isolation ist beabsichtigt: Ein positiver Audit- oder Inspectorausgang
darf keine unbeaufsichtigte Ressourcenmutation auslösen.

## Fehlendes zusammenhängendes Runbook

Unter `operations/runbooks` existiert derzeit kein Runtime-Cleanup-Runbook.

Die einzelnen Slice-Dokumente beschreiben Verträge und Implementierungen,
ersetzen aber keine ausführbare Betreiberreihenfolge.

Es fehlt eine aktuelle einzige Quelle für:

- Voraussetzungen und environmentbezogene Freigabe;
- Auswahl des ersten zulässigen Commands;
- Erzeugung und Übergabe jeder owner-only Autorisierung;
- Zuordnung aller neutralen, terminalen und technischen Ausgänge;
- Unknown-Outcome- und Incidentwege;
- Lineage-Aufbau und wiederholbare CLI-Optionen;
- terminalen Handoff an LQ-343;
- Abbruchbedingungen und ausdrücklich verbotene Abkürzungen.

Damit ist der Prozess noch nicht beaufsichtigt ausführbar dokumentiert.

## Fehlende Autorisierungsmaterial-Hilfe

Die Operatoren validieren Autorisierungsdateien vollständig, erzeugen sie aber
bewusst nicht selbst.

Es existiert kein Betreiberartefakt, das die erforderlichen Felder und
Hashübergaben in der vollständigen Reihenfolge beschreibt.

Direktes improvisiertes JSON, Python-REPL-Nutzung oder Kopieren aus Tests wäre
keine zulässige Production-Prozedur.

Ein späterer Runbook-Slice muss die owner-only Materialübergabe erklären, ohne
eine neue Authority, Signatur oder automatische Entscheidung einzuführen.

## Fehlende Evidence-Retention-Prozedur

Die Verträge definieren klare Retention- und Nichtwiederverwendungsuntergrenzen,
aber keine betriebliche Ablage- und Incidentprozedur.

Es fehlt eine dokumentierte Verantwortung für:

- owner-only Evidenceverzeichnis und Sicherung;
- Schutz vor Überschreiben, Rotation und Teilkopien;
- Aufbewahrung aller Autorisierungen, Claims und Evidencegenerationen;
- Untersuchung malformed oder widersprüchlicher Artefakte;
- Wiederaufnahme nach Prozessabbruch oder Hostverlust;
- Nachweis, dass IDs nicht unter neuer Bindung wiederverwendet werden.

Ohne diese Prozedur darf Evidence-Retention nicht als operativ gelöst gelten.

## Environmentbezogene Voraussetzungen

Die interne Testvollständigkeit ist keine Freigabe eines konkreten Hosts.

Vor einem beaufsichtigten Lauf müssen mindestens Docker-Binary, Compose-Datei,
Runtime- und Image-Environment, Projektname, Evidenceverzeichnis, Source-
Commit und Image-Digest zum selben freigegebenen Run gehören.

Prozesskonto, Dateieigentum, Modus, lokaler Pfadschutz und ausreichende
Evidence-Speicherdauer müssen environmentbezogen bestätigt werden.

Ein Runbook darf diese Fakten nicht aus caller-gelieferten Behauptungen oder
Dateinamen ableiten.

## Monitoring und Incidentweg

Die Commands liefern bewusst nur detailarme Ausgänge und keine Telemetrie-
Automatisierung.

Für einen realen Lauf fehlen dokumentierte Betreiberentscheidungen für
Exitcode 2, offenen Claim nach unbekanntem Ausgang, `conflict`,
`investigation_required`, Hostverlust und beschädigte Evidence.

Ein technischer Fehler darf weder als `not_found` noch als erfolgreicher
Cleanup interpretiert werden.

Monitoring, Alarmierung und Incidentbesitz bleiben environment-owned und sind
nicht durch die Operatoren selbst bereitzustellen.

## Separate Volume-Disposition

Nach erfolgreichem LQ-343-Abschluss bleibt das PostgreSQL-Datenvolume bewusst
erhalten und dem ursprünglichen Run zugeordnet.

Damit ist Runtime-Cleanup abgeschlossen, aber die disposable Umgebung nicht
vollständig datenphysisch entsorgt.

Volume-Export, Retentionentscheidung, Legal Hold, Backupprüfung, Löschfreigabe
und tatsächliche Entfernung benötigen einen separaten Vertrag.

Die fehlende Volume-Disposition blockiert nicht die technische
Runtime-Entfernung, blockiert aber jeden Claim vollständiger
Umgebungsentsorgung.

Sie darf nicht als Zusatzschritt in einem Runtime-Cleanup-Runbook improvisiert
werden.

## Readiness-Entscheidung

Die interne Runtime-Cleanup-Mechanik ist code-, vertrags- und testseitig
vollständig.

Sie ist noch nicht als beaufsichtigter Betriebsprozess freigegeben, weil
Runbook, Autorisierungsmaterial-Handoff, Retention- und Incidentprozedur fehlen.

Ein realer Hostlauf bleibt deshalb bis zur Schließung dieser Betreiberlücke
fail-closed.

Selbst danach darf nur von „Runtime-Cleanup“ gesprochen werden; „vollständig
entsorgt“ bleibt bis separater Volume-Disposition unzulässig.

## Zulässiger aktueller Claim

Zulässig ist:

```text
Die interne owner-kontrollierte Runtime-Cleanup-Kette ist implementiert und
vollständig getestet; ein beaufsichtigter Environmentlauf und jede
Volume-Entsorgung bleiben separat freizugeben.
```

Nicht zulässig sind Aussagen wie „Production-ready“, „automatisch bereinigt“,
„vollständig entsorgt“ oder „Volume gelöscht“.

## Nichtziele

LQ-385 erstellt kein Runbook, keine Autorisierungsvorlage, keinen Operator,
keinen Claim, keine Evidence, kein Monitoring und keinen Volume-Remover.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Signatur-,
CLI-, Compose-, Deployment- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben unverändert.

## Nächster Slice

LQ-386 sollte den owner-kontrollierten Runtime-Cleanup-Betriebshandoff als
Runbookvertrag definieren.

Er muss die 16 Commands, Autorisierungsmaterial, Ausgangsrouting,
Unknown-Outcome-/Incidentwege und Evidence-Retention schließen, ohne
Volume-Disposition, automatische Ausführung oder neue Authority einzubeziehen.
