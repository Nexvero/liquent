# LQ-160 — OIDC Verification Adapter Contract

## Status

Architekturentscheidung und **Vertrag**, providerneutral. **Nur Dokumentation.**
**Keine** Implementierung, **kein** Adapter, **kein** HTTP-Client, **kein**
JWKS-Cache, **keine** Bibliotheksinstallation und **keine**
Dependency-Änderung — `pyproject.toml` und Lockfiles bleiben unverändert.

Baut auf LQ-155 (Verifikationsgrenze), LQ-156 (Konfigurationsgrenze), LQ-157
(Port und Eingabeobjekt) und LQ-158 (Callback-Ingress) auf.

## 1. Ziel und Systemgrenze

Der Vertrag legt fest, **wie ein späterer Adapter den LQ-157-Port erfüllen
darf**, ohne einen konkreten Identity Provider auszuwählen:

```python
class OidcAuthorizationCodeVerifier(Protocol):
    def verify_authorization_code(
        self, verification: OidcAuthorizationCodeVerification
    ) -> ExternalIdentity | None: ...
```

Ein konkreter Provider bleibt **Konfiguration**, niemals eine
Fallunterscheidung im Adapter.

## 2. Keine eigene Kryptografie

**Verbindlich:**

- **Keine** selbst implementierte JWT-, JWS-, ASN.1-, RSA-, EC- oder
  Signaturprüfung.
- **Keine** manuelle Interpretation kryptografischer Schlüssel — kein eigenes
  Parsen von JWK-Parametern zu Schlüsselobjekten, kein eigenes Base64URL-
  gestütztes Zusammensetzen von Modulus/Exponent oder Kurvenpunkten.
- Eine **etablierte, gepflegte Python-Bibliothek** muss die JOSE/JWT-
  Verifikation übernehmen.

Selbstgebaute Signaturprüfung ist historisch eine der ergiebigsten Fehlerquellen
in OIDC-Integrationen (Algorithmusverwechslung, fehlende Prüfung, unsichere
Vergleiche). Diese Klasse von Fehlern wird durch die Bibliothekspflicht
**strukturell** ausgeschlossen, nicht durch Sorgfalt.

**Eine konkrete Bibliothek wird in LQ-160 nicht als Abhängigkeit hinzugefügt.**
Abschnitt 12 gibt eine **Empfehlung**; die Aufnahme ist eine eigene Entscheidung
des späteren Implementierungsslices.

## 3. Serverseitiger Code-Austausch

Der Adapter sendet den Authorization Code **ausschließlich serverseitig** an den
konfigurierten `token_endpoint`.

Verbindliche Parameter:

| Parameter | Quelle |
|---|---|
| `grant_type=authorization_code` | fest |
| `code` | `OidcAuthorizationCodeVerification.authorization_code` |
| `redirect_uri` | `OidcAuthorizationCodeVerification.redirect_uri` |
| `client_id` | aktive vertrauenswürdige Konfiguration |
| `code_verifier` | `OidcAuthorizationCodeVerification.code_verifier` |

**Keine** Werte aus Browser-Headern, Queryparametern, `Host`, `Origin`, Cookies
oder frei gewählten Provider-/Issuer-Parametern.

`redirect_uri` und `code_verifier` stammen aus dem **geclaimten Record**, weil
das Protokoll exakt die Werte verlangt, die im Authorization Request standen;
`client_id` stammt aus der **aktuellen** Konfiguration, weil sie eine aktuelle
serverseitige Tatsache ist (LQ-155 §6).

**Client-Authentifizierung bleibt eine spätere explizite Erweiterung.** In
diesem Slice gibt es **kein Client-Secret-Modell**; entsprechend trägt
`TrustedOidcClientConfiguration` weiterhin kein Secret (LQ-156).

## 4. Netzwerkgrenze

- **Ausschließlich** die exakt konfigurierte HTTPS-URL des `token_endpoint`.
- **Keine** Discovery und **keine** Weiterleitung auf einen anderen
  Token-Endpunkt.
- **Redirects beim Token-Austausch sind standardmäßig verboten.** Ein
  gefolgter Redirect könnte Code und PKCE-Verifier an einen nicht
  konfigurierten Host tragen.
