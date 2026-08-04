# LQ-145 — OIDC Authorization Request Contract

## Status

Architekturentscheidung und Vertrag, **providerneutral**. **Keine**
Implementierung, **kein** Anbieter, **keine** Route, **keine** URL-Erzeugung,
**keine** Konfigurationstypen, **keine** Bibliothek. Baut auf LQ-136
(Transaktionsvertrag), LQ-137 (sicheres Login-Material), LQ-138
(`PendingOidcLoginTransaction`) und LQ-144 (`start_oidc_login` →
`StartedOidcLogin`) auf.

## Ziel

Definiere den Sicherheits- und Datenvertrag für den späteren **OIDC
Authorization Request** im Authorization Code Flow mit PKCE `S256`. Der Vertrag
verbindet konzeptionell drei Dinge: eine aktuell vertrauenswürdige,
ausschließlich serverseitige Issuer-/Client-Konfiguration, das öffentliche
Ergebnis von `start_oidc_login` und einen exakt definierten Request.

## Vier Quellen, strikt getrennt

Der gesamte Vertrag beruht darauf, dass diese vier Bereiche **niemals**
vermischt werden:

| Bereich | Inhalt | Darf in den Authorization Request? |
|---|---|---|
| **Vertrauenswürdige Serverkonfiguration** | Issuer, Authorization Endpoint, Client-ID, Redirect-URI, Scopes | **ja**, ausschließlich von hier |
| **LQ-144-Startmaterial** (`StartedOidcLogin`) | `state`, `nonce`, `code_challenge` | **ja**, exakt diese drei |
| **Browsertransport** | Query, Body, Cookies, Header der eingehenden Anfrage | **nein**, niemals |
| **Serverseitiger Pending-Record** | `code_verifier`, `admission_id`, `return_path`, `created_at`, `expires_at` | **nein**, niemals |

Die beiden linken Bereiche speisen den Request; die beiden rechten sind
ausgeschlossen — der Browsertransport, weil er nicht vertrauenswürdig ist, der
Pending-Record, weil er Geheimnisse und interne Bindungen hält.

## 1. Vertrauensquelle

Diese Werte stammen **ausschließlich** aus aktiver, vertrauenswürdiger
serverseitiger Liquent-Konfiguration:

- kanonischer erwarteter Issuer,
- Authorization Endpoint,
- Client-ID,
- exakte Redirect-URI,
- erlaubte Scopes,
- gegebenenfalls später ausdrücklich freigegebene Zusatzparameter.

**Keiner** dieser Werte darf stammen aus Request-Query, Request-Body, Cookie,
Browser-Header, `return_path`, Admission-ID, unbestätigten Token-Claims oder
dynamischem Callback-Inhalt.

Ein Browser darf insbesondere **keinen** Authorization Endpoint, Issuer,
Client-ID oder Redirect-URI auswählen, ergänzen oder überschreiben. Es gibt
**keinen** Parameter, mit dem ein Aufrufer den Zielprovider beeinflusst.

## 2. Aktueller Issuer-Trust

- Bereits **beim Login-Start** muss der ausgewählte Issuer aktuell
  vertrauenswürdig und **aktiviert** sein.
- Der Authorization Endpoint muss zur **aktuell aktiven** Konfiguration genau
  dieses Issuers gehören.
- Ein gespeicherter oder vom Browser gelieferter Endpoint ist **niemals** ein
  Trust-Beweis.
- Die Login-Transaktion speichert den **erwarteten Issuer**, aber **keinen
  dauerhaft eingefrorenen Trust-Status**. Trust ist Laufzeitzustand, kein
  mitgeführter Wert.
- Beim Callback wird der aktuelle Issuer-Trust gemäß LQ-136 **erneut** geprüft.
- Eine seit dem Start **entzogene oder deaktivierte** Freigabe beendet den
  Callback **neutral**, auch wenn der Start zuvor gültig war.

