# LQ-600 — Supervisor Job Document Types and Codec

## Ergebnis

LQ-600 implementiert `ManifestHandoffSupervisorJobDocument` und den
kanonischen Version-1-Codec.

## Typbindung

Das Domainobjekt verlangt die bestehenden geschlossenen Gate-, Runtime-,
Image- und Requesttypen.

Das Gateprofil bestimmt zwingend den Writer- oder Recoveryrequesttyp.

Alle internen Werte bleiben repr-frei.

## Codec

Der Codec serialisiert exakt 20 geschlossene Felder mit sortierten Keys,
kompakten Separatoren, ASCII-sicherem UTF-8 und verbotenen NaN-Werten.

Decode verlangt exaktes Schema, exakte Version, exakte Schlüssel und
eindeutige JSON-Keys.

Alle Domainkonstruktoren validieren die dekodierten Werte erneut.

Ein Byte-Roundtrip muss exakt denselben kanonischen Inhalt erzeugen.

## Integrität

Encoded bindet Dokument, begrenzte Bytes, SHA-256 und Byteanzahl.

Manipulierte Facts oder divergente Re-Encodes scheitern fail-closed.

Technische Fehler verwenden die bestehende detailfreie Unverfügbarkeit.

## Kein bestehendes Rollenwachstum

Die vier bestehenden Control-Artefaktrollen bleiben unverändert.

Das Jobdokument ist eine separate Startbindung und kein Ready-, Release-,
Consumed- oder Terminalartefakt.

## Keine Persistenzänderung

LQ-600 ergänzt keine Tabelle, Migration, SQL- oder Portsignatur.

Head bleibt `20260826_0042`.

## Nächster Slice

LQ-601 implementiert die atomare private No-replace-Übergabe.
