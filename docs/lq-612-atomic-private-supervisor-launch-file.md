# LQ-612 — Atomic Private Supervisor Launch File

## Ergebnis

LQ-612 implementiert
`AtomicLocalManifestHandoffSupervisorLaunchDocuments`.

## Publikation

Der Adapter verwendet eine zufällige `.pending-launch-*`-Datei mit
`O_EXCL`, `O_NOFOLLOW` und Modus `0600`.

Vollständiger Write, Datei-fsync, No-replace-Link, Pending-Unlink und
Directory-fsync bilden die Erfolgssequenz.

Alle Deskriptoren werden in jedem Ausgang geschlossen.

## Bestehender Bestand

Vorhandene identische Bytes werden kanonisch dekodiert und als derselbe
Published-Nachweis zurückgegeben.

Abweichender Bestand liefert
`ManifestHandoffSupervisorLaunchDocumentConflict`.

Es gibt kein Last-write-wins.

## Read-only Auflösung

Read verwendet ausschließlich die interne Directory-ID und den festen Namen.

Abwesenheit bleibt neutral.

Vorhandener Bestand wird gegen Typ, Owner, Modus, Linkanzahl, Größe und Codec
geprüft.

## Keine UID/GID- oder Mountentscheidung

Die Datei bleibt in diesem Slice host-owner `0600`.

Containerlesbarkeit und read-only Mount folgen separat.

## Nächster Slice

LQ-613 belegt Retry, Konflikt, Race- und Dateisicherheitsgrenzen.
