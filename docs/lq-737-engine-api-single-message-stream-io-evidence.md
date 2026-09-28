# LQ-737 — Engine API Single-Message Stream I/O Evidence

## Leseevidenz

Die Tests lesen fragmentierte Header und Bodies vollständig und bytegenau. Der
letzte Read wird auf die exakt fehlende Bytemenge begrenzt; nachfolgende
simulierte Pipelinedaten verbleiben unangetastet.

Bodylose Nachrichten enden am Headerabschluss. Bereits mitgelesener Suffix,
doppelte oder führend genullte Content-Length, Chunking, EOF vor Sollende,
Übergröße und ein nicht terminierter übergroßer Header werden abgelehnt.

## Schreibevidenz

Mehrere Partial Writes erzeugen exakt die ursprüngliche Nachricht. Null-,
Negativ- und typfalscher Fortschritt scheitern fail-closed.

Weder erfolgreicher noch fehlerhafter Betrieb schließt den extern besessenen
Stream.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Listen, Bind, Accept, Connect, Settimeout oder
Close. Streamausnahmen bleiben detailfrei.

Die Evidenz erteilt keine Request-, Response- oder Forwardingautorität.
