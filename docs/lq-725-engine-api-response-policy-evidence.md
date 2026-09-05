# LQ-725 — Engine API Response Policy Evidence

## Positive Matrix

Die Tests decken Find 200, Create 201, Inspect 200, Wait 200, Start 204 sowie
Stop/Kill mit 204 und 304 ab.

Find verlangt eine JSON-Liste. Create, Inspect und Wait verlangen ein
JSON-Objekt. Erfolgreiche JSON-Bodies bleiben bytegenau erhalten.

Inspect 404 wird sowohl aus leerer als auch aus leerer JSON-Objektform auf eine
detailfreie leere Antwort normalisiert.

## Negative Matrix

Für jede der sieben Operationen wird mindestens ein nicht erlaubter
Daemonfehlerstatus mitsamt vertraulichem Beispielbody abgelehnt. Die beobachtbare
Fehlermeldung enthält keine Daemondetails.

Zusätzlich werden falsche oder erweiterte Medientypen, falsche Rootformen,
doppelte Schlüssel, Bodies an leeren Antworten, detaillierte 404-Antworten,
Übergröße und falsche Callertypen geprüft.

## Fähigkeitsgrenze

Ein Oberflächencheck belegt, dass die Policy weder Listener-, Bind-, Connect-,
Request-, Forward- noch Close-Fähigkeit anbietet.

Die Evidenz öffnet deshalb keinen Datenpfad zum Engine-Daemon.
