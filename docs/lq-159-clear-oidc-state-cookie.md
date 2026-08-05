# LQ-159 — Clear OIDC State Cookie

## Ergebnis

Der in **LQ-158 §8** spezifizierte Löschhelfer für das
OIDC-Browserbindungs-Cookie, umgesetzt als eine Funktion neben dem vorhandenen
Setter in `src/liquent_platform/transport/http/oidc_state_cookie.py`.

```python
def clear_oidc_state_cookie(response: Response) -> None: ...
```

## Slot und Attribute

Der Helfer löscht **exakt denselben einzelnen Slot**, den
`set_oidc_state_cookie` schreibt:

| Attribut | Wert |
|---|---|
| Name | `OIDC_STATE_COOKIE_NAME` (`__Host-liquent_oidc_state`) |
| `Path` | `/` |
| `Domain` | **kein** |
| `Secure` | ja |
| `HttpOnly` | ja |
| `SameSite` | `Lax` |

Zusätzlich setzt er `Cache-Control: no-store`.

Ein Browser ordnet eine Löschung über Name, `Path` und `Domain` zu. Wiche die
Löschung dort ab, bliebe das ursprüngliche Cookie als wiederverwendbarer
Bindungsnachweis bestehen. Der Name stammt deshalb aus der gemeinsamen
Konstante.

## Reine Response-Mutation

Der Helfer nimmt nur `response`, gibt `None` zurück und braucht weder Uhr noch
Lebensdauer noch State-Wert. Er liest **kein** Request-Cookie und entscheidet
nicht, ob eines vorhanden war — er ist damit kein Bestandsorakel.

## Aufrufreihenfolge

**Ob und wann** der Helfer aufgerufen wird, entscheidet erst der spätere
Callback-Slice. Unverändert gilt **LQ-158 §7**: Aufruf **erst nach
erfolgreichem State-/Cookie-Match** und danach auf jedem weiteren Endpfad; ein
**fehlendes** Cookie und ein **Mismatch** führen **nicht** zum Aufruf, weil ein
Schreiben auf diesen einzigen Slot sonst eine neuere, gültige Bindung löschen
könnte.

## Tests

`tests/test_oidc_state_cookie.py` — drei fokussierte Vertragstests:
vollständiger Löschvertrag inklusive `Cache-Control`, Signaturgrenze, und der
Nachweis, dass Setter und Löscher denselben Slot adressieren. Cookie-Attribute
werden semantisch über `SimpleCookie` verglichen, nicht über Headerreihenfolge.

## Nicht-Ziele

Kein Callback, kein Callback-Use-Case, keine Route, kein Verifier-Adapter, kein
Claim-Aufruf, keine Queryverarbeitung, kein Request-Cookie-Lesen, keine
Identitätsauflösung, keine Admission-Verarbeitung, keine Session-Erzeugung, kein
Redirect, kein globaler Error-Handler, keine Änderung an `app.py`, an
Identity-Ports oder Adaptern, am Session-Cookie-Helfer oder am
`liquent_session`-Cookie, keine Persistenz, kein Production-Wiring und keine
CORS-, Deployment-, CI-, Container-, Dependency- oder Grype-Änderung.

## Nächster Schritt

Unverändert die Reihenfolge aus LQ-158 §15, alle noch nicht begonnen:
Verifikationsadapter, transportfreier Callback-Anwendungsfall, Session-/
CSRF-Ausgabeentscheidung, validierte interne Ziele und zuletzt die
Callback-Route, die diesen Helfer dann aufruft.
