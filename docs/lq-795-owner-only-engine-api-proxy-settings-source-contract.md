# LQ-795 — Owner-only Engine API Proxy Settings Source Contract

## Ziel

Ein explizit übergebener privater Dateipfad projiziert genau die 21
Proxysettings, ohne geerbtes Process-Environment oder Defaults zu lesen.

## Dateigrenze

Der Pfad ist absolut und ohne Parentsegment. Die descriptorgebunden geöffnete
Quelle ist eine reguläre Datei des aktuellen effektiven Owners, Modus 0600,
genau ein Hardlink, nicht vererbbar und höchstens 16.384 Bytes groß.

Symlinks werden beim Open abgelehnt. Device, Inode, Modus, Owner, Gruppe,
Linkzahl und Größe müssen vor und nach dem begrenzten Lesen identisch bleiben.

## Projektion

Die Datei enthält exakt 21 fest benannte, präfixierte `KEY=VALUE`-Zeilen in
UTF-8 mit abschließendem Linefeed. Leerzeilen, Kommentare, Exportsyntax,
Duplikate, unbekannte Schlüssel, CRLF, Nullbytes und Mehrfachgleichheit sind
verboten.

Die Werte werden unverändert auf den LQ-787-Parser projiziert. Erst dessen
vollständiger Erfolg liefert einen Settingswert.

## Grenzen

Kein Process-Environment, Secretstore, Reload, Watcher, Entry Point, Start oder
Deployment wird ergänzt. Technische Fehler bleiben detailfrei.