**Nicht** in diesem Slice: ein konkreter Identity Provider und jede
Multi-Issuer-Auswahl.

## 3. Authorization Endpoint

Für Produktionskonfiguration gilt:

- ausschließlich **absolute HTTPS-URL**,
- **kein** Fragment,
- **keine** Benutzerinformationen in der URL (`user:password@`),
- **kein** dynamischer Host aus Benutzereingaben,
- **keine** offene Weiterleitung über einen vom Browser kontrollierten Endpoint.

**Umgang mit vorhandenen Query-Parametern am konfigurierten Endpoint —
Entscheidung:**

- Konfigurierte Authorization Endpoints enthalten **keine** Query-Parameter.
- Ein Endpoint **mit** vorhandener Query **oder** Fragment wird **abgewiesen**.
- Es gibt **keine** stille Zusammenführung unbekannter Parameter.

Das ist die sicherste Standardentscheidung: Sie schließt Parameterkollision und
das Überschreiben verpflichtender Parameter **per Konstruktion** aus, statt sie
zur Laufzeit auflösen zu müssen. Lokale Entwicklungs-Ausnahmen sind **nicht**
Teil von LQ-145.

## 4. Verbindliche Request-Parameter

Der spätere Request enthält **mindestens exakt**:

| Parameter | Wert |
|---|---|
| `response_type` | `code` |
| `client_id` | serverseitig konfiguriert |
| `redirect_uri` | serverseitig konfiguriert |
| `scope` | serverseitig erlaubte Scopes, zwingend mit `openid` |
| `state` | `StartedOidcLogin.state` |
| `nonce` | `StartedOidcLogin.nonce` |
| `code_challenge` | `StartedOidcLogin.code_challenge` |
| `code_challenge_method` | `S256` |
| `response_mode` | `query` |

Zusätzliche Festlegungen:

- `response_mode=query` wird **explizit gesetzt**, damit der spätere
  Callback-Vertrag eindeutig ist und nicht von einer Provider-Vorgabe abhängt.
- **Keine** Plain-PKCE-Option. `code_challenge_method` ist ausschließlich
  `S256`.
- **Kein** impliziter und **kein** hybrider Flow.
- **Kein** `token`, `id_token` oder anderer Response Type.
- **Keine** doppelt vorkommenden sicherheitsrelevanten Parameter. Tritt ein
  verpflichtender Parameter mehrfach auf, ist das ein Abbruch, keine Auflösung.
- Parameter werden später **standardkonform URL-kodiert**; **keine**
  String-Konkatenation und **kein** manuelles Zusammensetzen der Query.

## 5. Scope-Vertrag

- `openid` ist **zwingend**. Fehlt es, bricht der Start ab.
- Scopes stammen **ausschließlich** aus der vertrauenswürdigen
  Client-Konfiguration.
- Scopes werden als **eindeutige, nicht leere** Werte behandelt.
- **Keine** Scope-Erweiterung durch den Browser.
- **Keine** automatische Anforderung von `email`, `profile`, `offline_access`
  oder providerbezogenen Scopes.
- `offline_access` und jedes Refresh-Token-Verhalten bleiben eine **spätere
  ausdrückliche** Entscheidung.
- Eine erfolgreiche Scope-Gewährung erzeugt **keine** Liquent-Berechtigung —
  Mitgliedschaft, Rollen und Autorisierung bleiben intern.

**Noch kein** Scope-Wertobjekt in diesem Slice.

## 6. Zusätzliche Parameter — Deny-by-default

In LQ-145 gilt **Deny-by-default**. Nicht automatisch gesendet werden:

`login_hint` · `domain_hint` · `hd` · `prompt` · `max_age` · `acr_values` ·
`ui_locales` · providerbezogene Erweiterungen · beliebige freie Extra-Parameter.

Jeder zusätzliche Parameter braucht später **alle vier**:

