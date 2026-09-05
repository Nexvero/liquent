# LQ-707 — Parent Launch Document Publication Contract

## Ziel

Der Kandidatenparent muss das vollständig gebundene Launchdokument atomar vor
jeder Containeranlage publizieren.

## Autoritative Eingabe

Das Dokument wird ausschließlich aus dem typisierten Preparecommand aufgebaut:

- Launchdokument-ID und Soll-Digest
- Creation-, Handle- und Control-Directory-ID
- Image-Digest und Profil
- vollständige Gatebindung
- bereits journalgebundener Writer- oder Recoveryrequest

Es gibt keinen Callerinhalt, freien Pfad oder Dokument-Fallback.

## Reihenfolge

Die zulässige Prefixfolge lautet:

1. Journalregistrierung
2. Launch-Commit
3. kanonische Dokumentrekonstruktion
4. Soll-Digestvergleich
5. atomare No-replace-Publikation
6. Runtimeauflösung oder Container-Create
7. Gatebindung, Start und direkte Beobachtung

Container-Create darf ohne erfolgreich belegte Publikation nicht aufgerufen
werden.

## Retry und Konflikt

Jeder Retry publiziert denselben kanonischen Inhalt erneut über die bestehende
idempotente Grenze.

Identischer Bestand bleibt wirkungsgleich. Abweichender Digest, Inhalt, ID oder
Publikationsfakt ist ein detailfreier Servicekonflikt und erzeugt keinen Create.

## Eigentümer und Modus

Publisher, Directoryresolver und Control-Artefakte teilen dieselbe Controlwurzel.

Die bestehende Identitypolicy erzwingt Host-Owner-UID, Reader-GID und Modus 0640
bei privatem 0700-Child-Verzeichnis.

## Grenzen

Keine Löschung, Ersetzung, Capabilityausführung, Engine-API-, Compose-, Schema-,
SQL-, Migrations- oder Productionfreigabe.
