# LQ-147 — OIDC Authorization Request Builder

## Ergebnis

Ein kleiner, **deterministischer und seiteneffektfreier** Builder, der aus einer
bereits vertrauenswürdig ausgewählten `TrustedOidcClientConfiguration` (LQ-146)
und einem erfolgreichen `StartedOidcLogin` (LQ-144) den Authorization Request
gemäß LQ-145 formt.

**Keine** Route, **kein** Netzwerk, **keine** Trust-Auswahl, **keine**
Materialerzeugung, **kein** Store, **keine** HTTP-Weiterleitung.

## Signaturen

`src/liquent_platform/application/build_oidc_authorization_request.py`

```python
@dataclass(frozen=True, slots=True)
class OidcAuthorizationRequest:
    url: str = field(repr=False)


def build_oidc_authorization_request(
    configuration: TrustedOidcClientConfiguration,
    started: StartedOidcLogin,
) -> OidcAuthorizationRequest: ...
```

Das Rückgabeobjekt liegt in der **Anwendungsschicht**, weil es ein transportnahes
Ergebnis des Ablaufs ist und kein dauerhaftes Identity-Domainmodell. Kein Export
über `application/__init__.py` — dort stehen ausschließlich `ports` und
`health`; auch `create_session`, `issue_session` und `start_oidc_login` sind
nicht exportiert.

## Exakte Parameterfläche

Genau **neun** Parameter, jeder **genau einmal**, in dieser **festen**
Reihenfolge:

| # | Parameter | Quelle |
|---|---|---|
| 1 | `response_type` | Konstante `code` |
| 2 | `response_mode` | Konstante `query` |
| 3 | `client_id` | `configuration.client_id` |
| 4 | `redirect_uri` | `configuration.redirect_uri` |
| 5 | `scope` | `" ".join(configuration.scopes)` |
| 6 | `state` | `started.state` |
| 7 | `nonce` | `started.nonce` |
| 8 | `code_challenge` | `started.code_challenge` |
| 9 | `code_challenge_method` | Konstante `S256` |

Die Scope-Reihenfolge bleibt exakt die des konfigurierten Tupels — **keine**
Sortierung, Deduplizierung oder Ergänzung. Die Konstanten haben **keine**
konfigurierbaren Alternativen.

**Nicht enthalten:** `code_verifier`, Admission-ID, `return_path`, `prompt`,
`login_hint`, `domain_hint`, `hd`, `max_age`, `acr_values`, `ui_locales`,
Provider-Erweiterungen. `offline_access` wird **nie** automatisch ergänzt; ist es
ausdrücklich Teil der konfigurierten Scopes, bleibt es **ausschließlich**
innerhalb des kodierten `scope`-Werts und wird **kein** eigener Parameter.

## Kodierungsstrategie

Eine **geordnete Liste von Schlüssel-Wert-Tupeln** an `urllib.parse.urlencode`.
**Keine** manuelle Kodierung einzelner Werte, **keine** Bildung der Query durch
Aneinanderreihen von Parameterstrings, **keine** ungefilterte Einfügung von
Daten. Sämtliche Schlüssel und Werte stammen aus `urlencode`.

Verifiziert:

- `&`, `=`, `#`, `?`, `/` und `:` in Werten werden prozentkodiert und können
  **weder** einen zusätzlichen Parameter erzeugen **noch** einen
  verpflichtenden überschreiben oder duplizieren.
- Die feste Query einer Redirect-URI wird vollständig als **Teil des einen**
  `redirect_uri`-Werts kodiert.
- Das Scope-Trennzeichen wird standardkonform als Form-/Querywert kodiert
  (Leerzeichen → `+` gemäß `application/x-www-form-urlencoded`, RFC 6749) und
  decodiert exakt zurück.
- Unicode wird standardkonform UTF-8-prozentkodiert und rundläuft exakt.
- Es entsteht **kein** Fragment.

Die Ziel-URL ist `f"{configuration.authorization_endpoint}?{query}"` — genau
**ein** `?` an den **unveränderten** Endpoint. Das ist zulässig, weil LQ-146
bereits garantiert, dass der Endpoint eine absolute HTTPS-URL mit Host, ohne
Userinfo, ohne Query, ohne Fragment, ohne rohe Leer-/Steuerzeichen und mit
gültigem Port ist. Es findet **keine** URL-Neukanonisierung und **keine**
Rekonstruktion des Endpoints statt (insbesondere **kein** `urlunsplit`), damit
dessen exakte Schreibweise unangetastet bleibt.

## Geheimnis- und `repr`-Grenze

`OidcAuthorizationRequest` ist unveränderlich, `slots=True`, hashbar und hat
**exakt ein** Feld `url` mit `repr=False`.

Der `repr` lautet `OidcAuthorizationRequest()`. Der **Klassenname darf**
erscheinen; die vollständige URL und mit ihr `state`, `nonce`, `client_id`,
`redirect_uri` und `code_challenge` **dürfen nicht**. Die URL muss als
Redirect-Ziel verwendbar bleiben, darf aber nicht über Objekt-Repräsentationen
in Logs oder Fehlerdiagnosen gelangen — daher wird sie verborgen statt
abgeschwächt. Der Wert bleibt über `.url` für die spätere **autorisierte**
Transportgrenze verfügbar.

