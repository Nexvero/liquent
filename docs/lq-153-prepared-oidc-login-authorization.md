# LQ-153 — Prepared OIDC Login Authorization

## Ergebnis

**Ergebnisgrenzen-Erweiterung von LQ-151.** `prepare_oidc_login_authorization`
liefert nicht mehr nur die fertige `OidcAuthorizationRequest`, sondern
zusätzlich exakt den dazugehörigen `OidcLoginState`.

Dieser Slice ist die **notwendige Vorbedingung** für die in LQ-152 festgelegte
Login-Start-Route: Der spätere Handler braucht beides — die URL zum Weiterleiten
und den State für das Binding-Cookie.

**Keine** Route, **kein** Cookie, **kein** Callback.

## Signatur

`src/liquent_platform/application/prepare_oidc_login_authorization.py`

```python
@dataclass(frozen=True, slots=True)
class PreparedOidcLoginAuthorization:
    request: OidcAuthorizationRequest
    state: OidcLoginState = field(repr=False)


def prepare_oidc_login_authorization(
    configuration_lookup: ActiveOidcClientConfigurationLookup,
    transaction_store: OidcLoginTransactionCreationStore,
    generator: SecureOidcLoginMaterialGenerator,
    *,
    now: datetime,
    lifetime: timedelta,
    admission_id: IdentityAdmissionId | None = None,
    return_path: str | None = None,
) -> PreparedOidcLoginAuthorization: ...
```

Die **Eingabesignatur bleibt unverändert**; nur der Rückgabetyp ändert sich. Das
Modell liegt im bestehenden Modul — **kein** neues Modul, konsistent damit, dass
`OidcAuthorizationRequest` in `build_oidc_authorization_request.py` und
`StartedOidcLogin` in `start_oidc_login.py` liegen.

## Der Handler darf den State niemals aus der URL parsen

Die Authorization-URL **enthält** den State als Queryparameter. Ihn dort wieder
herauszulesen wäre eine **zweite und schwächere Quelle** für einen
sicherheitskritischen Wert: abhängig von Encoding, Parserverhalten und
Parameterreihenfolge, und ohne jede Garantie, dass er mit dem gespeicherten
Transaktionsschlüssel übereinstimmt. LQ-153 gibt ihn deshalb **direkt** heraus.

**Woher der Wert kommt:** `StartedOidcLogin.state` ist ein `str`; den Store-Key
bildet `start_oidc_login` intern als `OidcLoginState(material.state)`. Die
Orchestrierung reicht **denselben verbatim String** weiter:

```python
request = build_oidc_authorization_request(configuration, started)
return PreparedOidcLoginAuthorization(request, OidcLoginState(started.state))
```

Das ist **keine** Ableitung, **keine** Normalisierung und **keine** Kopie eines
anderen Werts, sondern das Verpacken exakt desselben opaken Strings in das
vorhandene Wertobjekt. Verifiziert: Das Ergebnis ist `==` zum Store-Key, hat
denselben Hash und denselben `.value`.

**Warum nicht `StartedOidcLogin.state` direkt auf `OidcLoginState` umstellen:**
Das wäre eine Änderung an LQ-144 und würde den LQ-147-Builder brechen, der den
String für `urlencode` benötigt. Bewusst nicht getan.

## Konsistenz eines Starts

Derselbe opake State wird durchgängig verwendet für:

| Verwendung | Quelle |
|---|---|
| Schlüssel der gespeicherten Pending-Transaktion | `OidcLoginState(material.state)` in LQ-144 |
| `state`-Parameter der Authorization Request | `started.state` in LQ-147 |
| `PreparedOidcLoginAuthorization.state` | `OidcLoginState(started.state)` |

Alle drei stammen aus **einem** Generatoraufruf innerhalb **eines** Starts.

## Geheimnisgrenze

- `state` ist im `repr` des Ergebnisobjekts **vollständig verborgen**.
- Die Authorization-URL bleibt durch den bestehenden
  `OidcAuthorizationRequest`-Vertrag ebenfalls repr-frei.
