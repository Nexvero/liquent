# LQ-158 — OIDC Callback Ingress and Browser Binding Contract

## Status

Architekturentscheidung und **Transportvertrag**, providerneutral. **Keine**
Route, **keine** Implementierung, **kein** Querymodell, **kein** Parser, **kein**
Cookie-Helfer, **kein** Adapter.

Baut auf LQ-136 (Transaktionsvertrag), LQ-139 (atomarer Claim-Port), LQ-152
(Login-Start-Transportvertrag und Browserbindung), LQ-154 (implementierte
Login-Start-Route), LQ-155 (Verifikationsgrenze), LQ-156
(Verifikationskonfiguration) und LQ-157 (Verifikationsport) auf.

## 1. Ziel und Systemgrenze

Dieser Vertrag beschreibt den HTTP-Ingress für

```
GET /v1/session/oidc/callback
```

vom **ungeprüften Browserrequest** bis zu genau einem von drei internen
Ergebnissen:

1. eine vollständig verifizierte `ExternalIdentity` **plus** die außerhalb der
   Verifikationsgrenze zurückbehaltenen serverseitigen Transaktionswerte,
2. eine neutrale **fachliche** Ablehnung,
3. eine neutrale **technische** Nichtverfügbarkeit.

**LQ-158 implementiert keine Route** und entscheidet **noch nicht** die
nachgelagerte Identitätsauflösung, Admission-Bindung, Session-Ausgabe oder
endgültige Benutzerweiterleitung.

## 2. Ebenentrennung und verbindliche Reihenfolge

0. HTTP-Methode prüfen.
1. Query-Struktur erfassen — zunächst **nur** so weit, dass exakt ein nicht
   leerer `state` bestimmt werden kann (§6).
2. Browserbindung über Query-`state` und `__Host-liquent_oidc_state`
   **konstantzeitlich** prüfen.
3. **Erst nach erfolgreichem Match** die Transaktion atomar **genau einmal**
   claimen.
4. Binding-Cookie **nach dem Match** auf **jedem** weiteren Endpfad löschen.
5. Erfolgs- beziehungsweise Providerfehler-Query **abschließend** auswerten.
6. Bei Erfolg `OidcAuthorizationCodeVerification` aus Code und geclaimtem Record
   bilden.
7. `OidcAuthorizationCodeVerifier` **genau einmal** aufrufen.
8. **Nur** eine verifizierte `ExternalIdentity` an die spätere interne
   Completion-Grenze weiterreichen.
9. `admission_id` und `return_path` bleiben **außerhalb** des Verifiers beim
   aufrufenden Ablauf.

**Kein Schritt darf übersprungen oder umgeordnet werden.** Jeder Schritt
beantwortet eine andere Vertrauensfrage; jede Vermischung entwertet eine der
Antworten.

## 3. Route und Methode

**Reserviert:** `GET /v1/session/oidc/callback`

- **ausschließlich `GET`** — der Identity Provider leitet den Browser per
  Top-Level-Navigation hierher; `SameSite=Lax` erlaubt genau das,
- **kein POST-Callback**,
- **kein Fragmenttransport** — ein Fragment erreicht den Server nie und wäre
  nur clientseitig auswertbar,
- **kein Issuer und kein Provider im Pfad** (wie LQ-152 §2).

Andere Methoden auf demselben Pfad später:

| Antwort | Wert |
|---|---|
| Status | leerer `405 Method Not Allowed` |
| `Allow` | `GET` |
| `Cache-Control` | `no-store` |
| Abhängigkeiten | **keine** aufrufen |
| Cookie | **nicht** verändern |

FastAPIs automatische JSON-Fehlerantwort ist für diese Route **nicht
ausreichend**, wenn sie den neutralen leeren Vertrag verletzt — dieselbe
Feststellung wie in LQ-154, wo die Route deshalb jede Methode selbst besitzt.
**Keine globale Fehlerbehandlung für andere Routen.**

## 4. Query-Formen

Es sind genau **zwei** konzeptionelle Formen erlaubt.

### Erfolgsform

```
state=<ein Wert>&code=<ein Wert>
```

- genau **ein** `state`, nicht leer,
- genau **ein** `code`, nicht leer,
- **kein** `error`, **kein** `error_description`, **kein** `error_uri`,
- **keine** unbekannten und **keine** doppelten Parameter.

### Providerfehlerform

```
state=<ein Wert>&error=<ein Wert>
```

Zusätzlich optional **jeweils höchstens einmal**: `error_description`,
`error_uri`.

