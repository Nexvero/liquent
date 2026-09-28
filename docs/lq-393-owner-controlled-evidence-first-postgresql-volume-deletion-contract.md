# LQ-393 — Owner-controlled Evidence-first PostgreSQL Volume Deletion Contract

## Zweck

LQ-393 definiert den mutierenden Operatorvertrag für die Entfernung genau des
in LQ-392 als `ready` geprüften disposable PostgreSQL-Datenvolumes.

Der Vertrag begrenzt die Operation auf einen owner-kontrollierten
Evidence-first-Versuch mit vorab gebundenem Claim und höchstens einem
Volume-Remove.

Dieser Slice implementiert keinen Command, Claimwriter, Dockeraufruf,
Evidencewriter, Inspector oder Ressourceneffekt.

## Keine übertragene Preflightentscheidung

Ein früherer LQ-392-Ausgang `ready` wird weder gespeichert noch als Delete-
Ticket akzeptiert.

Der spätere Operator muss dieselbe Löschautorisierung und sämtliche gebundenen
System-of-Record-Dateien erneut laden und LQ-392 unmittelbar vor der
Claimanlage frisch ausführen.

Nur ein neu abgeleitetes `ready` darf den Mutationsweg erreichen.

`rejected`, `investigation_required` und technische Nichtverfügbarkeit führen
zu keinem Claim und keiner Mutation.

Caller liefern weder Allow-Boolean, Ausgang, Volumename, Dockerargumente noch
Claim-ID.

## Eigenständiger kurzlebiger Prozess

Der Operator ist eine explizit gestartete, beaufsichtigte und kurzlebige
Offline-Grenze.

Er ist kein Service, Scheduler, Queue-Consumer, HTTP-Endpunkt, Deploymenthook
oder automatischer Nachfolger des Preflight.

Ein positiver Preflightausgang startet den Operator nicht automatisch.

Der Prozess verwendet ein dediziertes nicht interaktives Konto, dessen Besitz
keine Löschauthority gewährt.

## Unveränderte owner-only Authority

Die LQ-391/392-Löschautorisierung bleibt die einzige aktuelle
Mutationsauthority.

Sie bindet weiterhin Volume-Deletion-ID, vorab festgelegte Claim-ID, Run,
Source, Image, Compose, Zielvolume, Resolver-, Lineage-, Retention-, Hold- und
Recoveryhashes, Operation `remove_disposable_postgres_data_volume`, Scope
`data_volume_only` sowie getrennte Identitäten und aktuelles Zeitfenster.

Der Operator erweitert, verlängert oder repariert diese Datei nicht.

Eine neue Datei oder neue ID ist ein neuer Versuch und niemals Retry desselben
Unknown Outcome.

## Aktuelle Revocation vor Claimanlage

Der frisch wiederholte LQ-392-Preflight löst Resolverauthority, Identitäten,
Retention, Legal Hold, Recovery, Lineage, Claims und Volumezustand erneut auf.

Widerruf, Deaktivierung, neuer Hold, Retentionänderung, Recoveryregression,
spätere Nutzung oder abgelaufenes Zeitfenster muss die Claimanlage verhindern.

Es gibt keinen positiven Cache, keine Grace Period und keinen eingefrorenen
Authority-Snapshot aus einem früheren Aufruf.

Nach erfolgreicher Claimanlage wird kein neuer positiver Ausgang erfunden;
eine technische Mehrdeutigkeit folgt ausschließlich dem Unknown-Outcome-Weg.

## Geschlossenes Mutationsbudget

Das Mutationsbudget enthält ausschließlich das intern als
`<project-name>-postgres-data` abgeleitete Volume desselben gebundenen Runs.

Container, Netze, andere Volumes, Images, Backups, Exporte, Snapshots,
Replikate, Claims und Evidence liegen außerhalb des Ressourcenbudgets.

Der Operator darf weder Ziel noch Scope durch Callerwert, Prefix, Wildcard,
Labelgruppe, Composeprojekt oder Hostauswahl verändern.

Es gibt keine Herabstufung, Erweiterung oder Bündelung mit Runtime-Cleanup.

## Finale Evidence vor Preflight und Ressourcenzugriff

Nach Laden und struktureller historischer Validierung der exakten
Löschautorisierung, aber vor frischem Preflight oder Dockerzugriff, prüft der
Operator den intern abgeleiteten Pfad seiner finalen Evidence.

