# LQ-319 — Controlled Artifact Probe Recovery Contract

## Zweck

LQ-319 definiert den beobachtbaren Recoveryvertrag für einen technisch
unbekannten Ausgang der LQ-318-Phase `artifact_capabilities`.

Recovery darf ausschließlich einen möglicherweise verbliebenen, exakt
rungebundenen LQ-317-Probe-Prefix klassifizieren und gegebenenfalls gezielt
entfernen. Sie wiederholt die Capability-Probe nicht und entscheidet keine
Stagingreadiness.

Dieser Slice implementiert keinen Inspector, Cleanup-Command, Container oder
realen Volumezugriff.

## Eigene Recovery-Autorisierung

Die ursprüngliche Staging-Run-Autorisierung erlaubt keinen späteren
Cleanupversuch. Recovery verlangt eine neue owner-only, zeitlich begrenzte und
ausdrücklich auf genau einen unbekannten Probeausgang bezogene Autorisierung.

Sie bindet mindestens:

- eine stabile opake Recovery-ID;
- die ursprüngliche Run-ID und Phase `artifact_capabilities`;
- Source-Commit, autorisierten Image-Digest und Compose-SHA-256 des Runs;
- den daraus intern reproduzierbaren 64-Hex-Run-Token;
- getrennte Recovery-Executor- und Autorisiereridentitäten;
- ein enges UTC-Gültigkeitsfenster;
- ausschließlich die Operation `inspect`, danach optional `remove_exact`.

Executor und Autorisierer müssen verschieden sein. Production, Wildcards,
freie Prefixe, Volume-Namen, Pfade, Dateinamen, erwartete Allow-Booleans und
allgemeine Cleanuprechte sind unzulässig.

Recovery ist keine Produktrolle, Membership, Researchpermission oder
übertragbare Artifactfähigkeit.

## Erneute Run-Bindung

Vor jedem Volumezugriff werden ursprüngliche Autorisierung, aktueller
Recoveryauftrag, Composefile und Environmentdateien über dieselben owner-only
Grenzen erneut geladen.

Source-Commit, Image-Digest, Composehash, Projektnamen und der intern
abgeleitete Token müssen exakt zur ursprünglichen Run-Bindung passen.

Das Composemodell wird erneut gerendert. Der Worker muss weiterhin genau ein
benanntes Artifactvolume am festen Ziel `/var/lib/liquent/artifacts` besitzen.
Der Recovery-Aufrufer darf keinen Volume-Namen oder Hostpfad präsentieren.

Jede Abweichung endet vor Containerstart technisch unavailable. Recovery darf
kein ähnlich benanntes Projekt, Volume, Image oder Prefix als Ersatz wählen.

## Zwingende read-only Inspektion

Der erste Recoverycontainer mountet ausschließlich das gebundene
Artifactvolume read-only. Rootfilesystem, Netzwerk, Capabilities,
Runtimeidentität und Ressourcenlimits bleiben mindestens so eng wie in
LQ-318.

Er erhält keine Secrets, Datenbank, Worker-Konfiguration, Worker-ID,
Researchdaten, Ports oder Produktidentitäten.

Der Inspector öffnet Root und den exakten Prefix descriptor-relativ und
no-follow. Er listet weder reguläre Artifactbereiche noch durchsucht er das
Volume nach ähnlichen Namen.

Ohne eine vollständig erfolgreiche read-only Klassifikation darf kein
read-write Container gestartet werden.

## Geschlossene Klassifikation

Die Inspektion kennt genau vier interne Ergebnisse:

1. `absent`: der exakte Prefix ist nachweislich nicht vorhanden;
2. `recoverable`: der Prefix und sämtliche vorhandenen Kindobjekte entsprechen
   exakt einem zulässigen LQ-317-Zwischenzustand;
3. `conflict`: der Prefix ist vorhanden, aber nicht vollständig als
   ausschließlich LQ-317-eigener Bestand beweisbar;
4. `unavailable`: Abwesenheit, Bestand oder Metadaten sind technisch nicht
   eindeutig beobachtbar.

Außerhalb der Recoverygrenze werden nur detailarme Statuswerte und keine
Objekt-, Pfad- oder Metadatendetails sichtbar.

## Zulässige Zwischenzustände

`recoverable` verlangt ein echtes Verzeichnis mit effektivem Owner 10001 und
Modus 0700 unter dem exakt abgeleiteten Prefix.

Es dürfen ausschließlich die festen LQ-317-Namen `.capability.tmp` und
`capability.json` vorhanden sein, einzeln oder gemeinsam entsprechend einer
erreichbaren monotonen Sequenzposition.

Jede vorhandene Datei muss regulär, no-follow geöffnet, Owner 10001, Modus
0600 und in Linkcount, Größe, vollständigem Inhalt sowie SHA-256 exakt an die
festen nicht geheimen LQ-317-Probebytes gebunden sein.

Ein leerer Prefix ist ebenfalls recoverbar. Er kann nach erfolgreichem Create
oder nach bestätigter Entfernung der letzten Datei verblieben sein.

