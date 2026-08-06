# LQ-165 — OIDC Token Endpoint Exchange

## Grenze

Ein kleiner technischer Baustein, der den bereits geclaimten Authorization Code
**genau einmal** am exakt konfigurierten Token-Endpunkt einlöst und
ausschließlich ein **vorläufiges, noch unverifiziertes** ID-Token zurückgibt.

**Keine** ID-Token-Signatur- oder Claimprüfung, **kein** JWKS-Abruf, **kein**
Cache, **keine** Discovery, **keine** Retry-Schleife und **keine**
LQ-157-Portimplementierung.

`src/liquent_platform/identity/oidc_token_exchange.py`

```python
@dataclass(frozen=True, slots=True)
class OidcIdToken:
    value: str = field(repr=False)


class OidcTokenEndpointClient:
    def __init__(self, client, policy, monotonic=time.monotonic) -> None: ...
    def exchange_authorization_code(
        self, configuration, verification
    ) -> OidcIdToken | None: ...
```

`OidcIdToken` bedeutet **nur**: Der Endpunkt hat einen String namens `id_token`
geliefert — **nicht**, dass dieser gültig oder vertrauenswürdig ist. Der Wert
ist `repr`-frei und wird verbatim gehalten.

## Genau ein Request

Methode `POST`, URL **exakt** `configuration.token_endpoint`, keine Discovery,
keine URL-Zusammensetzung, **keine Redirects**.

Formdaten exakt fünf Felder:

| Feld | Quelle |
|---|---|
| `grant_type=authorization_code` | fest |
| `code` | `verification.authorization_code` |
| `redirect_uri` | `verification.redirect_uri` |
| `client_id` | `configuration.client_id` |
| `code_verifier` | `verification.code_verifier` |

**Kein** Client Secret, State, Nonce, Issuer, Scope, Admission- oder
Return-Path, **keine** Browserheader oder Cookies. Header ausschließlich
`Accept: application/json` und `Accept-Encoding: identity`.

**Kein Retry.** Genau ein Aufruf pro Methodenaufruf; nach Timeout,
Netzwerkfehler, 5xx, malformed Antwort oder Codeablehnung folgt **kein**
zweiter Request. Der Code wird nie erneut vorgelegt.

## Zeit- und Größengrenze

**Phasen-Timeouts** stellt der Client: `connect` aus `connect_timeout`, `read`
aus `read_timeout`, `write` und `pool` durch `total_timeout` begrenzt. Kein
Timeoutwert stammt je aus einer Providerantwort.

**Die monotone Gesamtgrenze wird zwischen den I/O-Schritten fail-closed
geprüft** — vor dem Request, nach den Headern, nach jedem Chunk und vor der
Rückgabe. Erreicht oder überschreitet die verstrichene Zeit `total_timeout`,
folgt `OidcVerificationUnavailable`.

**Das ist ausdrücklich keine harte präemptive Deadline.** Bei einem synchronen
Client wird ein Thread, der bereits in einem blockierenden I/O-Aufruf steht,
nicht abgebrochen; garantiert sind die Phasen-Timeouts des Clients plus die
Schrittgrenze dazwischen. `monotonic` dient nur dieser messbaren Grenze und der
Testbarkeit — **keine Kalenderuhr**. Ein nicht endlicher oder falsch typisierter
Messwert ergibt neutral `OidcVerificationUnavailable`.

**Streaming**: Die Antwort wird **inkrementell als Rohbytes** gelesen und
kumulativ gegen `policy.token_response_max_bytes` gezählt; beim ersten Byte
darüber folgt `Unavailable`. Ein gültiges `Content-Length` bereits über der
Grenze wird **früh** abgewiesen, ein malformed `Content-Length` ebenfalls.
`Content-Encoding` darf fehlen oder exakt `identity` sein — andere Kompression
wird abgewiesen, damit keine Dekompression die Grenze umgeht. Der Stream wird
auf **jedem** Pfad geschlossen.

## Ergebnisgrenze

| Situation | Ergebnis |
|---|---|
| HTTP 200, JSON-Objekt, `id_token` nicht leerer String, **kein** `error` | `OidcIdToken` |
| HTTP 400/401, JSON-Objekt, `error` nicht leerer String, **kein** `id_token` | `None` |
| Netzwerk-, TLS-, Connect-, Read-, Write-, Pool- oder Timeoutfehler | `Unavailable` |
| Redirectantwort, 5xx, unerwarteter Status | `Unavailable` |
| falscher Content-Type oder Content-Encoding | `Unavailable` |
| zu große Antwort, malformed `Content-Length` | `Unavailable` |
| nicht parsebares oder strukturell falsches JSON | `Unavailable` |
| 200 ohne brauchbares `id_token`, `id_token` **und** `error` zugleich | `Unavailable` |
| malformed OAuth-Fehlerantwort | `Unavailable` |
| technisch unbrauchbare monotonic clock, interner Clientfehler | `Unavailable` |

**Keine** technische Detailunterklasse nach außen. Access Token, Refresh Token,
Token Type, Scope und sonstige Felder werden ignoriert und **nicht**
gespeichert.

## Geheimnisgrenze

Authorization Code, Code Verifier, ID Token, Access Token, Refresh Token und
die vollständige Tokenantwort erscheinen **niemals** in `repr`, Exceptiontext,
Log, Telemetrie, Trace, Metriklabel, URL oder Cookie. `error`,
`error_description`, `error_uri` und Providertexte werden **nicht**
zurückgegeben, geloggt oder in Exceptions übernommen. Dieser Slice fügt
**kein** Logging und **keine** Telemetrie hinzu.

## Nicht-Ziele

Keine ID-Token-Signatur-/Claimprüfung, kein JWKS-Abruf oder Cache, keine
Discovery, keine Client-Secret-/mTLS-/Private-Key-JWT-/DPoP-Authentifizierung,
keine LQ-157-Portimplementierung, keine aktive Konfigurationsauflösung, keine
Callback-Route, keine Session-/CSRF-Erzeugung, kein Production-Wiring und keine
Dependency-, Lockfile-, CI-, Container-, Grype- oder Deployment-Änderung.

## Nächster Schritt

Der vollständige Verifikationsadapter, der diesen Austausch mit dem begrenzten
JWKS-Abruf und dem LQ-164-Verifikationskern zu einer LQ-157-Portimplementierung
zusammensetzt.
