# LQ-395 — Read-only PostgreSQL Volume Deletion Claim Reconciliation Contract

## Zweck

LQ-395 definiert die strikt read-only Reconciliation eines möglichen offenen
LQ-394-Volume-Deletion-Claims nach unbekanntem Ausgang.

Sie klassifiziert Claim, finale Evidence und den aktuellen Zustand genau des
gebundenen Datenvolumes.

Dieser Slice implementiert keinen Command, Dockerzugriff, Claimwrite,
Evidencewrite, Finalizer oder Ressourceneffekt.

## Separate Reconciliation-Authority

Die ursprüngliche Volume-Deletion-Autorisierung gewährt keine zeitlich
unbegrenzte Inspectorauthority.

Ein späterer Inspector benötigt eine neue private owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Volume-Deletion-Reconciliation-ID.

Sie muss mindestens exakt binden:

- Schemaversion und Reconciliation-ID;
- ursprüngliche Volume-Deletion- und Claim-ID;
- ursprüngliche Volume-Disposition-ID;
- Retention-, Legal-Hold- und Recoveryentscheidungs-IDs;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, immutable Image-Referenz und Compose-SHA-256;
- intern abgeleitete exakte Volumeidentität;
- SHA-256 der ursprünglichen Lösch- und Resolverautorisierung;
- Lineage-, Retention-, Hold- und Recoveryhashes;
- Operation exakt Inspektion einer disposable PostgreSQL-Volume-Deletion;
- Scope exakt `data_volume_only`;
- neue getrennte Executor-, Authorizer- und Revieweridentitäten;
- positives aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Volumename, Ausgang, letzten Schritt, Allow-Boolean noch
Dockerargumente.

## Keine neue Löschbefugnis

Die Reconciliation-Autorisierung erlaubt ausschließlich read-only
Zustandsauflösung.

Sie verlängert weder die ursprüngliche Löschautorisierung noch Retention-,
Hold- oder Recoveryclearance.

Ein aktiver oder neuer Hold ändert nicht die historische Frage, ob ein
früherer Remove möglicherweise wirksam wurde; er sperrt jedoch jede spätere
Mutation außerhalb dieses Inspectors.

Membership, Researchpermission, SessionPrincipal, Dockerkontobesitz und
allgemeine Administratorrollen sind keine Reconciliation-Authority.

Kein Inspectorausgang ist ein Delete- oder Claimfreigabeauftrag.

## Historische Löschbindung

Der Inspector lädt die ursprüngliche Löschautorisierung owner-only und prüft
sie strukturell in ihrem damaligen gültigen Zeitkontext.

Volume-Deletion-ID, Claim-ID, Run, Phase, Source, Image, Compose, Volume,
Operation, Scope, Entscheidungs-IDs und alle Hashbindungen müssen exakt der
neuen Reconciliation-Autorisierung entsprechen.

Die ursprüngliche Resolverautorisierung, das Lineage-Manifest sowie die
gebundenen Retention-, Hold- und Recoverydateien werden bytegenau erneut
geprüft.

Historische Gültigkeit beweist nur die ursprüngliche Bindung und gewährt keine
neue Mutation.

Malformed, fremde oder widersprüchliche Ketten sind technische
Nichtverfügbarkeit.

## Aktuelle Inspectoridentitäten

Reconciliation-Executor, -Authorizer und -Reviewer müssen drei verschiedene
aktive Identitäten sein.

Sie müssen von den ursprünglichen Lösch-, Resolver- und fachlichen
Clearance-Identitäten getrennt bleiben.

Eine deaktivierte, widerrufene, fehlende oder widersprüchlich gebundene
Identität stoppt fail-closed.

Der Actor identifiziert den ausführenden Inspector, gewährt aber allein keine
Authority.

Die Identitäten werden bei jedem Aufruf neu aus dem zuständigen System of
Record aufgelöst; es gibt keinen positiven Cache.

## Intern abgeleitete Pfade

Der exakte Claimpfad wird ausschließlich aus dem vollständigen SHA-256 der
ursprünglich gebundenen Claim-ID abgeleitet.

Der finale Evidencepfad wird ausschließlich aus dem vollständigen SHA-256 der
Volume-Deletion-ID abgeleitet.

Projekt und Volume werden aus dem gebundenen Run intern als
`liquent-<run-id>` und `<project>-postgres-data` abgeleitet.

Callerpfade für Claim oder finale Evidence sowie Callerressourcennamen werden
nicht akzeptiert.

Wildcard-, Prefix-, Labelgruppen-, Projekt- und Hostauswahl bleiben
unerreichbar.

## Finale Evidence hat Priorität

Vor jedem Dockerzugriff prüft der Inspector die intern abgeleitete finale
LQ-394-Evidence.

