# LQ-167 — Single-Slot OIDC JWKS Cache

## Zweck und Signatur

Hält **höchstens ein** bereits kontrolliert geladenes JWKS-Dokument für die
aktive Konfiguration und begrenzt so, wie oft der LQ-166-Loader das Netz
berührt. **Kein** Refresh bei unbekanntem `kid`, **keine** Schlüsselauswahl,
**keine** ID-Token-Verifikation, **keine** LQ-157-Portimplementierung.

```python
# src/liquent_platform/identity/oidc_jwks_cache.py
class InMemoryOidcJwksCache:
    def __init__(self, loader, policy, monotonic=time.monotonic) -> None: ...
    def get_jwks(self, configuration) -> Mapping[str, object]: ...
```

Keine weitere öffentliche Methode, keine Resultatklasse, kein Port und keine
generische Cache- oder Loader-Abstraktion; der LQ-166-Loader wird injiziert.

## Zustand und Übergänge

Die Instanz hält genau zwei private Werte: `_slot` mit höchstens **einem**
Snapshot samt exakter `jwks_uri` und monotoner Ablaufgrenze, und `_last_clock`
mit höchstens **einem** technischen Monotonic-Wert. `_last_clock` ist kein
zweiter Cache-Slot. Beides ist instanzlokal, es gibt keinen globalen Zustand.

| Von | Auslöser | Aktion | Nach |
|---|---|---|---|
| leer | `get_jwks` | Uhr lesen → **genau ein** `load_jwks` → Uhr erneut lesen → `expires_at = loaded_at + ttl` | gefüllt |
| leer | Ladefehler | nichts speichern | leer |
| gefüllt | URI bytegleich **und** `now < expires_at` | kein Loader-Aufruf, Snapshot zurück | gefüllt |
| gefüllt | `now >= expires_at` | Slot **vor** dem Laden verwerfen, einmal laden | gefüllt bzw. leer |
| gefüllt | bytegenau andere `jwks_uri` | Slot **vor** dem Laden verwerfen, einmal laden | gefüllt bzw. leer |
| gefüllt | unbrauchbare Uhr | Slot verwerfen, neutral fehlschlagen | leer |

Verworfen wird immer **vor** dem Ladeversuch, damit ein Fehler nie stale
Schlüssel übriglässt; ein neuer Slot entsteht nur nach vollständigem Erfolg.

## Warum genau ein Slot

Es gibt **eine** aktive OIDC-Konfiguration; Multi-Issuer bleibt vertagt.
LQ-160 §8 verlangt „keine unbeschränkte Schlüssel- oder Issuer-Sammlung" — ein
einzelner Slot erfüllt das **strukturell** statt durch eine Eviction-Regel, die
man falsch konfigurieren kann. Rotierte Konfigurationen sammeln nichts an, weil
jede neue URI die vorige verdrängt, und da der Slot an die **konfigurierte** URI
gebunden ist, kann kein Token eine eigene Cache-Partition anlegen.

## Zeit- und TTL-Grenze

Ausschließlich die injizierte monotone Uhr und `policy.jwks_cache_ttl`. Die
Ablaufgrenze wird **nach** erfolgreichem Laden gestempelt, damit Netzwerkzeit
nicht als Frischezeit verkauft wird. Frisch ist nur `now < expires_at`; exakt
auf der Grenze gilt der Eintrag als abgelaufen.

Jeder Read einer Instanz muss `>= _last_clock` sein, Gleichstand ist zulässig.
Ein unbrauchbarer Wert (`bool`, Nicht-Zahl, `NaN`, unendlich), ein Rückwärts-
sprung oder eine normale Clock-Exception verwerfen den Slot und ergeben neutral
`OidcVerificationUnavailable`: Eine Uhr, die Frische nicht entscheiden kann,
darf nichts servierbar zurücklassen. Ist `loaded_at + ttl` nicht endlich, wird
neutral abgebrochen und kein Slot gesetzt. Keine versteckte Systemuhr. Die
Netzwerk- und Gesamtdeadline bleibt Sache des LQ-166-Loaders.

## Fehler-, Geheimnis- und Mapping-Grenze

Ein `OidcVerificationUnavailable` des Loaders wird neutral weitergereicht, jede
andere normale Exception in eine **neue** neutrale übersetzt, ohne Details oder
Cause. In beiden Fällen bleibt der Cache leer; kein Retry, keine
Wiederherstellung eines alten Slots. `BaseException` wird nicht abgefangen.
Cache-URI, Schlüssel und Mapping erscheinen nie in `repr`, Exceptions, Logs oder
Telemetrie.

Der Cache verändert das Mapping nicht: keine Normalisierung, Schlüsselwahl,
JWK-Konstruktion, Neuparsung oder Serialisierung. Bei frischen Treffern wird
derselbe Snapshot zurückgegeben, weil die heutigen internen Nutzer ihn **nur
lesen** — der Verifikationskern greift lesend zu und kopiert einen ausgewählten
JWK, bevor er ihn an die Bibliothek gibt. Das gilt für diese interne, read-only
Nutzung und ist **keine allgemeine öffentliche Mutabilitätsgarantie**.

## Warum noch kein Refresh bei unbekanntem `kid`

`verify_oidc_id_token(...)` liefert für **jede** belastbare Ablehnung dasselbe
neutrale `None` — fehlender eindeutiger Schlüssel ebenso wie Signatur-,
Algorithmus-, Claim-, Issuer-, Audience- oder Nonce-Fehler. Ein Aufrufer kann
daraus nicht erkennen, ob speziell ein unbekanntes `kid` vorlag.

Ein Refresh darauf zu stützen hieße entweder, diesen Grund nach außen sichtbar
zu machen — ein Bestandsleck, das preisgäbe, welche `kid` das vertrauenswürdige
Set kennt — oder bei jeder Ablehnung nachzuladen, was über beliebige Tokens
einen Netzwerk-Amplifier ergäbe. Die Entscheidung gehört **modulintern** in
einen späteren Adapter. Daher hier: kein tokengesteuerter Refresh, kein
Tokenheader-Parsing, keine Änderung des Verifikationsresultats, kein neuer
Ablehnungsgrund, keine zweite Netzwerkabfrage.

## Nicht-Ziele

Kein Multi-URI-Cache, keine konfigurierbare Kapazität, kein LRU, kein
persistenter oder verteilter Cache, kein stale-while-error, kein
Background-Refresh, kein Locking, kein Refresh bei unbekanntem `kid`, kein
Tokenheader-Parsing, kein Token-Endpunkt-Aufruf, keine ID-Token-Verifikation,
keine LQ-157-Portimplementierung, keine Callback-Route, keine Session-/CSRF-
Ausgabe, keine Composition oder Production-Wiring, keine neue Dependency und
keine CI-, Container-, Deployment- oder Grype-Änderung.