- genau **ein** nicht leerer `state`,
- genau **ein** nicht leerer `error`,
- **kein** `code`,
- **keine** unbekannten und **keine** doppelten Parameter,
- `error_description` und `error_uri` werden **niemals** vertraut, angezeigt,
  geloggt, telemetriert oder an eine Folge-URL weitergereicht,
- ihr Inhalt beeinflusst **keine** fachliche Entscheidung.

### Ungültige Form — neutral ablehnen

- fehlender `state`,
- leerer `state`,
- doppelter `state`,
- doppelter `code` oder `error`,
- gleichzeitig `code` **und** `error`,
- **weder** `code` **noch** `error`,
- leerer `code` oder `error`,
- unbekannte Zusatzparameter,
- mehrfaches `error_description` oder `error_uri`.

## 5. Duplikaterkennung über die echte Query-Multimap

**Verbindlich:** Mehrfachwerte müssen über die **tatsächliche Query-Multimap**
erkannt werden. **Kein** Zugriff über eine API, die Duplikate stillschweigend
auf einen Wert reduziert.

Das ist keine Stilfrage — die bequemen APIs verbergen genau das, worauf diese
Prüfung zielt. Nachgemessen im hier verwendeten Stack:

| Zugriff | `?state=a&state=b` | Wirkung |
|---|---|---|
| `QueryParams["state"]` | `"b"` | Duplikat **unsichtbar** |
| `QueryParams.get("state")` | `"b"` | Duplikat **unsichtbar** |
| `dict(parse_qsl(...))` | `{"state": "b"}` | Duplikat **unsichtbar** |
| `QueryParams.getlist("state")` | `["a", "b"]` | Duplikat sichtbar |
| `QueryParams.multi_items()` | `[("state","a"),("state","b")]` | Duplikat sichtbar |
| `parse_qsl(...)` als Liste | `[("state","a"),("state","b")]` | Duplikat sichtbar |

Ein einzelner skalarer FastAPI-`Query`-Parameter fällt in dieselbe Kategorie und
ist für diese Route **nicht zulässig**.

### Leere Werte müssen gesehen, nicht erschlossen werden

Ein zweiter, subtilerer Fallstrick: `parse_qsl` **entfernt** ohne
`keep_blank_values=True` einen Parameter mit leerem Wert vollständig.
`?state=x&error=` erscheint dann **nicht** als „leerer `error`", sondern als
„**kein** `error`" — und damit als der Fall „weder Code noch Fehler".

Beide Fälle werden ohnehin abgelehnt, es entsteht also **keine** Lücke. Aber der
Vertrag unterscheidet *fehlend* von *leer*, und eine Implementierung darf diese
Unterscheidung nicht dem Zufall der Parserkonfiguration überlassen: **leere
Werte müssen sichtbar sein**, nicht erschlossen werden.

## 6. Zweiphasiges Querylesen — und der bewusste Trade-off

**Die Query wird zunächst nur so weit gelesen, dass exakt ein nicht leerer
`state` bestimmt werden kann.**

Dann:

1. Binding-Cookie lesen,
2. `state` **konstantzeitlich** vergleichen,
3. **erst nach erfolgreichem Match** atomar claimen,
4. Cookie löschen,
5. **erst danach** die restliche Queryform abschließend bewerten.

**Begründung:**

- Ohne **genau einen** `state` ist keine sichere Browserbindung möglich: **nicht
  claimen, nichts löschen**.
- Fehlendes Cookie oder Mismatch: **nicht claimen, nichts löschen**.
- Nach erfolgreichem Match gehört das Cookie **nachweislich** zu dieser
  Transaktion.
- Eine anschließend erkannte mehrdeutige oder ungültige Providerantwort lässt
  die Transaktion **fail-closed verbraucht**.
- Eine gemischte oder manipulierte Antwort wird **niemals** mit derselben
  Transaktion erneut verarbeitet.
- **Kein Store-Rollback.**

### Der Trade-off, ausdrücklich

**Nach erfolgreichem State-/Cookie-Match kann eine malformed Antwort den Login
verbrauchen.** Das ist **bewusst fail-closed** und keine Nachlässigkeit.

Die Alternative — die Queryform vollständig **vor** dem Claim prüfen — wäre
schlechter: Ein Angreifer könnte dann mit gezielt fehlerhaften Antworten
beliebig oft an derselben, weiterhin gültigen Transaktion vorbeisondieren, und
jede Wiederverwendbarkeit nach einer teilweise verarbeiteten Antwort wäre ein
Replay-Pfad.

### Was die Browserbindung dabei leistet — und was nicht

Das Binding-Cookie ist `HttpOnly` und bleibt für einen Angreifer **nicht
lesbar**. Er muss es aber auch **weder lesen noch verändern noch
kontrollieren**. Für diesen Pfad genügt, dass er

