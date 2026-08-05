# LQ-162 — OIDC Verification Policy

## Zweck

Ein kleines, providerneutrales Wertobjekt für die technischen Grenzen, die
LQ-160 verbindlich verlangt. Es wird dem späteren Adapter per **Composition**
übergeben, statt als implizite Konstante in ihm zu stehen.

`src/liquent_platform/identity/oidc_verification_policy.py`

```python
@dataclass(frozen=True, slots=True)
class OidcVerificationPolicy:
    connect_timeout: timedelta
    read_timeout: timedelta
    total_timeout: timedelta
    token_response_max_bytes: int
    jwks_response_max_bytes: int
    jwks_cache_ttl: timedelta
```

Exakt sechs Felder in dieser Reihenfolge, unveränderlich, `slots`, hashbar.

## Validierungsregeln

| Gruppe | Regel |
|---|---|
| Zeitwerte | echtes `timedelta`, **strikt positiv**, verbatim gespeichert |
| Relation | `connect_timeout <= total_timeout` und `read_timeout <= total_timeout` |
| Größenwerte | echtes `int`, **`bool` abgelehnt**, strikt positiv |

`bool` wird gesondert abgewiesen, weil es eine `int`-Unterklasse ist und `True`
sonst stillschweigend „ein Byte" bedeuten würde.

**Keine Regel `connect + read <= total`.** Die tatsächliche Ablaufsteuerung
entscheidet das spätere Deadline-Modell.

Fehlermeldungen nennen den Feldnamen, geben aber **nie** den Wert wieder.

## Keine Defaults und keine Obergrenzen

- **Keine Defaults:** Ein Default-Timeout oder eine Default-Größe wäre eine
  betriebliche Entscheidung, die niemand bewusst getroffen hat.
- **Keine Obergrenzen:** keine maximale Byteanzahl, Timeout- oder Cache-Dauer.

Geprüft wird **strukturelle Gültigkeit** — jede Grenze vorhanden und positiv —
**nicht** betriebliches Tuning. Konkrete Werte kommen aus der Composition und
werden dort geprüft.

## Verhältnis zu LQ-160 und LQ-161

- **LQ-160** verlangt explizite Zeitgrenzen, eine begrenzte Antwortgröße und
  einen zeitlich begrenzten JWKS-Cache. LQ-162 macht genau diese Grenzen zu
  einem expliziten, überprüfbaren Eingabewert.
- **LQ-161** hat `PyJWT[crypto]` und `httpx2` aufgenommen. LQ-162 nutzt beide
  **nicht**: Das Modul importiert nur `dataclasses` und `datetime`.
- Das **Redirect-Verbot** ist keine Zahl und deshalb kein Feld; es bleibt eine
  Adapterregel aus LQ-160 §4.

## Nicht-Ziele

Kein Verifikationsadapter, kein HTTP-Client, kein Tokenaustausch, kein
JWKS-Fetch oder Cache, kein JWT-/JOSE-Aufruf, kein Retry, kein Redirect, keine
Uhrabfrage, keine Portänderung, keine Änderung an
`TrustedOidcClientConfiguration`, keine Route oder Callback-Logik, kein
Production-Wiring und keine Dependency-, Lockfile-, CI-, Container-, Grype-
oder Deployment-Änderung.

## Nächster Schritt

Unverändert die Reihenfolge aus LQ-158 §15, alle noch nicht begonnen: der
Verifikationsadapter, der diese Policy entgegennimmt, danach der transportfreie
Callback-Anwendungsfall, die Session-/CSRF-Ausgabeentscheidung, validierte
interne Ziele und zuletzt die Callback-Route.
