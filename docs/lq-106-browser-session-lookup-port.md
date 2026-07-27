# LQ-106 — Browser Session Lookup Port

## Status

- Eine opake `SessionId` identifiziert den serverseitigen Browser-Session-Eintrag.
- Genau ein Lookup-Port löst diese ID zu einem `ResolvedBrowserSession`-Kontext
  oder neutral `None` auf.
- Der Port macht keine Annahmen über Speicher, Provider oder Sessionformat.

## Sicherheitsgrenze

Ein Treffer bedeutet, dass der konkrete Adapter Ablauf, Widerruf und Integrität
bereits geprüft hat. Fehlende, abgelaufene, widerrufene und ungültige Sessions
sollen nach außen als derselbe fehlende Treffer erscheinen. Session-IDs dürfen
nicht geloggt oder in URLs übertragen werden.

## Bewusst nicht enthalten

- kein konkreter Session-Speicher oder Adapter,
- keine Erzeugung, Rotation, Ablauf- oder Widerrufsimplementierung,
- kein Cookie-Name und keine Cookie-Auswertung,
- keine HTTP-Dependency oder Middleware,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