1. eine eigene fachliche Entscheidung,
2. eine **serverseitige Allowlist**,
3. Kollisionsschutz gegen die verpflichtenden Parameter aus Abschnitt 4,
4. eine Geheimnis- und Datenschutzprüfung (insbesondere `login_hint`,
   `domain_hint` und `hd` können Benutzer- oder Organisationsdaten preisgeben).

Browserwerte dürfen verpflichtende Parameter **niemals** überschreiben.

## 7. Datenzuordnung

**Aus vertrauenswürdiger Serverkonfiguration:**

| Wert | Ziel |
|---|---|
| Issuer | Auswahl der aktiven Konfiguration (kein eigener Request-Parameter) |
| Authorization Endpoint | Ziel-URL |
| Client-ID | `client_id` |
| Redirect-URI | `redirect_uri` |
| Scopes | `scope` |

**Aus `StartedOidcLogin` (LQ-144):**

| Wert | Ziel |
|---|---|
| `state` | `state` |
| `nonce` | `nonce` |
| `code_challenge` | `code_challenge` |

**Konstant:**

| Parameter | Wert |
|---|---|
| `response_type` | `code` |
| `response_mode` | `query` |
| `code_challenge_method` | `S256` |

**Ausschließlich im serverseitigen Pending-Record — niemals im Authorization
Request:**

- `code_verifier`
- `admission_id`
- `return_path`
- `created_at`
- `expires_at`

## 8. Geheimnis- und Datenschutzgrenze

- Der `code_verifier` verlässt den Server **niemals**. Er wird erst beim
  Token-Austausch verwendet.
- Admission-ID und internes Rückkehrziel erscheinen **niemals** im Authorization
  Request.
- Zu diesem Zeitpunkt existieren **keine** IdP-Tokens.
- `state` und `nonce` müssen protokollbedingt zum Browser und zum IdP gelangen,
  bleiben aber **sensible Korrelationswerte**. Die notwendige
  Protokollübertragung erlaubt keine weitergehende Verwendung.
- Die **Authorization-Request-URL darf nicht vollständig** in Anwendungslogs,
  Telemetrie oder Fehlerdiagnosen geschrieben werden.
- Query-Parameter müssen in Zugriffsausgaben **redigiert oder vollständig
  ausgespart** werden.
- **Keine** Speicherung in Web Storage.
- **Kein** Einbau in interne Analytics- oder Business-Events.
- Fehler enthalten **keine** State-, Nonce-, Admission-, Issuer- oder
  Clientdetails.

## 9. Redirect-URI

- Die Redirect-URI stammt **ausschließlich** aus Serverkonfiguration.
- Sie muss **exakt** mit der im Pending-Record gespeicherten Redirect-URI
  übereinstimmen — Zeichen für Zeichen, ohne Normalisierung.
- **Keine** dynamische Ableitung aus `Host`, `Forwarded`, `X-Forwarded-Host`
  oder anderen Browserparametern.
- **Keine** Auswahl beliebiger Callback-URLs durch den Aufrufer.
- Proxy-/Deployment-Vertrauen und die externe Basis-URL bleiben **separate**
  Entscheidungen.

## 10. Rückkehrziel

- `return_path` beeinflusst **niemals** Authorization Endpoint oder
  Redirect-URI.
- Es wird **nicht** an den IdP übertragen.
- Es bleibt **ausschließlich serverseitig** an die Pending-Transaktion gebunden.
- Nach erfolgreichem Callback darf **nur** ein bereits validierter interner
  **relativer** Pfad verwendet werden.
- **Kein** offener Redirect.

## 11. Transportgrenze

Konzeptionell gilt:

- Eine spätere Liquent-Login-Start-Route startet die **serverseitige
  Transaktion**.
- **Erst nach erfolgreicher Speicherung** darf sie den Browser zum Authorization
  Endpoint weiterleiten.
