# LQ-164 — Offline OIDC ID Token Verification

## Offline-Grenze

Der kryptografische und Claim-Verifikationskern des späteren Adapters: Er prüft
ein **bereits erhaltenes** `id_token` gegen ein **bereits vertrauenswürdig
geladenes** JWKS.

**Keine** Netzwerkoperation, **keine** Konfigurations- oder JWKS-Ladung,
**kein** Code-Austausch, **kein** Cache, **keine** Portimplementierung.

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

Die Trennlinie folgt der PyJWT-Hierarchie, in der `InvalidTokenError` und
`PyJWKError` **disjunkte** Zweige sind:

| Situation | Ergebnis |
|---|---|
| Format, Signatur, Algorithmus, Issuer, Audience (`InvalidTokenError`) | `None` |
| eigene Claim-Ablehnung: Zeit, Audience-Form, `azp`, Nonce, Subject | `None` |
| kein eindeutiger passender Schlüssel | `None` |
| unbrauchbare `jwks`-Struktur oder nicht parsebarer vertrauenswürdiger JWK | `Unavailable` |
| unerwarteter Bibliotheks- oder Kryptofehler | `Unavailable` |
| naive Uhr (Aufruferfehler) | `ValueError` vor jeder Tokenverarbeitung |

`None` heißt „belastbar geprüft und abgelehnt", `Unavailable` heißt „kein
Urteil möglich". Kein pauschales `except Exception: return None`, und keine
Exception gibt Token, Header, Claim, Schlüssel, Issuer, Subject oder Nonce
wieder.

## Algorithmus- und Schlüsselauswahl

Eine **modulinterne, private** Allowlist erlaubt ausschließlich asymmetrische
Verfahren (RS/PS/ES in 256, 384, 512 sowie EdDSA); geteilte Geheimnisse und
unsignierte Tokens können die Identität eines Issuers nicht beweisen.
Akzeptiert wird die **Schnittmenge** mit
`configuration.allowed_signing_algorithms`, exakt und case-sensitiv. Der
Header kann die Konfiguration nie erweitern, und es gibt keinen Fallback.

**`jku`, `x5u` und `jwk` im Header führen zu `None`** und werden nie befolgt,
geladen oder geloggt: Ihnen zu folgen hieße, den Prüfschlüssel vom Prüfling
bestimmen zu lassen.

Schlüssel stammen **nur** aus `jwks["keys"]`, gefiltert auf `use`, `key_ops`
und ein deklariertes `alg`; `kid` wählt ausschließlich **innerhalb** dieses
Sets und muss, falls vorhanden, ein nicht leerer String sein. Null oder
mehrere Kandidaten werden **abgewiesen**, nicht aufgelöst. Kein Refresh und
keine zweite Auswahlrunde.

## Verpflichtende Prüfungen und explizite Uhr

**PyJWT** prüft Tokenformat, Signatur, den gewählten Algorithmus, den Issuer
byte-genau und dass die Audience `configuration.client_id` enthält. Signatur,
Issuer und Audience werden nie deaktiviert; es gibt **keine eigene**
Kryptografie.

**Anschließend im Modul**, auf verifizierten Claims:

- **Zeit** ausschließlich mit dem übergebenen `now` und
  `configuration.clock_skew`. `exp` und `iat` sind erforderlich und endlich,
  `nbf` optional, aber falls vorhanden gültig; `bool` ist keine NumericDate.
  PyJWTs automatische Zeitprüfung ist **abgeschaltet**, damit keine versteckte
  Systemuhr über Gültigkeit entscheidet.
- **Audience** als String oder Stringliste; leere, falsch typisierte oder
  gemischte Audience wird abgelehnt. Bei mehreren Audiences ist `azp` zwingend
  und muss — wie immer, wenn es vorhanden ist — exakt dem Client entsprechen.
- **Nonce** erforderlich, nicht leer, **konstantzeitlich** verglichen.
- **Subject** erforderlich und nicht leer.

Nichts wird normalisiert oder getrimmt.

## Ergebnis

Nur nach vollständig erfolgreicher Prüfung:

```python
ExternalIdentity(issuer=configuration.issuer, subject=claims["sub"])
```

Der Issuer stammt aus der **aktiven vertrauenswürdigen Konfiguration**, nicht
erneut aus einem Claim. Keine Rohclaims, Tokens, E-Mails, Namen, Gruppen,
Rollen, Admission-, User-, Workspace- oder Sessiondaten.

## Nicht-Ziele

Kein Authorization-Code-Austausch, kein Token-Endpunkt, kein JWKS-Abruf oder
Cache, kein HTTP-Client, keine Discovery, kein Retry oder Redirect, keine
Portimplementierung, keine aktive Konfigurationsauflösung, keine
Callback-Route, keine Identity-Auflösung oder Admission, keine
Session-/CSRF-Erzeugung, kein Production-Wiring und keine Dependency-,
Lockfile-, CI-, Container-, Grype- oder Deployment-Änderung.

## Nächster Schritt

Der vollständige Verifikationsadapter, der den Code am Token-Endpunkt einlöst,
das JWKS innerhalb der LQ-162-Grenzen lädt und diesen Kern aufruft.
