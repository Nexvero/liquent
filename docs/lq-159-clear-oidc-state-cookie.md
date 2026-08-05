# LQ-159 — Clear OIDC State Cookie

## Ergebnis

Der in **LQ-158 §8** bereits spezifizierte Löschhelfer für das
OIDC-Browserbindungs-Cookie, umgesetzt als **eine** kleine Funktion neben dem
vorhandenen Setter.

**Kein** Callback, **kein** Verifier-Adapter, **kein** Use-Case, **keine**
Route, **kein** neuer Port und **keine** neue Abstraktion.

## Signatur

`src/liquent_platform/transport/http/oidc_state_cookie.py`

```python
def clear_oidc_state_cookie(response: Response) -> None: ...
```

Genau **ein** Parameter, Rückgabe **`None`**.

## Derselbe Cookie-Slot, dieselben Attribute

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

Zusätzlich setzt er:

```
Cache-Control: no-store
```

**Warum die Attribute exakt übereinstimmen müssen:** Ein Browser ordnet eine
Löschung über Name, `Path` und `Domain` zu. Wiche die Löschung in einem dieser
Punkte ab, bliebe das ursprüngliche Cookie **unverändert bestehen** — und damit
ein wiederverwendbarer Bindungsnachweis, während der Server die Löschung für
erledigt hielte. Der Name stammt deshalb aus der **gemeinsamen Konstante** und
nicht aus einem wiederholten Literal.

Der Slot ist derselbe wie beim Setzen, weil es laut LQ-152 §9 genau **einen**
gibt: gleicher Name, `Path=/`, kein `Domain`.

## Reine Response-Mutation

Der Helfer:

- nimmt **keine** Parameter außer `response`,
- gibt **nichts** außer `None` zurück,
- braucht **keine Uhr**, **keine Lebensdauer** und **keinen State-Wert**,
- **liest kein** Request-Cookie,
- **prüft und entscheidet nicht**, ob überhaupt ein Cookie vorhanden war,
- enthält **keine** Callback-, Claim-, Query-, Verifier-, Identity-,
  Admission-, Session- oder Redirect-Logik,
- **loggt nichts** und erzeugt **keine** Telemetrie.

### Kein Cookie-Bestandsorakel

Weil der Helfer das Request-Cookie **nicht liest** und **keine** Fallunter-
scheidung trifft, sieht sein Ergebnis **identisch** aus, ob der Browser ein
Cookie gesendet hat oder nicht — nachgewiesen über zwei Aufrufe mit
byteweise gleichem `Set-Cookie`-Header. Ein Aufruf verrät damit **nichts** über
den Bestand einer Login-Transaktion.

## Keine Callback-Reihenfolge in diesem Slice

**Ob und wann** der Helfer aufgerufen wird, entscheidet **erst ein späterer
Callback-Slice**. LQ-159 stellt ausschließlich die Response-Mutation bereit.

Für den späteren Aufruf gilt unverändert **LQ-158 §7**:

- Verwendung **erst nach erfolgreichem State-/Cookie-Match**,
- danach auf **jedem** weiteren Endpfad,
- ein **fehlendes** Cookie und ein **Mismatch** führen **gerade nicht** zum
  Aufruf.

Das ist kein Detail: Ein `Set-Cookie` mit Ablauf in der Vergangenheit ist eine
**Schreiboperation auf denselben einzigen Slot**. Bei einem Mismatch gehört das
vorhandene Cookie typischerweise zu einer **neueren, legitimen** Transaktion —
sie zu löschen wäre ein Login-Denial-of-Service, ausgelöst von einem Aufruf, der
die Bindungsprüfung gerade **nicht** bestanden hat.

## Keine Änderung am Session-Cookie

`set_oidc_state_cookie` bleibt semantisch **unverändert**. Der Helfer
`clear_session_cookie` in `transport/http/session_cookie.py` dient nur als
**strukturelles Vorbild** und wurde **nicht angefasst**; das
`liquent_session`-Cookie bleibt vollständig unberührt.

