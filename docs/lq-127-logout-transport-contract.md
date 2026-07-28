# LQ-127 — Logout Transport Contract

## Status

Nur Vertrag und Roadmap-Dokumentation. Keine Route, keine neuen Ports, keine
Implementierung und keine Tests. Ein späterer Slice kann die Route auf Basis der
vorhandenen Bausteine umsetzen.

## Entscheidung

Der Browser-Logout ist ein zustandsändernder Request an einer einzigen HTTP-Grenze:

- **Methode und Pfad:** `POST /v1/session/logout` (konsistent zur bestehenden
  `/v1`-Konvention; Logout verändert Zustand und ist daher kein `GET`).

Der Logout überführt den Client in einen neutralen zustandslosen Endzustand.
Erfolgreiche und bereits zustandslose Logouts sind nach außen ununterscheidbar.

## Verbindliches Verhalten

### Session-Zustände

Die Grenze löst die aktuelle Session read-only über den vorhandenen
`BrowserSessionLookup` aus dem `liquent_session`-Cookie auf, ausschließlich um zu
entscheiden, ob eine CSRF-Prüfung erforderlich ist.

- **Gültige aktive Session:** verlangt den gebundenen CSRF-Nachweis (siehe unten).
  Nach bestandener Prüfung wird die Session serverseitig widerrufen; der Endzustand
  ist neutral `204 No Content` mit gelöschtem Cookie.
- **Fehlende, unbekannte, abgelaufene oder bereits widerrufene Session:** es gibt
  nichts zu widerrufen. Der Request ist ein idempotenter No-op und liefert
  denselben neutralen Endzustand `204 No Content` mit gelöschtem Cookie. Für diese
  Fälle ist keine CSRF-Prüfung erforderlich, da keine aktive Session geschützt wird.

Alle neutralen Endzustände sind über Statuscode, Header und (leeren) Body
identisch; sie verraten nicht, ob eine Session existierte oder gültig war.

### CSRF

- CSRF wird **nur** geprüft, wenn eine gültige aktive Session aufgelöst wurde
  (nur dann existiert ein zu schützender zustandsändernder Effekt).
- Die Prüfung nutzt den vorhandenen CSRF-Validierungspfad: der Request muss den an
  die Session gebundenen `X-CSRF-Token` mitführen. Fehlt er oder passt er nicht,
  wird der Request über die bestehende neutrale CSRF-Ablehnung zurückgewiesen;
  es findet **kein** Widerruf und **keine** Cookie-Löschung statt.
- Da keine CORS-Freigabe existiert, kann ein Cross-Origin-Aufrufer die Antwort
  (Status/Body) nicht lesen; die CSRF-Ablehnung ist damit kein
  Session-Existenz-Orakel für fremde Ursprünge.

### Statuscodes

- Erfolgreicher Widerruf und bereits zustandsloser Logout: `204 No Content`.
- CSRF-Ablehnung einer gültigen aktiven Session: bestehende neutrale
  CSRF-Antwort (kein Session-Material).
- Store-/Infrastrukturfehler beim Widerruf: neutraler `500`-Endzustand (siehe
  „Store-Fehler"). Es werden keine unterscheidenden `401`/`404` verwendet.

### Cookie-Löschung

- Bei jedem neutralen Endzustand (`204`) wird der Browser-Cookie mit dem
  vorhandenen `clear_session_cookie`-Helfer (LQ-118) gelöscht. Der Helfer verwendet
  dieselben Transportattribute (host-only, `Secure`, `HttpOnly`, `SameSite=Lax`,
  `Path=/`).

### Cache-Control

- Jede Antwort trägt `Cache-Control: no-store`. Der Body bleibt leer und nicht
  cachebar. Der `clear_session_cookie`-Helfer setzt `no-store` bereits mit.

### Reihenfolge von Widerruf und Cookie-Löschung

1. Bei gültiger aktiver Session zuerst der **serverseitige Widerruf** über den
   `revoke_browser_session`-Anwendungsfall (LQ-125) als maßgebliche Wahrheit.
2. Erst **nach** erfolgreichem Widerruf wird der Cookie gelöscht und `204`
   geliefert.
3. Bei bereits zustandslosen Fällen entfällt der Widerruf; der Cookie wird
   gelöscht und `204` geliefert.

Der Cookie (Client-Bequemlichkeit) wird nie vor der serverseitigen Wahrheit
gelöscht.

### Store-Fehler

- Schlägt der Widerruf infrastrukturell fehl, darf **kein** erfolgreicher Logout
  vorgetäuscht werden: es wird **nicht** `204` geliefert und der Cookie wird
  **nicht** gelöscht (die Session kann serverseitig noch aktiv sein). Stattdessen
  neutraler `500`-Endzustand mit leerem, nicht cachebarem Body. Der Client kann den
  idempotenten Logout erneut versuchen.

### Vertraulichkeit

- Session-ID und CSRF-Werte erscheinen niemals in Body, URL, Query, Logs,
  Fehlermeldungen oder Telemetrie.

## Bewusst nicht enthalten

- keine Route-Implementierung und keine neuen Ports,
- keine Tests, die eine Implementierung vortäuschen,
- keine Provider-, Login- oder Callback-Integration,
- keine Datenbank-, Locks- oder Transaktionsentscheidung,
- keine CORS-Erweiterung,
- keine Freigabe von Preview, Staging oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

Ein späterer Slice kann `POST /v1/session/logout` als dünne Route umsetzen, die
den vorhandenen Lookup, den CSRF-Validierungspfad, den
`revoke_browser_session`-Anwendungsfall und `clear_session_cookie` gemäß diesem
Vertrag verbindet.
