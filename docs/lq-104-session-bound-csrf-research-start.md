# LQ-104 — Session-Bound CSRF Research Start

## Status

- Der CSRF-geschützte Research-Start akzeptiert den gebundenen
  `ResolvedBrowserSession`-Kontext.
- Principal und erwarteter CSRF-Wert können nicht mehr als lose Parameter aus
  unterschiedlichen Quellen übergeben werden.
- Der präsentierte Nachweis wird gegen den Wert des aufgelösten Kontexts geprüft.
- Danach wird unverändert der bestehende `research:write`-Pfad verwendet.

## Sicherheitsgrenze

Die äußere Session-Grenze bleibt dafür verantwortlich, ausschließlich einen
gültigen, nicht widerrufenen Kontext zu erzeugen. Der Anwendungsfall prüft weder
Cookies noch Session-IDs und erhält keinen rohen Session-Identifier.

## Bewusst nicht enthalten

- keine Session-Auflösung, Ablaufprüfung oder Widerrufslogik,
- kein Session-Speicher,
- keine Cookie-, Header-, HTTP- oder Middlewareintegration,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