Symlink, Unterverzeichnis, Socket, Device, fremder Owner, breiter Modus,
unbekannter Name, zusätzliche Datei, abweichender Inhalt, unerwarteter
Linkcount oder regulärer Researchschlüssel ergibt `conflict`, niemals
Cleanupberechtigung.

## Abwesenheit

`absent` ist ein neutraler bereits bereinigter Ausgang. Er erzeugt keinen
zweiten Cleanupcontainer und beweist weder den früheren Probe-Erfolg noch
`artifact_capabilities_valid=true`.

Die ursprüngliche Stagingphase bleibt `unavailable`. Recovery darf Evidence
nicht nachträglich in `passed` oder `failed` umschreiben.

Eine exakte technische Wiederholung derselben Recovery-ID darf erneut
`absent` feststellen, ohne Mutation oder Ersatz-ID.

## Getrennte Remove-Entscheidung

Nur `recoverable` erlaubt unter derselben unveränderten Recoverybindung einen
zweiten, bewusst schreibenden Container.

Dieser Container revalidiert unmittelbar nach dem read-write Mount noch einmal
Prefix, vollständige Namensmenge, Typ, Owner, Modus, Linkcount, Größe, Inhalt
und Digest. Die frühere read-only Klassifikation ist kein caller-supplied
Delete-Ticket.

Erst bei exakter Übereinstimmung entfernt er in fester Reihenfolge ausschließlich
die vorhandenen bekannten Probe-Dateien, fsynct das Probeverzeichnis, entfernt
das danach leere exakte Prefixverzeichnis, fsynct das Volumeroot und bestätigt
die Abwesenheit.

Es gibt kein rekursives Löschen, Glob, Rename, Truncate, Quarantäneverschieben,
Volume-Remove, Compose-Down, Prune oder Zugriff auf reguläre Artifacts.

## Race- und Unknown-Outcome-Grenze

Jede Änderung zwischen read-only Inspektion und write-time Revalidierung stoppt
vor dem ersten Unlink unavailable.

Nach dem ersten möglichen Remove-Effekt sind Timeout, Outputverlust,
Truncation, Hard Kill, Dockerverlust, Fsync-Fehler oder uneindeutiger
Abwesenheitsnachweis ein neuer Unknown Outcome.

Es folgt kein automatischer Retry, kein dritter Container und kein blindes
Restcleanup. Derselbe stabile Recoveryfall muss später erneut von read-only
beginnen und darf nur die dann vollständig beobachtete Realität klassifizieren.

Ein `conflict` wird niemals automatisch „repariert“. Er verlangt separate
manuelle Securitybewertung außerhalb dieses Vertrags.

## Ergebnis und Evidence

Recovery darf ausschließlich detailarme neutrale Fakten ausgeben:

- `already_absent` nach bestätigter read-only Abwesenheit;
- `removed` nach vollständig bestätigter exakter Entfernung;
- `conflict` ohne Bestandsdetail;
- technisch `unavailable` ohne Ergebnisobjekt.

`already_absent` und `removed` bedeuten nur, dass kein exakter Probe-Prefix
mehr nachgewiesen ist. Sie erteilen keine Artifactfähigkeit, Readiness oder
Deploymentfreigabe.

Evidence bindet Recovery-ID, ursprünglichen Run, Source-/Image-/Composewerte,
Inspektionszeit, getrennte Identitäten und den neutralen Ausgang. Token,
Volume-Name, Prefix, Dateien, Inhalte, Digests und Systemfehler bleiben intern.

Ein Evidenceziel muss privat, exklusiv, atomar und nicht überschreibbar sein.

## Retention und Nichtwiederverwendung

Recovery-ID, ursprüngliche Run-Bindung und finales neutrales Evidence müssen
mindestens so lange unterscheidbar bleiben, wie Audit, technische Wiederholung
oder Interpretation der ursprünglichen unavailable Phase darauf angewiesen
sind.

Eine Recovery-ID darf nie einem anderen Run, Token, Volume oder Ausgang neu
zugeordnet werden. Der Vertrag legt keine konkrete Frist, Tabelle oder
Archivierungsstrategie fest.

## Nichtziele

LQ-319 entscheidet keine Datei- oder JSON-Signatur, CLI, Executablenamen,
Docker-argv, Timeoutzahl, Evidence-Dateinamen, Persistenztabelle oder
Operator-Credentialquelle.

Es gibt keine Implementierung, keinen Testcontainer, keinen realen Inspect-
oder Remove-Zugriff und keine Compose-, Bundle-, Entry-Point-, Schema-, SQL-,
Migration-, Port-, Domainmodell-, Produkt- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-320 sollte das reine read-only In-Image-Recovery-Inspection-Executable mit
geschlossener Klassifikation implementieren. Der bewusst schreibende
Remove-Command, seine Docker-Composition und owner-only Operatorgrenze bleiben
danach getrennte Slices.
