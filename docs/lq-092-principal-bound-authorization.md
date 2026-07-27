# LQ-092 — Principal-bound Authorization

## Ergebnis

Die bestehende `authorize_research`-Anwendungsfunktion akzeptiert keine frei
übergebene `UserId` mehr. Ihre Identität stammt ausschließlich aus dem
`SessionPrincipal` aus LQ-091.

Der übrige Ablauf bleibt unverändert:

1. `UserId` aus dem Principal verwenden.
2. Membership für diese Identität und den angeforderten Workspace laden.
3. Fehlende oder inkonsistente Membership verweigern.
4. Die bestehende reine Research-Entscheidung anwenden.

## Sicherheitswirkung

Der aufrufende Anwendungsfall kann keine separate User-ID neben dem bereits
verifizierten Principal behaupten. Workspace und Rechte bleiben serverseitig an
die geladene Membership gebunden.

## Bewusst nicht enthalten

- keine Erzeugung oder Prüfung des Principals,
- keine Session-, Cookie-, CSRF- oder Provider-Implementierung,
- keine HTTP-Route, Dependency oder Middleware,
- keine konkrete Membership-Speicherung,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-093 kann den neutralen Autorisierungsfehler als kleinen Anwendungsvertrag
definieren, ohne Ressourcenzugehörigkeit oder interne Ablehnungsgründe
offenzulegen. HTTP-Abbildung bleibt ein separater späterer Slice.
