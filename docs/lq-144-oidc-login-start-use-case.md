# LQ-144 — OIDC Login Start Use Case

## Ergebnis

Ein transportfreier Anwendungsfall startet genau **eine** serverseitige
OIDC-Login-Transaktion: Material erzeugen, Pending-Record bauen, atomar über den
bestehenden Creation-Port (LQ-142/LQ-143) ablegen und ausschließlich das
öffentliche Material für den späteren Authorization Request zurückgeben.

**Keine** Login-Start-Route, **keine** Callback-Route, **keine**
Authorization-URL, **kein** Provider, **kein** Wiring.

## Signaturen

```python
@dataclass(frozen=True, slots=True)
class StartedOidcLogin:
    state: str = field(repr=False)
    nonce: str = field(repr=False)
    code_challenge: str


def start_oidc_login(
    store: OidcLoginTransactionCreationStore,
    generator: SecureOidcLoginMaterialGenerator,
    *,
    expected_issuer: str,
    redirect_uri: str,
    now: datetime,
    lifetime: timedelta,
    admission_id: IdentityAdmissionId | None = None,
    return_path: str | None = None,
) -> StartedOidcLogin: ...


class OidcLoginStartConflict(Exception):
    code = "oidc_login_start_conflict"
```

## Ablauf

1. `lifetime` strikt positiv? Sonst `ValueError`.
2. `now` timezone-aware? Sonst `ValueError`.
3. `generator.new_login_material()` — **genau einmal**.
4. `PendingOidcLoginTransaction` bauen.
5. `store.add_transaction(OidcLoginState(material.state), pending)` — **genau
   einmal**.
6. `True` → `StartedOidcLogin`; `False` → `OidcLoginStartConflict`.

## Datenzuordnung

| Ziel im Pending-Record | Quelle |
|---|---|
| `expected_issuer` | Aufrufparameter, verbatim |
| `expected_nonce` | `material.nonce` |
| `code_verifier` | `material.code_verifier` |
| `redirect_uri` | Aufrufparameter, verbatim |
| `created_at` | `now` |
| `expires_at` | exakt `now + lifetime` |
| `admission_id` | Aufrufparameter, verbatim (Default `None`) |
| `return_path` | Aufrufparameter, verbatim (Default `None`) |

| Ziel im Rückgabeobjekt | Quelle |
|---|---|
| `state` | `material.state` |
| `nonce` | `material.nonce` |
| `code_challenge` | `material.code_challenge` |

Der **Store-Key** ist `OidcLoginState(material.state)`. Es wird **nichts**
normalisiert, getrimmt oder abgeleitet.

`material.code_challenge` wandert **ausschließlich** ins Rückgabeobjekt und wird
**nicht** redundant im Pending-Record gespeichert — der Record hält dieses Feld
gemäß LQ-138 bewusst nicht.

## Schutz von Code-Verifier und Admission-ID

- Der `code_verifier` ist **kein** Feld von `StartedOidcLogin`. Er existiert nur
  im serverseitigen Pending-Record und verlässt den Server nie.
- Die `admission_id` ist ebenfalls **kein** Rückgabefeld. Die Admission-Bindung
  wird serverseitig am Callback aufgelöst und reist nicht mit dem Browser.
- `state` und `nonce` **müssen** den Browser erreichen, um wirksam zu sein,
  bleiben aber sensible Login-Korrelationswerte und sind daher **repr-frei**.
  `code_challenge` ist kein Geheimnis und darf im `repr` erscheinen.
- Das Rückgabeobjekt trägt **keine** Tokens, Claims, User-, Workspace-, Rollen-
  oder Session-Daten und erzeugt **keine** URL.

## Zeitgrenze

- `lifetime` muss strikt positiv sein; `timedelta(0)` und negative Werte →
  `ValueError`.
- `now` muss timezone-aware sein; naives `now` → `ValueError`.
- `expires_at` ist exakt `now + lifetime`. **Keine** Obergrenze in diesem Slice.
- Der Anwendungsfall liest **keine** eigene Systemuhr; `now` wird injiziert.

Beide Prüfungen laufen **vor** der Materialerzeugung. Das ist **keine**
überflüssige Duplizierung der Record-Validierung: `PendingOidcLoginTransaction`
prüft dieselben Bedingungen erst **nach** dem Generatoraufruf, es würde also
unnötig Entropie gezogen und der ungültige Aufruf wäre nicht wirkungsfrei. Alle
übrigen Feldinvarianten — leerer Issuer, leere Redirect-URI, leerer
`return_path`, `expires_at > created_at`, Awareness beider Zeitstempel —
bleiben **ausschließlich** beim Wertobjekt und werden hier **nicht** wiederholt.
`StartedOidcLogin` hat aus demselben Grund **kein** `__post_init__`: seine Werte
stammen ausschließlich aus dem bereits validierten `OidcLoginMaterial`.

## Konfliktverhalten

