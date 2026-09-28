# LQ-464 — Canonical Control Artifact Codec and Atomic Local File Adapter

## Ergebnis

LQ-464 implementiert die LQ-463-Grenzen als kanonischen JSON-Codec und
atomaren lokalen Fileadapter.

Es gibt weiterhin kein Wrapper-, Service- oder Production-Wiring.

## Kanonisches Schema

Jedes Dokument trägt Schema `liquent.manifest-handoff-control` und Version 1.

Gemeinsame Felder sind Artefakt-ID, Handle, Rolle und Korrelations-ID.

Nur Terminal-Envelope besitzt zusätzlich ein geschlossenes Outcome.

Andere Felder sind unzulässig.

## Kanonisches JSON

Encoding verwendet sortierte Schlüssel, kompakte Separatoren, UTF-8 und
ASCII-Escaping.

NaN und nicht geschlossene Pythonwerte sind ausgeschlossen.

Semantisch identische Dokumente erzeugen byteidentischen Inhalt.

Der Codec berechnet SHA-256 und Bytezahl ausschließlich aus diesen Bytes.

## Striktes Decode

Decode verlangt exakt bekannte Schema- und Versionswerte mit exakten Typen.

Doppelte JSON-Schlüssel werden bereits beim Parsen abgelehnt.

Rolle und Korrelationsklasse bestimmen den konkreten Dokumenttyp.

Unbekannte Rolle, Version, Zusatzfelder oder fehlende Felder scheitern
detailfrei.

## Round-trip-Sperre

Jedes dekodierte Dokument wird erneut kanonisch kodiert.

Nur byteidentischer Round-trip gilt als gültig.

Alternative Whitespace-, Schlüssel-, Unicode- oder Timestampformen werden
nicht tolerant normalisiert.

Beschädigte Bytes werden niemals als neuer gültiger Record repariert.

## Terminal-Outcome

Writer und Recovery werden durch einen geschlossenen Process-Discriminator
getrennt.

Claim-ID, Owner-ID, Kind, UTC-Endzeit, optionaler Dateiname und optionale
Manifestfakten werden verlustfrei rekonstruiert.

Die bestehenden Domainkonstruktoren validieren Kind-/Fakten-/Dateinamenmatrix
erneut.

Der Dokumentkonstruktor prüft zusätzlich denselben Supervisorhandle.

## Begrenzung

Die bestehende 65.536-Byte-Grenze wird vor jedem gültigen Encoded-Record
erneut erzwungen.

Der Reader liest höchstens 65.537 Bytes, um Übergröße sicher zu erkennen.

Leere und übergroße Dateien bleiben technische Unverfügbarkeit.

Dateiinhalte erscheinen nicht in Fehlern oder Repräsentationen.

## Private Rootregistry

Der Adapter erhält ein absolutes privates Root und einen konstruktiv
injizierten Resolver von Control-Directory-ID zu Pfad.

Ein aufgelöster Jobpfad muss direkt unter diesem Root liegen.

Der Request selbst enthält weiterhin keinen Pfad.

Resolverfehler und fremde Pfade scheitern detailfrei.

## Deskriptorauflösung

Das Root wird mit `O_DIRECTORY` und `O_NOFOLLOW` geöffnet.

Das Jobverzeichnis wird ausschließlich relativ zum Rootdeskriptor und ebenfalls
mit `O_NOFOLLOW` geöffnet.

Damit werden weder Root- noch Job-Symlinks verfolgt.

Lexikalische Vorprüfung allein ist keine Sicherheitsannahme.

## Verzeichnisprüfung

Root und Jobverzeichnis müssen echte Verzeichnisse sein.

Beide müssen dem aktuellen effektiven User gehören und exakt Modus 0700
besitzen.

Abweichung wird nicht automatisch korrigiert.

Gruppen- oder Weltzugriff bleibt fail-closed.

## Feste Rollennamen

Die vier Dateinamen sind intern fest auf wrapper-ready, release-token,
release-consumed und terminal-envelope abgebildet.

IDs und Callerstrings werden niemals zu Dateinamen zusammengesetzt.

Traversal und Namenswahl sind ausgeschlossen.

Temporäre Namen entstehen ausschließlich aus internem Zufall.

## Private temporäre Datei

Publish legt eine neue Tempdatei relativ zum geöffneten Jobverzeichnis an.

Es verwendet `O_CREAT`, `O_EXCL`, `O_NOFOLLOW` und Modus 0600.

