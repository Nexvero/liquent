# LQ-162 — OIDC Verification Policy

## Ergebnis

Ein kleines, providerneutrales Wertobjekt für die technischen Grenzen, die
LQ-160 verbindlich verlangt. Es wird dem späteren Adapter per **Composition**
übergeben.

**Kein** Netzwerkcode, **kein** Adapter, **kein** HTTP-Client, **kein** Cache.

## Signatur

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

Exakt sechs Felder in dieser Reihenfolge, **keine Defaults**, unveränderlich,
`slots`, hashbar.

## Invarianten

| Gruppe | Regel |
|---|---|
| Zeitwerte | echtes `timedelta`, **strikt positiv**, verbatim gespeichert |
| Relation | `connect_timeout <= total_timeout` und `read_timeout <= total_timeout` |
| Größenwerte | echtes `int`, **`bool` ausdrücklich abgelehnt**, strikt positiv |

**Keine Aussage `connect + read <= total`.** Die tatsächliche Ablaufsteuerung
entscheidet das spätere Deadline-Modell; dieses Objekt legt nur die einzelnen
Obergrenzen fest.

`bool` wird gesondert abgewiesen, weil es eine `int`-Unterklasse ist und `True`
sonst stillschweigend „ein Byte" bedeuten würde.

### Endlichkeit ist durch den Typ garantiert

Die Forderung „endlich und vollständig in Mikrosekunden darstellbar" wird durch
die **Typprüfung selbst** erfüllt und **nicht** durch eine zusätzliche Prüfung:
Ein `timedelta` kann weder unendlich noch `NaN` sein —
`timedelta(seconds=float("inf"))` löst `OverflowError` aus, `NaN` löst
`ValueError` aus — und der Typ ist begrenzt (`timedelta.min`/`max`) mit
Mikrosekundenauflösung. Eine separate Endlichkeitsprüfung wäre **unerreichbarer
Code**.

Sub-Mikrosekunden-Eingaben rundet `timedelta` bereits **bei der Konstruktion
durch den Aufrufer**: `timedelta(microseconds=0.4)` ist `timedelta(0)` und
scheitert damit an der Positivitätsregel. Eine Dauer, die zu klein für jede
Wirkung wäre, kann so nicht durchrutschen. **Das Modell selbst normalisiert
nichts.**

## Keine Defaults und keine willkürlichen Obergrenzen

- **Keine Defaults:** Ein Default-Timeout oder eine Default-Größe wäre eine
  betriebliche Entscheidung, die niemand bewusst getroffen hat. Jeder Wert muss
  bei der Composition ausdrücklich angegeben werden.
- **Keine Obergrenzen:** keine hartcodierte Maximalzahl für Bytes, keine
  maximale Timeout- oder Cache-Dauer, keine produktspezifischen Werte.

LQ-162 prüft **strukturelle Gültigkeit** — dass jede Grenze vorhanden, endlich
und positiv ist — **nicht** betriebliches Tuning. Konkrete Werte kommen später
ausschließlich aus der Composition und werden dort separat geprüft.

## Sicherheitsgrenze

Das Modell enthält **ausschließlich technische Limits**: keine URL, keinen
Issuer, Client, Redirect, Algorithmus, Schlüssel, Token, Code, Nonce, State,
Identity, Admission, Session oder Providerdaten.

Es führt **keine Uhrabfrage** und **keine Netzwerkoperation** aus, baut **kein**
`httpx2.Timeout`, implementiert **keinen** Cache und entscheidet **keine**
Retry- oder Redirect-Policy. All das tut der Adapter — begrenzt durch diese
Werte.

Fehlermeldungen nennen den **Feldnamen**, geben aber **niemals** den Wert
wieder.

## Verhältnis zu LQ-160 und LQ-161

- **LQ-160** verlangt Redirect-Verbot, explizite Verbindungs-, Lese- und
  Gesamtzeitgrenzen, begrenzte Antwortgröße und einen zeitlich begrenzten
  JWKS-Cache. LQ-162 macht **genau diese Grenzen** zu einem expliziten,
  überprüfbaren Eingabewert statt zu impliziten Konstanten im Adapter.
- **LQ-161** hat `PyJWT[crypto]` und `httpx2` als Laufzeitbasis aufgenommen.
  LQ-162 nutzt **keine** davon: Das Modul importiert ausschließlich
  `dataclasses` und `datetime`.
- Das Redirect-Verbot selbst ist **keine** Zahl und deshalb **kein** Feld dieses
  Objekts; es bleibt eine Adapterregel aus LQ-160 §4.

## Bewusst nicht enthalten

- kein Verifikationsadapter, kein HTTP-Client, kein Tokenaustausch,
- kein JWKS-Fetch und kein Cache, kein JWT-/JOSE-Aufruf,
- kein Retry und kein Redirect,
- keine Portänderung, keine Änderung an `TrustedOidcClientConfiguration`,
- keine Route oder Callback-Logik, kein Production-Wiring,
- keine Dependency-, Lockfile-, CI-, Container-, Grype- oder
  Deployment-Änderung.

## Nächster Schritt

Unverändert die Reihenfolge aus LQ-158 §15 — **alle noch nicht begonnen**: der
Verifikationsadapter nach LQ-160, der diese Policy entgegennimmt, danach der
transportfreie Callback-Anwendungsfall, die Session-/CSRF-Ausgabeentscheidung,
validierte interne Ziele und zuletzt die Callback-Route.
