# LQ-407 — PostgreSQL Volume Disposition and Deletion End-to-End Audit

## Zweck

LQ-407 auditiert den vollständigen PostgreSQL-Volume-Disposition- und
-Deletion-Lebenszyklus von LQ-388 bis LQ-406.

Der Audit ist read-only. Er startet keinen Operator, Dockerprozess, Claimwrite,
Ressourceneffekt oder Deployment.

## Auditumfang

Geprüft wurden Verträge, installierte Commands, Authority- und Claimgrenzen,
positive und unbekannte Ausgänge, Evidence-Reihenfolge, Mutationsbudgets,
Retention, Tests und terminaler Handoff.

Der Audit trennt drei Aussagen:

- interne Code-, Vertrags- und Testvollständigkeit;
- beaufsichtigte operative Ausführbarkeit;
- vollständige Datenentsorgung über alle Speicherorte.

Keine dieser Aussagen wird aus einer anderen abgeleitet.

## Installierte Prozesskette

Die Volume-Kette besitzt neun installierte Commands:

1. read-only Volume-Disposition-Resolver;
2. read-only Volume-Deletion-Preflight;
3. Evidence-first initialer Volume-Deletion-Operator;
4. read-only Inspector des ursprünglichen Löschclaims;
5. Evidence-first Finalizer des ursprünglichen Löschclaims;
6. begrenzte Volume-Deletion-Continuation;
7. read-only Inspector des Continuation-Claims;
8. Evidence-first Finalizer des Continuation-Claims;
9. kontrollierter terminaler Handoff an eine neue ursprüngliche Finalisierung.

Alle neun Commands sind als Console Entry Points registriert.

Die Kette beginnt erst nach terminalem Runtime-Cleanup und separat
bereitgestellten Retention-, Hold-, Recovery- und Lineagefakten.

## Disposition vor Mutation

LQ-390 löst die Volume-Disposition strikt read-only aus System-of-Record-
Artefakten auf.

Nur bestätigte Retentionfreigabe, klarer Legal-Hold-Zustand, erfüllte Backup-
und Restoreanforderungen, abgeschlossener Runtime-Cleanup und fehlende spätere
Nutzung können `deletion_review_ready` ergeben.

Caller liefern weder Allow-Boolean, Rolle, Ressourcennamen noch Zielausgang.

Unbekannte oder widersprüchliche Fakten bleiben neutral, rejected,
investigation_required oder technisch unavailable und erzeugen keinen Claim.

## Authority-Trennung

Resolver, Preflight, initiale Löschung, jeder Inspector, jeder Finalizer,
Continuation und terminaler Handoff besitzen getrennte owner-only
Autorisierungen.

Mutierende, inspizierende und finalisierende Schritte binden stabile,
nicht wiederverwendbare IDs, vollständige Hashketten und getrennte
Executor-, Authorizer- und Revieweridentitäten.

Historische Autorisierungen werden nur in ihrem ursprünglichen gültigen
Kontext geprüft. Aktuelle Autorisierungen besitzen positive UTC-Fenster von
höchstens einer Stunde.

Kein positiver Ausgang verlängert frühere Authority oder startet den nächsten
Schritt automatisch.

## Exakte Ressourcenbindung

Projekt- und Volumename werden ausschließlich aus Run und historischer
System-of-Record-Bindung abgeleitet.

Alle Dockerreads adressieren das exakte Volume über verankerte Namensfilter
und gegebenenfalls ein einzelnes exaktes Inspect.

Alle Mutationen adressieren ausschließlich dasselbe intern abgeleitete
Volume.

Wildcard-, Prefix-, Label-, Projektgruppen- oder caller-gelieferte
Ressourcenauswahl ist in der gesamten Kette ausgeschlossen.

## Direkt positiver Pfad

Der direkte positive Pfad lautet:

1. LQ-390 ergibt `deletion_review_ready`;
2. LQ-392 ergibt nach frischer Auflösung `ready`;
3. LQ-394 legt den ursprünglichen Claim durable an;
4. LQ-394 inspiziert die letzte exakte Bindung;
5. LQ-394 führt genau einen Volume-Remove aus;
6. LQ-394 bestätigt exakte Abwesenheit;
7. LQ-394 schreibt atomare Lösch-Evidence;
8. erst danach wird der ursprüngliche Claim freigegeben.

Ein Evidence-Retry überspringt Preflight und Docker und wiederholt nur eine
gegebenenfalls unbekannte exakte Claimfreigabe.

## Initialer Unknown Outcome

Jede technische Mehrdeutigkeit ab möglichem LQ-394-Ressourceneffekt lässt den
ursprünglichen Claim offen und erzeugt keine Erfolgsevidence.

LQ-396 inspiziert anschließend strikt read-only und klassifiziert:

- vorhandenes korrekt gebundenes Volume;
- bestätigte Abwesenheit ohne Lösch-Evidence;
- Konflikt;
- bereits vorhandene Evidence;
- neutrale Claimabwesenheit.