Die Datei wird aus dem vollständigen SHA-256 der stabilen Volume-Deletion-ID
abgeleitet.

Exakt gebundene finale Evidence und bereits fehlender Claim liefern
idempotent denselben Abschluss, ohne Dockerzugriff oder neue Mutation.

Exakt gebundene finale Evidence mit noch vorhandenem exakten Claim erlaubt nur
den Evidence-Retry der Claimfreigabe.

Malformed, fremde, anders gehashte oder kollidierende Evidence ist technische
Nichtverfügbarkeit und wird nicht ersetzt.

Nur wenn finale Evidence fehlt, beginnt der normale Mutationsweg mit dem
frischen LQ-392-Preflight und danach der Claimanlage.

## Evidence-first Volume-Deletion-Claim

Ohne finale Evidence muss jeder Volume-Deletion-Claim fehlen.

Der exakte Claimpfad wird ausschließlich aus der in der Autorisierung
gebundenen Claim-ID abgeleitet.

Der Operator legt genau diesen Claim owner-only und mit exklusiver Neuanlage
an.

Der Claim bindet mindestens:

- Volume-Deletion- und Claim-ID;
- ursprüngliche Run-ID und Phase;
- Scope `data_volume_only` und feste Operation;
- intern abgeleitete Volumeidentität;
- SHA-256 der Lösch- und Resolverautorisierung;
- Lineage-, Retention-, Hold- und Recoveryhashes;
- getrennte Executor-, Authorizer- und Revieweridentitäten;
- UTC-Startzeit.

Claimdatei und privates Evidenceverzeichnis müssen vor dem ersten möglichen
Volumeeffekt geflusht und synchronisiert sein.

## Claimkollision und Konkurrenz

Ein vorhandener erwarteter oder anderer Volume-Deletion-Claim beendet den
normalen Mutationsweg technisch unavailable.

Der Operator liest kein Alter zur Heuristik, überschreibt und entfernt keinen
Claim und vergibt keine Ersatz-ID.

Ein offener Claim beweist weder laufende Mutation noch Erfolg oder
Volumeabwesenheit.

Nur eine spätere separate read-only Reconciliation darf den Zustand eines
offenen Claims klassifizieren.

Andere Prozesskonten, Dockerlocks oder sichtbare Volumeabwesenheit ersetzen
die Claimordnung nicht.

## Letzte Bindung vor dem Effekt

Nach durable Claimanlage und unmittelbar vor dem Remove darf der Operator das
exakte Volume ein letztes Mal read-only inspizieren.

Es muss weiterhin vorhanden und ausschließlich dem gebundenen Run und
Composeprojekt zugeordnet sein.

Eine vollständig lesbare Abweichung vor dem Remove führt zu keinem Effekt;
der Claim bleibt für getrennte Reconciliation offen, weil zwischen Preflight
und Claim ein konkurrierender Zustand entstanden ist.

Technische Nichtverfügbarkeit stoppt ebenfalls mit erhaltenem Claim.

Der Operator mountet oder öffnet das Volume nicht und liest keine
PostgreSQL-Datei.

## Genau ein Volume-Remove

Nach positiver letzter Bindung ist genau ein mutierender Aufruf zulässig:

```text
docker volume rm <intern abgeleitetes exaktes volume>
```

Der Aufruf verwendet absoluten Dockerpfad, leeres temporäres CWD, ausschließlich
`LANG=C` und `LC_ALL=C`, keine Shell sowie feste Zeit- und Outputgrenzen.

Force, mehrere Namen, Optionen zur Gruppenauswahl und alternative
Fallbackbefehle sind verboten.

Der Remove wird nie parallelisiert, wiederholt oder mit anderen Ressourcen
gebündelt.

## Verbotene Befehlsformen

Unzulässig sind insbesondere:

- `docker compose down --volumes` und jede Compose-Down-Variante;
- `docker volume prune`, System-Prune und Projektcleanup;
- Force, Wildcard-, Prefix-, Labelgruppen- oder Hostselektion;
- Mount, Export, Dateisystemzugriff, SQL oder Ersatzcontainer;
- manuelles Entfernen, Umbenennen oder Leeren des Volumes;
- Löschung von Backup, Restoreobjekt, Snapshot, Evidence oder Claim;
- Retry mit neuer ID, anderem Scope oder alternativer Dockerform.