Der Adapter schreibt alle Bytes vollständig und synchronisiert den
Dateideskriptor.

Ein partieller Write wird niemals als Erfolg behandelt.

## No-replace-Publikation

Die Tempdatei wird über einen atomaren Hardlink unter dem festen Rollennamen
veröffentlicht.

Ein bestehender Rollename wird nie ersetzt oder überschrieben.

Nach erfolgreichem Link wird die Tempdatei entfernt.

Erst danach synchronisiert der Adapter das Verzeichnis und bestätigt Erfolg.

## Concurrent Retry

Gewinnt ein paralleler Publisher denselben Rollennamen, liest der Verlierer
den bereits publizierten Record sicher neu.

Seine Tempdatei wird entfernt und die Bereinigung vor Rückkehr per
Directory-fsync gesichert.

Byteidentischer Inhalt liefert denselben faktischen Erfolg.

Jede Byteabweichung liefert den detailfreien Konflikt.

## Bestehender Record

Vor einer neuen Tempdatei prüft Publish den festen Rollennamen.

Ein existierender byteidentischer Record ist ein exakter Retry ohne Write.

Abweichung ist Konflikt und verändert keine Datei.

Artefakt-ID und Fakten stammen weiterhin aus dem geprüften Requestrecord.

## Sichere Reads

Dateien werden relativ zum Jobverzeichnis mit `O_NOFOLLOW` geöffnet.

Sie müssen regulär sein, dem effektiven User gehören, exakt Modus 0600 und
genau einen Hardlink besitzen.

Symlink, Device, Directory, fremder Owner, falscher Modus oder zusätzlicher
Hardlink sind technische Unverfügbarkeit.

## Reader

Nur `ENOENT` des festen finalen Rollennamens liefert neutral `None`.

Jeder vorhandene Record wird begrenzt gelesen, strikt dekodiert und kanonisch
erneut kodiert.

Die dekodierte Rolle muss der angefragten Rolle entsprechen.

Temporäre Dateien werden nicht als Rollenbestand betrachtet.

## Dateifakten

Der Reader berechnet Fakten über das erneute kanonische Encoding.

Damit passen Bytezahl und SHA-256 exakt zum gelesenen Inhalt.

Persistente LQ-460-Fakten können anschließend ohne Dateipfad korreliert werden.

Der Fileadapter schreibt selbst nicht in die Datenbank.

## Fehlergrenze

Codec-, Resolver-, Open-, Read-, Write-, Link-, Unlink- und fsync-Fehler werden
über die bestehende `ManifestHandoffRegistryUnavailable` vereinheitlicht.

Es werden keine Pfade, IDs, Bytes, Modes oder Betriebssystemdetails ausgegeben.

Der fachliche Artefaktkonflikt bleibt davon getrennt und feldlos.

## Keine Authority

Der Adapter akzeptiert keine Session, User-ID, Permission, Rolle im
Autorisierungssinn oder Allowentscheidung.

Dateibesitz und Modus sind Sicherheitsinvarianten, aber keine
Plattformauthority.

Journal- und Capabilityentscheidungen bleiben in der späteren Composition.

## Keine Prozesswirkung

Der Adapter startet, stoppt oder inspiziert keinen Container.

Er importiert keine Docker-, subprocess-, Socket- oder Shellgrenze.

Ein Control-Artefakt allein autorisiert keinen Prozessstart.

## Kein Cleanup

Finale Rollenartefakte werden niemals gelöscht oder ersetzt.

Nur die eigene unveröffentlichte Tempdatei wird bestmöglich bereinigt.

Retention und owner-kontrolliertes Jobverzeichnis-Cleanup bleiben separat.

## Kein Schema oder Wiring

LQ-464 ändert keine Tabelle, Migration oder bestehende Persistenzsignatur.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Seed, Backfill, CLI-, Route-, Compose-, Wrapper-, Service- oder
Production-Wiring.

## Tests

Fokussierte Prüfungen belegen Schema/Version, exakte Schlüsselmengen,
Duplicate-Key- und Round-trip-Sperre, geschlossene Outcomes, sichere
Deskriptorflags, 0700/0600, vollständigen Write, File-/Directory-fsync,
No-replace-Link, Retryvergleich und fehlende Authority-/Prozessgrenzen.

## Nächster Slice

LQ-465 sollte den geschlossenen Gatewrapper-Vertrag für Ready, Tokenkonsum,
Consumed-Ack und Terminal-Envelope definieren.

Wrapperimplementation und Supervisorservice folgen separat.
