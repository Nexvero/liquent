# LQ-611 — Atomic Private Pre-create Launch File Contract

## Ergebnis

LQ-611 definiert die unveränderliche lokale Dateiübergabe für das kanonische
LQ-608-Launchdokument.

## Fester Name und Ort

Die Datei heißt ausschließlich `launch-binding.json`.

Sie liegt direkt im aktuell aufgelösten privaten Control-Directory.

Requests enthalten weder Dateiname noch Hostpfad oder Modus.

## Vor Create

Die Publikation muss vor dem ersten Docker Create abgeschlossen sein.

Document-ID, Creation-ID und Digest stehen danach unveränderlich für den
späteren Labelanchor bereit.

Dieser Slice verdrahtet die Reihenfolge noch nicht in Prepare.

## Atomare No-replace-Wirkung

Bytes werden vollständig in eine private exklusive Pending-Datei geschrieben
und fsync-synchronisiert.

Ein No-replace-Link publiziert den finalen Namen.

Bestehender Inhalt wird niemals durch Rename oder Replace überschrieben.

## Retry und Konflikt

Identische vollständige Bytes liefern stabil denselben Published-Nachweis.

Abweichende Bytes liefern einen feldlosen Konflikt.

Der ursprüngliche Inhalt bleibt unverändert.

## Sichere Dateifakten

Root und Directory werden symlinkfrei über Deskriptoren geöffnet.

Das Directory muss ownerkontrolliert und `0700` sein.

Das Launchfile muss regulär, ownerkontrolliert, `0600`, einfach verlinkt und
zwischen 1 und 65536 Bytes groß sein.

## Lesen

Belegte Abwesenheit liefert neutral `None`.

Vorhandene Bytes werden begrenzt gelesen und vollständig kanonisch dekodiert.

Unsichere oder beschädigte Fakten bleiben technische Unverfügbarkeit.

## Keine Löschfähigkeit

Der Adapter besitzt nur Publish und Read.

Cleanup, Replace und Retention sind keine Launchfilefähigkeit.

## Nächster Slice

LQ-612 implementiert diese atomare private Grenze.
