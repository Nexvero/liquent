# LQ-137 — Secure OIDC Login Material

## Ergebnis

Providerneutrale Erzeugung des kurzlebigen Kryptomaterials für einen
OIDC-Login-Start: ein unveränderliches `OidcLoginMaterial`-Modell und ein
`SecureOidcLoginMaterialGenerator`. Kein Store, keine Route, kein OIDC-Client und
kein Production-Wiring. Der bestehende Session-Material-Generator bleibt unberührt.

## OidcLoginMaterial

```
@dataclass(frozen=True, slots=True)
class OidcLoginMaterial:
    state: str = field(repr=False)
    nonce: str = field(repr=False)
    code_verifier: str = field(repr=False)
    code_challenge: str
```

- Alle vier Werte müssen **nicht leer** sein.
- `state`, `nonce` und `code_verifier` gelten als **sensibel** und erscheinen
  **nicht** im `repr`; `code_challenge` ist kein Geheimnis und **darf** im `repr`
  erscheinen.
- Keine Tokens, Claims, Issuer-, User-, Admission-, Workspace- oder Session-Daten.
- Keine Normalisierung irgendeines Wertes.

## SecureOidcLoginMaterialGenerator

```
class SecureOidcLoginMaterialGenerator:
    def __init__(self, entropy_bytes: int = 32) -> None: ...
    def new_login_material(self) -> OidcLoginMaterial: ...
```

- Die Entropie liegt je Zufallswert bei **32 bis einschließlich 96 Bytes**;
  `bool`, Nicht-Integer sowie Werte unter 32 oder über 96 werden abgewiesen
  (`login material entropy must be between 32 and 96 bytes`).
- **Begründung der Obergrenze:** RFC 7636 erlaubt für den `code_verifier` 43 bis
  128 Zeichen. `token_urlsafe(32)` ergibt 43 Zeichen, `token_urlsafe(96)` ergibt
  128 Zeichen; mehr als 96 Bytes kann einen nicht interoperablen, zu langen
  Verifier erzeugen. Die Grenze gilt für **alle drei** unabhängigen Ziehungen,
  da der konfigurierte Wert weiterhin gemeinsam verwendet wird.
- `state`, `nonce` und `code_verifier` entstehen aus **drei unabhängigen**
  Aufrufen eines kryptografisch sicheren URL-safe Generators — keine Ableitung
  oder Wiederverwendung zwischen diesen drei Werten.
- PKCE **ausschließlich `S256`**:
  `code_challenge = BASE64URL-ENCODE(SHA256(ASCII(code_verifier)))`, Base64url
  **ohne** abschließendes `=`.
- Keine `plain`-PKCE-Unterstützung, keine konfigurierbare Hashfunktion, keine
  Protokoll- oder Netzwerkanfrage, kein Logging von Werten.

## Bewusst nicht enthalten

- kein Generator-Port ohne konkreten Anwendungsfall,
- kein Login-Transaktionsmodell oder Store,
- keine Admission-Verknüpfung,
- keine Login-Start-/Callback-Route,
- keine OIDC-/OAuth-Bibliothek,
- keine Discovery-, JWKS- oder Tokenlogik,
- keine Datenbank oder Migration,
- kein Provider,
- kein Production-Wiring oder Deployment.

## Nächster Schritt

Ein späterer Slice kann dieses Material innerhalb eines Login-Start-Anwendungsfalls
an eine kurzlebige Login-Transaktion (LQ-136) binden — mit eigener Persistenz- und
Wiring-Entscheidung.
