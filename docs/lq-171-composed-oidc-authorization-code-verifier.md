# LQ-171 — Composed OIDC Authorization Code Verifier

## Zweck und Signatur

Der konkrete Adapter für den bestehenden Port `OidcAuthorizationCodeVerifier`.
Er **komponiert** ausschließlich vorhandene Bausteine und fügt weder
Kryptografie noch einen zweiten JOSE-Parser, eine duplizierte Schlüsselwahl oder
einen eigenen Netzzugriff hinzu.

```python
# src/liquent_platform/identity/oidc_authorization_code_verifier.py
class ComposedOidcAuthorizationCodeVerifier:
    def __init__(self, configurations, token_endpoint, jwks_cache, now) -> None: ...
    def verify_authorization_code(
        self, verification: OidcAuthorizationCodeVerification
    ) -> ExternalIdentity | None: ...
```

`ports.py` bleibt unverändert; die Erfüllung ist **strukturell**, ohne
Vererbungspflicht. Die Uhr ist eine **zwingende** Konstruktorabhängigkeit ohne
Default — keine versteckte Systemuhr.

## Ablauf und Obergrenzen

1. Aktive Konfiguration **genau einmal** lesen; `None` → `None`.
2. `configuration.issuer` bytegenau gegen `verification.expected_issuer`;
   ungleich → `None`.
3. Code **genau einmal** eintauschen; gültige OAuth-Ablehnung → `None`.
4. JWKS über `get_jwks(configuration)`.
5. Uhr **genau einmal** lesen.
6. Erste Offline-Verifikation über die private LQ-169-Grenze.
7. Nur bei `refreshable_key_miss` **genau ein** `refresh_jwks(configuration)`
   und **genau eine** zweite Verifikation mit demselben Token, derselben
   Konfiguration, demselben Verification-Objekt und **demselben** Zeitwert.

| Aufruf | Höchstens |
|---|---|
| Konfigurationslookup | 1 |
| Code-Austausch | 1 |
| `get_jwks` | 1 |
| `refresh_jwks` | 1 |
| Uhrlesevorgang | 1 |
| Offline-Verifikation | 2 |

Keine dritte Schlüsselabfrage, kein zweiter Refresh, keine dritte Verifikation,
nie ein zweiter Code-Austausch und kein erneutes Lookup.

## Warum die Uhr genau einmal an dieser Stelle

Der Port liest keine Uhr vom Aufrufer, und LQ-164 schaltet PyJWTs automatische
Zeitprüfung ab — die Zeit muss der Adapter also explizit liefern.

Gelesen wird **nach** Token- und JWKS-Bezug: Ein früher gelesener Wert wäre um
die gesamte Netzwerkzeit veraltet und ließe ein knapp abgelaufenes Token gegen
einen zu alten Zeitpunkt passieren.

Gelesen wird **genau einmal**, weil ein Refresh ausschließlich Schlüsselmaterial
tauscht. Zwei Lesevorgänge ließen die beiden Verifikationen gegen verschiedene
Zeitpunkte laufen; ein Token, das die erste Prüfung zeitlich knapp bestand,
könnte die zweite verfehlen oder umgekehrt. Ein einziger Wert macht die zweite
Prüfung zur echten Wiederholung derselben Frage mit neuen Schlüsseln.

## Ergebnis- und Fehlerpfade

| Situation | Ergebnis |
|---|---|
| beide Verifikationen liefern eine Identität | genau dieses `ExternalIdentity` |
| keine aktive Konfiguration, Issuer-Mismatch | `None`, ohne Netz, Cache und Uhr |
| gültige OAuth-Ablehnung des Codes | `None`, **ohne** JWKS-Zugriff |
| erste Verifikation endgültig abgelehnt | `None`, **ohne** Refresh |
| zweite Verifikation abgelehnt oder erneut Miss | `None`, kein weiterer Versuch |
| jeder technische Fehler an jeder Stufe | `OidcVerificationUnavailable` |

Der zweite Ausgang wird **ausschließlich über `identity`** ausgewertet; ein
zweiter `refreshable_key_miss` endet daher als `None`, nie als weiterer Refresh.

Ein bereits neutrales `OidcVerificationUnavailable` wird als **exakt dasselbe
Objekt** unverändert weitergereicht. Jede andere normale `Exception` aus Lookup,
Token-Client, `get_jwks`, Uhr, erster Verifikation, `refresh_jwks` oder zweiter
Verifikation wird in eine **neue** detailfreie Exception übersetzt, die
**außerhalb** des Handlers erzeugt wird und daher weder Cause noch Context des
Ursprungsfehlers trägt. `BaseException` wird an keiner dieser Grenzen gefangen.

Fehler, die bereits in einem der genutzten Bausteine neutralisiert wurden,
behalten deren eigene Exceptionkette; was sie tragen, ist Vertrag des jeweils
erzeugenden Moduls, nicht dieses Adapters.

Eine werfende, falsch typisierte oder timezone-naive Uhr ist technische
Unverfügbarkeit. Ein Fehler während Refresh oder zweiter Verifikation gibt
niemals das alte JWKS zurück, refresht nicht erneut, tauscht den Code nicht
erneut, löst keine dritte Verifikation aus und erscheint nie als `None`.

Keine Fehlermeldung trägt Code, ID-Token, Verifier, Nonce, Issuer, URI,
Providertext, Header, Claim, JWK oder Konfigurationswert. `repr` des Adapters
zeigt weder Kollaborateure noch Material.

## Ein Konfigurationssnapshot

Die Konfiguration wird einmal gelesen und als **exakt dasselbe Objekt** an
Token-Client, Cache und beide Verifikationen weitergereicht — kein Kopieren,
Rekonstruieren, Normalisieren und kein erneutes Lookup. Eine Rotation während
eines laufenden Aufrufs kann damit keinen gemischten Snapshot erzeugen
(LQ-160 §10).

Der Login-Transaction-Claim liegt vor diesem Port und bleibt konsumiert: kein
Rollback und kein Retry, weder bei `None` noch bei technischer
Unverfügbarkeit.

## Nicht-Ziele

Keine Änderung an `ports.py` oder an LQ-165 bis LQ-170, kein direkter
Netzzugriff außerhalb von Token-Client und JWKS-Loader, keine eigene
Kryptografie, kein Token, `kid`, Algorithmus oder privates Verifikationsergebnis
an den Cache, kein Export der privaten LQ-169-Form, keine Route, kein Cookie,
kein State, keine Session, kein CSRF, keine Admission-Verarbeitung, keine
User-Auflösung, keine neue Dependency und kein Lockfile-, CI-, Container- oder
Grype-Eingriff.
