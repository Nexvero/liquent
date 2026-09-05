# LQ-797 — Engine API Proxy Settings Source Evidence

## Positive Evidenz

Eine owner-private Datei mit exakt 21 Zeilen liefert den bestehenden
unveränderlichen Settingswert und bewahrt Pfade, Identitäten und Grenzen.

## Dateievidenz

Abweichende Modi, Symlink, Hardlink, Verzeichnis und relativer Pfad scheitern.
Leere, ungültig codierte und übergroße Dateien werden detailfrei abgelehnt.

## Projektionsevidenz

Fehlende, zusätzliche und doppelte Schlüssel sowie Kommentar, Whitespace,
fehlender Abschluss und Mehrfachgleichheit scheitern. Ungültige Feldwerte werden
vom unverändert nachgelagerten Settingsparser verworfen.

Ein gleichnamiger Wert im Process-Environment beeinflusst das Ergebnis nicht.

## Fähigkeitsgrenze

Die Quelle liest genau die explizite Datei und startet weder Composition noch
Proxyprozess.
