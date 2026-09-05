# LQ-740 — Closed Engine API Single Exchange

## Umsetzung

`ClosedManifestHandoffSupervisorEngineApiExchange` besitzt genau ein konkretes
Gate und genau eine konkrete begrenzte Stream-I/O-Instanz.

`exchange` führt die feste Read-Gate-Write-Read-Gate-Write-Folge aus. Client- und
Daemonstream müssen verschiedene Objekte sein.

## Kanonische Ausgabe

Die private Responsekodierung kennt ausschließlich die von der Responsepolicy
erlaubten Status 200, 201, 204, 304 und 404. Sie erzeugt lowercase Header in
fester Reihenfolge und berechnet Content-Length aus dem autorisierten Body.

Damit kann kein Daemonheader, Reasontext oder caller-gelieferter Status in die
lokale Antwort gelangen.

## Fehlergrenze

Gate-, Stream- und Kodierungsfehler werden gemeinsam auf die bestehende
detailfreie technische Nichtverfügbarkeit reduziert. Es gibt keinen internen
Retry.

## Nicht umgesetzt

Kein Listener, Socketfactory, Peercredentialcheck, Daemonconnect,
Timeoutmanagement, Close, Parallelismus oder Prozesslifecycle wird ergänzt.
