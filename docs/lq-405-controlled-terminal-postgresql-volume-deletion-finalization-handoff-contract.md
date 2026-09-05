# LQ-405 — Controlled Terminal PostgreSQL Volume Deletion Finalization Handoff Contract

## Zweck

LQ-405 definiert den kontrollierten terminalen Handoff von positiver
LQ-404-Finalization-Evidence an eine frische LQ-398-Ausführung.

Der Handoff komponiert vorhandene Grenzen, erzeugt aber keine eigene Evidence
und mutiert selbst weder Claims noch Dockerressourcen.

Dieser Slice implementiert keinen Command, Writer, Claimrelease oder
Dockerzugriff.

## Separate Handoff-Authority

Lösch-, Reconciliation-, Finalisierungs-, Continuation- und
Continuation-Finalization-Authority gewähren kein terminales Handoff-Recht.

Ein späterer Handoff benötigt eine neue owner-only Autorisierung mit stabiler,
nicht wiederverwendbarer Volume-Deletion-Terminal-Handoff-ID.

Sie muss mindestens geschlossen binden:

- Terminal-Handoff-ID;
- Continuation-Finalization-, Continuation-Reconciliation-, Continuation- und
  Continuation-Claim-ID;
- neue Volume-Deletion-Finalization- und neue
  Volume-Deletion-Reconciliation-ID;
- ursprüngliche Volume-Deletion-, Claim- und Volume-Disposition-ID;
- Retention-, Legal-Hold- und Recoveryentscheidungs-IDs;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, immutable Image-Referenz und Compose-SHA-256;
- intern abgeleitete exakte Volumeidentität;
- SHA-256 der LQ-404-Finalization-Evidence;
- SHA-256 der LQ-404-, neuen LQ-398-, neuen LQ-396-, ursprünglichen Lösch- und
  Resolverautorisierung;
- Lineage-, Retention-, Hold- und Recoveryhashes;
- Operation exakt
  `handoff_disposable_postgres_volume_deletion_finalization`;
- Scope exakt `data_volume_only`;
- neue getrennte Executor-, Authorizer- und Revieweridentitäten;
- positives aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Volumezustand, Claimstatus, LQ-398-Ausgang, Volumename,
Rolle noch Allow-Boolean.

## Neue aktuelle Downstream-Authority

Der Handoff akzeptiert keine Wiederverwendung der früheren LQ-396- oder
LQ-398-Autorisierung, die vor LQ-400 bereits
`continuation_required` ergeben hat.

Er benötigt eine neue aktuelle LQ-396-Autorisierung mit neuer stabiler
Reconciliation-ID sowie eine neue aktuelle LQ-398-Autorisierung mit neuer
stabiler Finalization-ID.

Die neue LQ-398-Autorisierung muss den bytegenauen SHA-256 der neuen
LQ-396-Autorisierung binden.

Beide bleiben owner-only, besitzen ihre eigenen getrennten Executor-,
Authorizer- und Revieweridentitäten und ein positives UTC-Fenster von
höchstens einer Stunde.

Der Handoff erzeugt, verlängert oder ersetzt diese Autorisierungen nicht.

## Keine geerbte Authority

Positive LQ-404-Evidence beweist einen historischen Continuation-Abschluss,
gewährt aber allein kein Recht zur Freigabe des ursprünglichen Claims.

SessionPrincipal, Membership, Researchpermission, Rollenname und Besitz des
Prozesskontos sind ebenfalls keine Handoff-Authority.

Der ausführende Actor identifiziert die Komposition, autorisiert aber allein
weder Entscheidung noch Write.

Deaktivierung, Widerruf, fehlende Bindung oder Identitätsüberschneidung stoppt
fail-closed.

## Vollständige historische Bindung

Der Handoff validiert Resolver-, Lösch-, alle Reconciliation-, alle
Finalisierungs- und Continuation-Autorisierungen sowie Lineage-, Retention-,
Hold- und Recoveryartefakte erneut.

Historische Autorisierungen werden nur in ihrem damaligen gültigen Kontext
strukturell geprüft. Handoff-, neue LQ-396- und neue LQ-398-Authority müssen
aktuell sein.

IDs, Run, Source, Image, Compose, Volume, Scope, Identitäten und sämtliche
Hashbeziehungen müssen exakt dieselbe Kette beschreiben.

Neue Authority repariert keine beschädigte historische Evidence und
verlängert kein früheres Zeitfenster.

## Positive LQ-404-Evidence als Gate