Ist sie vollständig owner-only, atomar und exakt an Authority, Claim, Volume,
Entscheidungen, ausgeführten Einzelschritt, bestätigte Abwesenheit und Ausgang
`volume_removed` gebunden, lautet der read-only Ausgang
`final_evidence_present`.

Dies gilt sowohl bei fehlendem als auch bei noch vorhandenem exakten Claim.

Der Inspector entfernt den Claim nicht und wiederholt keine Claimfreigabe.

Malformed, teilweise, fremde oder anders gebundene Evidence ist technische
Nichtverfügbarkeit und wird nicht ignoriert oder ersetzt.

## Claim- und Evidence-Abwesenheit

Fehlen finale Evidence und der exakt abgeleitete Claim gemeinsam, lautet der
neutrale Ausgang `not_found`.

`not_found` entsteht ohne Dockerzugriff.

Es beweist weder erfolgreiche Volumenlöschung noch unveränderte
Volumeexistenz, weil kein gebundener offener Versuch vorliegt.

Der Inspector erzeugt keinen Claim nachträglich und startet keinen neuen
Preflight.

Ein späterer neuer Löschversuch benötigt vollständig neue aktuelle Authority
und darf `not_found` nicht als Löschclearance verwenden.

## Exakte Claimvalidierung

Nur ein Claim ohne finale Evidence erreicht die Ressourcenbeobachtung.

Der Claim muss regulär, owner-only, einfach verlinkt und kanonisches JSON sein.

Er muss exakt Volume-Deletion- und Claim-ID, Run, Phase, Source, Image,
Compose, Volume, Scope, Operation, sämtliche Authority- und
Entscheidungshashes, ursprüngliche Identitäten und eine gültige
zeitzonenbehaftete Startzeit binden.

Alter, Dateiname, Prozessstatus oder Dockerzustand allein beweist keine
Claimbindung.

Ein fremder, beschädigter, breiter oder widersprüchlicher Claim ist technische
Nichtverfügbarkeit und wird weder überschrieben noch entfernt.

## Strikt begrenzte Dockerbeobachtung

Nach exakter Claimvalidierung darf der Inspector nur den aktuellen Zustand des
intern abgeleiteten Volumes beobachten.

Zuerst erfolgt eine exakte verankerte Namensliste für genau dieses Volume.

Ist das Volume eindeutig vorhanden, folgt genau ein read-only
`docker volume inspect` für denselben intern abgeleiteten Namen.

Der Inspector rendert kein Compose, weil Projekt- und Volumeidentität bereits
geschlossen aus der validierten Authority abgeleitet sind.

Alle Prozesse verwenden absoluten Dockerpfad, temporäres leeres CWD,
`LANG=C`, `LC_ALL=C`, keine Shell sowie feste Zeit- und Outputgrenzen.

## Geschlossene Zustände

Bei offenem exaktem Claim ohne finale Evidence darf der Inspector nur
klassifizieren:

- `volume_present`: Die exakte Namensliste enthält genau das Ziel und Inspect
  bestätigt weiterhin ausschließlich die gebundene Composeprojektzuordnung.
- `volume_absent_evidence_missing`: Die exakte Namensliste ist eindeutig leer.
- `conflict`: Ein vollständig lesbares Volumeobjekt oder Listenzustand ist
  vorhanden, aber nicht exakt der erwarteten Run- und Projektbindung
  zuzuordnen.

Diese Ausgänge beschreiben nur die aktuelle Beobachtung.

Sie beweisen nicht, ob der frühere Remove überhaupt gestartet wurde, welche
Prozessantwort verloren ging oder ob ein konkurrierender externer Effekt
stattfand.

## Bedeutung von volume_present

`volume_present` bedeutet ausschließlich, dass das exakte rungebundene Volume
zum Inspektionszeitpunkt weiterhin vorhanden ist.

Es ist kein Beweis, dass der frühere mutierende Prozess keinen Effekt hatte,
und keine automatische Erlaubnis für einen zweiten Remove.

Der offene Claim bleibt unverändert bestehen.

Eine mögliche spätere Wiederaufnahme benötigt eigene finalisierte
Reconciliation-Evidence, neue aktuelle Authority und einen ausdrücklich
definierten Continuationvertrag.

Der Inspector startet diese Fortsetzung nicht.

## Bedeutung von volume_absent_evidence_missing

`volume_absent_evidence_missing` bedeutet, dass das intern abgeleitete Volume
unter offenem gebundenem Claim aktuell eindeutig abwesend ist, während finale
LQ-394-Evidence fehlt.

Der Ausgang ist noch kein `volume_removed`, weil die Evidence-first-
Abschlussordnung nicht erfüllt ist.

Der Inspector schreibt keine Ersatz-Evidence und gibt den Claim nicht frei.

Ein späterer Finalizer muss die Beobachtung unter eigener aktueller Authority
frisch wiederholen, atomare Evidence schreiben und erst danach den Claim
freigeben.

Backups, Snapshots und andere Datenkopien bleiben außerhalb dieser Aussage.

