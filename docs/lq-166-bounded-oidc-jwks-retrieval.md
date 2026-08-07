# LQ-166 — Bounded OIDC JWKS Retrieval

## Zweck und Signatur

Lädt **genau ein** vertrauenswürdiges JSON Web Key Set von der exakt
konfigurierten `jwks_uri` und gibt es als bereits begrenzt geparstes Mapping für
`verify_oidc_id_token(...)` weiter.

```python
# src/liquent_platform/identity/oidc_jwks_retrieval.py
class OidcJwksEndpointClient:
    def __init__(self, client, policy, monotonic=time.monotonic) -> None: ...
    def load_jwks(self, configuration) -> Mapping[str, object]: ...
```

Keine zusätzliche öffentliche Resultatklasse: Das Mapping passt direkt auf den
`jwks`-Parameter des Offline-Verifikationskerns (LQ-164).

## Exakter Request

Methode `GET`, URL **ausschließlich** `configuration.jwks_uri` — keine
Discovery, keine URL-Zusammensetzung und keine URL aus Tokenheader, Browser oder
Aufrufer. `jku`, `x5u` und `jwk` werden hier **niemals gelesen oder befolgt**;
ihnen zu folgen hieße, den Prüfschlüssel vom Prüfling bestimmen zu lassen.

Header ausschließlich `Accept: application/json` und
`Accept-Encoding: identity`. Kein Request-Body. **Keine Redirect-Verfolgung,
kein Retry, kein Fallback auf eine andere URL.**

`Cookie` und `Authorization` **fehlen** im Request — sie werden nicht leer
gesetzt. Der Request wird genau einmal mit `build_request` gebaut, geerbte
Zugangsdatenheader werden entfernt, und `send(..., auth=None)` verhindert, dass
das Auth-Verfahren des Clients einen erzeugt. Ein absichtlich mit Cookie und
Auth vorkonfigurierter Client kann diesem Request also keine Zugangsdaten
leihen; harmlose Default-Header bleiben unangetastet. Gesendet wird genau
einmal, und die Response wird auf jedem Pfad geschlossen.

## Zeit- und Bytegrenzen

Phasen-Timeouts stammen aus der `OidcVerificationPolicy`: `connect` und `read`
direkt, `write` und `pool` durch `total_timeout` begrenzt — nie aus einer
Providerantwort.

Die monotone Gesamtgrenze wird **zwischen** den I/O-Schritten fail-closed
geprüft — vor dem Request, nach den Headern, während des Streamens und vor der
Rückgabe; wie in LQ-165 ausdrücklich **keine harte präemptive Deadline**, weil
ein synchroner Client blockierendes I/O nicht abbricht.

Eine Uhr ist unbrauchbar und ergibt neutral `Unavailable`, wenn sie einen nicht
endlichen oder falsch typisierten Wert liefert (`bool` ist nie ein Messwert)
oder eine Exception wirft; deren Text tritt nie nach außen. **`BaseException`
wird nicht gefangen**, damit ein Abbruchsignal nicht in einer neutralen
Unavailability verschwindet.

Geprüft wird die **echte monotone Folge**: Jeder Messwert muss mindestens dem
zuletzt akzeptierten entsprechen, Gleichstand bleibt zulässig. `0.0 → 5.0 →
4.0` ist damit unbrauchbar, obwohl beide späteren Werte über dem Startwert
liegen. Der zuletzt akzeptierte Wert lebt **nur innerhalb eines Aufrufs**;
zwischen zwei Abrufen bleibt keine Uhrinformation bestehen.

Der Body wird **inkrementell als Rohbytes** gelesen und kumulativ gegen
`policy.jwks_response_max_bytes` gezählt; beim ersten Byte darüber folgt
`Unavailable`, sodass auch ein zu klein gemeldetes `Content-Length` begrenzt
bleibt. Der Stream wird auf **jedem** Pfad geschlossen.

## Antwort-, JSON- und JWKS-Grenze

**Nur HTTP 200 ist verwertbar.** Jeder andere Status — Redirects, 304, 4xx, 5xx
— ergibt `Unavailable`, auch wenn der Body ein wohlgeformtes Key-Set enthielte.