- Endliche **Verbindungs-, Lese- und Gesamtzeitgrenzen** müssen später
  **explizit konfiguriert** sein — kein Verlass auf Bibliotheksdefaults.
- **Begrenzte Antwortgröße**: eine unbegrenzt gelesene Antwort ist ein
  Speicher-DoS-Vektor.
- **Keine automatische Wiederholung** des Authorization-Code-Austauschs. Der
  Code ist einmalig; ein Retry wäre ein Replay-Versuch mit einem bereits
  verbrauchten Wert.
- **Keine** Proxy-, mTLS-, Private-Key-JWT- oder DPoP-Entscheidung in diesem
  Slice.
- Netzwerk-, Timeout-, TLS- und Parserfehler werden **neutral** zu
  `OidcVerificationUnavailable`.

## 5. Tokenantwort

- Erwartet wird eine **erfolgreiche, syntaktisch gültige** Tokenantwort mit
  `id_token`.
- **Access Token, Refresh Token und sonstige Token werden nicht in
  Liquent-Domainmodelle übernommen und nicht persistiert.** Sie werden nicht
  gebraucht: die Grenze beweist eine Identität, sie ruft keine
  Provider-APIs auf.
- **Kein Token** erscheint in URL, Cookie, Log, Telemetrie, Trace, Metriklabel
  oder Fehlertext.
- **Providerfehlertexte** (`error`, `error_description`, `error_uri`) werden
  **nicht** nach außen und **nicht** in sicherheitskritische innere Modelle
  übernommen.
- Eine Antwort **ohne** `id_token` — ebenso ein leeres oder nicht
  stringförmiges `id_token` — liefert den für die angeforderte OpenID-Prüfung
  **zwingenden Beweis nicht** und ergibt **`OidcVerificationUnavailable`**,
  auch wenn die Antwort im Übrigen erfolgreich und lesbar ist. Ohne `id_token`
  kann **keine** Signatur-, Issuer-, Audience-, Nonce-, Ablauf- oder
  Subject-Prüfung stattfinden; es gibt also **kein** belastbares negatives
  Identitätsurteil (Abschnitt 6).
- Eine syntaktisch nicht parsebare, übergroße oder strukturell nicht als
  Tokenantwort verwertbare Antwort ergibt ebenfalls
  **`OidcVerificationUnavailable`**.

## 6. Klassengrenze: `None` oder `OidcVerificationUnavailable`

**Die Entscheidungsregel — nicht die Liste — ist verbindlich:**

> Konnte die Prüfung **belastbar zu einem Urteil** geführt werden?
> **Ja**, und das Urteil lautet „abgelehnt" → `None`.
> **Nein**, die Prüfung war technisch nicht belastbar abschließbar →
> `OidcVerificationUnavailable`.

Daraus folgen unter anderem:

| Situation | Ergebnis |
|---|---|
| Token-Endpunkt lehnt den Code ab (gültige Fehlerantwort) | `None` |
| `id_token` vorhanden, aber Signatur ungültig | `None` |
| Algorithmus nicht in `allowed_signing_algorithms` | `None` |
| kein eindeutig passender Schlüssel, Prüfung war durchführbar | `None` |
| `iss`, `aud`, `azp`, `exp`, `nbf`, `iat` oder `nonce` fehlerhaft | `None` |
| `sub` fehlt oder leer | `None` |
| **`id_token` fehlt, leer oder nicht stringförmig** | **`Unavailable`** |
| Token-Endpunkt nicht erreichbar, TLS- oder Timeoutfehler | `Unavailable` |
| Antwort nicht parsebar oder überschreitet die Größengrenze | `Unavailable` |
| Antwort strukturell nicht als Tokenantwort verwertbar | `Unavailable` |
| JWKS-Quelle nicht erreichbar oder nicht parsebar | `Unavailable` |
| Konfigurationsquelle technisch nicht lesbar | `Unavailable` |
| Krypto-Backend oder Bibliothek intern gescheitert | `Unavailable` |

