# LQ-660 — Canonical Child Launch Anchor Codec

## Ergebnis

Der kanonische Kindanker-Codec bildet eine vollständig typisierte
`ManifestHandoffSupervisorLaunchDocumentExpectation` verlustfrei auf genau
vierzehn geordnete Argumentelemente ab und zurück.

## Encode

Encode akzeptiert ausschließlich den exakten Erwartungstyp und gibt sieben
feste Flag-/Wertpaare zurück.

Werte werden weder normalisiert noch aus alternativen Namen übernommen.

## Decode

Decode akzeptiert ausschließlich ein Tuple mit exakter Länge und exakter
Flagreihenfolge.

Alle Werte werden durch die bestehenden Identifier-, Digest- und Profiltypen
erneut validiert. Fehler verlassen die Grenze ausschließlich als bestehende
detailfreie technische Unverfügbarkeit.

## Sicherheitsgrenzen

NUL, Zeilenumbrüche, leere und überlange Werte werden abgewiesen.

JSON, freie Umgebungsvariablen, caller-gelieferte Optionen und unbekannte
Zusatzfelder sind keine Eingabeform.

Repräsentationen geben keine gebundene Erwartung aus.
