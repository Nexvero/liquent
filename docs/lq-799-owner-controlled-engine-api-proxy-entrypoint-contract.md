# LQ-799 — Owner-controlled Engine API Proxy Entrypoint Contract

## Ziel

Ein separater Prozesseinstieg verbindet exakt einmal die owner-only
Settingsquelle, die vollständige Proxycomposition und deren signalbesessenen
Run.

## Eingabe

Der Prozess akzeptiert ausschließlich den expliziten Pflichtparameter
`--settings-file` mit einem Pfad. Es gibt keinen Default, Environmentfallback,
zweiten Settingspfad oder interaktive Eingabe.

## Reihenfolge

Load muss vollständig erfolgreich sein, bevor Composition beginnt. Composition
muss vollständig erfolgreich sein, bevor Run beginnt. Jede Stufe wird genau
einmal aufgerufen und reicht ihre konkrete Objektinstanz an die nächste weiter.

## Ergebnis

Nur ein typisierter Serve-Abschluss mit `stopped` oder `exchange_limit` und einer
zur Settingsgrenze passenden nichtnegativen Austauschzahl ist erfolgreich.

Der CLI-Prozess liefert dann Exitcode 0. Argument-, Load-, Composition-, Run-
oder Ergebnisfehler liefern detailfrei Exitcode 2 und keine Ausgabe.

## Grenzen

Kein Process-Environment, Logging, Health, Daemonisierung, Retry, Deployment
oder automatische Control-Plane-Kopplung wird ergänzt.
