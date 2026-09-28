# LQ-785 — Engine API Signal-Owned Run Evidence

## Erfolgsreihenfolge

Die Tests belegen exakt Install, Process Run und Restore. An den Process Run wird
die gebundene `requested`-Methode derselben installierten Signalinstanz übergeben.

Das ServeResult bleibt objekt- und wertidentisch und wird erst nach Restore
ausgegeben.

## Fehlerpfade

Installfehler erzeugt weder Run noch Restore. Processfehler restauriert genau
einmal.

Restorefehler nach Erfolg verhindert Erfolg. Gleichzeitiger Run- und
Restorefehler bleibt ein einziges detailfreies Ergebnis.

Ein typfalsches Processergebnis wird erst nach Restore abgelehnt. Duck-typed
Signal- oder Processersatz scheitert beim Aufbau.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Main, Exit, Signal, Install, Restore oder Close.
Tests patchen ausschließlich konkrete Komponenten und verändern keine realen
Signalhandler.