Der Handoff liest den privaten LQ-404-Evidencepfad ausschließlich aus dem
vollständigen SHA-256 der gebundenen Continuation-Finalization-ID.

Die Evidence muss vollständig, owner-only, regulär, einfach verlinkt und
bytegenau an die historische Kette gebunden sein.

Ihr Ausgang muss exakt einer von zwei positiven Zuständen sein:

- `continuation_evidence_confirmed`;
- `volume_removal_ready_for_deletion_finalization`.

`not_found`, `investigation_required`, ein caller-gelieferter Ausgang oder
fehlende Evidence erreicht LQ-398 nicht.

Malformed, teilweise oder fremd gebundene Evidence ist technische
Nichtverfügbarkeit und wird weder ersetzt noch ignoriert.

## Unterclaim muss freigegeben sein

Nach positiver LQ-404-Evidence muss der aus der gebundenen
Continuation-Claim-ID abgeleitete LQ-400-Unterclaim exakt abwesend sein.

Ein vorhandener kanonischer Unterclaim bedeutet, dass der LQ-404-Release noch
nicht abgeschlossen ist, und ergibt `investigation_required` ohne Write.

Ein fremder oder beschädigter Unterclaim bleibt technische
Nichtverfügbarkeit.

Der Handoff gibt den Unterclaim nicht frei und startet keinen LQ-404-Retry.

Suche, Alter, Prefix, Wildcard und Gruppenauswahl existieren nicht.

## Ursprünglicher Claim als Voraussetzung

Vor der ersten frischen LQ-398-Komposition muss der ursprüngliche LQ-394-Claim
offen, kanonisch und exakt an dieselbe Löschkette gebunden sein.

Seine lesbare Abwesenheit ohne neue LQ-398-Finalization-Evidence ergibt
`investigation_required`.

Beschädigung oder Fremdbindung bleibt technische Nichtverfügbarkeit.

Der Handoff selbst gibt diesen Claim niemals frei.

## LQ-398-Evidence vor neuer Komposition

Der neue LQ-398-Evidencepfad wird ausschließlich aus dem vollständigen
SHA-256 der neuen Volume-Deletion-Finalization-ID abgeleitet.

Vor einem neuen LQ-398-Lauf wird vorhandene Evidence vollständig gegen die
neue LQ-398-Bindung geprüft.

Exakt gebundene terminale LQ-398-Evidence erlaubt den idempotenten Handoff-
Retry über dieselbe LQ-398-Komposition.

Malformed, kollidierende oder fremd gebundene Evidence bleibt unavailable.

Der Handoff schreibt keine eigene Abschlussdatei neben LQ-398.

## Frische LQ-398-Komposition

Ohne neue terminale LQ-398-Evidence ruft der Handoff LQ-398 genau einmal mit
der neuen LQ-396- und neuen LQ-398-Autorisierung sowie allen autoritativen
Quellartefakten auf.

LQ-398 führt LQ-396 unmittelbar frisch read-only aus.

Damit muss lokale Volumeabwesenheit erneut über die exakte verankerte
Namensliste bestätigt werden; ein früherer LQ-402-Ausgang oder LQ-404-Record
ersetzt diese Beobachtung nicht.

LQ-396 darf bei Abwesenheit kein Inspect, keinen Remove und keinen anderen
Ressourcenzugriff ausführen.

Der Handoff akzeptiert nur kanonische Schemaversion, feste LQ-398-Operation
und einen geschlossenen Ausgang.

## Terminaler positiver Ausgang

Nur zwei LQ-398-Ausgänge sind terminal positiv:

- `volume_removal_finalized`;
- `deletion_evidence_confirmed`.

Beide werden öffentlich zu `volume_deletion_finalized` vereinheitlicht.

Sie sind nur erfolgreich, nachdem LQ-398 eigene atomare
Volume-Deletion-Finalization-Evidence vollständig zurückgelesen und den
exakten ursprünglichen LQ-394-Claim freigegeben hat.

Der Handoff erzeugt keine gefälschte LQ-394-Evidence und dupliziert keine
LQ-398-Evidence.

## Nichtterminale LQ-398-Ausgänge

`continuation_required`, `not_found` und `investigation_required` werden
write-frei als `investigation_required` ausgegeben.

Sie erzeugen keine Handoff-Evidence, keinen Claimrelease und keinen weiteren
LQ-398- oder LQ-400-Versuch.

Aktuelle Volumeanwesenheit nach abgeschlossenem LQ-404-Lebenszyklus ist kein
automatisches neues Mutationsrecht.