`app.py` wurde **nicht** geändert — die Route, die den Helfer später aufruft,
existiert noch nicht.

## Tests

`tests/test_oidc_state_cookie.py` — **29** fokussierte Tests. Cookie-Attribute
werden **semantisch** über `http.cookies.SimpleCookie` verglichen, **nicht**
über Headerreihenfolge oder Substringsuche.

**Löschen:** Rückgabe `None` · Name exakt `__Host-liquent_oidc_state` und aus
der gemeinsamen Konstante · leerer Wert · `Max-Age=0` plus vorhandenes
`expires` (sofortiger Ablauf) · `Path=/` · `Secure` · `HttpOnly` · `SameSite`
case-insensitiv `lax` · **kein** `Domain` (Attribut leer **und** kein
`domain=` im Header) · `Cache-Control` exakt `no-store` · genau **ein**
`Set-Cookie`-Header · `liquent_session` kommt im Header nicht vor.

**Signaturgrenze:** Parameter exakt `["response"]` · Rückgabeannotation `None` ·
acht verbotene Parameternamen (`now`, `clock`, `lifetime`, `expires`,
`max_age`, `state`, `state_value`, `value`) abwesend · aufrufbar, ohne dass
Uhr, Lebensdauer oder State verfügbar sein müssen.

**Kein Bestandsorakel:** zwei Aufrufe erzeugen einen byteweise identischen
`Set-Cookie`-Header.

**Setter-Regression** (bisher gab es **keinen** direkten Helfertest; der Setter
war nur indirekt über die LQ-154-Routentests abgedeckt): derselbe Slot mit
`Secure`, `HttpOnly`, `SameSite`, `Path=/`, ohne `Domain`, mit dem exakten
State als Wert · `Max-Age` bleibt durch die Lebensdauer begrenzt · **Setter und
Löscher adressieren nachweislich denselben Slot** (Name, `Path`, fehlendes
`Domain`, `Secure`, `HttpOnly`, `SameSite`) · der gelöschte Slot trägt den State
nicht mehr.

Es gibt **keine** Tests, die das gesamte Modul, seine Importe oder globale
AST-/Substring-Eigenschaften festschreiben; geprüft wird ausschließlich der
konkrete Helfervertrag.

**Gegenproben:** Ein abweichender `Path`, ein hinzugefügtes `Domain`, ein
fehlendes `HttpOnly` und ein fehlendes `Cache-Control: no-store` lassen jeweils
genau die zugehörigen Tests scheitern — der Slot-Gleichheitstest schlägt bei
den ersten drei mit an. Das Entfernen des expliziten `path="/"` ist dagegen
**kein** wirksamer Mutant, weil `delete_cookie` diesen Wert bereits als Default
führt; das wurde geprüft und ist keine Testlücke.

## Bewusst nicht enthalten

- kein Callback, kein Callback-Use-Case, keine Route,
- kein Verifier-Adapter, kein Tokenaustausch,
- kein Claim-Aufruf, keine Queryverarbeitung, kein Request-Cookie-Lesen,
- keine Identitätsauflösung, keine Admission-Verarbeitung, keine
  Session-Erzeugung, kein Redirect,
- kein globaler Error-Handler, keine Änderung an `app.py`,
- keine Änderung an Identity-Ports oder Adaptern,
- keine Änderung am Session-Cookie-Helfer oder am `liquent_session`-Cookie,
- keine Persistenz, kein Production-Wiring,
- keine CORS-, Deployment-, CI-, Container-, Dependency- oder Grype-Änderung.

## Nächster Schritt

Unverändert die Reihenfolge aus LQ-158 §15 — **alle noch nicht begonnen**: der
Verifikationsadapter, danach der transportfreie Callback-Anwendungsfall, die
Session-/CSRF-Ausgabeentscheidung nach OIDC-Navigation, validierte interne
Ziele und **erst zuletzt** die Callback-Route, die diesen Helfer dann gemäß
LQ-158 §7 aufruft.
