# LQ-736 — Bounded Engine API Single-Message Stream I/O

## Umsetzung

`BoundedManifestHandoffSupervisorEngineApiStreamIo` stellt genau `read` und
`write` für extern gelieferte Streamobjekte bereit.

Der Reader sammelt in höchstens 4.096-Byte-Schritten bis zum Headerabschluss,
ermittelt die einzige zulässige Content-Length und liest den Rest mit einer an
die verbleibende Länge gebundenen Maximalanforderung.

Der Writer verwendet eine Memoryview und verfolgt bestätigten Sendefortschritt,
bis exakt die gelieferte Nachricht geschrieben wurde.

## Begrenzung

Header, Body und Gesamtnachricht besitzen feste Obergrenzen. Der Reader legt
keinen unbegrenzten Buffer an und fordert nie mehr als die jeweilige verbleibende
Grenze an.

## Detailfreiheit

Alle Interface-, Stream-, EOF-, Framing- und Fortschrittsfehler werden auf die
bestehende technische Nichtverfügbarkeit reduziert.

## Nicht umgesetzt

Kein Sockettyp, Listener, Accept, Connect, Timeout, Shutdown, Close, Retry,
Thread oder Forwardingloop wird ergänzt.