- Ein neutrales `False` des Stores wird zu `OidcLoginStartConflict`.
- Der Fehler trägt **kein** State, Nonce, Verifier, Issuer, Redirect-URI oder
  Admission-ID und unterscheidet **nicht** zwischen „noch pending" und „bereits
  verbraucht" — die Neutralität des Ports wird unverändert weitergereicht.
- **Kein** Retry, **kein** zweiter Generator- oder Store-Aufruf.
- **Keine** Teilerfolgsmeldung: bei Ablehnung wird nichts zurückgegeben.
- Der Store-Aufruf ist **nicht** in `try`/`except` gekapselt, damit eine echte
  Store-Ausnahme unverändert propagiert und **nicht** als fachlicher Konflikt
  umgedeutet wird.

## Getroffene Einordnungsentscheidungen

- **Kein neuer Port.** In `identity/ports.py` existiert für OIDC-Material kein
  Generator-Protokoll (nur `BrowserSessionMaterialGenerator` für Sessions). Der
  Parameter ist daher mit dem **konkreten** `SecureOidcLoginMaterialGenerator`
  annotiert; Test-Doubles werden strukturell per Duck Typing eingesetzt. Ein
  eigenes Protokoll wäre für diesen Slice nicht erforderlich.
- **`StartedOidcLogin` liegt in der Anwendungsschicht**, nicht in `identity/`.
  Die Identity-Modelle, Ports und Adapter bleiben unverändert, und die
  Anwendungsschicht definiert bereits eigene `frozen`-Dataclasses
  (`health.py`, `experiment.py`, `ports.py`).
- **Eigene Fehlerdatei `application/oidc_login_errors.py`.** Das Projekt trennt
  neutrale Fehler nach Domäne (`authorization_errors.py`,
  `session_lifecycle_errors.py`). `SessionLifecycleConflict` würde die
  Browser-Session-Grenze mit dem OIDC-Login vermischen. Das Muster ist
  identisch: `code`-Klassenattribut, argumentloser `__init__`, keine Details.

## Tests

`tests/test_start_oidc_login.py` — 24 fokussierte Tests.

**Erfolgsfall:** genau ein Pending-Record · Generator genau einmal · Store genau
einmal · State-Key exakt der generierte State · Nonce und Verifier exakt aus dem
Generator · Issuer und Redirect-URI verbatim · `created_at`/`expires_at` exakt ·
Admission-ID identisch gebunden · `return_path` verbatim · beide Optionalwerte
ohne Angabe `None`.

**Rückgabe:** exakt State, Nonce und Code-Challenge · Feldliste exakt
`["state", "nonce", "code_challenge"]` (damit zugleich **keine**
Authorization-URL und **keine** weiteren Protokollparameter) · weder
`code_verifier` noch `admission_id` als Attribut oder im `repr` · `repr`
verbirgt State und Nonce, zeigt die Challenge · unveränderlich.

**Zeitgrenze:** positive Laufzeit akzeptiert · `timedelta(0)` und negative
Laufzeit abgewiesen · naives `now` abgewiesen · bei beiden ungültigen
Zeitgrenzen werden **weder** Generator **noch** Store aufgerufen.

**Konflikt:** abgelehnter Store → `OidcLoginStartConflict` · der Fehler enthält
keinen der sechs sensiblen Werte und führt den neutralen `code` · kein Retry
(Generator und Store je genau ein Aufruf) · eine Store-`RuntimeError`
propagiert unverändert und wird nicht zum Konflikt umgedeutet.

Es gibt **keine** globalen AST-, Import- oder Substring-Verbote über ganze
Module; geprüft wird ausschließlich der LQ-144-Vertrag.

## Bewusst nicht enthalten

- keine Login-Start-Route, keine Callback-Route,
- keine Authorization-URL-Erzeugung,
- kein konkreter Identity Provider, keine OIDC-/OAuth-Bibliothek,
- keine Discovery-, JWKS-, Token- oder Claim-Verarbeitung,
- keine aktuelle Issuer-Trust-Prüfung (bleibt beim Callback),
- keine Admission-Erzeugung oder -Validierung,
- keine Workspace-Mitgliedschaft oder Autorisierung,
- keine Liquent-Session-Erzeugung,
- keine Validierung des `return_path` (die aufrufende Grenze muss laut LQ-138
  einen bereits geprüften internen relativen Pfad liefern),
- keine Obergrenze für die Lebensdauer,
- keine Datenbank, Migration oder Produktionspersistenz,
- kein Production-Wiring, kein Deployment,
- keine Änderung an CI oder Grype,
- kein Retry-Mechanismus, keine Threads oder Locks,
- keine Änderung an bestehenden Identity-Modellen, Ports oder Adaptern.

## Nächster Schritt

Ein späterer Slice kann den Authorization Request formen — Provider-Konfiguration
und Issuer-Trust, daraus die Authorization-URL aus `state`, `nonce`,
`code_challenge` und `S256` — oder den Callback-Anwendungsfall, der die
Transaktion über den Claim-Port genau einmal einlöst.
