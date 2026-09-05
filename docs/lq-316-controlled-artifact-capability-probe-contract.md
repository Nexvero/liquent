# LQ-316 — Controlled Artifact Capability Probe Contract

## Zweck

LQ-316 definiert den beobachtbaren Vertrag der ersten bewusst schreibenden
Phase des kontrollierten Research-Worker-Staginglaufs.

Die Phase `artifact_capabilities` weist nach, dass das exakt gebundene
Artifactvolume unter der effektiven Workeridentität die von LQ-296 benötigte
Create-, Fsync-, Link-, Immutable-Publish- und Read-back-Semantik trägt.

Dieser Slice implementiert oder startet noch keine Probe, keinen Container und
keinen Dockerzugriff. Er verändert kein Schema, keine Migration und keinen
Produktport.

## Getrennte Mutationsgrenze

Die Phase ist nicht read-only und darf deshalb weder in eine LQ-311-
Image-/Composeprüfung noch in die LQ-314-Runtime-Inspection eingeschmuggelt
werden.

Sie verlangt eine eigene, bereits validierte LQ-305-Run-Autorisierung und darf
erst nach den statischen sowie rein beobachtenden Runtimephasen beginnen.

Die Autorisierung des Staginglaufs erlaubt nur den hier beschriebenen
temporären Probe-Namensraum. Sie gewährt keine Researchpermission, Membership,
Produktrolle, Artifactreferenz oder allgemeine Schreibfähigkeit.

Ein Phaseaufruf gehört exakt zu einer Run-ID und darf nicht automatisch
wiederholt, parallelisiert oder für einen anderen Lauf wiederverwendet werden.

## Vorbedingungen

Vor dem ersten möglichen Write muss die Composition erneut feststellen:

- das Workerimage entspricht dem unveränderlich autorisierten Digest;
- das gerenderte Composemodell erfüllt weiterhin alle LQ-311-Invarianten;
- genau das deklarierte Artifactvolume ist am festen Artifactziel schreibbar
  eingebunden;
- kein anderes schreibbares Volume oder Bindmount wird mitgegeben;
- Netzwerk, Ports, Secrets, Datenbankzugang und Researchdaten fehlen;
- Rootfilesystem und alle übrigen Mounts bleiben read-only;
- effektive UID und GID sind exakt `10001:10001`;
- der rungebundene Probe-Namensraum ist vor dem Start nachweislich abwesend.

Fehlt eine Vorbedingung, endet die Phase vor Mutation technisch unavailable.
Sie darf keinen bestehenden Namensraum bereinigen oder übernehmen.

## Rungebundener Probe-Namensraum

Der Name wird intern deterministisch aus Run-ID und festem Phasennamen
abgeleitet und enthält keine User-, Workspace-, Job-, Claim- oder Hostidentität.

Er liegt unter einem reservierten, ausschließlich für Stagingproben bestimmten
Prefix außerhalb der regulären LQ-296-Schlüsselgrammatik. Dadurch kann er nie
als Researchartifact interpretiert oder von einem Produktjob referenziert
werden.

Der Aufrufer liefert weder Prefix, Datei-, Verzeichnis- oder temporären Namen
noch Probeinhalt, Digest oder erwarteten Allow-Boolean.

Existiert irgendein Objekt unter dem exakten rungebundenen Prefix bereits,
startet kein Write. Wiederaufnahme und Recovery sind eigene Entscheidungen.

## Feste Capability-Sequenz

Die Probe führt unter der effektiven Workeridentität genau diese monotone
Sequenz aus:

1. reserviertes rungebundenes Verzeichnis exklusiv und owner-only erzeugen;
2. intern feste, nicht geheime kanonische Probebytes in eine exklusive
   owner-only Temporärdatei vollständig schreiben;
3. Dateiinhalt und Verzeichniszustand mit den erforderlichen Fsync-Grenzen
   dauerhaft machen;
4. den finalen Namen durch einen exklusiven Hardlink veröffentlichen, ohne
   vorhandene Ziele zu ersetzen;
5. die Temporärdatei entfernen und den Verzeichniszustand erneut fsyncen;
6. das finale Objekt no-follow öffnen und Typ, Owner, Linkcount und Modus
   prüfen;
7. Größe und SHA-256 durch vollständigen Read-back gegen die intern bekannten
   Probebytes prüfen;
8. einen zweiten Publish auf denselben finalen Namen ausschließlich als
   explizit beobachteten No-overwrite-Nachweis abweisen lassen;