1. den passenden `state` **kennt** und
2. einen Callback-Request in **genau dem Browserkontext auslöst**, der das
   passende Cookie aktuell hält und automatisch mitsendet.

Nach einer Offenlegung des `state` — oder durch einen **bösartigen oder
kompromittierten Identity Provider**, der die Rückleitung ohnehin steuert — kann
ein gezielt malformed Callback deshalb denselben Login fail-closed verbrauchen.

**Die Browserbindung verhindert also nicht jeden Verfügbarkeitsangriff.** Sie
schützt die **Einmaligkeit** einer Transaktion, verhindert deren **erneute
Verarbeitung** und vermeidet einen **Store-Rollback**; sie garantiert **keine
vollständige DoS-Immunität**.

Der Schaden bleibt auf die **betroffene einzelne Login-Transaktion** begrenzt:
Es entsteht kein Zugriff, keine Session und keine Identitätsbindung, und andere
Logins bleiben unberührt. Ein Nutzer, dessen Login so verbraucht wurde, startet
einen **neuen Login-Start** — der reguläre, jederzeit verfügbare Weg. Das ist
ein begrenzter Login-Denial-of-Service gegen genau diese eine Transaktion und
bewusst der Preis für die Einmaligkeitsgarantie.

## 7. Browserbindung und Cookie-Löschung

**Cookie:** `__Host-liquent_oidc_state` (LQ-152 §7, gesetzt von LQ-154).

### Fehlendes Cookie

- **neutral** abbrechen,
- **kein** Claim,
- **kein** Verifier,
- Cookie **nicht** löschen,
- **keine** Session.

### Mismatch

- der konstantzeitliche Vergleich **wurde durchgeführt**,
- **neutral** abbrechen,
- **kein** Claim,
- **kein** Verifier,
- vorhandenes Cookie **nicht löschen**,
- **keine** Session.

Das schützt den **neueren** Login bei `last-start-wins` (LQ-152 §9): Es gibt
genau einen Cookie-Slot, ein nicht passendes Cookie gehört daher zu einer
anderen — typischerweise neueren und legitimen — Transaktion. Würde ein
fehlgeschlagener Callback löschen, könnte ein veralteter oder untergeschobener
Link die Bindung eines laufenden Logins entfernen: ein Login-Denial-of-Service,
ausgelöst von einem Aufruf, der die Bindungsprüfung gerade **nicht** bestanden
hat.

Ein **fehlendes** Cookie löscht aus demselben Grund nichts: Ein `Set-Cookie` mit
Ablauf in der Vergangenheit ist eine Schreiboperation auf denselben Slot und
könnte ein zwischenzeitlich gesetztes, gültiges Cookie treffen.

### Match

- `OidcLoginState` aus dem **exakt** passenden Querywert bilden,
- Claim-Port **genau einmal** aufrufen,
- danach Cookie auf **jedem** weiteren Endpfad löschen:

| Endpfad |
|---|
| Claim liefert `None` |
| Queryform ungültig |
| Providerfehler |
| Verifier liefert `None` |
| `OidcVerificationUnavailable` |
| sonstiger interner Fehler |
| spätere Identitäts-, Admission- oder Sessionfehler |
| vollständiger Erfolg |

**Kein zweiter Claim, kein Rollback und kein erneutes Setzen desselben
Binding-Cookies.** Die Liste umfasst ausdrücklich auch Endpfade aus Slices, die
noch nicht existieren — die Löschpflicht überlebt sie.

## 8. Cookie-Löschvertrag

Für den späteren Helfer gilt verbindlich:

```
clear_oidc_state_cookie(response)
```

Er löscht **exakt denselben Slot**:

| Attribut | Wert |
|---|---|
| Name | `__Host-liquent_oidc_state` |
| `Secure` | ja |
| `HttpOnly` | ja |
| `SameSite` | `Lax` |
| `Path` | `/` |
| `Domain` | **kein** |

Die Löschung setzt mindestens `Cache-Control: no-store`.

Der Name folgt dem bestehenden `clear_session_cookie` in
`transport/http/session_cookie.py`; der Helfer gehört jedoch neben
`set_oidc_state_cookie` in `transport/http/oidc_state_cookie.py`, weil dort die
`__Host-`-Invarianten bereits liegen.

**Keine Änderung am bestehenden `liquent_session`-Cookie.**

**Noch keine Implementierung des Helfers in LQ-158.**

## 9. Atomarer Claim

Nach erfolgreichem Binding-Match:

```
claim_transaction(OidcLoginState(query_state))
```

**Vertrag:**

- **exakt einmal**,
- **kein** vom Browser geliefertes `now` — der Store liest seine eigene Uhr
  (LQ-139),
- `None` vereinheitlicht **unbekannt**, **abgelaufen** und **bereits
  konsumiert**,
- `None` führt **neutral** zum Ende,
- das Cookie wird **trotzdem gelöscht**, weil das Match zuvor erfolgreich war,
- der Verifier wird bei `None` **nicht** aufgerufen,
- die geclaimte Transaktion bleibt auf **allen** Folgeschritten verbraucht,
- **keine** Retry- oder Kompensationslogik.

**Der `state` verlässt nach dem Claim die Browserbindungs- und Store-Ebene
nicht** und wird **nicht** in das Verifikationsobjekt übernommen (LQ-157 §3).

## 10. Providerfehler

Bei gültiger Providerfehlerform **und** erfolgreichem Match:

1. Transaktion claimen,
2. Cookie löschen,
3. Verifier **nicht** aufrufen,
4. **neutral** beenden.

**Der Providerfehler wird nicht differenziert.** Insbesondere **keine**
Verzweigung auf `access_denied`, `login_required`, `interaction_required`,
`temporarily_unavailable` oder andere Providerwerte.

**Keine Providertexte** im Body, Redirect, Log oder in Telemetrie.

Ein Providerfehler ist damit **kein Sonderweg** an Bindung und Claim vorbei:
Sonst wäre ein angehängter `error`-Parameter ein billiger Weg, die
Browserbindung zu umgehen oder eine Transaktion unverbraucht zu lassen
(LQ-155 §11).

## 11. Erfolgsform und Verifier-Aufruf

**Nur** bei erfolgreichem Binding-Match, erfolgreichem atomarem Claim **und**
gültiger Erfolgsquery wird **exakt ein** Objekt erzeugt:

```python
OidcAuthorizationCodeVerification(
    authorization_code=<exakter Query-Code>,
    expected_issuer=transaction.expected_issuer,
    expected_nonce=transaction.expected_nonce,
    code_verifier=transaction.code_verifier,
    redirect_uri=transaction.redirect_uri,
)
```

**Verbindlich:**

- **keine** Normalisierung oder Dekodierung jenseits der standardmäßigen
  Querydekodierung,
- **keine** Werte aus der aktiven Konfiguration im Transport zusammensetzen —
  Token-Endpunkt, JWKS-Quelle, Allowlist und Clock-Skew liest die
  Verifikationsimplementierung selbst (LQ-156, LQ-157 §3),
- **kein** `state`,
- **keine** Admission-ID,
- **kein** Return-Path,
- **keine** URL- oder Tokenanalyse,
- Verifier **genau einmal** aufrufen.

Alle vier Transaktionswerte stammen **ausschließlich** aus dem geclaimten
Record, nicht aus der Query und nicht aus der aktuellen Konfiguration.

### Serverseitig zurückbehalten

Der Callback-Ablauf behält **separat** und serverseitig:

- `transaction.admission_id`
- `transaction.return_path`

**Diese erreichen den Verifier niemals.** Die Admission ist ein Capability-Wert,
der eine einmalige Onboarding- oder Bindungsoperation autorisiert; eine Grenze,
die ausschließlich eine Identität **beweist**, darf ihn weder tragen noch
konsumieren können. Der Return-Path ist eine reine Transportentscheidung.

## 12. Verifier-Ergebnisse

### `ExternalIdentity`

Bedeutet **ausschließlich**: die externe Identität wurde für genau diese
Login-Transaktion vollständig verifiziert. **Keine** Berechtigung, **keine**
Mitgliedschaft, **keine** Session.

Danach — in **späteren** Slices:

1. bestehende Bindung über `ExternalIdentityLookup` auflösen,
2. falls ungebunden, **ausschließlich** die geclaimte `admission_id` über
   `ExternalIdentityAdmissionStore` verwenden,
3. interne Zulassung und Autorisierung prüfen,
4. **erst danach** eine Liquent-Session ausgeben.

### `None` — neutrale fachliche Verifikationsablehnung

- Cookie **bereits gelöscht**,
- Transaktion **verbraucht**,
- **keine** Identitätsauflösung,
- **keine** Admission-Verarbeitung,
- **keine** Session,
- **kein** Retry derselben Transaktion.

### `OidcVerificationUnavailable` — technische Nichtverfügbarkeit

- Cookie **bereits gelöscht**,
- Transaktion **verbraucht**,
- **keine** Identitätsauflösung,
- **keine** Admission-Verarbeitung,
- **keine** Session,
- **kein** Retry derselben Transaktion.