Der Operator entfernt kein Image, keinen Container und kein Netz.

## Bestätigung nach dem Remove

Ein erfolgreich beendeter Removeprozess allein ist noch keine finale Evidence.

Der Operator muss anschließend read-only über eine exakte Namensabfrage
bestätigen, dass genau das Zielvolume abwesend ist.

Die Abfrage darf keine Prefix- oder Labelgruppenheuristik verwenden.

Ein weiterhin sichtbares Volume, fremdes gleichnamiges Objekt, malformed
Output, Nonzero, stderr, Timeout, Truncation oder verlorene Ausgabe ist Unknown
Outcome.

Es gibt nach dem Remove keinen zweiten Remove und keine alternative
Bestätigungsabkürzung.

## Unknown Outcome

Ab Start des einzigen mutierenden Dockerprozesses ist jede technische
Mehrdeutigkeit Unknown Outcome.

Der Claim bleibt unverändert vorhanden und finale Evidence wird nicht
erfunden.

Der Operator stoppt ohne Retry, Fortsetzung, Claimfreigabe oder
Erfolgsableitung.

Auch ein Nonzero mit „not found“, „in use“ oder ähnlich interpretierbarem Text
wird nicht als neutraler Zustand vertraut.

stdout und stderr werden nicht als Authority veröffentlicht.

Der einzige technische Folgeweg ist ein separater owner-only read-only
Inspector mit eigener aktueller Autorisierung.

## Keine unmittelbare Wiederholung

Ein erneuter normaler Operatoraufruf trifft auf den offenen Claim und stoppt
vor Docker.

Eine neue Löschautorisierung, neue Claim-ID oder ein neues Zeitfenster darf
einen Unknown Outcome nicht umgehen.

Manuelles `docker volume inspect`, `rm`, Claimlöschen oder Evidenceerstellen
ist keine zulässige Reconciliation.

Wiederaufnahme möglicher Mutation benötigt zuerst finalisierte separate
Reconciliation-Evidence und einen späteren ausdrücklich definierten Vertrag.

LQ-393 definiert keine Continuation.

## Finale private Evidence

Nur nach eindeutig bestätigter Volumeabwesenheit schreibt der Operator finale
private Evidence.

Sie bindet mindestens:

- Schemaversion und Volume-Deletion-ID;
- Claim-ID, Run, Phase, Operation und Scope;
- Source, Image, Compose und exakte Volumeidentität;
- Lösch-, Resolver-, Lineage-, Retention-, Hold- und Recoveryhashes;
- stabile IDs der aktuellen Entscheidungen;
- getrennte Identitäten;
- exakten ausgeführten Remove-Schritt;
- bestätigte exakte Abwesenheitsbeobachtung;
- UTC-Start- und Abschlusszeit;
- kanonischen Ausgang `volume_removed`.

Interne IDs und Ressourcendetails bleiben in der privaten Evidence und werden
nicht öffentlich ausgegeben.

## Atomare Evidenceanlage

Finale Evidence wird owner-only über exklusive Temporäranlage vollständig
geschrieben und geflusht.

Die finale Anlage darf nur atomar erfolgen; danach wird das
Evidenceverzeichnis synchronisiert.

Der Operator liest die finale Datei vollständig zurück und prüft Bindung und
bytegenauen Inhalt, bevor der Claim freigegeben werden darf.

Eine bereits vorhandene abweichende finale Datei wird nie überschrieben.

Teilgeschriebene Temporärdateien sind keine Evidence und kein Erfolg.

## Claimfreigabe nach Evidence

Erst nach erfolgreicher Evidenceanlage und Rücklesung darf ausschließlich der
exakte Volume-Deletion-Claim entfernt werden.

Andere Claims und historische Evidence bleiben unverändert.

Claimfreigabe und Verzeichnissynchronisation gehören zum Abschluss.

Ist der Ausgang der Claimfreigabe mehrdeutig, bleibt die finale Evidence
erhalten und der Operator endet technisch unavailable.

Der exakte Wiederholungsaufruf mit unveränderten Dateien darf dann nur die
Evidence prüfen und die Claimfreigabe wiederholen; Docker bleibt unerreichbar.

