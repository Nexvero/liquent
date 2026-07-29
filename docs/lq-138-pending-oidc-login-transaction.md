# LQ-138 — Pending OIDC Login Transaction

## Ergebnis

Das minimale unveränderliche Modell einer **noch nicht konsumierten**,
serverseitigen OIDC-Login-Transaktion: `PendingOidcLoginTransaction` in
`src/liquent_platform/identity/oidc_login_transaction.py`. Kein Store, kein Port,
keine Route und keine Tokenverarbeitung. Setzt den Vertrag aus LQ-136 in genau
einem Modell um und lässt das LQ-137-Material unberührt.

## Modell

```
@dataclass(frozen=True, slots=True)
class PendingOidcLoginTransaction:
    expected_issuer: str
    expected_nonce: str = field(repr=False)
    code_verifier: str = field(repr=False)
    redirect_uri: str
    created_at: datetime
    expires_at: datetime
    admission_id: IdentityAdmissionId | None = field(default=None, repr=False)
    return_path: str | None = None
```

## Verbindlicher Vertrag

- Das Modell beschreibt **ausschließlich** eine noch nicht konsumierte
  Login-Transaktion.
- `state` ist der spätere **opake Store-Schlüssel** und wird **nicht** redundant im
  Record gespeichert.
- `code_challenge` wird nur für den Authorization Request benötigt und **nicht**
  redundant serverseitig gespeichert.
- `expected_issuer`, `expected_nonce`, `code_verifier` und `redirect_uri` dürfen
  **nicht leer** sein.
- Werte werden **exakt** gespeichert und **nicht normalisiert** (kein Trimmen,
  kein Lowercasing, keine Slash-Entfernung).
- `expected_nonce`, `code_verifier` und `admission_id` sind **sensibel** und
  erscheinen **nicht** im `repr`; `expected_issuer`, `redirect_uri`, Zeiten und
  `return_path` dürfen im `repr` erscheinen.
- Eine `IdentityAdmissionId` kann einen **einmalig konsumierbaren**
  Onboarding-/Binding-Vorgang referenzieren und ist deshalb als sensibler
  **Capability-Handle** zu behandeln. Sie darf nicht versehentlich über
  Objekt-Repräsentationen in Logs oder Fehlerdiagnosen gelangen. Der Wert bleibt
  im Modell verfügbar und wird weiterhin exakt bewahrt.
- `created_at` und `expires_at` müssen **timezone-aware** sein.
- `expires_at` muss **strikt nach** `created_at` liegen.
- `admission_id` ist optional und wurde bereits beim Login-Start **serverseitig
  gebunden**; der Callback darf keine andere Admission einsetzen.
- `return_path` ist optional und gilt als **bereits von einer äußeren Grenze
  validierter interner relativer Pfad**; ist er gesetzt, darf er nicht leer sein.
- Das Modell validiert **keine** URL- oder Redirect-Sicherheitsregeln. Die spätere
  Login-Start-Grenze muss ausschließlich einen bereits validierten internen Pfad
  übergeben.
- Das Modell enthält **keine** IdP-Tokens, Authorization Codes, Claims, `UserId`,
  Workspace-Mitgliedschaft, Rollen, Berechtigungen oder Liquent-Session-Daten.
- Das Modell entscheidet **nicht** über aktuelle Issuer-Vertrauenswürdigkeit;
  diese wird beim Callback erneut gegen die aktive Trust-Konfiguration geprüft.
- Das Modell **mutiert keinen Zustand** und markiert nichts als konsumiert.

### Prüfreihenfolge

Die Timezone-Awareness wird **vor** dem Zeitvergleich geprüft. Ein naiver Wert
scheitert damit an der vertraglichen `ValueError` statt an einem
`TypeError` aus einem gemischten naiv/aware-Vergleich.

| # | Invariante | Meldung |
|---|---|---|
| 1 | `expected_issuer` nicht leer | `expected_issuer must not be empty` |
| 2 | `expected_nonce` nicht leer | `expected_nonce must not be empty` |
| 3 | `code_verifier` nicht leer | `code_verifier must not be empty` |
| 4 | `redirect_uri` nicht leer | `redirect_uri must not be empty` |
| 5 | `created_at` timezone-aware | `created_at must be timezone-aware` |
| 6 | `expires_at` timezone-aware | `expires_at must be timezone-aware` |
| 7 | `expires_at` strikt nach `created_at` | `expires_at must be after created_at` |
| 8 | gesetzter `return_path` nicht leer | `return_path must not be empty` |

## Lebenszyklusentscheidung

- Der Record repräsentiert **nur** den pending/aktiven geheimnistragenden Zustand.
- Ein späterer **atomarer Claim-Store** entfernt beziehungsweise ersetzt diesen
  pending Zustand **fail-closed**.
- Der Store kann einen **separaten** Konsumnachweis oder Tombstone führen.
- Geheimnisse werden **nicht** in einem dauerhaft konsumierten Record
  weitergeführt.
- Ein späteres einmaliges Claim-Ergebnis darf die für genau diesen Callback
  benötigten Geheimnisse **kurzfristig** an die Anwendung übergeben.
- Diese Claim-/Store-Modelle sind ausdrücklich **nicht** Teil von LQ-138.

## Tests

`tests/test_pending_oidc_login_transaction.py` — 21 fokussierte Tests:

- gültiger Record mit timezone-aware Zeiten; Werte werden nicht normalisiert,
- alle vier Pflichtstrings nicht leer (parametrisiert),
- naive `created_at` und naive `expires_at` werden abgewiesen,
- `expires_at == created_at` und `expires_at < created_at` werden abgewiesen,
- optionale Admission-ID und optionaler Return-Pfad werden exakt bewahrt,
- gesetzter leerer Return-Pfad wird abgewiesen,
- Modell unveränderlich und hashbar,
- `expected_nonce`, `code_verifier` und `admission_id` fehlen im `repr`;
  nicht-sensitive Metadaten (`expected_issuer`, `redirect_uri`, validierter
  interner `return_path`) erscheinen im `repr`,
- exakt die acht vereinbarten Felder in vereinbarter Reihenfolge,
- kein `state`- und kein `code_challenge`-Feld,
- keine Token-, Code-, Claim-, User-, Workspace-, Rollen- oder Session-Felder,
- keine Issuer-Trust-Prüfung, keine Store- oder Konsumlogik im Modul.

## Bewusst nicht enthalten

- kein State-Wertobjekt,
- kein Store-Port oder Adapter,
- kein Claim-/Consumed-Modell,
- kein Tombstone,
- kein Generator,
- keine Login-Start-/Callback-Route,
- keine OIDC-/OAuth-Bibliothek,
- keine Discovery-/JWKS-/Tokenlogik,
- keine Datenbank oder Migration,
- keine Admission-Verarbeitung,
- kein Production-Wiring oder Deployment.

## Nächster Schritt

Ein späterer Slice kann einen **atomaren, einmalig konsumierbaren**
Login-Transaktions-Store über diesem Modell definieren — mit eigener Entscheidung
über Claim-Ergebnis, Tombstone und Persistenz.
