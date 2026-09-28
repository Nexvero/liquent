# LQ-839 — Engine API Health Stream I/O Contract

## Ziel

Ein bereits verbundener, extern besessener Stream erhält eine kleine
Single-Message-I/O-Grenze für das geschlossene Healthprotokoll.

## Requestread

Es wird genau bis zum ersten `CRLF CRLF` gelesen. Der vollständige Request ist
höchstens 128 Bytes groß, jeder Read höchstens 64 Bytes.

EOF vor dem Abschluss, leerer oder fremder Chunk, Überschreitung sowie Bytes im
selben Chunk hinter dem Abschluss scheitern fail-closed. Nach exakt erkanntem
Abschluss erfolgt kein weiterer Read.

Die I/O-Grenze interpretiert Methode, Route oder Header nicht; das bleibt beim
LQ-823-Protokoll.

## Responsewrite

Genau eine nichtleere, gerahmte Bytesresponse von höchstens 512 Bytes wird über
beliebig viele positive Partial-Sends vollständig geschrieben.

Null, negative, boolesche, übergroße oder fremde Sendresultate scheitern.

## Ownership und Grenzen

Die Primitive besitzt, verbindet oder schließt den Stream nicht. Kein Listener,
Accept, Peercheck, Protokollaufruf, Thread oder Deployment wird ergänzt.
