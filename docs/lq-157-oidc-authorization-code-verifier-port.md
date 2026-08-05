# LQ-157 — OIDC Authorization Code Verifier Port

## Ergebnis

Die providerneutrale Grenze für **Ebene 3** aus LQ-155, bestehend aus genau
drei Dingen:

1. einem kleinen unveränderlichen **Eingabeobjekt**,
2. einem **Port** ohne Implementierung,
3. einer detailfreien **Infrastruktur-Fehlerklasse**.

**Kein** Adapter, **keine** Tokenlogik, **kein** HTTP-Client, **kein**
JWKS-Zugriff, **keine** Signatur- oder Claimprüfung, **keine** Route.

Mit LQ-156 (Konfigurationsgrenze) ist die Vorbedingung aus LQ-155 §5 erfüllt;
LQ-157 formuliert nun den Port selbst.

## Signatur

`src/liquent_platform/identity/oidc_verification.py`

```python
@dataclass(frozen=True, slots=True)
class OidcAuthorizationCodeVerification:
    authorization_code: str = field(repr=False)
    expected_issuer: str = field(repr=False)
    expected_nonce: str = field(repr=False)
    code_verifier: str = field(repr=False)
    redirect_uri: str = field(repr=False)


class OidcVerificationUnavailable(Exception):
    code = "oidc_verification_unavailable"

    def __init__(self) -> None:
        super().__init__(self.code)
```

`src/liquent_platform/identity/ports.py`

```python
class OidcAuthorizationCodeVerifier(Protocol):
    def verify_authorization_code(
        self,
        verification: OidcAuthorizationCodeVerification,
    ) -> ExternalIdentity | None: ...
```

Exakt fünf Pflichtfelder in dieser Reihenfolge, alle nicht leer, `frozen`,
`slots`, hashbar. Die Portmethode nimmt **exakt** `self` und `verification`.

## Eingabegrenze

Das Objekt trägt den Authorization Code aus dem Callback und exakt die **vier
verifikationsrelevanten** Werte einer **bereits atomar geclaimten**
Login-Transaktion. Es wird vom aufrufenden Callback-Ablauf zusammengestellt,
**nachdem** Browserbindung und Einmal-Claim beide erfolgreich waren.

### Was bewusst fehlt — und warum

| Nicht enthalten | Grund |
|---|---|
| `state` | gehört zu Browserbindung und Claim (Ebenen 1 und 2) und hat in der Tokenverifikation **keine** Rolle; ihn mitzuführen vergrößerte nur die Geheimnisfläche |
| `admission_id` | ein **Capability-Handle**, das eine einmalige Onboarding- oder Bindungsoperation autorisiert; eine Grenze, die ausschließlich eine Identität **beweist**, darf ihn weder tragen noch konsumieren können |
| `return_path` | reine Transportentscheidung des aufrufenden Ablaufs |
| aktive Konfiguration, Token-Endpunkt, JWKS-URI, Algorithmus-Allowlist, Clock-Skew | wird **innerhalb** der späteren Portimplementierung erneut gelesen und kommt **nie** vom Aufrufer oder Browser — so kann kein Aufrufer steuern, mit welchem Provider eine Verifikation spricht |

Ebenfalls nicht enthalten: Tokens, Claims, Subject, `ExternalIdentity`, User-,
Workspace-, Rollen-, Session- oder Berechtigungsdaten. Das Objekt **autorisiert
nichts**.

### Exakt und opak

Alle fünf Werte bleiben **unverändert**: **kein** Trimmen, **kein**
Lowercasing, **kein** URL-Parsen, **kein** Percent-Decoding, **keine**
Normalisierung. Authorization Code und Redirect-URI müssen den Token-Endpunkt
**byteweise** so erreichen, wie sie ausgestellt beziehungsweise gespeichert
wurden; Nonce und Verifier werden exakt verglichen beziehungsweise
nachgewiesen.

### Geheimnisgrenze

Alle fünf Werte sind kurzlebige Geheimnisse oder sensible Korrelationswerte und
deshalb **vollständig aus `repr` ausgeblendet**. Praktisch lautet die
Repräsentation:

```
OidcAuthorizationCodeVerification()
```

Der Klassenname bleibt sichtbar; keiner der fünf Werte kann über eine
Objektrepräsentation in Logs oder Fehlerdiagnosen geraten.

Fehlermeldungen der Validierung nennen den **Feldnamen**, geben aber **niemals**
den Wert wieder.

## Fehlerform

Es gibt **genau zwei** Ausgänge neben dem Erfolg, und sie liegen auf **zwei
verschiedenen Kanälen**.

### Fachliche Ablehnung → `None`

`None` ist die **einzige** fachliche Ablehnung und unterscheidet **nichts**:

