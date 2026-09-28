# LQ-815 — Engine API Process Bundle Contract

## Ziel

Die vollständige Proxycomposition muss Run, Status und Readinessprobe als ein
inertes, unveränderliches und objektidentisch gebundenes Ergebnis liefern.

## Bestandteile

Das Bundle enthält genau einen signalbesessenen Process Run, genau einen
Process Status und genau eine Readinessprobe.

Der innere Owned Process Run muss exakt dieselbe Statusinstanz besitzen, die das
Bundle ausgibt. Die Readinessprobe muss ebenfalls exakt diese Instanz abfragen.
Gleichwertige, aber andere Instanzen werden abgelehnt.

## Wirkung

Bundlecomposition liest keine Umgebung oder Hostfakten, öffnet keinen Socket,
installiert kein Signal und startet keinen Run. Der Status bleibt `initial` und
die Probe nicht-ready.

## Kompatibilität

Der bestehende Composer bleibt erhalten und projiziert ausschließlich den Run
aus genau einem vollständigen Bundle. Er baut keinen zweiten Graphen.

## Grenzen

Kein Healthserver, HTTP-Modell, Thread, Entry-Point-Returnwert, Deployment oder
Productionclaim wird ergänzt.