## Evidence-Retry

Evidence-Retry verwendet dieselbe Löschautorisierung, Volume-Deletion-ID,
Claim-ID, finale Evidence und sämtliche ursprünglichen Eingabedateien.

Er überspringt LQ-392, Volumeinspektion, Remove und Abwesenheitsprüfung, weil
der Ressourceneffekt bereits durch finale Evidence abgeschlossen ist.

Eine neue ID, neue Autorisierung oder veränderte Evidence ist kein
Evidence-Retry.

Fehlt der Claim bereits, liefert die exakt gebundene Evidence idempotent den
kanonischen Abschluss.

Malformed Evidence oder fremder Claim stoppt fail-closed.

## Geschlossene Ausgänge

Der spätere Operator darf ausschließlich liefern:

- `volume_removed` nach bestätigter Entfernung, finaler Evidence und
  bestätigter Claimfreigabe;
- `rejected`, wenn der frische Preflight fachlich ablehnt und kein Claim
  entsteht;
- `investigation_required`, wenn der frische Preflight diesen Ausgang liefert
  und kein Claim entsteht;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Ein bei Preflight bereits fehlendes Volume ist niemals `volume_removed`.

Unknown Outcome nach möglichem Effekt bleibt technische Nichtverfügbarkeit mit
offenem Claim und ohne finale Evidence.

## Detailarme Ausgabe

Erfolg schreibt ausschließlich kanonische Schemaversion, feste Operation für
PostgreSQL-Volume-Deletion und einen geschlossenen Ausgang.

Run-, Volume-, Claim-, Evidence-, Retention-, Hold-, Recovery-, Identitäts-,
Hash-, Zeit- und Pfaddetails bleiben privat.

Technische Nichtverfügbarkeit liefert keine internen Fehlerdetails.

Konkreter Entry-Point-Name, Argumentliste, Exitcode und Funktionssignatur
werden in diesem Slice nicht festgelegt.

## Retention und Nichtwiederverwendung

Run-, Volume-, Resolver-, Retention-, Hold-, Recovery-, Lösch- und Claim-IDs,
Autorisierungen, finale Evidence und Reconciliationmaterial müssen mindestens
so lange eindeutig unterscheidbar bleiben, wie Audit, Widerruf, Idempotenz,
Evidence-Retry oder Unknown-Outcome-Aufklärung davon abhängen.

Keine ID, Claimdatei, Evidence oder Volumeidentität darf unter neuer Bindung,
anderem Scope oder neuer Bedeutung wiederverwendet werden.

Volumeabwesenheit und Claimfreigabe beenden diese Retention nicht.

Der Vertrag legt keine konkrete Frist, Tabelle oder Ablageform fest.

## Grenzen vollständiger Datenentsorgung

`volume_removed` bestätigt nur die Entfernung des exakten lokalen
Docker-Volumeobjekts im gebundenen Environment.

Backups, Exporte, Snapshots, Replikate, Logs und historische Evidence besitzen
weiterhin eigene Retention- und Dispositionsgrenzen.

Der Operator darf deshalb keinen allgemeinen Ausgang „alle Daten entsorgt“
liefern.

Vollständige Datenentsorgung bleibt eine übergeordnete System-of-Record-
Aussage außerhalb dieses Operators.

## Nichtziele und Bundle

LQ-393 entscheidet keine konkrete JSON-Struktur, Signatur, Exception,
Funktionssignatur, CLI, Timeout-, Claimdatei- oder Evidenceimplementierung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP-, Monitoring-, Test- oder Production-Wiring-
Änderung.

Der Slice implementiert keinen Operator, Claim, Evidencewriter, Inspector,
Finalizer, Reconciliation oder Volume-Remove.

Bundle-Gates bleiben bei 51 Entry Points, 55 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-394 sollte den owner-kontrollierten Evidence-first Volume-Deletion-Operator
gemäß diesem Vertrag implementieren.

Fake-basierte Tests müssen frischen Preflight, exklusive durable Claimanlage,
exakt einen Remove, Abwesenheitsbestätigung, atomare Evidence, Claimfreigabe,
Unknown Outcome und Evidence-Retry ohne echtes Dockerobjekt prüfen.

Read-only Claim-Reconciliation bleibt ein separater späterer Slice.
