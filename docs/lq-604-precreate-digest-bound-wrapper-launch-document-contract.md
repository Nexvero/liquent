# LQ-604 — Pre-create Digest-bound Wrapper Launch Document Contract

## Ergebnis

LQ-604 definiert die korrigierte Startbindung als vor Docker Create vollständig
bestimmbares Launchdokument.

Der Slice implementiert noch keine neuen Typen oder Labels.

## Vor Create bestimmbar

Das Launchdokument bindet Document-ID, Creation-ID, Handle,
Control-Directory-ID, Profil und Image-Digest.

Es bindet Gateartefakt- und Observation-IDs, Claim, Owner, Scope, Source,
Target und Handoffname.

Es enthält keine Runtime-Container-ID.

Alle Werte müssen vor dem ersten Engine-Create aus System-of-Record-
Entscheidungen vorliegen.

## Runtime getrennt

Die Docker Runtime-ID entsteht weiterhin erst aus Create.

Der Parent bindet sie atomar an Creation-ID, Handle, Directory, Image und
Profil in der bestehenden Runtimepersistenz.

Der Wrapper behauptet seine Runtime-ID nicht selbst.

Parent und Engine korrelieren Runtimebestand separat.

## Unabhängiger Digest-Anchor

Der kanonische Launchdokumentdigest wird vor Create berechnet.

Docker Create erhält genau diesen Digest und die Document-ID als zusätzliche
konstruktive Labels.

Der Wrapper erhält den erwarteten Digest aus der unveränderlichen
Createkonfiguration, nicht aus dem Dokumentinhalt.

Ein divergentes Dokument scheitert vor Ready.

## Exakte Labelmenge

Die LQ-462- und LQ-591-Labelallowlist muss explizit versioniert erweitert
werden.

Creation, Handle, Directory, Profil, Document-ID und Document-SHA-256 bilden
die vollständige erlaubte Menge.

Unbekannte oder fehlende Labels bleiben Konflikt beziehungsweise technische
Unverfügbarkeit.

## Keine Secrets in Labels

Claim, Owner, Scope, Source, Target und Manifestname werden nicht als Labels
dupliziert.

Labels enthalten keine Session, Authority, Credentials oder Pfade.

Der Digest offenbart keinen Dokumentinhalt.

## Kanonischer Inhalt

Schema, Version, exakte Schlüssel, Duplicate-Key-Sperre und Byte-Roundtrip
bleiben wie LQ-600.

Der Launchdocumenttyp ist getrennt vom heutigen runtimegebundenen
Parentdokument zu benennen.

Eine stille Bedeutungsänderung von Version 1 ist verboten.

## Retry

Create-Retry verwendet dieselbe Creation-ID, Document-ID und denselben Digest.

Ein vorhandener Container wird nur bei vollständiger Label-, Image-, Profil-
und Sicherheitsübereinstimmung adoptiert.

Ein anderer Dokumentdigest führt zu Konflikt und niemals zu zweitem Create.

## Authority

Der Digestanchor ist Integritätsbindung, keine fachliche Authority.

Aktuelle Release-, Terminate-, Claim- und Ownerentscheidungen bleiben beim
Parent und im System of Record.

## Nächster Slice

LQ-605 definiert die private lesbare, aber für den Container unveränderliche
Datei- und Mountownershipgrenze.
