# LQ-608 — Supervisor Launch Document Types and Codec

## Ergebnis

LQ-608 implementiert `ManifestHandoffSupervisorLaunchDocument` und den
kanonischen Launchdocumentcodec.

## Domainmodell

Das Dokument verwendet ausschließlich bestehende geschlossene IDs, Gate,
Image und Writer-/Recoveryrequests.

Das Gateprofil entscheidet den exakten Requesttyp.

Document-, Creation-, Handle-, Directory-, Claim- und Ownerwerte bleiben
repr-frei.

## Schema

Das eigenständige Schema heißt
`liquent.manifest-handoff-supervisor-launch` und besitzt Version 1.

Es enthält exakt 19 Felder und keine Runtime-Container-ID.

Eine spätere Bedeutungsänderung benötigt eine neue Version.

## Codec

Encode verwendet sortierte Keys, kompakte Separatoren, UTF-8,
ASCII-Escaping und verbotene NaN-Werte.

Decode sperrt unbekannte, fehlende und doppelte Felder.

Alle rekonstruierten Werte laufen erneut durch ihre Domainkonstruktoren.

Nur ein exakt gleicher kanonischer Re-Encode ist gültig.

## Integritätsfacts

Encoded bindet Domainobjekt, begrenzte Bytes, SHA-256 und Byteanzahl.

Die maximale Größe bleibt 65536 Bytes.

Fehler bleiben über die bestehende technische Grenze detailfrei.

## Keine bestehende Signaturänderung

LQ-608 verändert weder LQ-600-Jobdokument noch Engine-, Gate-, Runtime-, Port-
oder Persistenzsignaturen.

Es ergänzt keine Migration.

## Nächster Slice

LQ-609 belegt Profile, Manipulationssperren und Digestbindung.
