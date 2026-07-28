# LQ-123 — Rotate Session Use Case

## Ergebnis

Ein Anwendungsfall `rotate_browser_session` erzeugt für eine bestehende Session
frisches, unabhängiges Session- und CSRF-Material und übergibt es über den
atomaren `BrowserSessionRotationStore`. Er nutzt den vorhandenen
`BrowserSessionMaterialGenerator` und spiegelt die Struktur des Issuance-Falls.

## Verhalten

- Uhr (`now`) und positive Laufzeit (`lifetime`) werden explizit injiziert.
- Eine nicht-positive Laufzeit scheitert vor jeder Nebenwirkung; weder der
  Generator noch der Store werden aufgerufen.
- Session-ID und CSRF-Nachweis werden unabhängig und nicht leer erzeugt; leeres
  Material scheitert vor dem Store.
- Der Anwendungsfall übergibt dem Store **nur** die aktuelle Session-ID und das
  neue `IssuedBrowserSession`-Material — **keinen** Principal. Der Store übernimmt
  den Principal aus dem bestehenden Record, sodass hier konstruktiv kein fremder
  Principal gebunden werden kann.
- Liefert der Store `False` (unbekannte, ungültige Quelle oder Ziel-ID-Kollision),
  wird ausschließlich der neutrale `SessionLifecycleConflict` ausgelöst.
- Bei Erfolg wird das ausgegebene `IssuedBrowserSession` zurückgegeben.

## Grenzen

Die Atomarität von Widerruf und Neuanlage sowie die Übernahme des bestehenden
Principals liegen vollständig im Store; dieser Anwendungsfall führt keine eigene
Gültigkeits-, Widerrufs- oder Principal-Logik aus. Cookie-Ausgabe und Transport
bleiben getrennte, spätere Slices.

## Bewusst nicht enthalten

- keine In-Memory-Rotation oder sonstige Store-Implementierung (LQ-124),
- keine HTTP-, Cookie-, Login-/Logout- oder Provider-Integration,
- keine Datenbank, Locks oder Transaktionen,
- keine CORS-, Deployment- oder Shared-Environment-Änderung,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-124 kann den lokalen Adapter um die atomare Rotation erweitern und Erfolg,
unbekannte/abgelaufene/widerrufene Quelle sowie Ziel-ID-Kollision prüfen.