- keine aktive Konfiguration,
- erwarteter Issuer nicht mehr aktiv,
- Code abgelehnt oder ungültig,
- Token fehlt oder ungültig,
- Signatur-, Algorithmus-, Schlüssel- oder Claimfehler,
- Issuer-, Audience-, `azp`-, Zeit- oder Noncefehler,
- fehlendes oder leeres Subject.

`None` trägt **keine Ursache** und **keine Bestandsinformation**.

**Es gibt bewusst keine zweite Fehlerklasse für fachliche Ablehnung.** Ein
typisierter fachlicher Fehler würde Aufrufer einladen, auf eine Ursache zu
verzweigen, die nach außen ununterscheidbar bleiben muss.

### Technische Nichtverfügbarkeit → `OidcVerificationUnavailable`

Geworfen, wenn die Verifikation **überhaupt nicht** durchgeführt werden konnte:

- aktiver Konfigurationsspeicher technisch nicht lesbar,
- Netzwerkfehler,
- Token-Endpunkt oder JWKS-Quelle technisch nicht erreichbar,
- sichere Schlüsselverifikation technisch nicht ausführbar,
- interner Adapter- oder Bibliotheksfehler.

Die Exception nimmt **keine** Konstruktorparameter und trägt nichts außer ihrem
neutralen Code — **kein** Authorization Code, State, Nonce, Verifier, Issuer,
Redirect-URI, Token, Claim, Providertext oder Konfigurationsdetail. Ein
späterer Adapter **muss** interne Fehler in diese Exception übersetzen, statt
eine durchzureichen, die einen solchen Wert tragen könnte.

Sie sagt ausschließlich „gerade nicht" und verrät nicht, ob eine Identität, ein
Nutzer oder eine Konfiguration existiert. **Wie** ein späterer
Callback-Transport sie beantwortet — mit demselben neutralen Status wie eine
fachliche Ablehnung oder mit einem anderen — bleibt gemäß LQ-155 §12
ausdrücklich **jenem** Vertrag überlassen. LQ-157 nimmt das nicht vorweg.

## Portvertrag

### Erfolg

Eine `ExternalIdentity` wird **nur** zurückgegeben, wenn eine spätere
Implementierung **alles** davon vollständig erfolgreich durchgeführt hat:

1. aktive Konfiguration **genau einmal** lesen,
2. aktuell aktive Konfiguration vorhanden,
3. deren Issuer entspricht **bytegenau** dem `expected_issuer`,
4. Code **genau einmal** am konfigurierten Token-Endpunkt einlösen,
5. gespeicherten `code_verifier` und gespeicherte `redirect_uri` **exakt**
   verwenden,
6. ID-Token-Signatur und **fest erlaubten** Algorithmus prüfen,
7. Schlüssel **nur** aus dem konfigurierten vertrauenswürdigen JWKS-Satz,
8. `iss`, `aud`, gegebenenfalls `azp`, `exp`, `nbf`, `iat` und `nonce`
   **vollständig** prüfen,
9. **nicht leeres** `sub`,
10. Ergebnis **exakt** `ExternalIdentity(issuer, subject)`.

Ein erfolgreicher Token-Endpunkt-Response ist **niemals** ein Grund, eine dieser
Prüfungen zu überspringen (LQ-155 §7).

**LQ-157 implementiert nichts davon.** Der Vertrag legt ausschließlich fest, was
eine Implementierung schuldet.

### Konsumregel

Der Port:

- **claimt keine** Login-Transaktion,
- **sieht keinen** State,
- führt **keinen** Store-Rollback aus,
- **weiß nicht**, ob eine Transaktion früher existierte,
- wird **erst nach** dem atomaren Claim aufgerufen,
- macht **weder** `None` **noch** `OidcVerificationUnavailable` retrybar.

Die bereits geclaimte Transaktion bleibt in **jedem** Fall verbraucht. Ein neuer
Versuch benötigt einen **neuen Login-Start** — ein Retry wäre ein Replay-Pfad.

Der Port wählt **keinen** Provider, akzeptiert **keinen** Issuer, Tenant,
Client, Host, Header, Cookie oder Requestwert, liest **keine** Uhr vom Aufrufer,
löst **keine** Identität auf einen `UserId` auf, konsumiert **keine** Admission
und erzeugt **keine** Session.

Eine zurückgegebene Identität bedeutet **ausschließlich**: *Diese externe
Identität wurde für genau diese Login-Transaktion vollständig verifiziert.*

## Tests

Zwei fokussierte Dateien, **180** Tests.

