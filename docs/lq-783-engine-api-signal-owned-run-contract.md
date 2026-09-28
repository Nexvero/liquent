# LQ-783 — Engine API Signal-Owned Run Contract

## Ziel

Die explizite Signal-Stopquelle und der vollständig besessene endliche
Prozesslauf werden in eine feste Install-Run-Finally-Restore-Operation gebunden.

## Reihenfolge

Die konkrete Stopquelle wird genau einmal installiert. Erst nach bestätigter
Installation wird ihre gebundene `requested`-Methode unverändert an den Owned
Process Run übergeben.

Der Process Run besitzt weiterhin Dependency- und Vollpreflight, Listener,
Serve-Loop und Retire. Die obere Operation greift nicht in diese Ownership ein.

Nach Rückkehr oder Fehler des Process Run wird die Signalquelle genau einmal
wiederhergestellt.

## Fehlersemantik

Ein Installfehler besitzt kein Restoreziel und ruft den Process Run nicht auf.

Jeder Post-Install-Fehler führt zu Restore. Ein Restorefehler nach erfolgreichem
Run verhindert Erfolg, weil der globale Signalzustand nicht bestätigt ist.

Gleichzeitiger Run- und Restorefehler bleibt eine einzige detailfreie technische
Nichtverfügbarkeit. Es gibt keinen Retry.

## Ergebnis

Nur ein echtes unverändertes ServeResult des Process Run darf nach erfolgreichem
Restore zurückgegeben werden.

## Grenzen

Kein Main, Exitcode, Logging, Settingsaufbau, Entry Point, Deployment-Wiring oder
Accept-Wakeup wird ergänzt.
