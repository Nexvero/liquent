# LQ-599 — Wrapper-bound Supervisor Job Document Contract

## Ergebnis

LQ-599 definiert das unveränderliche Jobdokument, das genau einen gebundenen
LQ-596-Wrapper vor jeder Capabilitywirkung versorgt.

## Vollständige Bindung

Das Dokument bindet Document-ID, Handle, Control-Directory, Profil,
Runtime-Container-ID und Image-Digest.

Es bindet außerdem Ready-, Consumed- und Terminal-Artefakt-ID sowie Gated- und
Terminal-Observation-ID.

Claim, Owner, Scope-ID, Source, Target und Handoffname sind Bestandteil
desselben kanonischen Inhalts.

## Zwei Profile

Writer akzeptiert ausschließlich Execution-Claim und Execution-Owner.

Recovery akzeptiert ausschließlich Recovery-Claim und Recovery-Owner.

Cross-Profile-Dokumente sind ungültig.

Cleanup oder freie Capabilitynamen sind ausgeschlossen.

## Keine Authority

Das Dokument enthält keine Session, Rolle, Permission oder Allowentscheidung.

Claim und Owner sind Bindungsfakten und keine allgemeine Authority.

Aktuelle Release- und Terminateentscheidungen bleiben im System of Record.

## Pfadgrenze

Source und Target stammen aus der bereits validierten Scopebindung.

Sie sind absolute lexikalisch getrennte Pfade.

Der Wrapper erhält keine frei ergänzten Mounts oder Arbeitsverzeichnisse.

## Kanonizität

Das Format besitzt festes Schema, Version 1, exakte Schlüssel, UTF-8 und
kanonische JSON-Bytes.

Doppelte, unbekannte oder fehlende Felder scheitern fail-closed.

Der vollständige Byteinhalt besitzt SHA-256- und Bytelängenfakten.

## Unveränderlichkeit

Pro Control-Directory existiert höchstens ein `job-binding.json`.

Ein identischer Retry darf denselben Nachweis liefern.

Abweichender Bestand ist detailfreier Konflikt und wird nicht überschrieben.

## Private Übergabe

Die Übergabe erfolgt nur im bereits aktiven privaten Control-Directory.

Datei und Verzeichnis müssen ownerkontrolliert, regulär und ohne Symlinkpfad
sein.

Der Caller liefert keinen Dateinamen oder Hostpfad.

## Keine Parent-Umstellung

LQ-599 ändert noch keinen Prepare-, Release- oder Terminalservice.

Es aktiviert keinen Wrapperentrypoint, Docker-Socket oder Productiongraphen.

## Nächster Slice

LQ-600 implementiert geschlossene Typen und den kanonischen Codec.
