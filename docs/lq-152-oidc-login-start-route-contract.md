# LQ-152 — OIDC Login Start Route and Browser Binding Contract

## Status

Architekturentscheidung und **Transportvertrag**. **Keine** Implementierung,
**keine** Route, **keine** Cookie-Helfer, **keine** Änderung an LQ-151. Baut auf
LQ-136 (Transaktionsvertrag), LQ-144 (Login-Start), LQ-145
(Authorization-Request-Vertrag), LQ-147 (Builder), LQ-148/LQ-150 (aktive
Konfiguration) und LQ-151 (Orchestrierung) auf.

## 1. Kritische Sicherheitsentscheidung: Browserbindung

Der serverseitige `state`-Store (LQ-139/LQ-142/LQ-143) verhindert Raten und
Wiederverwendung. Er bindet eine Transaktion aber **nicht** an den Browser, der
den Login gestartet hat.

**Angriff ohne zusätzliche Bindung:**

1. Ein Angreifer startet einen Login in seinem **eigenen** Browser.
2. Er kennt damit seinen `state` und kann den späteren Callback-Link
   übertragen.
3. Im Browser des Opfers ausgelöst, würde der Callback dort eine Session
   etablieren, die an die **Angreifer**-Identität gebunden ist — ein klassischer
   Login-CSRF beziehungsweise Session-Fixation-Pfad.

**Verbindliche Entscheidung:**

- Beim **erfolgreichen** Login-Start wird der erzeugte OIDC-`state`
  **zusätzlich** in einem kurzlebigen, geschützten, host-only Browser-Cookie
  gebunden.
- Beim späteren Callback wird der Query-`state` **vor** dem Claim
  **konstantzeitlich** mit dem Cookie-Wert verglichen.
- Ein fehlendes oder nicht passendes Binding-Cookie führt **neutral** zum
  Abbruch.
- **Erst nach** erfolgreicher Bindungsprüfung darf der State über den atomaren
  Claim-Port beansprucht werden.
- Das Binding-Cookie wird beim Callback auf **jedem** Endpfad gelöscht.

Diese Entscheidung ist hier abschließend getroffen und wird **nicht** an einen
späteren Implementierer verschoben. Die konkrete Callback-Implementierung bleibt
ein eigener Slice.

## 2. Route und Methode

**Verbindlich:**

```
POST /v1/session/oidc/login
```

Begründung:

- Der Aufruf erzeugt **serverseitigen Zustand** und ist deshalb kein sicheres
  HTTP-GET.
- Mit GET würden Browser-Prefetching, Linkscanner, Vorschau-Bots und
  unbeabsichtigte Navigationen Login-Transaktionen erzeugen.
- Die Route folgt dem bestehenden Session-Namespace (`POST /v1/session/logout`).
- **Kein** Issuer und **kein** Provider im Pfad.

Konzeptionell **reserviert** für später:

```
GET /v1/session/oidc/callback
```

Der Callback wird hier **nicht** implementiert, aber der Pfad ist für
Redirect-URI und Cookie-Lebenszyklus eindeutig festgelegt.

## 3. Eingabegrenze

Die Login-Start-Route akzeptiert in diesem ersten Slice **keine** fachlichen
Browserwerte: keine Queryparameter, keinen Request-Body, keinen Issuer,
Provider, keine Client-ID, Redirect-URI, keine Scopes, keine Admission-ID,
keinen Return-Path, keinen Workspace, keinen Benutzer, kein `login_hint`,
`prompt` oder `max_age`.

Der spätere Route-Handler ruft LQ-151 auf mit:

- serverseitig injizierten Abhängigkeiten,
- serverseitig gelesener **aktueller** Konfiguration,
- serverseitig festgelegter **positiver** Transaktionslebensdauer,
- aktueller serverseitiger Uhr,
- `admission_id=None`,
- `return_path=None`.

Kontrolliertes Onboarding (Admission) und validierte Rückkehrziele brauchen
später **eigene** serverseitige Transportgrenzen. Diese Capability-Werte werden
**nicht** in die allgemeine Login-Route aufgenommen — sonst könnte ein Aufrufer
über eine unauthentifizierte Route eine Admission-Bindung oder ein Rückkehrziel
setzen.

Nicht leere Query **oder** nicht leerer Body → neutraler Clientfehler, **keine**
Transaktion, **kein** Cookie, **kein** Redirect.

## 4. Schutz gegen Cross-Site-Login-Start

Die Route ist **unauthentifiziert**, ein Liquent-Session-CSRF-Token steht daher
noch nicht zur Verfügung. Produktionsvertrag:

