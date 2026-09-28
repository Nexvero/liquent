# LQ-2637 — Staging Installed Artifact Parity

## Ergebnis

Die sieben nicht-sensitiven Betriebsartefakte für Basis-Compose, Prometheus,
Edge-Compose, Edge-Route, Deployment-Bibliothek, Initial-Preflight und
Initial-Bootstrap wurden lokal und auf dem Ziel-VPS mit SHA-256 gelesen. Jeder
lokale Wert stimmt bytegenau mit dem Wert der zugehörigen installierten Datei
unter `/opt/liquent` überein.

Damit ist nicht nur die semantische Online-Prüfung erfolgreich, sondern auch
belegt, dass sie mit demselben Artefaktstand arbeitet, der lokal die
fokussierte Regression bestanden hat. Private Konfigurationen, Zertifikate und
Secrets wurden absichtlich nicht in diese öffentlich beschreibbare
Artefaktmenge aufgenommen.

## Vorher-Zustand

Nach dem Vergleich ist der Ubuntu-nginx weiterhin aktiv und für den Systemstart
aktiviert. Docker meldet null laufende Container und keines der vier
`liquent_*`-Deployment-Netzwerke. Der Vergleich hat weder Ports noch Dienste,
Netzwerke, Volumes oder Daten verändert.

## Grenze

Die Bytegleichheit ersetzt keinen integrierten Git-Stand und keine erneute
Review der noch uncommitteten Operationsänderungen. Sie autorisiert den
Bootstrap nicht selbst und trifft keine Aussage über geheime Dateiinhalte.
Der nächste mutierende Gate bleibt der ausdrücklich bestätigte und
protokollierte Initial-Bootstrap nach dem Integrationscheckpoint.
