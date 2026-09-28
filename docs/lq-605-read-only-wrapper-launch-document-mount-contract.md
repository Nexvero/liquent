# LQ-605 — Read-only Wrapper Launch Document Mount Contract

## Ergebnis

LQ-605 definiert die getrennte Datei- und Mountgrenze für das LQ-604-
Launchdokument.

## Zwei Mountfähigkeiten

Das Launchdokument wird als einzelne Datei read-only in den Container
gebunden.

Ready-, Release-, Consumed- und Terminalartefakte verwenden einen getrennten
begrenzten read-write Control-Mount.

Der Wrapper kann das Launchdokument weder ersetzen noch entfernen.

## Hostownership

Der Parent erzeugt das Launchdokument atomar und no-replace vor Docker Create.

Owner-UID, Reader-GID, Directorymodi und Dateimodus werden als gemeinsame
process-owned Policy konstruktiv festgelegt.

Es gibt keinen chmod/chown aus Requestwerten.

## Containeridentity

Der feste Containeruser muss mit der Readerentscheidung übereinstimmen.

Numerische UID und GID werden gemeinsam validiert und ohne Namenauflösung an
Docker übergeben.

Ein beliebiger konfigurierbarer Userstring ist für Production nicht
ausreichend.

## Minimale Lesbarkeit

Nur die konkrete Launchdatei erhält die erforderliche Readerfähigkeit.

Andere Hostdateien und Parentsecrets bleiben unzugänglich.

Der read-write Artifactmount enthält keine Datenbank-, Socket- oder
Credentialdatei.

## Mountsicherheit

Sourcepfade müssen absolut, ownerkontrolliert, symlinkfrei und direkt unter
dem privaten Root aufgelöst sein.

Das Launchfile muss regulär, einfach verlinkt, größenbegrenzt und nach
Publikation unverändert sein.

Docker Create setzt den Launchbind explizit read-only.

## Wrapperprüfung

Vor Ready liest der Wrapper höchstens die feste Bytegrenze.

Er prüft Dateifakten, kanonischen Decode, Document-ID und den unabhängig
injizierten erwarteten SHA-256.

Er vergleicht Creation, Handle, Directory, Profil und Image mit seiner festen
Createbindung.

Erst danach darf Ready publiziert werden.

## Keine Schreibfallbacks

Der Wrapper kopiert oder normalisiert das Launchdokument nicht.

Fehlende Lesbarkeit löst keinen chmod-, chown-, Remount- oder
World-readable-Fallback aus.

Der Parent publiziert kein stellvertretendes Ready.

## Cleanup

Shutdown entfernt weder Launchdocument noch Control-Directory.

Retirement und Retention bleiben getrennte persistente owner-kontrollierte
Entscheidungen.

## Nächster Slice

LQ-606 schließt den Loaderblockerentscheid und legt die sichere
Implementierungsreihenfolge fest.