**Warum ein fehlendes `id_token` kein `None` ist:** `None` bedeutet „der
**vorhandene** Identitätsbeweis wurde belastbar geprüft und abgelehnt". Ein
**fehlender** Beweis wurde **nicht geprüft** und darf nicht so behandelt werden,
als läge ein negatives Prüfurteil vor. Die Trennlinie verläuft also **nicht**
zwischen „Antwort erfolgreich" und „Antwort fehlerhaft", sondern zwischen „ein
Beweis lag vor und wurde beurteilt" und „es gab nichts zu beurteilen".

Eine **gültige OAuth-/OIDC-Fehlerantwort**, die den einmaligen Code ablehnt,
bleibt dagegen `None`: Der Provider hat den vorgelegten Nachweis belastbar
beurteilt und verworfen.

**Keine Detailunterklassen nach außen.** Die Regel existiert, damit ein späterer
Implementierer auch einen hier **nicht** aufgeführten Fall korrekt einordnen
kann, statt die Tabelle zu erweitern. Beide Ergebnisse bleiben **detailfrei**;
insbesondere gelangen **keine Providerdetails** nach außen.

Beide Ausgänge lassen die bereits geclaimte Transaktion **verbraucht** und sind
für dieselbe Transaktion **nicht retrybar** (LQ-157, LQ-158 §12).

## 7. JWKS und Schlüsselwahl

- Schlüssel **ausschließlich** vom exakt konfigurierten `jwks_uri`.
- **Keine** Discovery und **keine** `jku`-/`x5u`-gesteuerte Netzwerkanfrage aus
  dem Token.
- **`jku`, `x5u`, `jwk`** und ähnliche **tokenkontrollierte** Schlüsselquellen
  werden ignoriert beziehungsweise abgewiesen. Ihnen zu folgen hieße, den
  Prüfschlüssel vom Prüfling bestimmen zu lassen.
- **Nur** Algorithmen aus `allowed_signing_algorithms` (LQ-156). Der `alg`-Wert
  im Header darf **auswählen**, niemals **erweitern**.
- **`alg=none` ist immer verboten.**
- **Keine Algorithmusverwechslung**: ein Schlüsseltyp darf nicht mit einem
  Algorithmus einer anderen Familie verwendet werden, und der Tokenheader darf
  keinen Wechsel zwischen asymmetrisch und symmetrisch auslösen.
- **`kid`** dient **ausschließlich** zur Auswahl **innerhalb** des
  vertrauenswürdig geladenen JWKS.
- Kein passender eindeutiger Schlüssel → **`None`**, sofern die Prüfung
  belastbar durchgeführt werden konnte.
- JWKS-Netzwerk- oder Parserfehler → **`OidcVerificationUnavailable`**.

## 8. JWKS-Cache und Rotation

Zielvertrag für einen späteren Cache:

- **begrenzter In-Memory-Cache pro exakt konfigurierter `jwks_uri`**,
- **keine** unbeschränkte Schlüssel- oder Issuer-Sammlung,
- **begrenzte Cache-Laufzeit**,
- bei unbekanntem `kid` **höchstens ein kontrolliertes Refresh**,
- **danach keine Retry-Schleife**,
- **kein erneuter Token-Endpunkt-Aufruf** — der Code ist bereits verbraucht,
- Rotation darf **keine alten, nicht mehr vertrauenswürdigen Schlüssel
  unbegrenzt festhalten**,
- **persistenter oder verteilter Cache** bleibt späteren Entscheidungen
  vorbehalten.

Der Cache ist an die **konfigurierte URI** gebunden und nicht an einen aus dem
Token gelesenen Wert; sonst könnte ein Token seine eigene Cache-Partition
anlegen.

**Keine Cache-Implementierung in LQ-160.**

## 9. ID-Token-Prüfung

Es gilt unverändert **LQ-155 §7**. Bestätigt und für den Adapter verbindlich:

- Signatur **vollständig** geprüft,
- Algorithmus **allowlisted**,
- `iss` **byte-genau** gegen die aktive Konfiguration,
- `aud` enthält den konfigurierten Client,
- **`azp`-Regel** bei mehreren Audiences,
- `exp` und `nbf` mit **ausschließlich** dem konfigurierten `clock_skew`
  (LQ-156) — kein Wert aus dem Token, kein Bibliotheksdefault,