LQ-398 finalisiert bestätigte Abwesenheit oder vorhandene Evidence mit eigener
atomarer Finalization-Evidence vor ursprünglicher Claimfreigabe.

Ein vorhandenes Volume bleibt `continuation_required` und erzeugt keinen
Write.

## Begrenzte Continuation

LQ-400 benötigt neue aktuelle Authority und einen separaten vorab gebundenen
Unterclaim.

Nach frischer LQ-398-Entscheidung darf genau ein weiterer exakter
Volume-Remove versucht werden.

Damit beträgt das gesamte vertragliche Mutationsbudget höchstens zwei
einzelne Removeversuche: einer in LQ-394 und einer in LQ-400.

Es gibt keinen dritten Versuch, Force, Prune, Compose-Down, Mount, Export,
Container- oder Networkmutation oder SQL.

Der ursprüngliche Claim bleibt während der gesamten Continuation offen.

## Continuation Unknown Outcome

Technische Mehrdeutigkeit nach möglichem LQ-400-Effekt lässt ursprünglichen
und untergeordneten Claim offen und erzeugt keine Continuation-Evidence.

LQ-402 inspiziert Evidence vor Claims und Docker und klassifiziert den exakten
Volumezustand read-only.

LQ-404 finalisiert nur vorhandene Continuation-Evidence oder bestätigte
Abwesenheit mit eigener atomarer Evidence.

Er gibt danach ausschließlich den Unterclaim frei. Der ursprüngliche Claim
bleibt für die separate terminale LQ-398-Kette offen.

Aktuelle Volumeanwesenheit oder Konflikt bleibt `investigation_required` und
erteilt kein neues Mutationsrecht.

## Terminaler Handoff

LQ-406 akzeptiert nur positive, bytegenau gebundene LQ-404-Evidence bei
abwesendem Unterclaim.

Er verlangt neue aktuelle LQ-396- und LQ-398-Autorisierungen und vor dem
ersten Lauf einen offenen exakt gebundenen ursprünglichen Claim.

LQ-398 beobachtet Volumeabwesenheit erneut read-only, schreibt eigene atomare
Finalization-Evidence und gibt erst danach den ursprünglichen Claim frei.

Der Handoff besitzt keinen eigenen Writer und keine Releasefunktion.

Sein positiver Ausgang `volume_deletion_finalized` ist nur nach terminalem
LQ-398-Abschluss erreichbar.

## Claim- und Evidence-Ordnung

Der ursprüngliche Claim wird vor dem ersten möglichen Remove durable angelegt
und bleibt über jeden Unknown-Outcome- und Continuation-Pfad offen.

Der Unterclaim wird vor dem zweiten möglichen Remove durable angelegt und nur
nach eigener Continuation- oder Continuation-Finalization-Evidence
freigegeben.

Jeder Finalizer schreibt eigene atomare Evidence vor Freigabe ausschließlich
seines exakten Claims.

Kein späterer Schritt erfindet historische Operator-Evidence oder schreibt
einen früheren Record um.

Evidence-Retry erreicht weder Inspector noch Docker und wiederholt nur die
exakte Claimfreigabe.

## Terminaler claimfreier Zustand

Nach positivem LQ-406-Abschluss sind der LQ-400-Unterclaim und der
ursprüngliche LQ-394-Claim abwesend.

LQ-404- und terminale LQ-398-Finalization-Evidence bleiben vollständig
erhalten und binden den Abschluss an dieselbe historische Kette.

Claimfreiheit ohne diese Evidence ist kein terminaler Erfolg.

Lokale Volumeabwesenheit allein ersetzt weder Evidence noch
System-of-Record-Disposition.

## Technische Fehlergrenze

Nonzero, stderr, Timeout, Truncation, Hard Kill, ungültiges UTF-8, doppelte
JSON-Schlüssel, malformed private Dateien und uneindeutige Namenslisten
bleiben detailfrei unavailable.

Technische Nichtverfügbarkeit wird niemals als Abwesenheit, Konflikt,
Fortschritt oder Erfolg umgedeutet.

CLI-Ausgaben enthalten nur Schemaversion, feste Operation und geschlossenen
Ausgang; private IDs, Hashes, Pfade, Zeiten und Dockerdetails bleiben intern.

## Test- und Codebereitschaft

Die fokussierte LQ-390- bis LQ-406-Kette umfasst 116 bestandene Tests.

Sie decken Disposition, Preflight, beide Removebudgets, beide
Unknown-Outcome-Routen, read-only Inspectorwege, atomare Evidence,
Claimfreigabe, Evidence-Retry, terminalen Handoff und CLI-Grenzen ab.

Die vollständige Suite besteht mit 3941 Tests, 99 Skips und 615 bestehenden
Warnungen.

Für die implementierte Volume-Disposition- und -Deletion-Mechanik besteht
kein offener Code-, Vertrags- oder Testblocker.

## Bundle-Bestand

