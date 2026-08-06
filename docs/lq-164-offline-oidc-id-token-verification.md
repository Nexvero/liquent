# LQ-164 — Offline OIDC ID Token Verification

## Reine Offline-Grenze

Der kryptografische und Claim-Verifikationskern des späteren Adapters. Er prüft
ein **bereits erhaltenes** `id_token` gegen ein **bereits vertrauenswürdig
geladenes** JWKS.

Der Baustein führt **keine Netzwerkoperation** aus, lädt **keine
Konfiguration** und **kein JWKS**, tauscht **keinen** Authorization Code,
implementiert **keinen** Cache und erfüllt **noch nicht** den LQ-157-Port. Der
vollständige Adapter ruft ihn später auf.

`src/liquent_platform/identity/oidc_id_token_verifier.py`

```python
def verify_oidc_id_token(
    id_token: str,
    jwks: Mapping[str, object],
    configuration: TrustedOidcClientConfiguration,
    verification: OidcAuthorizationCodeVerification,
    now: datetime,
) -> ExternalIdentity | None: ...
```

## `None` versus `OidcVerificationUnavailable`

Die Trennlinie folgt der PyJWT-Ausnahmehierarchie, in der `InvalidTokenError`
und `PyJWKError` **disjunkte** Zweige sind:

| Situation | Ergebnis |
|---|---|
| `InvalidTokenError` und Unterklassen — Format, Signatur, Algorithmus, Issuer, Audience | **`None`** |
| eigene Claim-Ablehnung — Zeit, Audience-Form, `azp`, Nonce, Subject | **`None`** |
| kein eindeutiger passender Schlüssel im Set | **`None`** |
| `jwks` strukturell unbrauchbar | **`Unavailable`** |
| ausgewählter, aber nicht parsebarer vertrauenswürdiger JWK | **`Unavailable`** |
| unerwarteter Bibliotheks- oder Kryptofehler | **`Unavailable`** |
| naive Uhr — Aufruferfehler | **`ValueError`** vor jeder Tokenverarbeitung |

`None` heißt „belastbar geprüft und abgelehnt", `Unavailable` heißt „kein
Urteil möglich". Es gibt **kein** pauschales `except Exception: return None`.
**Keine** Exception gibt Token, Header, Claim, Schlüsselmaterial, Issuer,
Subject oder Nonce wieder.

## Algorithmus- und Schlüsselauswahl

**Interne Allowlist** — ausschließlich asymmetrisch: `RS256/384/512`,
`PS256/384/512`, `ES256/384/512`, `EdDSA`. PyJWT böte zusätzlich
`HS256/384/512`, `none`, `ES256K` und `ES521`; alle sind bewusst
ausgeschlossen, weil ein geteiltes Geheimnis oder ein unsigniertes Token die
Identität eines Issuers nicht beweisen kann.

Akzeptiert wird die **Schnittmenge** aus dieser Allowlist und
`configuration.allowed_signing_algorithms`, exakt und case-sensitiv verglichen.
Der Header kann die Konfiguration **nie erweitern**; es gibt **keinen**
Fallback. (LQ-156 verbietet `none` bereits in der Konfiguration — die interne
Allowlist ist die zweite, unabhängige Sperre.)

**`jku`, `x5u` und `jwk` im Header → `None`.** Sie werden nie befolgt, geladen
oder geloggt: ihnen zu folgen hieße, den Prüfschlüssel vom Prüfling bestimmen
zu lassen. Unverifizierte Header dienen ausschließlich der sicheren Auswahl
**innerhalb** des übergebenen Sets.

**Auswahl nur aus `jwks["keys"]`.** Jeder Kandidat muss ein Mapping sein; `use`
fehlt oder ist exakt `sig`; `key_ops` fehlt oder ist eine Liste mit `verify`;
ein im JWK vorhandenes `alg` muss exakt zum Header passen. Mit Header-`kid`
muss dieser ein nicht leerer String sein und genau einen Kandidaten treffen;
ohne `kid` muss nach den Filtern genau einer übrig bleiben. Null oder mehrere →
`None`; Mehrdeutigkeit wird **abgewiesen**, nicht aufgelöst. **Kein** Refresh
und **keine** zweite Auswahlrunde in diesem Slice.