- Der POST **muss** einen `Origin`-Header tragen.
- `Origin` muss **exakt** einer vertrauenswürdigen, serverseitig konfigurierten
  öffentlichen Liquent-Origin entsprechen.
- Die vertrauenswürdige Origin wird **niemals** aus `Host`, `Forwarded`,
  `X-Forwarded-Host`, Query, Body oder anderen Browserdaten abgeleitet.
- Fehlender, `null` oder abweichender Origin → neutraler **`403`**.
- Ist `Sec-Fetch-Site` vorhanden, **muss** der Wert `same-origin` sein.
  `cross-site`, `same-site` und `none` werden für diesen POST **nicht**
  akzeptiert.
- `Referer` ist **kein** Ersatz für einen fehlenden Origin.
- **Keine** CORS-Freigabe für diese Route.
- **Keine** automatische Fallback-Origin.

Die spätere Oberfläche kann einen leeren same-origin HTML-Form-POST verwenden;
die Route benötigt **keine** Formfelder. Lokale Entwicklungs-Ausnahmen sind
**nicht** Bestandteil dieses Produktionsvertrags.

## 5. Erfolgsreihenfolge

1. Methode, Pfad, **leere** Eingabe und Same-Origin-Grenze prüfen.
2. Serverseitige Uhr und feste positive Lebensdauer bereitstellen.
3. `prepare_oidc_login_authorization(...)` (LQ-151) **genau einmal** aufrufen.
4. **Erst nach** erfolgreicher atomarer Speicherung liegt ein
   `OidcAuthorizationRequest` vor.
5. Den `state` für das Binding-Cookie **nicht** aus der URL neu ableiten; er
   muss aus dem vertrauenswürdigen Startablauf **separat** verfügbar sein
   (siehe Abschnitt 8).
6. Binding-Cookie im Redirect-Response setzen.
7. Browser mit **`303 See Other`** zur erzeugten Authorization-Request-URL
   weiterleiten.

**Kein** Redirect vor erfolgreicher Speicherung. **Kein** Cookie bei
Origin-Ablehnung, ungültiger Eingabe, fehlender aktiver Konfiguration,
Creation-Konflikt oder Generator-/Store-/Builder-/Infrastrukturfehler.

**Verwaiste Transaktionen:** Schlägt die Response-Erzeugung **nach**
erfolgreicher Speicherung fehl, kann eine kurzlebige Pending-Transaktion
zurückbleiben. Sie darf **nicht** nachträglich wiederverwendet werden und läuft
gemäß LQ-139 **fail-closed** ab. Es gibt in diesem Vertrag **kein** Rollback des
atomaren Stores — ein Rollback wäre selbst ein Wiederverwendungspfad.

## 6. Redirect-Status

**Verbindlich: `303 See Other`.**

- Der Login-Start ist ein POST.
- `303` weist den Browser eindeutig an, den Authorization Endpoint anschließend
  mit **GET** aufzurufen.
- **Kein** methodenerhaltender `307`/`308` — der Browser dürfte sonst den POST
  an den Identity Provider wiederholen.
- **Kein** semantisch uneindeutiger `302`.
- **Kein** permanenter Redirect — jede Login-URL ist einmalig und darf niemals
  gecacht werden.

Response: **leerer Body**, Authorization-Request-URL **ausschließlich** im
`Location`-Header, **keine** URL in einem JSON-, HTML- oder Text-Body.

## 7. Binding-Cookie

**Name:** `__Host-liquent_oidc_state`

| Eigenschaft | Wert |
|---|---|
| Wert | exakt der für **diese** Login-Transaktion erzeugte OIDC-`state` |
| `Secure` | ja |
| `HttpOnly` | ja |
| `SameSite` | `Lax` |
| `Path` | `/` |
| `Domain` | **kein** |
| `Max-Age` | höchstens die serverseitige Login-Transaktionslebensdauer |
| `Expires` | passendes absolutes Datum |
| Persistenz | **nicht** über die notwendige Login-Transaktion hinaus |

**`SameSite=None` ist verboten.** `Lax` genügt, weil der Callback eine
Top-Level-GET-Navigation ist.

**Warum `__Host-`:** Der Präfix erzwingt `Secure`, verlangt `Path=/`, verbietet
`Domain` und verhindert damit, dass ein kompromittierter Subdomain-Kontext das
Cookie überschreibt und so die Browserbindung aushebelt.