9. nur das selbst erzeugte finale Objekt und sein leeres Probeverzeichnis
   entfernen und die Entfernung dauerhaft bestätigen.

Es gibt kein Rename-overwrite, Truncate, rekursives Löschen, Glob, Listing
fremder Artifacts oder Schreiben in einen regulären Researchschlüssel.

## Erfolg und neutrale Evidence

`artifact_capabilities_valid=true` ist nur zulässig, wenn alle Schritte in
Reihenfolge bestätigt und der rungebundene Prefix am Ende nachweislich
abwesend ist.

Die kanonische Evidence enthält ausschließlich Schema-Version, Phasenname und
dieses Boolean-Faktum. Namen, Pfade, Inhalt, Digest, Ownerwerte, Modi,
Filesystemtyp und einzelne Systemfehler werden nicht ausgegeben.

Eine eindeutig vollständig beobachtete Abweichung der benötigten Semantik
ergibt `artifact_capabilities_valid=false`. Sie ist kein technischer Fehler und
wird vom äußeren Executor als `failed` behandelt.

Die Probe trifft selbst keine Readiness-, Deployment- oder
Produktionsentscheidung.

## Technische Nichtverfügbarkeit

Timeout, Outputverlust, Truncation, Hard Kill, Dockerverlust, uneindeutiger
Create-/Link-/Fsync-/Read-/Remove-Ausgang oder widersprüchliche Metadaten sind
detailfrei technisch unavailable.

Nach dem ersten möglichen Write wird in diesem Fall weder dieselbe Probe
erneut gestartet noch blind Stop, Remove, Unlink oder rekursives Cleanup
ausgeführt. Der möglicherweise verbliebene Prefix ist Recoverybestand des
gebundenen Runs.

Ein späterer Recovery-Schritt muss Run-Bindung, Eigentum und exakte
Prefixidentität unabhängig nachweisen. LQ-316 autorisiert oder implementiert
diesen Schritt nicht.

Ein bestätigter Capability-Mismatch darf nur dann selbst aufräumen, wenn die
Probe weiterhin jeden von ihr erzeugten Descriptor und Namen eindeutig besitzt
und die vollständige Entfernung beobachten kann. Andernfalls ist das Ergebnis
unavailable statt `false`.

## Isolation und Ressourcenbesitz

Eine spätere Containercomposition muss das autorisierte Image ohne Pull,
Shell, PATH-Lookup oder caller-geliefertes Prüfprogramm starten.

Sie verwendet einen kurzlebigen rungebundenen Container mit Auto-Removal,
Netzwerk `none`, read-only Rootfilesystem, `no-new-privileges`, Capability-Drop
`ALL` und festen Ressourcenlimits. Nur das Artifactvolume ist read-write.

Der Inspector besitzt ausschließlich seinen Containerprozess und den exakt
reservierten Probe-Prefix. Docker-Daemon, Image und Artifactvolume bleiben
extern besessen; reguläre Artifacts dürfen weder gelesen noch verändert
werden.

Unknown Outcome rechtfertigt kein `docker volume rm`, Compose-Down, Prune oder
ungebundenes Containercleanup.

## Secret- und Detailgrenze

Die Phase erhält keine Worker-Konfiguration, Worker-ID, Datenbank-URL,
Researchdaten, Environmentdatei, Credential, Artifactinhalt oder
Produktidentität.

Außer LANG/LC_ALL für den äußeren Prozess wird keine geerbte Umgebung benötigt.
stdout und stderr bleiben getrennt und begrenzt; Rohoutput wird nicht
persistiert.

Exceptions, Evidence, `repr` und Operatorausgabe dürfen weder Volume-, Host-
oder Containerpfade noch Probe-Namen oder Betriebssystemdetails offenlegen.

## Nichtziele

LQ-316 entscheidet kein Executable, CLI-Argument, Docker-argv, Timeout, Byte-
Limit, Prefixformat, Probebytesformat oder plattformspezifisches Fsyncverfahren.

Es gibt keine Implementierung, keinen Testcontainer, keinen realen Write,
keinen Cleanupversuch und keine Änderung an Compose, Bundle, Entry Points,
Schema, Tabelle, SQL, Migration, Port, Domainmodell oder Production-Wiring.

## Nächster Slice

LQ-317 sollte das reine in-image Artifact-Capability-Executable implementieren
und seine Dateisystemsequenz vollständig mit injizierten lokalen Grenzen
testen. Die Docker-Composition und ein Recoveryvertrag für unbekannte
Probeausgänge bleiben danach getrennte Slices.
