# LQ-831 — Engine API Health Settings Source Contract

## Ziel

Die neun Health-Socket-Authority-Fakten werden als separate atomare Gruppe aus
einer expliziten owner-only Datei geladen.

## Mapping

Der Authorityparser akzeptiert ausschließlich ein echtes Dictionary mit exakt
neun Stringschlüsseln und Stringwerten. Es gibt keine Defaults, Teilgruppen,
Zusatzschlüssel oder Mischung mit den 21 Proxysettings.

Pfade bleiben bytegenau kanonisch. Zahlen sind kanonische positive ASCII-
Dezimalwerte ohne Vorzeichen, Whitespace oder führende Null und bleiben in ihren
bereits geschlossenen Authoritybereichen.

## Datei

Die Quelle ist eine reguläre Datei des effektiven Owners, Modus 0600, genau ein
Hardlink, No-follow, Close-on-exec und höchstens 8.192 Bytes groß. Descriptorfakten
müssen vor und nach begrenztem Read stabil bleiben.

Sie enthält exakt neun feste präfixierte `KEY=VALUE`-Zeilen. Kommentare,
Leerzeilen, CRLF, Nullbytes, Duplikate und unbekannte Namen sind verboten.

## Grenzen

Kein Process-Environment, Proxysettings-Merge, Listener, Composition oder
Deployment wird ergänzt.