`Content-Encoding` darf fehlen oder exakt `identity` sein, damit keine
Dekompression die Bytegrenze umgeht. `Content-Type` muss `application/json` sein
(Media Type case-insensitiv).

Ein `charset`-Parameter darf fehlen oder case-insensitiv `utf-8` sein, mit
**höchstens einem** Anführungszeichenpaar — also nur `charset=utf-8` oder
`charset="utf-8"`. Einseitig, mehrfach oder gar nicht zugewiesene Werte wie
`"utf-8`, `utf-8"`, `""utf-8""` und `charset=` werden abgewiesen, statt durch
Entfernen beliebig vieler Anführungszeichen normalisiert zu werden;
widersprechen sich mehrere Charset-Parameter, wird ebenfalls abgewiesen. Die
Dekodierung ist **strikt UTF-8 ohne Fallback**.

`Content-Length` wird nach erlaubtem OWS nur als ASCII-Ziffern akzeptiert und
über der Grenze vor dem Body abgewiesen.

**Genau ein JSON-Parse**, kein toleranter Fallback. Ein mehrfach vorkommender
Membername ergibt auf **jeder** Objektebene `Unavailable`, sonst entschiede die
Parser-Konvention „letzter Wert gewinnt" statt dieses Vertrags.

Die gesamte Parser- und Strukturgrenze ist neutralisiert: ungültiges UTF-8,
JSON-Syntaxfehler, ein `RecursionError` aus tief verschachteltem JSON — er erbt
von `RuntimeError`, nicht von `ValueError` — und jede andere normale Exception
aus Parser oder Duplikat-Hook ergeben dieselbe neue neutrale `Unavailable`. Eine
bereits erzeugte `Unavailable` wird unverändert weitergereicht, kein interner
Fehler erscheint als Cause oder Text.

Geprüft wird nur die Grundform: Top-Level ein JSON-Objekt, darin ein Feld
`keys`, das eine Liste ist, deren Einträge jeweils JSON-Objekte sind. **Keine**
`kid`-Auswahl und keine Prüfung von `kty`, `crv`, `use`, `key_ops` oder `alg`,
keine JWK-Konstruktion — das bleibt im Verifikationskern (LQ-164), der allein
entscheidet, welcher Schlüssel zu einem Token passt. Das einmal geparste Mapping
wird **semantisch unverändert** weitergegeben: Reihenfolge und unbekannte Felder
bleiben erhalten, ohne Normalisierung oder Rekonstruktion der Einträge.

## Neutralitäts- und Geheimnisgrenze

Jeder technische Fehler — Netzwerk, Stream, Status, Header, Encoding, Größe,
Uhr, UTF-8, JSON, doppelte Member, unbrauchbare Grundstruktur, unerwarteter
normaler Bibliotheksfehler — ergibt eine neue neutrale
`OidcVerificationUnavailable`, die nur ihren festen Code trägt. **Niemals**
weitergegeben: URL oder Query, Responsebody, Headerwerte, Providertext,
Schlüsselmaterial, Bibliotheksfehler und interne Exceptiontexte. Kein Logging
und keine Telemetrie.

## Nicht-Ziele

Kein Cache, keine TTL, kein Refresh bei unbekanntem `kid`, kein zweiter
JWKS-Request, keine stale-while-error-Regel, keine Persistenz, keine Discovery,
kein Tokenaustausch, keine ID-Token-Verifikation, keine Implementierung von
`OidcAuthorizationCodeVerifier`, keine Callback-Route, keine Session-/CSRF-
Ausgabe, keine Portänderung, keine Composition oder Production-Wiring, keine
neue Dependency und keine CI-, Container-, Deployment- oder Grype-Änderung.

Der Cache nach **LQ-160 §8** bleibt einem eigenen Slice vorbehalten: Er ist
zustandsbehaftet und braucht eigene Regeln gegen unbegrenzte Schlüsselsammlung,
gegen das Festhalten rotierter Schlüssel und gegen eine tokengesteuerte
Cache-Partition. Sein Refresh setzt zudem die `kid`-Auswahl voraus, die im
Verifikationskern liegt — dieser Loader kennt `kid` gar nicht.
