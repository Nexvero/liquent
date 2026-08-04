# LQ-154 — OIDC Login Start Route

## Ergebnis

Umsetzung des LQ-152-Transportvertrags als **eine** Route:

```
POST /v1/session/oidc/login
```

Sie prüft die leere Eingabe und die Same-Origin-Grenze, liest die injizierte
Uhr **genau einmal**, ruft `prepare_oidc_login_authorization` (LQ-151/LQ-153)
**genau einmal** auf, setzt das Binding-Cookie ausschließlich aus
`prepared.state.value` und antwortet mit einem leeren `303 See Other` auf
`prepared.request.url`.

**Kein** Callback, **keine** Token-Einlösung, **keine** Claimprüfung, **keine**
Session, **keine** Admission-Verarbeitung, **kein** Return-Path, **keine** neuen
Ports, Stores oder Persistenz.

## Dependency-Grenze

`create_app` erhält sechs neue Schlüsselwortparameter. Die Route existiert
**nur**, wenn alle sechs explizit injiziert wurden:

```python
def create_app(
    ...,
    oidc_login_configurations: ActiveOidcClientConfigurationLookup | None = None,
    oidc_login_transactions: OidcLoginTransactionCreationStore | None = None,
    oidc_login_material: SecureOidcLoginMaterialGenerator | None = None,
    oidc_login_clock: Callable[[], datetime] | None = None,
    oidc_login_lifetime: timedelta | None = None,
    oidc_login_origin: str | None = None,
) -> FastAPI: ...
```

Die Default-App besitzt die Route damit **nicht** — ein `POST` darauf ist ein
gewöhnlicher `404`.

**Beim App-Aufbau mit `ValueError` abgelehnt:**

| Situation | Grund |
|---|---|
| irgendeine echte Teilmenge der sechs | halb konfigurierter Login-Start |
| `lifetime <= 0` | keine Transaktion ohne positive Lebensdauer |
| leere Origin | es gibt keine vertrauenswürdige Origin |
| Origin mit Leerraum oder Komma | ein Trennzeichen wäre eine geschmuggelte Liste |

Es gibt **keine** versteckte Systemuhr, **keine** Default-Origin und **keine**
Ableitung aus `Host`, `Forwarded`, `X-Forwarded-Host`, Query oder Body. Die
Route ist unauthentifiziert; ein Liquent-CSRF-Token existiert an dieser Stelle
noch nicht, deshalb trägt die Origin-Prüfung die gesamte Cross-Site-Abwehr.

Die Origin ist strukturell **genau eine**: ein einzelner `str`, exakt
verglichen. Ein Wert mit Trennzeichen würde nie matchen und damit still
fail-closed laufen — er wird stattdessen sofort beim Aufbau abgelehnt, damit ein
Konfigurationsfehler nicht als „Login geht nicht" erscheint.

## Ablauf

1. Methode ≠ `POST` → leerer `405` mit `Allow: POST`
2. nicht leere Query → leerer `400`; nicht leerer Body → leerer `400`
3. `Origin` fehlend, `null` oder abweichend → leerer `403`
4. `Sec-Fetch-Site` vorhanden und ≠ `same-origin` → leerer `403`
5. Uhr **genau einmal** lesen
6. `prepare_oidc_login_authorization(..., now=now, lifetime=lifetime,
   admission_id=None, return_path=None)` **genau einmal**
7. Erfolg → Cookie setzen und `303`

Die Eingabeprüfung liegt **vor** der Origin-Prüfung: eine Anfrage mit Query
**und** fremder Origin ist ein `400`. Das folgt der Reihenfolge aus LQ-152 §5
und hält die beiden Grenzen deterministisch auseinander.

Bei **jeder** Ablehnung: `Cache-Control: no-store`, **keine** Uhrabfrage,
**kein** Use-Case-Aufruf, **kein** Lookup, **kein** Generator, **kein** Store,
**kein** Cookie, **kein** Redirect, **kein** `Retry-After`.

## Warum die Route jede Methode selbst besitzt

Registriert man nur `POST`, erzeugt Starlette für andere Methoden ein
`HTTPException(405)`, das FastAPI als **JSON-Body** `{"detail": "Method Not
Allowed"}` rendert. Das widerspricht dem leeren Body des Vertrags.

Die Alternative wäre ein **globaler** Exception-Handler — der würde jedoch das
Verhalten unbeteiligter Routen ändern und war ausdrücklich ausgeschlossen.
Deshalb registriert die Route `POST`, `GET`, `HEAD`, `PUT`, `PATCH`, `DELETE`
und `OPTIONS` selbst und beantwortet alles außer `POST` mit einem leeren `405`
und `Allow: POST`. Aus demselben Grund fängt der Handler interne Fehler
**route-lokal** ab: nur so bleibt der `500` garantiert leer, ohne globale
Fehlerbehandlung.

