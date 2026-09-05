# LQ-609 — Supervisor Launch Document Integrity Evidence

## Ergebnis

LQ-609 belegt den LQ-608-Typ und Codec deterministisch ohne Datei-, Engine-
oder Containerwirkung.

## Profilnachweis

Writer und Recovery round-trippen jeweils vollständig und kanonisch.

Cross-Profile-Requests scheitern bereits am Domainkonstruktor.

Die Runtime-Container-ID fehlt nachweislich im serialisierten Inhalt.

## Manipulationsnachweis

Unbekannte Runtimefelder, falsche Version, unbekanntes Profil, relative Pfade,
leere Creation-ID und kollidierende Gateartefakt-IDs werden abgelehnt.

Doppelte Keys, nichtkanonische Whitespacebytes, leere und übergroße Inhalte
bleiben detailfrei technisch unverfügbar.

## Digestnachweis

Änderungen an Document, Creation, Handle, Directory, Image, Claim, Owner oder
Scope erzeugen jeweils einen anderen SHA-256.

Damit kann ein späteres Create-Label genau den vollständigen Pre-create-Inhalt
unabhängig verankern.

## Keine Productionevidence

LQ-609 belegt keinen Dockerlabel-, Mount-, UID/GID- oder Wrapperpfad.

Diese Wirkungen bleiben getrennte folgende Slices.

## Nächster Slice

LQ-610 schließt Typ-, Codec-, Architektur- und Regressionsaudit ab.
