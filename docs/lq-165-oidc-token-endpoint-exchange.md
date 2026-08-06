# LQ-165 — OIDC Token Endpoint Exchange

## Zweck und Signatur

Löst den bereits geclaimten Authorization Code **genau einmal** am exakt
konfigurierten Token-Endpunkt ein und gibt ausschließlich ein **vorläufiges,
noch unverifiziertes** ID-Token zurück.

```python
# src/liquent_platform/identity/oidc_token_exchange.py
class OidcTokenEndpointClient:
    def __init__(self, client, policy, monotonic=time.monotonic) -> None: ...
    def exchange_authorization_code(
        self, configuration, verification
    ) -> OidcIdToken | None: ...
```

`OidcIdToken` ist ein frozen, `repr`-freier Wert und bedeutet **nur**: Der
Endpunkt hat einen String namens `id_token` geliefert — **nicht**, dass dieser
gültig oder vertrauenswürdig ist.

## Exakter Request

`POST` an **exakt** `configuration.token_endpoint`, keine Discovery, keine
URL-Zusammensetzung, **keine Redirects**. Formdaten exakt fünf Felder:
`grant_type=authorization_code` fest, `code`, `redirect_uri` und
`code_verifier` aus der Verification, `client_id` aus der Konfiguration. Header
ausschließlich `Accept: application/json` und `Accept-Encoding: identity`.
**Kein** Client Secret, State, Nonce, Issuer, Scope, Admission- oder
Return-Path, **keine** Browserheader oder Cookies.

**Kein Retry.** Genau ein Aufruf pro Methodenaufruf; nach Timeout,
Netzwerkfehler, 5xx, malformed Antwort oder Codeablehnung folgt kein zweiter
Request. Der Code wird nie erneut vorgelegt.

## Zeit- und Bytegrenzen

Phasen-Timeouts stellt der Client aus der Policy: `connect` und `read` direkt,
`write` und `pool` durch `total_timeout` begrenzt. Kein Timeoutwert stammt je
aus einer Providerantwort.

Die monotone Gesamtgrenze wird **zwischen** den I/O-Schritten fail-closed
geprüft — vor dem Request, nach den Headern, nach jedem Chunk und vor der
Rückgabe. Das ist ausdrücklich **keine harte präemptive Deadline**: Ein
synchroner Client bricht einen Thread in blockierendem I/O nicht ab;
garantiert sind die Phasen-Timeouts plus die Schrittgrenze dazwischen.

`monotonic` ist **keine Kalenderuhr**. Eine Uhr ist technisch unbrauchbar und
ergibt neutral `Unavailable`, wenn sie einen nicht endlichen oder falsch
typisierten Wert liefert, **rückwärts unter den Startwert** läuft oder eine
Exception wirft; deren Text tritt nie nach außen. `BaseException` wird bewusst
nicht gefangen.

Der Body wird **inkrementell als Rohbytes** gelesen und kumulativ gegen
`policy.token_response_max_bytes` gezählt; beim ersten Byte darüber folgt
`Unavailable`. Der Stream wird auf **jedem** Pfad geschlossen.
`Content-Length` wird nach erlaubtem HTTP-Whitespace nur als ASCII-Ziffern
akzeptiert — `+10`, `-1`, `1.0`, `10, 10`, leer und Nicht-ASCII-Ziffern sind
unbrauchbar; ein gültiger Wert über der Grenze wird vor dem Body abgewiesen.
Eine zu klein gemeldete Länge bleibt durch die tatsächlich gelesene Bytezahl
begrenzt.

## Klassifikation

`Content-Type` muss `application/json` sein (Media Type case-insensitiv), ein
`charset`-Parameter fehlen oder case-insensitiv `utf-8` sein; die Dekodierung
ist strikt UTF-8 ohne Fallback. `Content-Encoding` darf fehlen oder exakt
`identity` sein, damit keine Dekompression die Bytegrenze umgeht.

Klassifiziert wird über die **Anwesenheit** der Schlüssel, nie über ihren Wert:
Ein bei 200 vorhandener `error` und ein bei 400/401 vorhandenes `id_token`
machen die Antwort strukturell unbrauchbar, auch bei `null` oder leerem Wert.

| Situation | Ergebnis |
|---|---|
| 200, JSON-Objekt, `id_token` nicht leerer String, `error` **abwesend** | `OidcIdToken` |
| 400/401, JSON-Objekt, `error` nicht leerer String, `id_token` **abwesend** | `None` |
| Netzwerk-, TLS-, Timeout- oder interner Clientfehler, unbrauchbare Uhr | `Unavailable` |
| Redirectantwort, 5xx, jeder andere Status | `Unavailable` |
| falscher Media Type, Charset, `Content-Encoding` oder `Content-Length` | `Unavailable` |
| zu große Antwort, kein JSON-Objekt, **doppelter Membername** | `Unavailable` |
| gemischte oder unvollständige Antwort in beiden Richtungen | `Unavailable` |

Ein mehrfach vorkommender Membername ergibt `Unavailable` — kein zweiter Parse
und keine tolerante Auflösung, sonst entschiede die Parser-Konvention „letzter
Wert gewinnt" statt dieses Vertrags.

## Neutralitäts- und Geheimnisgrenze

Keine technische Detailunterklasse nach außen; `Unavailable` trägt nur seinen
festen Code. Authorization Code, Code Verifier, ID Token, Access Token, Refresh
Token, die vollständige Tokenantwort sowie `error`, `error_description`,
`error_uri` und beliebige Schlüssel, Werte oder Fragmente der Antwort
erscheinen **niemals** in `repr`, Exceptiontext, Log, Telemetrie, Trace,
Metriklabel, URL oder Cookie. Access Token, Refresh Token, Token Type und Scope
werden ignoriert und nicht gespeichert. Dieser Slice fügt kein Logging und
keine Telemetrie hinzu.

## Nicht-Ziele

Keine ID-Token-Signatur-/Claimprüfung, kein JWKS-Abruf oder Cache, keine
Discovery, keine Client-Secret-/mTLS-/Private-Key-JWT-/DPoP-Authentifizierung,
keine LQ-157-Portimplementierung, keine aktive Konfigurationsauflösung, keine
Callback-Route, keine Session-/CSRF-Erzeugung, kein Production-Wiring und keine
Dependency-, Lockfile-, CI-, Container-, Grype- oder Deployment-Änderung.
