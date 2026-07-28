# LQ-117 — Session Cookie Contract

## Entscheidung

Die opake Browser-Session-ID wird ausschließlich im Cookie
`liquent_session` transportiert. Der Cookie enthält weder Identität noch
Workspace, Rechte, CSRF-Nachweis oder andere Anwendungsdaten.

## Verbindliche Attribute

| Attribut | Regel |
|---|---|
| Name | `liquent_session` |
| `Secure` | immer gesetzt |
| `HttpOnly` | immer gesetzt |
| `SameSite` | `Lax` |
| `Path` | `/` |
| `Domain` | nicht setzen; Cookie bleibt host-only |
| Lebensdauer | niemals länger als der serverseitige Session-Record |

`SameSite=Lax` schützt normale Cross-Site-Requests, ohne spätere sichere
Top-Level-Navigationen pauschal auszuschließen. Zustandsändernde Requests
benötigen weiterhin den bereits vorhandenen gebundenen CSRF-Nachweis.

## Ausgabe und Löschung

- Cookie-Ausgabe erfolgt erst nach erfolgreich gespeicherter Session.
- Rotationen setzen den neuen Cookie erst nach atomarem Erfolg.
- Löschung verwendet denselben Namen und Pfad sowie `Max-Age=0`.
- Antworten, die Session-Material ausgeben oder löschen, verwenden
  `Cache-Control: no-store`.
- Die Session-ID erscheint weder in URL noch Response-Body oder Web Storage.
- Der CSRF-Nachweis wird nicht in diesem Session-Cookie gespeichert.

## Fehlerverhalten

Ein Cookie ohne gültigen serverseitigen Record bleibt
`authentication_required`. Der Client erhält keine Information darüber, ob
der Cookie unbekannt, abgelaufen, widerrufen oder ersetzt wurde.

## Bewusst nicht enthalten

- keine Cookie-Helfer oder Response-Integration,
- keine Login-, Logout- oder Providerroute,
- keine CSRF-Auslieferungsentscheidung,
- keine konkrete Session-Lebensdauer,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-118 kann kleine, transportnahe Set-/Clear-Cookie-Helfer exakt nach diesem
Vertrag bereitstellen. Eine Route bleibt weiterhin ein eigener Slice.
