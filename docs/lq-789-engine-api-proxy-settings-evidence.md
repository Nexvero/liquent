# LQ-789 — Engine API Proxy Settings Evidence

## Positive Evidenz

Die vollständige exakte Map erzeugt einen unveränderlichen Wert mit Path- und
Integerfeldern. Daemon-UID null bleibt explizit erhalten.

Mutation der ursprünglichen Map nach Parsing verändert den Wert nicht.

## Atomarität

Jeder der 21 Schlüssel wird einzeln entfernt und führt zur Ablehnung. Zusätzliche
Schlüssel sowie Nicht-Stringschlüssel oder -werte scheitern ebenfalls.

## Pfad- und Commandevidenz

Relative, Root-, Parentsegment- und nichtkanonische Pfade, überlappende
Hostpfade, relative Commands, gleiche Commands und trailing Slash werden
abgelehnt.

## Zahlenbereich

Null für positive Identität, negative Daemon-UID, führende Null, Pluszeichen,
boolescher Text, Fließkomma sowie Timeout-, Backlog- und Laufgrenzen außerhalb
des Vertrags scheitern fail-closed.

## Fähigkeitsgrenze

Die Settingsoberfläche enthält kein Environment-, Load-, Reload- oder
Allow-Verfahren und führt kein I/O aus.