> **Abweichung von der bestehenden Cookie-Benennung, bewusst:** Das vorhandene
> Session-Cookie `liquent_session` (LQ-117/LQ-118) ist zwar host-only, `Secure`,
> `HttpOnly`, `SameSite=Lax`, `Path=/` und ohne `Domain`, trägt aber **keinen**
> `__Host-`-Präfix. Für dieses neue Bindungs-Cookie ist der Präfix vorgeschrieben
> und sachlich richtig. Eine Umstellung des bestehenden Session-Cookies wäre ein
> **eigener** Slice und ist hier ausdrücklich **nicht** Teil des Auftrags.

Der State ist protokollbedingt browserseitig sichtbar, bleibt aber ein
**sensibler Korrelationswert**: nicht in `repr`, nicht in Logs, nicht in
Telemetrie, nicht in Fehlertexten, nicht in Web Storage, nicht in
Analytics-Events.

Das Cookie ist **kein** Authentifizierungsnachweis und erzeugt **keine**
Berechtigung. Es bindet ausschließlich einen Callback an denselben
Browserkontext, der den Login gestartet hat.

## 8. Notwendige Konsequenz für die Anwendungsgrenze

LQ-151 gibt derzeit **ausschließlich** `OidcAuthorizationRequest` zurück. Die
vollständige URL enthält den State — aber der Route-Handler darf ihn **nicht**
durch erneutes Parsen dieser URL als vertrauenswürdige interne Quelle
zurückgewinnen. Ein Parser-Rückweg wäre eine zweite, schwächere Quelle für einen
sicherheitskritischen Wert.

**Verbindlich:** Vor Implementierung der Route ist ein kleiner **Folgeslice**
erforderlich, der der Transportgrenze den bereits erzeugten State separat und
sicher bereitstellt, zum Beispiel als unveränderliches Ergebnisobjekt:

```
PreparedOidcLoginAuthorization
- request: OidcAuthorizationRequest
- state:   OidcLoginState bzw. opaker State-Wert, repr-frei
```

Dabei gilt:

- **keine** URL erneut parsen,
- **keinen** State neu erzeugen,
- **exakt** den State aus demselben LQ-144-Startvorgang weiterreichen,
- **kein** Code-Verifier,
- **keine** Admission-ID,
- **kein** Pending-Record,
- **keine** Konfiguration im Ergebnis.

LQ-152 **entscheidet** nur diese notwendige Grenze. Es implementiert und ändert
LQ-151 **nicht**.

## 9. Callback-Browserbindungsvertrag

Für den späteren Callback verbindlich:

1. Die Query enthält **genau einen** nicht leeren `state`.
2. Das Binding-Cookie ist vorhanden und nicht leer.
3. Query-State und Cookie-State werden **konstantzeitlich** verglichen.
4. Bei fehlendem oder falschem Cookie: **neutral** abbrechen, Claim-Port
   **nicht** aufrufen, **keine** Token-Einlösung, **keine** Session,
   Binding-Cookie **löschen**.
5. **Erst** bei erfolgreichem Vergleich: `OidcLoginState` bilden und die
   Transaktion atomar **genau einmal** claimen.
6. Das Cookie wird auf **jedem** Callback-Endpfad gelöscht: Erfolg, unbekannter
   State, abgelaufen, bereits konsumiert, Mismatch, Token-/Claimfehler und
   interne Fehlerantwort.

**Kein** Logging der Query oder des Cookie-Werts. Die genaue Callback-Route und
die Tokenlogik bleiben spätere Implementierungen; der Pfad ist als
`GET /v1/session/oidc/callback` reserviert.

## 10. Erfolgsheader

Der erfolgreiche `303`-Response enthält:

```
Location: <OidcAuthorizationRequest.url>
Set-Cookie: __Host-liquent_oidc_state=...
Cache-Control: no-store
Pragma: no-cache
Referrer-Policy: no-referrer
```

**Kein** Response-Body.

Die vollständige `Location` enthält notwendigerweise State und Nonce und darf
deshalb **nicht** in Anwendungslogs oder Telemetrie aufgenommen werden.
Response-Header-Logging muss `Location` für diese Route **aussparen oder
redigieren**.

## 11. Fehlerverhalten

