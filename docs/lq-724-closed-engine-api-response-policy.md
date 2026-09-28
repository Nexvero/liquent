# LQ-724 — Closed Engine API Response Policy

## Umsetzung

`ClosedManifestHandoffSupervisorEngineApiResponsePolicy` bindet jede Antwort an
einen echten `ManifestHandoffSupervisorEngineApiOperation`-Wert.

Die Policy besitzt getrennte Pfade für JSON-Erfolg, leeren Erfolg und neutrale
Inspect-Abwesenheit. Das Ergebnis ist ein unveränderlicher autorisierter
Responsewert aus Status, normalisiertem Content-Type und Body.

## JSON-Grenze

Der Decoder akzeptiert nur UTF-8-JSON innerhalb der festen Obergrenze und lehnt
doppelte Objektschlüssel ab. Er prüft Liste beziehungsweise Objekt passend zur
Operation, verändert einen erfolgreichen Body aber nicht.

Damit bleibt die tiefere Docker-Antwortvalidierung im bestehenden
`LocalDockerEngineHttpClient`, ohne dass beliebige Rootformen den künftigen Proxy
passieren können.

## Detailfreiheit

Nicht erlaubte Daemonstatus werden vor jeder Bodyweitergabe abgelehnt. Auch
Content-Type-Erweiterungen, Body an leerer Operation und detaillierte 404-Bodies
scheitern mit derselben bestehenden technischen Nichtverfügbarkeit.

## Nicht umgesetzt

Dieser Slice ergänzt weder HTTP-Parsing noch Headerfilter, Chunking, Listener,
Peercredentials, Upstreamverbindung oder Prozessverdrahtung.