- `iat` nur soweit der bestehende Vertrag es verlangt,
- **`nonce` byte-genau und konstantzeitlich** gegen `expected_nonce`,
- `sub` vorhanden und **nicht leer**,
- Ergebnis **ausschließlich** `ExternalIdentity(issuer, subject)`.

**E-Mail, Anzeigename oder andere Claims sind niemals Identitätsschlüssel und
niemals Berechtigung** (LQ-129). Ein erfolgreicher Aufruf erzeugt **keinen**
User, **kein** Binding, **keine** Mitgliedschaft, **keine** Rolle und **keine**
Session.

Ein erfolgreicher Token-Endpunkt-Response ist **kein** Grund, eine dieser
Prüfungen zu überspringen (LQ-155 §7).

## 10. Aktive Konfiguration

Der spätere Adapter verwendet **genau einen** vertrauenswürdigen
Konfigurationssnapshot für den **gesamten** Verifikationsvorgang.

- **Keine** erneute browsergesteuerte Auswahl.
- **Keine Mischung** von Token-Endpunkt einer Konfiguration mit JWKS, Issuer
  oder Client einer anderen.
- Eine **Konfigurationsrotation während eines laufenden Aufrufs** darf **keinen
  gemischten Snapshot** erzeugen. Ein Aufruf, der den Token-Endpunkt der alten
  und das JWKS der neuen Konfiguration verwendete, prüfte gegen ein
  Vertrauensbild, das nie gültig war.

**Wie der Snapshot injiziert wird, bleibt dem späteren Implementierungsslice
vorbehalten. LQ-160 ändert den Port nicht.**

## 11. Fehler- und Geheimnisgrenze

- **`None`**: belastbar ausgeführte, aber **abgelehnte** Verifikation.
- **`OidcVerificationUnavailable`**: die Prüfung konnte **technisch nicht
  belastbar** abgeschlossen werden.
- **Beide enthalten keine Details.**

**Niemals** in Exceptions, Logs, Telemetrie, Traces oder Metriklabels:
Authorization Code, Code Verifier, ID Token, Access Token, Refresh Token,
Nonce, Schlüsselmaterial und vollständige Providerantworten.

**Keine Differenzierung** nach bekanntem Benutzer, Subject, E-Mail, Binding oder
Admission — eine solche Unterscheidung wäre ein Bestandsorakel.

Erlaubt bleiben ein normalisierter Operationsname, eine neutrale Fehlerklasse
und eine Korrelations-ID **ohne** OIDC-Material (LQ-152 §12).

## 12. Bibliotheksbewertung

**Vorläufig und nicht verbindlich.** Grundlage: die PyPI-JSON-Metadaten der
Pakete und der Quelltext des jeweiligen JWKS-Clients, abgerufen am
**2026-08-05**. Bewertet wird die **installierbare Paketoberfläche**, nicht ein
Marktüberblick. Es werden **keine** CVE- oder Sicherheitsbehauptungen
aufgestellt, die hier nicht verifiziert wurden.

| Paket | Version (Datum) | `requires-python` | Deklarierte Abhängigkeiten | 3.13-Classifier |
|---|---|---|---|---|
| **PyJWT** | 2.13.0 (2026-05-21) | `>=3.9` | `typing_extensions` nur für `<3.11`; `cryptography>=3.4.0` als `crypto`-Extra | ja (auch 3.14) |
| **joserfc** | 1.7.4 (2026-07-19) | `>=3.10` | `cryptography>=45.0.1` | ja (auch 3.14) |
| **Authlib** | 1.7.2 | `>=3.10` | `cryptography`, `joserfc>=1.6.0` | ja (auch 3.14) |
| *python-jose* | 3.5.0 (**2025-05-28**, rund 14 Monate alt) | `>=3.9` | `ecdsa`, `rsa`, `pyasn1` | ja |

**Priorisierte Empfehlung für den späteren Implementierungsslice:**

1. **PyJWT** — schmalste Oberfläche für genau diesen Zweck (JWT-Verifikation
   plus JWKS-Auswahl). `cryptography` kommt nur über das `crypto`-Extra, die
   Supply-Chain-Wirkung ist damit am kleinsten und explizit steuerbar.
