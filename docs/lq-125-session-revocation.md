# LQ-125 — Session Revocation Port and Use Case

## Ergebnis

Ein speicherneutraler `BrowserSessionRevocationStore`-Port beschreibt genau eine
idempotente Operation `revoke_session(session_id) -> None`. Ein schmaler
Anwendungsfall `revoke_browser_session` delegiert genau einmal an diesen Port und
enthält keine Speicher-, Zeit- oder HTTP-Logik.

## Verhalten

- `revoke_session` macht einen vorhandenen Eintrag dauerhaft unbrauchbar.
- Unbekannte, bereits widerrufene oder abgelaufene Sessions sind neutrale,
  idempotente No-ops.
- Es gibt keinen Rückgabewert; nach außen ist nicht unterscheidbar, ob eine
  Session existierte oder gültig war.
- Weder Fehler noch Ergebnisse noch Logs enthalten die Session-ID oder anderes
  internes Material.
- Der Anwendungsfall führt keine eigene Gültigkeits-, Zeit- oder Speicherlogik
  aus; er delegiert ausschließlich.

## Bewusst nicht enthalten

- keine In-Memory- oder sonstige Store-Implementierung (eigener Folgeslice),
- keine Datenbank, Locks oder Transaktionen,
- keine Uhr- oder Lebensdauer-Policy,
- keine HTTP-Logout-Route oder Cookie-Löschung,
- keine Provider-, CORS-, Deployment- oder Shared-Environment-Änderung,
- kein Release und kein Deployment.

## Nächster Schritt

Ein nachfolgender Slice kann den lokalen Adapter um die idempotente Widerrufs-
operation erweitern und Erfolg, unbekannte, abgelaufene sowie bereits widerrufene
Quellen prüfen. Ein HTTP-Logout bleibt ein separater, späterer Slice.