Ein späterer Transportvertrag **darf** technische Nichtverfügbarkeit anders
behandeln als fachliche Ablehnung, solange **beide** detail- und bestandsfrei
bleiben (LQ-155 §12).

**LQ-158 nimmt die endgültigen Statuscodes und Benutzerziele bewusst nicht
vorweg**, weil die Completion-/Session-Grenze noch fehlt.

## 13. HTTP-Datenschutz und Caching

Jeder spätere Callback-Ausgang:

```
Cache-Control: no-store
Pragma: no-cache
Referrer-Policy: no-referrer
```

Zusätzlich:

- **leerer Body**,
- **keine** Reflexion von Queryparametern,
- **kein** Authorization Code, `state` oder Providertext in `Location`,
- **keine** vollständige Callback-URL in Logs oder Telemetrie,
- **keine** Query in Traces oder Metriklabels,
- **keine** Token- oder Claimdaten in Browserantworten.

Erlaubt bleiben ein normalisierter Routenname, die HTTP-Methode, ein neutraler
Statuscode und eine Korrelations-ID **ohne** OIDC-Material (LQ-152 §12).

### Weg von der Callback-URL

Weil die Callback-URL **Code und State enthält**, muss die spätere vollständige
Route den Browser nach einem behandelten Callback mit **`303 See Other`** von
dieser URL wegführen. Sonst blieben beide Werte in Verlauf, Referer und
geteilten Links stehen.

Die Ziele müssen **serverseitig festgelegte oder bereits validierte interne
relative Pfade** sein — **keine** absolute URL und **kein** offener Redirect
(LQ-136).

## 14. Was LQ-158 ausdrücklich noch nicht entscheidet

- die konkreten Erfolgs- oder Fehlerziele,
- ob fachliche Ablehnung und technische Nichtverfügbarkeit **dasselbe** Ziel
  verwenden,
- wie ein Frontend einen neutralen Fehler anzeigt,
- wie der CSRF-Wert einer späteren Liquent-Session an den Browser gelangt.

Diese Entscheidungen benötigen **zuerst** die interne Completion-/Session-Grenze.
Sie jetzt zu treffen hieße raten.

## 15. Harte Implementierungsvoraussetzung

**Die vollständige Callback-Route darf noch nicht implementiert werden.**

Vorher erforderlich:

1. ein **transportfreier Callback-Anwendungsfall**, der Claim, Verifier,
   Identity-Lookup, optionale Admission-Bindung und Session-Ausgabe in
   korrekter Reihenfolge verbindet,
2. eine **Entscheidung, wie die neue Session samt CSRF-Wert** nach einer
   OIDC-Navigation sicher an den Browser ausgegeben wird,
3. **serverseitig validierte interne Erfolgs- und Fehlerziele**.

LQ-158 **dokumentiert diese Blockade ausdrücklich**, statt eine halbe Route mit
unsicherer Sessionübergabe zu bauen. Eine Route, die claimt, verifiziert und
danach nicht sicher abschließen kann, wäre schlechter als keine Route: Sie
verbrauchte Login-Transaktionen ohne erreichbares Ergebnis.

## Bewusst nicht enthalten

- keine Python-Implementierung, kein Querymodell, kein Parser,
- kein Cookie-Helfer, keine Callback-Route,
- kein Verifier-Adapter, kein Tokenaustausch,
- keine OIDC-/OAuth-/JWT-/JOSE-Bibliothek, keine JWKS-Abfrage,
- keine Identitätsauflösung, keine Admission-Verarbeitung, keine
  Session-Erzeugung, keine CSRF-Ausgabeentscheidung,
- keine Erfolgs-/Fehlerzielkonfiguration,
- keine Persistenz oder Migration, kein Production-Wiring,
- keine CORS-, Deployment-, CI-, Container-, Dependency- oder Grype-Änderung,
- keine Änderung an LQ-152, LQ-154, LQ-155, LQ-156, LQ-157 oder am
  `liquent_session`-Cookie.

## Nächster Schritt

In dieser Reihenfolge, jeweils als eigener kleiner Slice — **alle hier nicht
begonnen**:

1. der **Verifikationsadapter**, der LQ-157 erfüllt,
2. der **transportfreie Callback-Anwendungsfall** (§15.1),
3. die **Session-/CSRF-Ausgabeentscheidung** nach OIDC-Navigation (§15.2),
4. **validierte interne Ziele** (§15.3),
5. der **Cookie-Löschhelfer** nach §8,
6. **erst dann** die Callback-Route nach diesem Vertrag.
