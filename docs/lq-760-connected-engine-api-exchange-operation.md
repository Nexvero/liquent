# LQ-760 — Connected Engine API Exchange Operation

## Umsetzung

`ConnectedManifestHandoffSupervisorEngineApiExchange` bindet exakt den konkreten
Daemonconnector und den konkreten Verified Exchange.

`serve` hält lokal höchstens einen Daemonstream. Nach Connect wird genau der
Client-/Daemonpaarwert an den Verified Exchange weitergegeben.

Anschließend wird der Daemonstream unabhängig vom Exchangeergebnis genau einmal
geschlossen. Die Operation speichert ihn nicht über den Aufruf hinaus.

## Gemeinsame Fehlergrenze

Connect-, Verify-, Gate-, I/O-, Response- und Closefehler erscheinen als dieselbe
bestehende detailfreie technische Nichtverfügbarkeit.

Auch gleichzeitiger Exchange- und Closefehler erzeugt nur dieses eine
beobachtbare Ergebnis.

## Nicht umgesetzt

Kein Listener, Bind, Accept, Retry, Pool, Client-Close, Loop oder
Prozesslifecycle wird ergänzt.
