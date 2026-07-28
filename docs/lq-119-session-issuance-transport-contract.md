# LQ-119 — Session Issuance Transport Contract

## Entscheidung

Nach erfolgreicher Browser-Session-Erzeugung liefert die HTTP-Grenze die zwei
geheimen Werte getrennt aus:

- die opake Session-ID ausschließlich im in LQ-117 definierten
  `liquent_session`-Cookie,
- den zugehörigen CSRF-Nachweis ausschließlich im Response-Header
  `X-CSRF-Token`.

Die Response enthält keinen Session- oder CSRF-Wert im Body. Ein Browser-Client
hält den CSRF-Nachweis nur im Arbeitsspeicher und sendet ihn bei
zustandsändernden Requests wieder als `X-CSRF-Token`.

## Verbindliches Verhalten

- Cookie-Ausgabe erfolgt erst nach erfolgreicher, serverseitiger Speicherung.
- Der vorhandene LQ-118-Helfer setzt die Cookie-Attribute und
  `Cache-Control: no-store`.
- Der Response-Header enthält genau den zur ausgegebenen Session gehörenden
  CSRF-Nachweis.
- Der Header darf nicht in Logs, URLs, Fehlermeldungen oder Telemetrie
  übernommen werden.
- Ein Ausgabefehler liefert weder Cookie noch CSRF-Header.
- Cross-Origin-Ausgabe ist nicht vorgesehen; eine spätere CORS-Freigabe wäre
  eine eigene Sicherheitsentscheidung.

## Client-Lebenszyklus

Nach einem Seitenreload besitzt der Client keinen CSRF-Nachweis mehr. Eine
spätere, authentifizierte Refresh-Grenze kann einen neuen gebundenen Nachweis
bereitstellen. Bis dahin bleibt die Session für zustandsändernde Requests
nicht verwendbar; lesende Requests können den HttpOnly-Cookie weiterhin
nutzen.

## Bewusst nicht enthalten

- keine Login-, Callback-, Refresh- oder Logout-Route,
- kein Provider- oder Benutzer-Wiring,
- keine Speicherung in Web Storage,
- keine CORS-Erweiterung,
- keine Freigabe von Shared Environments,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-120 kann einen kleinen Response-Helfer ergänzen, der nach bereits
erfolgreicher Session-Erzeugung Cookie und CSRF-Header gemeinsam ausgibt.
