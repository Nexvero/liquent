# LQ-128 — Logout Route

## Ergebnis

Eine dünne HTTP-Route `POST /v1/session/logout` setzt den LQ-127-Vertrag um. Sie
verbindet ausschließlich vorhandene Bausteine: den `BrowserSessionLookup`, den
CSRF-Validierungspfad, den `revoke_browser_session`-Anwendungsfall und den
`clear_session_cookie`-Helfer.

## Aktivierung und Dependency-Injection

- Die Route wird nur registriert, wenn `create_app` **beide** neuen optionalen
  Abhängigkeiten erhält: `logout_sessions` (`BrowserSessionLookup`) und
  `logout_revocations` (`BrowserSessionRevocationStore`).
- Ist genau eine der beiden gesetzt, schlägt der App-Aufbau mit einem
  Konfigurationsfehler (`ValueError`) fehl.
- Ohne beide Abhängigkeiten bleibt die Route abwesend; bestehende Research- und
  Local-/CI-Pfade sind unverändert.
- Der rohe `liquent_session`-Cookie wird ausschließlich an dieser Transportgrenze
  gelesen. Der Research-Guard (der bei fehlender/ungültiger Session `401` liefert)
  wird bewusst nicht verwendet; die Session wird direkt über den Lookup aufgelöst.

## Verhalten (alle Antworten: leerer Body, `Cache-Control: no-store`)

1. **Fehlender Cookie:** kein Lookup, kein Widerruf; Cookie neutral gelöscht; `204`.
2. **Unbekannte, abgelaufene oder widerrufene Session** (Lookup liefert `None`):
   kein Widerruf; Cookie gelöscht; identisches `204`.
3. **Gültige aktive Session mit fehlendem/falschem CSRF:** vorhandene
   CSRF-Validierung; kein Widerruf; Cookie **nicht** gelöscht; `403`.
4. **Gültige aktive Session mit korrektem CSRF:** genau ein Aufruf von
   `revoke_browser_session`, erst **danach** Cookie-Löschung; `204`.
5. **Erwarteter Store-/Infrastrukturfehler** (`SessionRevocationUnavailable`):
   kein erfolgreicher Logout; Cookie **nicht** gelöscht; `500`; keine Session-ID
   oder internen Details.

## Fehlerbehandlung

An der HTTP-Grenze werden ausschließlich `CsrfValidationFailed` (→ `403`) und der
neutrale, typisierte `SessionRevocationUnavailable` (→ `500`) gefangen. Es gibt
**kein** pauschales `except Exception`; unerwartete Programmierfehler werden nicht
verschluckt.

## Bewusst nicht enthalten

- keine Login-, Callback- oder Provider-Route,
- keine Datenbank-, Locks- oder Transaktionsentscheidung,
- keine CORS-Erweiterung,
- keine Freigabe von Preview, Staging oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

Ein späterer Slice kann einen konkreten Revocation-Store an die Produktions-App
verdrahten. Persistente oder verteilte Speicherung bleibt eine separate
Architekturentscheidung.