Der Gesamtbestand liegt bei 58 Console Entry Points, 62 Operatormodulen und
27 linearen Migrationen.

Migration-Head bleibt `20260819_0027`.

Die Volume-Kette benötigt keine neue Tabelle, SQL-Persistenz oder
Production-App-Verdrahtung.

Alle Commands bleiben bewusst owner-kontrollierte Offline-Prozessgrenzen.

## Automatisierungsisolation

HTTP-App, Research-Worker und Compose starten keinen Volume-Operator.

CI führt keine mutierende Volume-Löschung gegen eine bereitgestellte Umgebung
aus.

Kein positiver Resolver-, Inspector-, Finalizer- oder Audit-Ausgang löst
automatisch eine Ressourcenmutation aus.

Diese Isolation ist Teil der Sicherheitsgrenze.

## Fehlendes zusammenhängendes Volume-Runbook

Unter `operations/runbooks` existiert kein zusammenhängendes
Volume-Disposition- und -Deletion-Runbook.

Die Slice-Dokumente ersetzen keine einzige beaufsichtigte
Betreiberreihenfolge für:

- environmentbezogene Voraussetzungen und Freigaben;
- Erstellung und Übergabe jeder owner-only Autorisierung;
- direkte und Unknown-Outcome-Pfade;
- Auswahl des jeweils nächsten zulässigen Commands;
- Claim-, Evidence- und Hashübergaben;
- Abbruch bei Conflict, Investigation oder technischer Nichtverfügbarkeit;
- terminale LQ-406-Bestätigung;
- ausdrücklich verbotene Abkürzungen und weitere Removeversuche.

Damit ist die interne Mechanik noch nicht als realer Betriebsprozess
freigegeben.

## Fehlende Retention- und Incidentprozedur

Die Verträge definieren Retention- und Nichtwiederverwendungsuntergrenzen,
aber keine environmentbezogene Aufbewahrungsdauer oder Betreiberverantwortung.

Es fehlt eine dokumentierte Prozedur für Evidenceverzeichnis, Sicherung,
Rotation, Hostverlust, malformed Artefakte, offene Claims, Exitcode 2,
`conflict` und `investigation_required`.

IDs, Autorisierungen, Claims und Evidence dürfen bis zur Klärung niemals unter
neuer Bindung wiederverwendet oder aufgrund von Alter entfernt werden.

Ein späteres Runbook muss diese Verantwortung benennen, ohne Retentionfristen
oder Incidententscheidungen zu erfinden.

## Grenzen der Entsorgungsaussage

`volume_deletion_finalized` bestätigt ausschließlich den Evidence-first
Abschluss des exakten lokalen Docker-Volumeobjekts und der zugehörigen Claims.

Backups, Restoreartefakte, Exporte, Snapshots, Replikate, Logs und historische
Evidence besitzen eigene Retention- und Dispositionsgrenzen.

Auch ein terminaler claimfreier Zustand erlaubt nicht die Aussage „alle Daten
entsorgt“.

Vollständige Datenentsorgung bleibt eine übergeordnete, separat belegte
System-of-Record-Aussage.

## Readiness-Entscheidung

Die interne PostgreSQL-Volume-Disposition- und -Deletion-Kette ist code-,
vertrags- und testseitig vollständig.

Sie ist noch nicht als beaufsichtigter Betriebsprozess freigegeben, weil ein
zusammenhängendes Runbook sowie environmentbezogene Authority-, Retention- und
Incidentübergaben fehlen.

Ein realer Hostlauf bleibt bis zur Schließung dieser Betreiberlücke
fail-closed.

Die technische Vollständigkeit erweitert weder den lokalen Aussageumfang noch
autorisiert sie unbeaufsichtigte Löschung.

## Zulässiger aktueller Claim

Zulässig ist:

```text
Die interne owner-kontrollierte PostgreSQL-Volume-Disposition- und
-Deletion-Kette ist implementiert und vollständig getestet; ein
beaufsichtigter Environmentlauf und jede übergeordnete Aussage vollständiger
Datenentsorgung bleiben separat freizugeben.
```

Unzulässig bleiben Aussagen wie „produktive Volume-Löschung freigegeben“,
„alle Daten entsorgt“ oder „automatischer Cleanup abgeschlossen“.

## Nichtziele und Bundle

LQ-407 implementiert keinen Operator, Entry Point, Test, Runbook, Writer,
Claimrelease, Volume-Remove, Monitoring oder Deployment.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP- oder Production-Wiring-Änderung.

Bundle-Gates bleiben bei 58 Entry Points, 62 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-408 sollte den owner-kontrollierten Betriebs- und Runbookvertrag für die
vollständige PostgreSQL-Volume-Disposition- und -Deletion-Kette definieren.

Er muss Voraussetzungen, Authority-Materialfluss, direkte und
Unknown-Outcome-Routen, Incidentabbrüche, Evidence-Retention und terminale
Bestätigung beschreiben, ohne neue Authority oder Automatisierung einzuführen.
