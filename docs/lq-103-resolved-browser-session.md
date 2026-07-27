# LQ-103 — Resolved Browser Session

## Status

- Ein kleiner unveränderlicher Übergabevertrag bindet den bereits verifizierten
  Principal an den erwarteten CSRF-Wert derselben Browser-Session.
- Ein leerer CSRF-Wert ist ungültig.
- Der CSRF-Wert erscheint nicht in der Objektdarstellung.
- `SessionPrincipal` bleibt unverändert und enthält weiterhin nur die `UserId`.

## Vertrauensgrenze

`ResolvedBrowserSession` darf erst entstehen, nachdem eine äußere Grenze die
Session geprüft hat. Das Objekt selbst authentifiziert niemanden und liest
keine Cookies. Es verhindert lediglich, dass Principal und erwarteter
CSRF-Nachweis als lose, möglicherweise unterschiedlich stammende Werte an den
Anwendungsfall übergeben werden.

## Bewusst nicht enthalten

- keine Session-ID, Erzeugung, Ablaufzeit oder Rotation,
- kein Widerruf und kein Session-Speicher,
- keine Cookie-, Header-, HTTP- oder Middlewareintegration,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

