# LQ-114 — Create Browser Session

## Status

- Ein kleiner Anwendungsfall bindet vorab erzeugtes Session-Material an einen
  verifizierten Principal.
- Daraus entsteht genau ein serverseitiger `BrowserSessionRecord`.
- Ein eigener Store-Port fügt den Record atomar nur dann hinzu, wenn die
  Session-ID noch nicht existiert.
- Eine Kollision liefert ausschließlich `session_lifecycle_conflict`.

## Sicherheitsgrenze

Der Anwendungsfall erzeugt weder Zufall noch Zeit. Session-ID, CSRF-Nachweis
und Ablaufzeitpunkt müssen bereits an der vertrauenswürdigen äußeren Grenze als
gültiges `IssuedBrowserSession` vorliegen. Erst ein erfolgreicher Store-Aufruf
liefert dieses Material zurück.

## Bewusst nicht enthalten

- kein konkreter Store oder Datenbankschema,
- keine Rotation oder Widerrufslogik,
- keine Generator-, Uhr- oder Lebensdauer-Policy,
- keine HTTP-, Cookie- oder Login-Integration,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-115 kann eine sichere Erzeugungsgrenze für opake Session-ID und CSRF-Wert
definieren. Der Store bleibt weiterhin austauschbar.
