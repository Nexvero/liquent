# LQ-165 — OIDC Token Endpoint Exchange

## Grenze

Ein kleiner technischer Baustein, der den bereits geclaimten Authorization Code
**genau einmal** am exakt konfigurierten Token-Endpunkt einlöst und
ausschließlich ein **vorläufiges, noch unverifiziertes** ID-Token zurückgibt.

**Keine** ID-Token-Signatur- oder Claimprüfung, **kein** JWKS-Abruf, **kein**
Cache, **keine** Discovery, **keine** Retry-Schleife und **keine**
LQ-157-Portimplementierung.

```python
# src/liquent_platform/identity/oidc_token_exchange.py
class OidcTokenEndpointClient:
    def __init__(self, client, policy, monotonic=time.monotonic) -> None: ...
    def exchange_authorization_code(
        self, configuration, verification
    ) -> OidcIdToken | None: ...
```

`OidcIdToken` ist ein `repr`-freier, frozen Wert und bedeutet **nur**: Der
Endpunkt hat einen String namens `id_token` geliefert — **nicht**, dass dieser
gültig oder vertrauenswürdig ist.

## Genau ein Request

Methode `POST`, URL **exakt** `configuration.token_endpoint`, keine Discovery,
keine URL-Zusammensetzung, **keine Redirects**. Formdaten exakt fünf Felder:
`grant_type=authorization_code` fest, `code`, `redirect_uri` und
`code_verifier` aus der Verification, `client_id` aus der Konfiguration. Header
ausschließlich `Accept: application/json` und `Accept-Encoding: identity`.
**Kein** Client Secret, State, Nonce, Issuer, Scope, Admission- oder
Return-Path, **keine** Browserheader oder Cookies.

**Kein Retry.** Genau ein Aufruf pro Methodenaufruf; nach Timeout,
Netzwerkfehler, 5xx, malformed Antwort oder Codeablehnung folgt **kein**
zweiter Request. Der Code wird nie erneut vorgelegt.

## Zeitgrenze

**Phasen-Timeouts** stellt der Client: `connect` und `read` aus der Policy,
`write` und `pool` durch `total_timeout` begrenzt. Kein Timeoutwert stammt je
aus einer Providerantwort.

Die **monotone Gesamtgrenze** wird zwischen den I/O-Schritten fail-closed
geprüft — vor dem Request, nach den Headern, nach jedem Chunk und vor der
Rückgabe. Das ist ausdrücklich **keine harte präemptive Deadline**: Bei einem
synchronen Client wird ein Thread, der bereits in blockierendem I/O steht,
nicht abgebrochen; garantiert sind die Phasen-Timeouts plus die Schrittgrenze
dazwischen.

`monotonic` dient nur dieser messbaren Grenze und der Testbarkeit — **keine
Kalenderuhr**. Eine Uhr ist technisch unbrauchbar und ergibt neutral
`Unavailable`, wenn sie einen nicht endlichen oder falsch typisierten Wert
liefert, **rückwärts unter den Startwert** läuft oder eine Exception wirft; der
Fehlertext einer injizierten Uhr tritt dabei **nie** nach außen.
`BaseException` wird bewusst **nicht** gefangen.

## Antwortgrenzen

**Streaming**: Die Antwort wird **inkrementell als Rohbytes** gelesen und
kumulativ gegen `policy.token_response_max_bytes` gezählt; beim ersten Byte
darüber folgt `Unavailable`. Der Stream wird auf **jedem** Pfad geschlossen.

**`Content-Length`** wird streng gelesen: nach erlaubtem HTTP-Whitespace
ausschließlich ASCII-Ziffern. `+10`, `-1`, `1.0`, `10, 10`, leer und
Nicht-ASCII-Ziffern sind unbrauchbar, nicht tolerant zu interpretieren. Ein
gültiger Wert bereits über der Grenze wird **vor** dem Body abgewiesen.

**`Content-Type`** muss `application/json` sein (Media Type case-insensitiv).
Ein `charset`-Parameter darf fehlen oder case-insensitiv `utf-8` sein; jeder
andere oder syntaktisch unbrauchbare `charset`-Parameter wird abgewiesen, denn
der Body wird **strikt** als UTF-8 dekodiert, ohne Fallback.
**`Content-Encoding`** darf fehlen oder exakt `identity` sein, damit keine
Dekompression die Bytegrenze umgeht.

**JSON**: Ein **mehrfach vorkommender Membername** ergibt `Unavailable` — kein
zweiter Parse, keine tolerante Auflösung, weil sonst die Parser-Konvention
„letzter Wert gewinnt" statt dieses Vertrags entscheiden würde.

## Ergebnisgrenze

Klassifiziert wird über die **Anwesenheit** der Schlüssel, nicht über ihren
Wert: Ein bei 200 vorhandener `error` und ein bei 400/401 vorhandenes
`id_token` machen die Antwort strukturell unbrauchbar, auch wenn der Wert
`null` oder leer ist.

| Situation | Ergebnis |
|---|---|
| HTTP 200, JSON-Objekt, `id_token` nicht leerer String, `error` **abwesend** | `OidcIdToken` |
| HTTP 400/401, JSON-Objekt, `error` nicht leerer String, `id_token` **abwesend** | `None` |
| Netzwerk-, TLS-, Timeout- oder interner Clientfehler, technisch unbrauchbare Uhr | `Unavailable` |
| Redirectantwort, 5xx, unerwarteter Status | `Unavailable` |
| falscher Media Type, Charset, `Content-Encoding` oder `Content-Length` | `Unavailable` |
| zu große Antwort, kein JSON-Objekt, doppelter Membername | `Unavailable` |
| gemischte oder unvollständige Antwort in beiden Richtungen | `Unavailable` |

**Keine** technische Detailunterklasse nach außen. Access Token, Refresh Token,
Token Type, Scope und sonstige Felder werden ignoriert und **nicht**
gespeichert.

## Geheimnisgrenze

Authorization Code, Code Verifier, ID Token, Access Token, Refresh Token und
die vollständige Tokenantwort erscheinen **niemals** in `repr`, Exceptiontext,
Log, Telemetrie, Trace, Metriklabel, URL oder Cookie. `error`,
`error_description`, `error_uri`, Providertexte sowie Schlüssel, Werte und
Fragmente der Antwort werden **nicht** zurückgegeben, geloggt oder in
Exceptions übernommen. Dieser Slice fügt **kein** Logging und **keine**
Telemetrie hinzu.

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
