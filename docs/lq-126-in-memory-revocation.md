# LQ-126 — In-Memory Revocation

## Ergebnis

Der lokale `InMemoryBrowserSessions`-Adapter erfüllt zusätzlich den
`BrowserSessionRevocationStore`-Port mit einem idempotenten
`revoke_session(session_id) -> None`.

## Verhalten

- Eine unbekannte Session ist ein neutraler No-op und liest die Uhr nicht.
- Eine bereits widerrufene Session ist ein neutraler No-op, liest die Uhr nicht
  und behält ihren ersten Widerrufszeitpunkt.
- Eine abgelaufene Session bleibt unverändert.
- Eine aktive Session wird mit genau einem gelesenen Uhrzeitwert widerrufen. Ein
  vollständiger neuer Records-Snapshot wird aufgebaut und in einem Schritt
  übernommen; alle anderen Records bleiben unverändert.
- Es gibt keinen Rückgabewert; weder Ergebnis, Fehler noch Log legen Existenz,
  Zustand oder Session-Material offen.

## Bewusst nicht enthalten

- keine HTTP-Logout-Route oder Cookie-Löschung,
- keine Datenbank, Locks oder Transaktionen,
- keine Provider-, CORS-, Deployment- oder Shared-Environment-Änderung,
- kein Release und kein Deployment.

## Nächster Schritt

Ein nachfolgender Slice kann Ausgabe- und Transportgrenzen für einen späteren
Logout definieren. Persistente oder verteilte Speicherung bleibt eine separate
Architekturentscheidung.