Unbekannter, malformed oder technisch nicht verfügbarer LQ-398-Ausgang bleibt
technische Nichtverfügbarkeit ohne Ergebnisobjekt.

## Zulässige Writes ausschließlich in LQ-398

Der Handoff besitzt keinen eigenen Writer und keine eigene Releasefunktion.

Die einzigen erreichbaren Writes sind die bereits vertraglich begrenzte
atomare LQ-398-Finalization-Evidence und danach die Freigabe ausschließlich
des exakten ursprünglichen LQ-394-Claims.

LQ-404-Evidence, Continuation-Evidence, Autorisierungen, Clearanceartefakte
und alle anderen Claims bleiben unverändert.

Volume-Remove, Force, Prune, Compose-Down, Mount, Export, SQL, Container- und
Networkmutation sowie neue Continuation sind verboten.

## Unknown Outcome und Retry

Ist die LQ-398-Claimfreigabe nach persistierter LQ-398-Evidence technisch
mehrdeutig, propagiert der Handoff technische Nichtverfügbarkeit.

Ein Retry mit denselben IDs, Autorisierungen und Artefakten ruft dieselbe
LQ-398-Grenze erneut auf.

LQ-398 erkennt zuerst eigene Evidence und versucht ausschließlich die
Freigabe desselben ursprünglichen Claims erneut.

Der Retry führt LQ-396 nicht erneut aus und erreicht kein Docker.

Eine neue Handoff-ID, neue Downstream-Autorisierung oder veränderte Evidence
ist kein Retry.

## Geschlossene Ausgabe

Der spätere Handoff darf ausschließlich liefern:

- `volume_deletion_finalized`;
- `investigation_required`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Die Ausgabe enthält nur kanonische Schemaversion, feste Operation
`disposable_postgres_volume_deletion_terminal_handoff` und Ausgang.

Run-, Volume-, Claim-, Evidence-, Retention-, Hold-, Recovery-, Identitäts-,
Hash-, Zeit- und Pfaddetails bleiben privat.

## Retention und Nichtwiederverwendung

Terminal-Handoff-, neue Finalization-, neue Reconciliation-, Continuation-
Finalization-, Continuation-, Lösch- und alle Claim-IDs sowie sämtliche
Autorisierungen, Evidence und Quellartefakte bleiben mindestens so lange
unterscheidbar, wie Audit, Idempotenz, Retry oder übergeordnete
Dispositionsbestätigung davon abhängen.

Keine ID, Claimdatei, Evidence oder Volumeidentität darf unter neuer Bindung,
anderem Scope oder neuer Bedeutung wiederverwendet werden.

Claimfreigabe und lokale Volumeabwesenheit beenden die Retention nicht.

Dieser Vertrag legt keine konkrete Frist, Tabelle oder Ablageform fest.

## Grenzen der Abschlussaussage

`volume_deletion_finalized` bestätigt nur den evidence-first Abschluss des
exakten lokalen Docker-Volumeobjekts und die Freigabe des zugehörigen
LQ-394-Claims.

Backups, Exporte, Snapshots, Replikate, Logs und historische Evidence besitzen
eigene Retention- und Dispositionsgrenzen.

Der Handoff liefert niemals die Aussage „alle Daten entsorgt“.

Vollständige Datenentsorgung bleibt eine übergeordnete
System-of-Record-Aussage.

## Nichtziele und Bundle

LQ-405 entscheidet keine konkrete JSON-Struktur, Signatur, Exception,
Funktionssignatur, CLI, Docker-argv, Timeout-, Claim- oder
Evidenceimplementierung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP-, Monitoring-, Test- oder Production-Wiring-
Änderung.

Der Slice implementiert keinen Handoff, Writer, Claimrelease, neuen
Volume-Remove, Authority-Generator oder allgemeinen Datenentsorgungsnachweis.

Bundle-Gates bleiben bei 57 Entry Points, 61 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-406 sollte den kontrollierten terminalen Volume-Deletion-Handoff gemäß
diesem Vertrag implementieren.

Fake-basierte Tests müssen beide positive LQ-404-Evidenceausgänge,
Unterclaimabwesenheit, offenen ursprünglichen Claim, neue Authorities, frische
LQ-396-Abwesenheitsbeobachtung, LQ-398-Evidence, Claimfreigabe, nichtterminale
Ausgänge und Retry ohne Ressourcenwrite prüfen.

Ein abschließender End-to-End-Audit des gesamten Volume-Disposition- und
-Deletion-Lebenszyklus bleibt ein separater späterer Slice.
