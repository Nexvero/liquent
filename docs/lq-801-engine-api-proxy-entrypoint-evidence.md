# LQ-801 — Engine API Proxy Entrypoint Evidence

## Sequenzevidenz

Tests belegen Load, Composition und Run in fester Reihenfolge, objektidentische
Übergabe und genau einen Run.

Fehler in jeder Stufe stoppen die Kette unmittelbar und verlieren private
Details. Fremde, negative, übergroße oder widersprüchliche Serve-Ergebnisse
scheitern fail-closed.

## CLI-Evidenz

Nur genau ein `--settings-file` wird akzeptiert. Fehlender, positionaler oder
zusätzlicher Input endet mit Exitcode 2, ohne Run und ohne stdout/stderr.

Ein erfolgreicher kontrollierter Run endet mit Exitcode 0.

## Fähigkeitsgrenze

Quellenaudit belegt das Fehlen von Environmentdefaults, PlatformSettings,
Appfactory, Datenbank, Compose und Readinessclaim.
