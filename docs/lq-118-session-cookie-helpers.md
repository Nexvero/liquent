# LQ-118 — Session Cookie Helpers

## Ergebnis

Zwei kleine HTTP-Helfer setzen und löschen den in LQ-117 definierten
`liquent_session`-Cookie. Sie transportieren ausschließlich die opake
Session-ID und verändern keinen serverseitigen Session-Zustand.

## Verhalten

- Ausgabe: host-only, `Secure`, `HttpOnly`, `SameSite=Lax`, `Path=/`.
- Die ganzzahlige `Max-Age` wird abgerundet und überschreitet deshalb nie den
  serverseitigen Ablaufzeitpunkt.
- Bereits abgelaufene oder nicht eindeutig zeitbezogene Ausgaben werden vor
  jeder Response-Mutation abgewiesen.
- Löschung verwendet denselben Namen und Pfad sowie `Max-Age=0`.
- Ausgabe und Löschung setzen `Cache-Control: no-store`.
- Session-ID und CSRF-Nachweis erscheinen nicht im Response-Body.

## Bewusst nicht enthalten

- keine Login-, Logout- oder Providerroute,
- kein Store- oder Generator-Wiring,
- keine CSRF-Auslieferung,
- keine Freigabe von Shared Environments,
- kein Release und kein Deployment.

## Nächster Schritt

Eine spätere Route kann den Ausgabehelfer nach erfolgreicher Session-Erzeugung
aufrufen. Dieses Wiring bleibt ein eigener, überprüfbarer Slice.