Das Objekt trägt **keine** separaten Parameterfelder und insbesondere keinen
Code-Verifier, kein Admission-Handle, keinen Return-Path, keine Tokens, Claims,
User-, Workspace-, Rollen- oder Session-Werte.

## Validierungsgrenze

**Nicht** erneut validiert werden Issuer, Authorization Endpoint, Client-ID,
Redirect-URI, Scopes und das `StartedOidcLogin`-Material. Diese Invarianten
gehören den bestehenden Wertobjekten (LQ-146) beziehungsweise dem LQ-144-Ablauf.
Es wird **nichts** normalisiert und **nichts** abgeleitet.

Der Builder trifft **keine** Trust-Entscheidung. Der Eingang
`TrustedOidcClientConfiguration` bedeutet lediglich, dass eine spätere
aufrufende Grenze diese Konfiguration **aktuell** ausgewählt hat; der Callback
muss den Issuer-Trust gemäß LQ-136 weiterhin **erneut** prüfen.

Es ist **keine** neue Exception nötig. Unerwartete Standardbibliotheksfehler
werden **nicht** in detaillierte, datenhaltige Meldungen umgeschrieben, und es
werden **keine** Eingabewerte in eigenen Fehlermeldungen ausgegeben.

## Tests

`tests/test_build_oidc_authorization_request.py` — 49 fokussierte Tests. Die URL
wird durchgängig mit `urlsplit` und `parse_qsl` **strukturell** ausgewertet;
reine Substring-Assertions dienen nirgends als alleiniger Nachweis.

**Erfolg und Struktur:** gültiger Request · unveränderlich · hashbar · exakt das
Feld `url` · `repr` verbirgt URL, Endpoint, State, Nonce, Client-ID,
Redirect-URI und Challenge, zeigt aber den Klassennamen · `.url` bleibt exakt
verfügbar.

**Endpoint:** exakt erhalten vor dem `?` · Pfad und expliziter Port bleiben
erhalten · kein Fragment entsteht (auch bei `#` im Nonce) · eine Redirect-URI
auf fremdem Host wird **nicht** zum Ziel abgeleitet.

**Parameterfläche:** exakt die neun Namen in fester Reihenfolge · jeder genau
einmal · Reihenfolge über mehrere Builds deterministisch · die drei Konstanten ·
Client-ID und Redirect-URI verbatim · Scope aus der Tupelreihenfolge mit
einzelnen Leerzeichen · State, Nonce und Challenge verbatim.

**Sichere Kodierung:** `&` in der Client-ID erzeugt keinen Parameter · `=`
bleibt Teil des State · `#` im Nonce erzeugt kein Fragment · Redirect-URI mit
fester Query bleibt genau ein Wert · reservierte Zeichen in Scopes rundlaufen ·
Unicode rundläuft · ein Injektionsversuch über Client-ID und State kann
`response_type` und `code_challenge_method` **nicht** überschreiben.

**Geheimnisgrenze:** 18 verbotene Parameternamen parametrisiert geprüft ·
`offline_access` bleibt bei ausdrücklicher Konfiguration im `scope`-Wert und
wird kein eigener Parameter · das Rückgabeobjekt trägt keine Parameterfelder.

**Architekturgrenze:** die Signatur nimmt **ausschließlich**
`["configuration", "started"]` — es wird also kein Store, Generator, Clock,
keine Trust-Registry und kein Transport injiziert · zweimaliges Bauen liefert
identische Ergebnisse, erzeugt also nichts und liest keine Uhr · beide Eingaben
bleiben unverändert.

Geprüft wird ausschließlich der LQ-147-Vertrag; es gibt **keine** globalen
Modulflächen-, Import-, AST- oder Substring-Verbote.

## Bewusst nicht enthalten

- keine Trust-Registry, keine aktive Issuer-Auswahl, keine Providerkonfiguration,
- keine Discovery, kein JWKS, kein Netzwerk, keine DNS-Prüfung,
- keine externe OIDC-/OAuth-Bibliothek,
- keine Login-Start-Route, keine HTTP-Weiterleitung, keine Entscheidung über
  Route, Methode oder Redirect-Status,
- kein Callback, kein Token-Endpunkt, kein Client-Secret,
- keine Token- oder Claim-Verarbeitung,
- keine Admission- oder Autorisierungslogik, keine Session-Erzeugung,
- keine Persistenz oder Migration, kein Production-Wiring,
- kein Deployment oder VPS-Zugriff, keine Proxy-/CORS-Konfiguration,
- keine CI-/Grype-Änderung, keine Änderung der CPython-Ausnahmen,
- keine Änderung an `TrustedOidcClientConfiguration`, `StartedOidcLogin`,
  Identity-Ports, Stores, Adaptern oder dem Login-Start-Anwendungsfall.

## Nächster Schritt

Damit ist die serverseitige Kette vollständig: Trust-Auswahl (offen) →
Login-Start (LQ-144) → Authorization Request (LQ-147). Ein späterer Slice kann
die **Trust-Grenze** definieren, die eine Konfiguration aus dem aktuell aktiven
Zustand auswählt, und danach die **Login-Start-Route** mit der in LQ-145
verschobenen Entscheidung über Pfad, Methode und Redirect-Status.