- Praktisch lautet der `repr`:
  `PreparedOidcLoginAuthorization(request=OidcAuthorizationRequest())` — weder
  State noch URL erscheinen.
- `.state.value` bleibt für die spätere Transportgrenze **exakt** verfügbar.

Der State ist ein **kurzlebiger Browser-Bindungswert**. Er muss protokollbedingt
zum Browser gelangen, bleibt aber ein sensibler Korrelationswert und darf nicht
über Objektrepräsentationen in Logs oder Fehlerdiagnosen geraten.

## Das Objekt autorisiert nichts

Es enthält **ausschließlich** `request` und `state` — **keine** Nonce, **keinen**
Code-Verifier, **keine** Code-Challenge, **keine** Admission-ID, **keinen**
Return-Path, **keine** Client-Konfiguration, **keine** Pending-Transaktion,
**keine** Tokens, Claims, Identitäts-, User-, Workspace- oder Session-Daten.

Es ist **kein** Authentifizierungsnachweis und erteilt **keine** Berechtigung.

## Unverändert gegenüber LQ-151

Aufrufreihenfolge, Fehlerarten und Aufrufzahlen bleiben exakt gleich:

1. aktive Konfiguration lesen (genau einmal),
2. Login-Material erzeugen bzw. Login-Transaktion starten,
3. atomar speichern,
4. Authorization Request bauen.

Fehlende Konfiguration → weiterhin `OidcLoginUnavailable`. Store-Konflikt →
weiterhin `OidcLoginStartConflict`. **Keine** zusätzliche Uhrabfrage, **kein**
zweiter Lookup, **kein** zweiter Generatoraufruf.

## Tests

`tests/test_prepare_oidc_login_authorization.py` — von 41 auf **61** fokussierte
Tests. Die bestehenden LQ-151-Tests wurden minimal an die neue Rückgabegrenze
angepasst (`prepared.request.url` statt `request.url`).

**Neu für LQ-153:** Ergebnis ist `PreparedOidcLoginAuthorization` mit
`OidcAuthorizationRequest` in `.request` · Dataclass ist `frozen` und nutzt
`slots` · Felder exakt `["request", "state"]` · unveränderlich
(`FrozenInstanceError`) · `.request` ist `is`-identisch das Builder-Ergebnis ·
`.state` ist `==` dem gespeicherten Transaktionsschlüssel · `.state.value`
stimmt mit dem **dekodierten** `state`-Queryparameter überein · `.state.value`
bleibt exakt verfügbar · `repr(result)` enthält weder State noch URL, wohl aber
den Klassennamen · zehn weitere Materialnamen sind parametrisiert als nicht
vorhanden belegt.

**Nachweis „kein URL-Parsing" über ein fokussiertes Double:** Der Builder wird
gepatcht und liefert eine URL, deren `state` **abweicht** — beziehungsweise eine
URL **ganz ohne** `state`-Parameter. In beiden Fällen bleibt `result.state` der
erzeugte State. Käme er aus der URL, müsste der Test scheitern. Kein globaler
AST- oder Substring-Test über ganze Module.

Reihenfolge, Aufrufzahlen, Fehlerpfade und Fehlercodes sind unverändert
abgesichert.

## Bewusst nicht enthalten

- keine Login-Start-Route,
- kein Cookie-Helfer und kein `Set-Cookie`,
- kein Callback,
- kein URL- oder Query-Parsing,
- keine Änderung an Ports oder Adaptern, kein neuer Store,
- keine OIDC-Bibliothek, Discovery, JWKS- oder Tokenlogik,
- keine Provider-Auswahl,
- keine Persistenz, Migration oder Production-Composition,
- keine CORS-, Deployment-, CI-, Container-, Dependency- oder Grype-Änderung.

## Nächster Schritt

Mit dieser Grenze ist die **LQ-152-Route** implementierbar: Sie setzt
`__Host-liquent_oidc_state` aus `prepared.state.value` und leitet per
`303 See Other` auf `prepared.request.url` weiter. Cookie-Erzeugung, Route und
Callback bleiben **spätere** Slices.
