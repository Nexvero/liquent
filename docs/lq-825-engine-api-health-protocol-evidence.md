# LQ-825 — Engine API Health Protocol Evidence

## Zustandsevidenz

Initial ist live, aber nicht ready. Serving ist live und ready. Stopping ist live,
aber nicht ready. Stopped und failed sind weder live noch ready.

Für alle Antworten werden Status, exakte Felder, feste Gründe, Content-Type,
Connection-Close und bytegenaue Content-Length geprüft.

## Requestevidenz

Leere, unbekannte, mutierende, nichtkanonische, falsche Host-, Body- und
übergroße Requests scheitern ohne Statusmutation.

## Fehlergrenze

Ein technischer Snapshotfehler mit privatem Detail wird zu einer detailfreien
503-Liveantwort.

## Oberflächenevidenz

Fremde Owner werden abgelehnt. Das Protokoll besitzt keine Listen-, Accept-,
Connect-, Close-, Run- oder Serve-Oberfläche.