- Bei Creation-Konflikt oder Konfigurationsfehler erfolgt **keine**
  Weiterleitung mit teilweise erzeugtem Material — es gibt keinen Teil-Erfolg.
- Die Browserweiterleitung erfolgt bevorzugt als **leerer Redirect-Response ohne
  reflektierten Fehlertext**.
- Der Response erhält `Cache-Control: no-store`.
- Die Authorization-Request-URL erscheint **nicht** im Response-Body.

**Route-Pfad, HTTP-Methode und Status werden ausdrücklich in einen späteren
Route-Slice verschoben.** Sie gehen aus den bestehenden Transportkonventionen
**nicht eindeutig** hervor: Es existieren `/v1/session/logout` (POST, `204`,
`Cache-Control: no-store`) und `/v1/research/…`, aber **kein** OIDC-Namespace
und **kein einziger Redirect** in der bisherigen Anwendung. Damit sind
Namespace (`/v1/session/…` gegenüber `/v1/oidc/…`), Methode (POST wie beim
Logout gegenüber GET-Navigation) und Status (`302` gegenüber `303`) offene,
sicherheitsrelevante Entscheidungen — insbesondere weil die Methodenwahl den
CSRF-Schutz des Login-Starts betrifft. LQ-145 legt daher nur das **Verhalten**
fest, nicht die Adresse.

## 12. Fehlerverhalten

**Neutraler Abbruch** bei:

- unbekannter oder deaktivierter Issuer-Konfiguration,
- ungültigem Authorization Endpoint (nicht HTTPS, Fragment, Userinfo, Query),
- fehlender Client-ID,
- ungültiger Redirect-URI,
- fehlendem `openid`-Scope,
- Parameterkollision,
- Creation-Konflikt der Login-Transaktion,
- Konfigurations- oder Trust-Änderung vor Abschluss.

**Keine Offenlegung**, ob ein Issuer konfiguriert ist, ob ein Client existiert,
ob eine Admission bekannt ist, ob ein `state` kollidierte oder ob ein Benutzer
beziehungsweise Workspace existiert. Alle genannten Fälle sind nach außen
**ununterscheidbar**.

**Keine stillen Fallbacks** auf einen anderen Issuer, Client oder Redirect. Ein
nicht vollständig gültiger Vertrauenspfad führt zum Abbruch, nicht zu einer
Ersatzwahl.

## Bewusst nicht enthalten

- keine Python-Modelle, keine neuen Ports,
- kein URL-Builder, keine Route, kein HTTP-Redirect,
- keine Providerkonfiguration, kein konkreter Identity Provider,
- keine Discovery, keine JWKS-Verarbeitung,
- keine OIDC-/OAuth-Bibliothek, keine Token-Endpunktlogik, kein Client-Secret,
- keine Callback-Implementierung,
- keine Claims- oder `ExternalIdentity`-Erzeugung,
- keine Admission-Verarbeitung, keine Workspace-Autorisierung,
- keine Liquent-Session-Erzeugung,
- kein Multi-Issuer- oder Enterprise-SSO,
- kein `login_hint`, `prompt`, `max_age` oder Assurance-Wiring,
- kein Refresh Token, kein `offline_access`,
- kein Production-Wiring, kein Deployment, kein VPS oder Shared Environment,
- keine CORS- oder Proxy-Konfiguration,
- keine CI- oder Grype-Änderung, keine Verlängerung der CPython-Ausnahmen.

## Nächster Schritt

Ein späterer Slice kann die **vertrauenswürdige Issuer-/Client-Konfiguration**
als Wertobjekt definieren — kanonischer Issuer, Authorization Endpoint,
Client-ID, Redirect-URI und Scopes mit den Validierungsregeln aus den
Abschnitten 3, 5 und 9. Erst danach folgen ein Authorization-Request-Builder und
zuletzt die Login-Start-Route mit der in Abschnitt 11 verschobenen Entscheidung
über Pfad, Methode und Status.