## Verpflichtende Prüfungen

**Durch PyJWT**, nach der Schlüsselwahl: Tokenformat, Signatur, ausgewählter
Algorithmus, Issuer byte-genau, Audience enthält `configuration.client_id`.
Signatur, Issuer und Audience werden **nicht** deaktiviert.

**Danach im Modul**, auf den verifizierten Claims:

- **Zeit** ausschließlich mit dem übergebenen `now` und
  `configuration.clock_skew`. `exp` ist erforderlich und endlich; abgelaufen,
  sobald `now` auch mit Skew nicht mehr davor liegt. `iat` ist erforderlich,
  endlich und nicht später als `now + skew`. `nbf` ist optional, muss aber
  falls vorhanden endlich und nicht zu weit in der Zukunft sein. `bool` ist
  **keine** gültige NumericDate. Kein Tokenwert bestimmt den Skew, und es gibt
  **keine versteckte Systemuhr**: PyJWTs automatische Zeitprüfung ist
  ausgeschaltet.
- **Audience und `azp`.** String- und Stringlisten-Audience werden
  unterstützt; leere, falsch typisierte oder gemischte Audience wird
  abgelehnt. Bei mehreren Audiences ist `azp` zwingend; ist `azp` überhaupt
  vorhanden, muss es ein echter String sein und exakt dem Client entsprechen.
- **Nonce** erforderlich, nicht leer, **konstantzeitlich** gegen
  `verification.expected_nonce` verglichen.
- **Subject** erforderlich und nicht leer.

**Keine Normalisierung**, kein Trimmen, keine E-Mail-Ableitung.

## Ergebnis

Nur nach vollständig erfolgreicher Prüfung:

```python
ExternalIdentity(issuer=configuration.issuer, subject=claims["sub"])
```

Der Issuer stammt aus der **aktiven vertrauenswürdigen Konfiguration**, nicht
erneut aus einem Claim. Es werden **keine** Rohclaims, Tokens, E-Mails, Namen,
Gruppen, Rollen, Admission-, User-, Workspace- oder Sessiondaten
zurückgegeben.

## Verhältnis zu LQ-155, LQ-160 und LQ-161

- **LQ-155 §7** listet die verpflichtenden ID-Token-Prüfungen; LQ-164 setzt sie
  um. Ein erfolgreicher Token-Endpunkt-Response wäre kein Grund, eine davon zu
  überspringen — hier gibt es ihn ohnehin nicht.
- **LQ-160** verbietet eigene Kryptografie und tokenkontrollierte
  Schlüsselquellen und verlangt die Algorithmus-Allowlist; LQ-164 hält beides
  ein. Redirect-Verbot, Timeouts, Größengrenzen und Cache bleiben Sache des
  späteren Adapters (LQ-162 liefert dessen Grenzen).
- **LQ-161** stellt `PyJWT[crypto]` bereit; LQ-164 ist die erste produktive
  Nutzung. **Keine eigene** RSA-, EC-, EdDSA-, ASN.1-, JWS- oder
  Signaturimplementierung.

## Bewusst nicht enthalten

Kein Authorization-Code-Austausch, kein Token-Endpunkt, kein JWKS-Abruf oder
Cache, kein HTTP-Client, keine Discovery, kein Retry oder Redirect, keine
Portimplementierung, keine aktive Konfigurationsauflösung, keine
Callback-Route, keine Identity-Auflösung oder Admission, keine
Session-/CSRF-Erzeugung, kein Production-Wiring und keine Dependency-,
Lockfile-, CI-, Container-, Grype- oder Deployment-Änderung.

## Nächster Schritt

Der vollständige Verifikationsadapter, der den Code am Token-Endpunkt einlöst,
das JWKS gemäß LQ-162 begrenzt lädt und diesen Kern aufruft — danach
unverändert die Reihenfolge aus LQ-158 §15.
