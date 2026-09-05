# LQ-723 — Engine API Response Policy Contract

## Ziel

Eine vom Daemon gelieferte Antwort darf nur nach Bindung an die zuvor
klassifizierte Supervisoroperation an den lokalen Client zurückgegeben werden.

## Erfolgsstatus

Find, Inspect und Wait erlauben ausschließlich 200. Create erlaubt ausschließlich
201. Start erlaubt ausschließlich 204. Stop und Kill erlauben 204 oder das vom
bestehenden Client neutral behandelte 304.

Andere Statuswerte sind technische Nichtverfügbarkeit. Insbesondere werden
Daemon-Konflikt-, Authentisierungs- und Serverfehler nicht durchgereicht.

## Neutrale Abwesenheit

Nur Inspect darf 404 als neutrale Abwesenheit liefern. Zulässig sind ein leerer
Body ohne Medientyp oder exakt `{}` als JSON.

Die Policy normalisiert beide Formen auf 404 ohne Medientyp und ohne Body. Eine
Daemonfehlermeldung darf dadurch nicht sichtbar werden.

## Medientyp und Body

JSON-Erfolge verlangen exakt `application/json`, einen nichtleeren UTF-8-Body,
höchstens 1.048.576 Bytes, eindeutige Objektschlüssel und den operationsgemäßen
Wurzeltyp.

Find liefert eine Liste; Create, Inspect und Wait liefern ein Objekt. Die
fachliche Tiefe dieser Objekte bleibt beim bestehenden Clientadapter.

204 und 304 verlangen Abwesenheit von Content-Type und einen exakt leeren Body.

## Fehlergrenze

Status, Content-Type, Bodytyp, Größe, JSON-Form und Operation werden fail-closed
geprüft. Ablehnungen verwenden ausschließlich die bestehende detailfreie
technische Nichtverfügbarkeit.

## Grenzen

Die Policy liest und klassifiziert nur bereits empfangene Daten. Sie besitzt
keinen Listener, Socket, Transport, Retry, Forwarder oder Lebenszyklus.
