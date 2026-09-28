# LQ-784 — Signal-Owned Engine API Run

## Umsetzung

`SignalOwnedManifestHandoffSupervisorEngineApiRun` bindet exakt die konkrete
Owned-Signalquelle und den konkreten Owned Process Run.

`run` merkt eine erfolgreiche Installation lokal, übergibt danach genau die
gebundene `requested`-Methode und hält das Process-Run-Ergebnis bis zum
erfolgreichen Restore zurück.

Restore wird auf jedem installierten Pfad genau einmal versucht. Die Operation
speichert weder Signalhandler noch Listener oder Streams selbst.

## Detailfreiheit

Install-, Process-, Ergebnis- und Restorefehler werden auf die bestehende
detailfreie technische Nichtverfügbarkeit reduziert.

## Nicht umgesetzt

Kein Signalversand, Main, Exit, Settingsparser, Logging, Entry Point,
Acceptinterrupt oder Deploymentaktivierung wird ergänzt.