`POST` und nicht `GET`, weil der Aufruf serverseitigen Zustand erzeugt: mit
`GET` würden Prefetching, Linkscanner und Vorschau-Bots Login-Transaktionen
anlegen.

## Erfolgsresponse

```
303 See Other
Location: <prepared.request.url>
Set-Cookie: __Host-liquent_oidc_state=<prepared.state.value>; ...
Cache-Control: no-store
Pragma: no-cache
Referrer-Policy: no-referrer
```

Leerer Body, **kein** `Content-Type`. Die URL steht ausschließlich im
`Location`-Header und niemals in einem JSON-, HTML- oder Textbody.

`303` weist den Browser eindeutig an, den Authorization Endpoint mit `GET`
aufzurufen. Ein methodenerhaltender `307`/`308` würde den POST beim Identity
Provider wiederholen, ein `302` bliebe semantisch uneindeutig.

`Referrer-Policy: no-referrer` verhindert, dass der Identity Provider die
vorherige Liquent-URL im `Referer` sieht.

`Location` enthält notwendigerweise State und Nonce und darf deshalb nicht in
Anwendungslogs oder Telemetrie geraten.

## Binding-Cookie

`src/liquent_platform/transport/http/oidc_state_cookie.py` —
`set_oidc_state_cookie(response, state_value, *, now, lifetime)`.

| Eigenschaft | Wert |
|---|---|
| Name | `__Host-liquent_oidc_state` |
| Wert | exakt `prepared.state.value` |
| `Secure` | ja |
| `HttpOnly` | ja |
| `SameSite` | `Lax` |
| `Path` | `/` |
| `Domain` | **kein** |
| `Max-Age` | `int(lifetime.total_seconds())`, damit nie größer als die Lebensdauer |
| `Expires` | derselbe `now` plus Lebensdauer |

**Eigenes Modul statt `session_cookie.py`:** Die `__Host-`-Invarianten sind
sicherheitskritisch und der spätere Callback braucht denselben Slot zum Löschen
nach erfolgreichem Match. `session_cookie.py` gehört zu LQ-117/LQ-118 und bleibt
laut LQ-152 §7 ausdrücklich unverändert — das bestehende `liquent_session`-Cookie
wird von diesem Slice nicht berührt.

**`expires` wird nach UTC normalisiert.** Das Cookie-Datumsformat verlangt UTC;
eine zeitzonenbewusste, aber nicht-UTC Uhr würde sonst genau hier scheitern —
**nachdem** die Transaktion bereits atomar gespeichert wurde — und ohne Not
einen verwaisten Pending-Record hinterlassen. Der Zeitpunkt bleibt derselbe.

**`SameSite=lax` in Kleinschreibung:** Starlette gibt den Wert so aus, wie das
bestehende Session-Cookie ihn schon nutzt. RFC 6265bis §5.4.7 vergleicht
Attributwerte case-insensitiv; der Vertrag ist erfüllt.

**`last-start-wins`:** Es gibt genau einen Slot — gleicher Name, `Path=/`, kein
`Domain`. Ein neuer erfolgreicher Start überschreibt das Cookie. Der ältere
Pending-Record bleibt serverseitig und läuft gemäß LQ-139 fail-closed ab; ein
älterer Callback trifft auf einen Mismatch, bricht neutral ab und löscht das
neuere Cookie nicht.

## Der State kommt niemals aus der URL

Die Authorization-URL **enthält** den State als Queryparameter. Ihn dort wieder
auszulesen wäre eine zweite, schwächere Quelle für einen sicherheitskritischen
Wert — abhängig von Encoding, Parserverhalten und Parameterreihenfolge und ohne
Garantie, dass er dem gespeicherten Transaktionsschlüssel entspricht. LQ-153
gibt ihn deshalb direkt heraus, und der Handler nimmt ausschließlich
`prepared.state.value`.

Nachgewiesen über ein fokussiertes Double: der Builder wird gepatcht und liefert
eine URL mit **abweichendem**, **leerem** oder **ganz fehlendem** `state`. Das
Cookie trägt in allen vier Fällen weiterhin den erzeugten State. Käme er aus der
URL, müssten diese Tests scheitern — gegenprobiert. **Kein** globaler AST-,
Import- oder Substring-Test über ganze Module.

## Fehlerabbildung

| Situation | Status | Header |
|---|---|---|
| andere Methode | `405` | `Allow: POST`, `Cache-Control: no-store` |
| nicht leere Query oder Body | `400` | `Cache-Control: no-store` |
| fehlender, `null` oder fremder Origin | `403` | `Cache-Control: no-store` |
| `Sec-Fetch-Site` ≠ `same-origin` | `403` | `Cache-Control: no-store` |
| `OidcLoginUnavailable` | `503` | `Cache-Control: no-store` |
| `OidcLoginStartConflict` | `503` | `Cache-Control: no-store` |
| jeder sonstige interne Fehler | `500` | `Cache-Control: no-store` |

