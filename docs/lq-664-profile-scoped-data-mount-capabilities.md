# LQ-664 — Profile-scoped Data Mount Capabilities

## Ergebnis

Der Engine-Create-Vertrag trägt jetzt die vollständig typisierte registrierte
Scopebindung bis zur geschlossenen Dockergrenze.

## Parent und Engine

Alter und neuer Preparepfad verwenden ausschließlich die Binding des bereits
geprüften Journalregistrierungsrequests.

Create- und Created-Werte bewahren diese Bindung repr-frei. Der Dockeradapter
übersetzt sie in genau zwei nicht caller-konfigurierbare Pfadwerte.

## Docker Create

Zusätzlich zu Control- und Launchmount entstehen:

- Writer: `/run/liquent/source:ro` und `/run/liquent/target:rw`
- Recovery: nur `/run/liquent/target:ro`

Der Containerroot bleibt read-only und alle bisherigen Netzwerk-, Privilegien-,
Capability- und Restartgrenzen bleiben unverändert.

## Docker Inspect

Inspect rekonstruiert Source und Target ausschließlich aus einer exakt passenden
Bindliste.

Unbekannte Reihenfolge, falscher Modus, zusätzliche Fähigkeit oder fehlendes
Verzeichnis bleibt detailfreie technische Unverfügbarkeit.

Die Engine projiziert die beobachteten Pfade typisiert und vergleicht sie beim
Create-Retry mit derselben Scopebindung.