`tests/test_oidc_authorization_code_verification.py` — **Modell:** alle fünf
Werte exakt bewahrt · frozen · `slots` und kein `__dict__` · hashbar und als
Dict-Key nutzbar · Gleichheit und Ungleichheit · exakt fünf Felder in
festgelegter Reihenfolge · jedes Feld einzeln verpflichtend (`TypeError`) ·
jedes Feld einzeln leer → `ValueError` mit Feldnamen · Meldung gibt **keinen**
der fünf Werte wieder · zwölf Rohwerte je Feld parametrisiert unverändert
bewahrt (Whitespace, Groß-/Kleinschreibung, Slashs, reservierte und
percent-kodierte Zeichen) · Redirect-URI wird **nicht** als URL geparst ·
`repr` enthält den Klassennamen, aber keinen der fünf Werte · `repr` ist exakt
die leere Klassenform · jedes Feld nachweislich `repr=False` · dreißig
verbotene Feldnamen als nicht vorhanden belegt.

**Fehlerklasse:** `code` ist der neutrale Konstant · `str(error)` exakt dieser
Code · `args` trägt nur ihn · Konstruktor akzeptiert **keinen**
Detailparameter · Signatur exakt `["self"]` · ist `Exception`, aber **kein**
`ValueError` · vierzehn sensible Attributnamen nicht vorhanden · ein Raise aus
einem sensiblen internen Fehler heraus lässt den Wert nicht durch.

`tests/test_oidc_authorization_code_verifier_port.py` — **Port mit reinem
Test-Stub:** strukturell kompatibel · Erfolg liefert exakt eine
`ExternalIdentity` mit nur `issuer` und `subject` · die Eingabe erreicht den
Port unverändert und identisch · fachliche Ablehnung liefert `None` · **neun**
verschiedene interne Ablehnungsursachen ergeben nach außen **dasselbe** `None`
und sind untereinander ununterscheidbar · Infrastrukturpfad wirft **exakt**
`OidcVerificationUnavailable` und niemals `None` · die neutrale Exception trägt
keinen der fünf Eingabewerte · Signatur exakt `["self", "verification"]` ·
achtzehn verbotene Parameternamen abwesend · Parameterannotation exakt das
Eingabeobjekt · Rückgabeannotation exakt `ExternalIdentity | None` · die
Protokollklasse deklariert **nur** `verify_authorization_code` mit einem bloßen
`...`-Rumpf · der Stub bleibt in der Testdatei und wird weder von `ports.py`
noch vom `identity`-Paket exportiert.

Der AST-Test ist **auf diese Protokollklasse begrenzt** und sagt nichts über den
Rest von `ports.py`, dessen Importe, andere Protokolle oder spätere Ergänzungen
— dieselbe Form wie beim LQ-139-Claim-Port. Es gibt **keine** globalen AST-,
Import- oder Substring-Verbote.

Jede der vier zentralen Zusicherungen wurde per **Gegenprobe** abgesichert:
sichtbares `repr`-Feld, entfallene Leerprüfung, Detailparameter an der Exception
und ein zusätzlicher Portparameter lassen jeweils genau die zugehörigen Tests
scheitern.

**Keine** Netzwerk-, JWT-, JOSE-, Token- oder Kryptotests.

## Bewusst nicht enthalten

- kein Adapter, kein aktiver Konfigurationslookup im Code,
- kein HTTP-Client, kein Tokenaustausch, kein JWKS-Download oder Cache,
- keine Signatur-, JOSE- oder Claimprüfung, keine OIDC-/OAuth-/JWT-Bibliothek,
- keine Callback-Route, keine Queryverarbeitung, kein Cookie-Vergleich oder
  Cookie-Löschen,
- kein Claim-Store-Aufruf,
- keine Identitätsauflösung, keine Admission-Verarbeitung, keine
  Session-Erzeugung,
- keine Persistenz oder Migration, kein Production-Wiring,
- keine CORS-, Deployment-, CI-, Container-, Dependency- oder Grype-Änderung,
- keine Änderung an bestehenden Ports, Modellen, Adaptern, Anwendungsfällen oder
  der LQ-154-Route.

## Nächster Schritt

Zwei getrennte, kleine Slices — in dieser Reihenfolge und **beide hier nicht
begonnen**:

1. der **Verifikationsadapter**, der diesen Port erfüllt: aktive Konfiguration
   lesen, Code einlösen, ID-Token vollständig prüfen und interne Fehler neutral
   in `OidcVerificationUnavailable` übersetzen,
2. der **Callback-Transportvertrag** nach LQ-155 §9 und §11 — Query-Form,
   Provider-Fehlerpfad und die neutrale HTTP-Abbildung von `None` und
   `OidcVerificationUnavailable`.

Erst danach folgen die Callback-Route, die Identitätsauflösung über LQ-131/133
und zuletzt die Session-Erzeugung.
