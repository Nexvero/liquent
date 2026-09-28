# LQ-735 — Engine API Single-Message Stream I/O Contract

## Ziel

Ein bereits verbundener und extern besessener Stream darf genau eine begrenzte
HTTP-Nachricht lesen oder eine bereits freigegebene Nachricht vollständig
schreiben, ohne Listener- oder Connectmacht zu erhalten.

## Reader

Der Reader sucht den Headerabschluss innerhalb von höchstens 16.384 Bytes. Er
akzeptiert ausschließlich keine Bodyrahmung oder genau eine kanonische
Content-Length bis 1.048.576 Bytes.

Nach Erkennung der Länge fordert jeder weitere Read höchstens die noch fehlenden
Bytes an. Bereits im gleichen Chunk überlesene Bytes werden abgelehnt; später
im Stream liegende Bytes werden nicht konsumiert.

EOF, leerer Read, falscher Rückgabetyp, doppelte oder nichtkanonische Länge,
Transfer-Encoding, Übergröße und vorzeitiges Ende scheitern detailfrei.

## Writer

Der Writer akzeptiert ausschließlich einen nichtleeren Byteswert innerhalb der
Gesamtgrenze mit Headerabschluss. Partial Writes werden bis zur vollständigen
Nachricht fortgesetzt.

Nullfortschritt, negativer oder typfalscher Fortschritt und Streamfehler
scheitern detailfrei.

## Ownership

Der Aufrufer besitzt Stream, Timeout und Lebenszyklus. Reader und Writer öffnen,
verbinden, konfigurieren oder schließen nichts.

## Autoritätsgrenze

Stream-I/O autorisiert weder Request noch Response. Im späteren aktiven Prozess
darf Lesen nur vor und Schreiben nur nach der geschlossenen Gatefolge erfolgen.