2. **joserfc** — Alternative, wenn breitere JOSE-Abdeckung gebraucht wird;
   jüngste Releasedaten der drei, zieht `cryptography` unbedingt.
3. **Authlib** — nur falls zusätzlich ein vollständiger OAuth-Client gewünscht
   ist; größere Oberfläche und zieht `joserfc` **und** `cryptography`.

**python-jose wird nicht empfohlen**: das älteste Releasedatum der Kandidaten
und ein Abhängigkeitssatz aus reinen Python-Krypto-Paketen (`ecdsa`, `rsa`,
`pyasn1`) statt der `cryptography`-Bindings. Das ist eine
**Supply-Chain-Beobachtung**, keine Aussage über konkrete Schwachstellen.

### Zwei geprüfte Feststellungen mit Folgen für den Adapter

**a) Der eingebaute JWKS-Client erfüllt Abschnitt 4 und 7 nicht vollständig.**
Der Quelltext von PyJWTs `PyJWKClient` holt das JWKS über
`urllib.request.urlopen` mit `timeout` und `ssl_context`. Er konfiguriert
**keine Redirect-Behandlung** und **keine Antwortgrößengrenze** — beides ist in
Abschnitt 4 verbindlich. Sein Cacheverhalten passt dagegen gut: JWK-Set-Cache
mit begrenzter Lebensdauer und **genau ein** Refresh-und-Retry bei unbekanntem
`kid`, was Abschnitt 8 entspricht.

**Verbindliche Folge:** Der Adapter muss die Redirect-Verbots- und
Größengrenze **selbst** durchsetzen — typischerweise, indem er das JWKS über
einen eigenen kontrollierten Client lädt und der Bibliothek **fertiges
Schlüsselmaterial** übergibt, statt deren eingebauten Fetcher zu verwenden. Das
gilt sinngemäß für jede Bibliothek mit eingebautem Fetcher und ist bei der
Auswahl zu prüfen.

**b) Ein HTTP-Client ist eine neue Laufzeitabhängigkeit.** Die sieben
deklarierten Laufzeitabhängigkeiten enthalten **keinen** HTTP-Client. `httpx`
liegt zwar in der Entwicklungsumgebung, ist aber **nicht deklariert** und hat
ein leeres `Required-by` — es ist beiläufiges Testwerkzeug. Der spätere Slice
muss den Client für Token-Endpunkt und JWKS also **ausdrücklich** entscheiden
und darf `httpx` nicht als vorhanden voraussetzen.

**`pyproject.toml` und Lockfiles bleiben in LQ-160 unverändert.**

## 13. Bewusst nicht enthalten

- keine Bibliotheksinstallation und keine Dependency-Änderung,
- kein Produktionscode, kein Adapter, kein HTTP-Client, kein JWKS-Cache,
- keine Ports oder Datenmodelle, keine Portänderung,
- keine Route und kein Callback-Use-Case,
- kein konkreter Identity Provider, keine Discovery,
- keine Client-Secrets, kein mTLS, DPoP oder Private-Key-JWT,
- keine Persistenz, kein Production-Wiring,
- keine CI-, Container-, Deployment-, CORS- oder Shared-Environment-Änderung.

## 14. Bewusst vertagte Entscheidungen

| Offen | Gehört zu |
|---|---|
| konkrete Bibliotheksaufnahme als Abhängigkeit | Implementierungsslice |
| HTTP-Client für Token-Endpunkt und JWKS | Implementierungsslice |
| Client-Authentifizierungsverfahren | eigener Slice |
| mTLS, DPoP, Private-Key-JWT, Proxy | eigener Slice |
| JWKS-Cache-Implementierung; persistenter/verteilter Cache | eigener Slice |
| Injektion des Konfigurationssnapshots | Implementierungsslice |
| konkreter Provider und Discovery-Vertrag | eigener Slice |

## 15. Nächster Schritt

Unverändert die Reihenfolge aus LQ-158 §15 — **alle noch nicht begonnen**: der
Verifikationsadapter nach diesem Vertrag, danach der transportfreie
Callback-Anwendungsfall, die Session-/CSRF-Ausgabeentscheidung, validierte
interne Ziele und zuletzt die Callback-Route.
