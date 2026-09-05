# LQ-601 — Atomic Private Supervisor Job Document Handoff

## Ergebnis

LQ-601 implementiert `AtomicLocalManifestHandoffSupervisorJobDocuments`.

## Fester Name

Die einzige Datei heißt `job-binding.json`.

Ein Request kann weder Namen noch Pfad oder Modus auswählen.

Der aktive Directoryresolver bindet die interne Directory-ID an genau ein
direktes Kind des privaten Roots.

## Atomare Publikation

Neue Bytes werden in einer privaten exklusiven Pending-Datei vollständig
geschrieben und fsync-synchronisiert.

Ein No-replace-Hardlink publiziert den finalen Namen atomar.

Die Pending-Datei wird danach entfernt und das Directory synchronisiert.

Es gibt kein Rename-overwrite oder Last-write-wins.

## Retry und Konflikt

Vorhandene identische Bytes liefern stabil denselben Published-Nachweis.

Abweichende Bytes liefern ausschließlich den feldlosen Jobdocumentkonflikt.

Der bestehende Inhalt bleibt unverändert.

## Sicheres Lesen

Neutrale Dateiabwesenheit liefert `None`.

Vorhandener Bestand muss regulär, ownerkontrolliert, `0600`, einfach verlinkt
und zwischen 1 und 65536 Bytes groß sein.

Symlink-, Modus-, Größen- und Decodefehler sind technische Unverfügbarkeit.

## Keine Cleanupfähigkeit

Der Adapter besitzt nur Publish und Read.

Er entfernt oder ersetzt kein finales Jobdokument.

Retention folgt dem getrennten Control-Directory-Lifecycle.

## Tests

Direkte Tests belegen beide Profile, kanonischen Roundtrip, Cross-Profile-
Sperre, Manipulationsablehnung, atomare Publikation, stabilen Retry,
wirkungslosen Konflikt und sichere Abwesenheit.

## Nächster Slice

LQ-602 führt den Abschlussaudit gegen bestehende Control-, Gate- und
Architekturgrenzen aus.