Alle Fehler haben einen leeren Body, **kein** Cookie, **keinen** Redirect,
**keine** reflektierte Origin, **keine** Detailbegründung, **keine**
Exceptiontexte und **kein** `Retry-After`.

**Warum beide fachlichen Fälle identisch `503` sind:** Eine Unterscheidung würde
nach außen offenlegen, ob überhaupt eine aktive Konfiguration existiert
beziehungsweise ob ein State kollidierte. Intern bleiben die Fehler getrennt
(LQ-151); nur der Transport vereinheitlicht sie — nachgewiesen byte-identisch
inklusive `Content-Length`.

**Kein `Retry-After`**, solange keine serverseitig belastbare Retryzeit
existiert; eine geratene Angabe wäre eine Falschaussage.

## Verwaiste Transaktionen

Scheitert die Responseerzeugung **nach** erfolgreicher Speicherung, antwortet
die Route trotzdem neutral und leer mit `500`. Der atomare Store wird **nicht**
zurückgerollt — ein Rollback wäre selbst ein Wiederverwendungspfad. Der
kurzlebige Pending-Record läuft gemäß LQ-139 fail-closed ab und wird nie
wiederverwendet.

## Tests

`tests/test_oidc_login_start_route.py` — **87** fokussierte Tests:

- Default-App ohne Route · vollständige Injektion aktiviert sie · jede der sechs
  Abhängigkeiten einzeln fehlend und einzeln allein vorhanden → `ValueError` ·
  nicht positive Lebensdauer · leere und mehrwertige Origin
- Erfolg: exakt `303`, leerer Body, exakte `Location`, `no-store`, `no-cache`,
  `no-referrer`, kein `Content-Type`
- Cookie: Name, Wert aus `prepared.state.value`, `Secure`, `HttpOnly`,
  `SameSite`, `Path=/`, **kein** `Domain`, `Max-Age ≤ Lebensdauer`, `Expires`
  aus demselben `now`, nicht-UTC-Uhr ergibt denselben Zeitpunkt
- Cookie-Wert `==` gespeicherter Transaktionsschlüssel · vier Builder-Doubles
  mit abweichendem, leerem oder fehlendem URL-State
- Uhr, Lookup, Generator und Store jeweils **genau einmal** · derselbe `now`
  begrenzt die gespeicherte Transaktion · `admission_id is None`,
  `return_path is None` · Admission und Return-Path nicht einschleusbar
- `last-start-wins` über zwei Starts im selben Slot
- Ablehnungen ohne Nebenwirkungen: sechs Query-/Body-Varianten, acht
  Origin-Varianten inklusive `null`, Schema-, Port-, Slash- und
  Groß-/Kleinschreibungsabweichung sowie `Referer` allein, sieben
  `Sec-Fetch-Site`-Werte; Eingabeablehnung schlägt Origin-Ablehnung
- beide fachlichen Fehler byte-identisch `503`, ohne Fehlercode im Response
- drei Infrastrukturfehler und eine naive Uhr als neutraler `500` ohne Issuer im
  Response · Builderfehler nach erfolgreichem Store bleibt neutraler `500` mit
  genau einem Store-Aufruf
- `GET`, `PUT`, `PATCH`, `DELETE` als leerer `405` mit `Allow: POST`, ohne
  JSON-Detail
- `liquent_session` bleibt unberührt · die Logout-Route bleibt unabhängig

## Bewusst nicht enthalten

- kein Callback, keine Token-Einlösung, keine Claimprüfung, keine Session,
- keine Admission-Verarbeitung, kein Return-Path,
- keine neuen Ports oder Stores, keine Persistenz,
- keine Änderung an LQ-151/LQ-153 oder am `liquent_session`-Cookie,
- kein Provider- oder Production-Wiring, keine Discovery, kein Client-Secret,
- keine CORS-Freigabe, keine lokale HTTP-Ausnahme,
- keine globale Fehlerbehandlung für andere Routen,
- keine Deployment-, CI-, Container-, Dependency- oder Grype-Änderung.

## Nächster Schritt

Der **Callback-Slice** `GET /v1/session/oidc/callback` mit der
Browserbindungsprüfung aus LQ-152 §9: konstantzeitlicher Vergleich von
Query-State und Cookie-State **vor** dem atomaren Einmal-Claim, neutraler
Abbruch bei fehlendem oder abweichendem Cookie ohne Löschen, Löschen erst nach
erfolgreichem Match auf jedem weiteren Endpfad.