## Conflict

`conflict` gilt bei vollständig lesbarer Fremd- oder Widerspruchsbindung.

Dazu gehören insbesondere:

- exakter Name mit fremdem Composeprojekt;
- ein eindeutig gelistetes und lesbares Objekt mit fremder Runzuordnung;
- Widerspruch zwischen Name, Labels und Authority;
- möglicher Ersatz des früheren Volumes durch ein neues Objekt unter demselben
  Namen.

Conflict autorisiert weder Übernahme, Umbenennung, Relabeling, Remove,
Evidencewrite noch Claimfreigabe.

## Technische Nichtverfügbarkeit

Malformed Dockeroutput, Nonzero, stderr, Timeout, Truncation, Hard Kill,
I/O-Fehler, unsichere Dateien, Hashabweichung oder technisch mehrdeutige
Authority bleibt detailfrei unavailable.

Unavailable wird nicht als `conflict`, `not_found`, `volume_present` oder
Abwesenheit umgedeutet.

Der Inspector liest keine Docker-Events, Logs oder Prozesshistorie und wertet
keine stderr-Texte wie „not found“ aus.

Technische Nichtverfügbarkeit liefert kein Ergebnisobjekt und benennt in
diesem Vertrag keinen neuen Exceptiontyp.

## Strikte Read-only-Grenze

Der spätere Command darf ausschließlich private Authority-, Claim- und
Evidenceobjekte lesen sowie die exakte Volumenliste und gegebenenfalls genau
ein Volume-Inspect ausführen.

Volume-Remove, Mount, Export, SQL, Compose-Down, Prune, Force, Relabeling,
Claimänderung, Evidencewrite und Dateisystembereinigung bleiben verboten.

Er erzeugt weder Reconciliation-Claim noch Reconciliation-Evidence.

Auch bei finaler Evidence oder bestätigter Volumeabwesenheit wird kein Claim
freigegeben.

Kein Ausgang startet automatisch Inspector, Finalizer, Continuation oder
neuen Löschversuch.

## Detailarme Ausgabe

Ein späterer Inspector darf ausschließlich kanonische Schemaversion, feste
Operation für Volume-Deletion-Reconciliation und einen Ausgang liefern:

- `not_found`;
- `final_evidence_present`;
- `volume_present`;
- `volume_absent_evidence_missing`;
- `conflict`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Run-, Volume-, Claim-, Evidence-, Retention-, Hold-, Recovery-, Identitäts-,
Hash-, Zeit- und Pfaddetails bleiben privat.

Konkreter Entry-Point-Name, Argumentliste, Exitcode und Funktionssignatur
werden in diesem Slice nicht festgelegt.

## Retention und Nichtwiederverwendung

Volume-Deletion- und Reconciliation-ID, Claim, Autorisierungen, finale
Evidence, beobachtete Zustände und sämtliche gebundenen Quellartefakte müssen
mindestens so lange unterscheidbar bleiben, wie Audit, Reconciliation,
Finalisierung, Continuation oder Unknown-Outcome-Aufklärung davon abhängen.

Keine ID, Claimdatei, Evidence oder Volumeidentität darf unter neuer Bindung,
anderem Scope oder neuer Bedeutung wiederverwendet werden.

Beobachtete Abwesenheit oder spätere Claimfreigabe beendet die Retention nicht.

Dieser Vertrag legt keine konkrete Frist, Tabelle oder Ablageform fest.

## Grenzen der Aussage

`volume_absent_evidence_missing` und `final_evidence_present` betreffen nur das
exakte lokale Docker-Volumeobjekt des gebundenen Environments.

Sie treffen keine Disposition für Backups, Exporte, Snapshots, Replikate, Logs
oder historische Evidence.

Der Inspector darf keinen allgemeinen Ausgang „alle Daten entsorgt“ liefern.

Vollständige Datenentsorgung bleibt eine übergeordnete
System-of-Record-Aussage.

## Nichtziele und Bundle

LQ-395 entscheidet keine konkrete JSON-Struktur, Signatur, Exception,
Funktionssignatur, CLI, Docker-argv, Timeout-, Claim- oder
Evidenceimplementierung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP-, Monitoring-, Test- oder Production-Wiring-
Änderung.

Der Slice implementiert keinen Inspector, Claim, Evidencewriter, Finalizer,
Continuation oder Volume-Remove.

Bundle-Gates bleiben bei 52 Entry Points, 56 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-396 sollte den strikt read-only Volume-Deletion-Claim-Inspector gemäß
diesem Vertrag implementieren.

Fake-basierte Tests müssen Evidencepriorität, `not_found`, exakten Claim,
vorhandenes, abwesendes und fremd gebundenes Volume, technische Fehler sowie
die nachweisbare Abwesenheit jedes Writes prüfen.

Finalisierung und mögliche Continuation bleiben separate spätere Slices.