| Situation | Status | Header | Body |
|---|---|---|---|
| andere Methode auf demselben Pfad | `405 Method Not Allowed` | `Allow: POST`, `Cache-Control: no-store` | leer |
| nicht leere Query oder nicht leerer Body | `400 Bad Request` | `Cache-Control: no-store` | leer |
| Cross-Site oder fehlender Origin | `403 Forbidden` | `Cache-Control: no-store` | leer |
| `OidcLoginUnavailable` **oder** `OidcLoginStartConflict` | `503 Service Unavailable` | `Cache-Control: no-store` | leer |
| Lookup-, Generator-, Store- oder Builderfehler | `500 Internal Server Error` | `Cache-Control: no-store` | leer |

In **allen** Fehlerfällen: **kein** Cookie, **kein** Redirect, **keine**
reflektierte Origin, **keine** Detailbegründung, **keine** Exceptiontexte im
Body.

**Warum `503` für beide Login-Fälle:** `OidcLoginUnavailable` und
`OidcLoginStartConflict` werden an der Transportgrenze **absichtlich gleich**
behandelt. Eine Unterscheidung würde nach außen offenlegen, ob überhaupt eine
aktive Konfiguration existiert beziehungsweise ob ein State kollidierte. Intern
bleiben die beiden Fehler getrennt (LQ-151); nur der Transport vereinheitlicht
sie.

**Kein `Retry-After`**, solange keine serverseitig belastbare Retryzeit
existiert — eine geratene Angabe wäre eine Falschaussage.

## 12. Logging und Telemetrie

**Nicht erfassen:** vollständige Authorization-Request-URL, `Location`, State,
Nonce, Binding-Cookie, Client-ID, Redirect-URI, Admission-ID, Return-Path sowie
Queryparameter dieser Route oder des Callbacks.

**Erlaubt:** normalisierter Routenname, HTTP-Methode, neutraler Statuscode,
Korrelations-ID **ohne** OIDC-Material, grobe interne Fehlerkategorie **ohne**
Bestands- oder Providerdetails.

**Keine** Metriklabels mit Issuer, Client-ID, State oder Origin-Wert — solche
Labels hätten unbegrenzte Kardinalität und würden zugleich Bestandsinformationen
preisgeben.

## 13. Caching und Browserdaten

Jeder Erfolg **und** jeder Fehler: `Cache-Control: no-store`.

Erfolg zusätzlich: `Pragma: no-cache` und `Referrer-Policy: no-referrer` — ohne
Letzteres könnte der Identity Provider die vorherige Liquent-URL im
`Referer` sehen.

**Keine** Speicherung in Local Storage, Session Storage, IndexedDB oder in für
JavaScript lesbaren Cookies. Das Binding-Cookie ist `HttpOnly`.

## 14. Trust- und Autorisierungsgrenze

Die Route wählt **keinen** Provider, akzeptiert **keinen** Issuer, liest die
aktive Konfiguration über LQ-151/LQ-148, trifft **keine** eigene
Callback-Trust-Entscheidung, erteilt **keine** Workspace-Mitgliedschaft, erzeugt
**keine** Rolle oder Berechtigung und erzeugt **noch keine** Liquent-Session.

Ein erfolgreicher Redirect bedeutet ausschließlich: **Eine kurzlebige
Login-Transaktion wurde sicher gestartet.**

## Bewusst nicht enthalten

- keine Python-Implementierung, keine Route, keine Cookie-Helfer,
- keine Änderung an LQ-151, kein neues Ergebnisobjekt,
- kein Callback-Code, keine Token-Einlösung,
- keine OIDC-/OAuth-Bibliothek, keine Discovery, kein
  Signaturschlüssel-Loading, kein Client-Secret,
- keine Claims oder `ExternalIdentity`, keine Admission-Verarbeitung, kein
  Return-Path,
- keine Workspace-Autorisierung, keine Session-Erzeugung, kein föderierter
  Logout,
- kein Multi-Issuer, kein Enterprise-SSO,
- kein Production-Wiring, kein Deployment oder VPS-Zugriff,
- keine Proxy-/CORS-Konfiguration, keine lokale HTTP-Ausnahme,
- keine CI-/Grype-Änderung, keine Änderung der CPython-Ausnahmen,
- keine Umstellung des bestehenden `liquent_session`-Cookies auf `__Host-`.

## Nächster Schritt

Zwingende Reihenfolge:

1. **Ergebnisgrenze erweitern** — `PreparedOidcLoginAuthorization` mit
   repr-freiem State (Abschnitt 8). Ohne diesen Slice ist die Route nicht
   sicher implementierbar.
2. **Login-Start-Route** nach diesem Vertrag umsetzen.
3. **Callback-Route** mit der Browserbindungsprüfung aus Abschnitt 9, davor
   beziehungsweise darin der atomare Einmal-Claim gemäß LQ-139.
