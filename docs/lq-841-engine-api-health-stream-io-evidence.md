# LQ-841 — Engine API Health Stream I/O Evidence

## Readevidenz

Fragmentierte und einteilige Requests werden exakt bis zum Abschluss gelesen.
Nach vollständigem einteiligen Request bleibt ein weiterer vorbereiteter Chunk
ungelesen.

EOF, leerer Chunk, unvollständige Maximalnachricht und Zusatzbytes im selben
Chunk scheitern.

## Writeevidenz

Eine Response wird über kleine Partial-Sends bytegenau vollständig geschrieben.
Leere, ungerahmte, übergroße und Nicht-Bytesresponses werden abgelehnt.

Null, negative, boolesche und die Restlänge überschreitende Sendresultate sowie
fehlende Streams scheitern fail-closed.

## Oberfläche

Die Primitive besitzt keine Close-, Connect-, Listen-, Accept-, Protocol- oder
Owneroberfläche.
