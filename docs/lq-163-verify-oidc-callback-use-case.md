# LQ-163 — Verify OIDC Callback Use Case

## Systemgrenze

Die transportfreie Orchestrierung **nach** erfolgreicher Browserbindung. Der
spätere HTTP-Handler hat zu diesem Zeitpunkt bereits die Query duplikatsicher
gelesen, genau einen nicht leeren State bestimmt, ihn konstantzeitlich gegen
`__Host-liquent_oidc_state` verglichen und bei fehlendem oder abweichendem
Cookie neutral abgebrochen — **ohne** zu claimen (LQ-158 §6/§7).

**Kein** HTTP, **kein** Verifikationsadapter, **keine** Session-Erzeugung.

## Signatur

`src/liquent_platform/application/verify_oidc_callback.py`

```python
@dataclass(frozen=True, slots=True)
class VerifiedOidcCallback:
    identity: ExternalIdentity = field(repr=False)
    admission_id: IdentityAdmissionId | None = field(repr=False)
    return_path: str | None = field(repr=False)


def verify_oidc_callback(
    transaction_store: OidcLoginTransactionClaimStore,
    verifier: OidcAuthorizationCodeVerifier,
    state: OidcLoginState,
    authorization_code: str | None,
) -> VerifiedOidcCallback | None: ...
```

Exakt vier Parameter in dieser Reihenfolge — **keine Uhr** und **kein** HTTP-,
Cookie- oder Requestparameter.

`authorization_code=None` bedeutet **ausschließlich**: Der duplikatsichere
Transportparser hat eine **gültige Providerfehlerform** erkannt. Malformed
Queryformen erreichen diesen Anwendungsfall gar nicht, und `error`,
`error_description` und `error_uri` sind deshalb **keine** Parameter — sie
überschreiten die Transportgrenze nicht.

## Verbindliche Reihenfolge

### 1. Claim zuerst und genau einmal

`claim_transaction(state)` läuft **vor** allem Externen. Ein neutrales `None`
vereinheitlicht **unbekannt, abgelaufen und bereits konsumiert** und beendet den
Aufruf, **ohne** den Verifier zu berühren. Der Store liest seine eigene Uhr
(LQ-139); es gibt **kein** browsergeliefertes `now`.

Ab hier bleibt die Transaktion auf **jedem** Pfad verbraucht: **kein** Retry,
**kein** zweiter Claim, **kein** Store-Rollback — jedes davon wäre ein
Replay-Pfad.

### 2. Providerfehler ohne Verifier

Wurde erfolgreich geclaimt und ist `authorization_code is None`: Ergebnis
`None`, Verifier **nicht** aufgerufen, Transaktion bleibt verbraucht. Die
geclaimte Transaktion wird **nicht** zurückgegeben.

### 3. Codeform

Ein vorhandener Code muss ein echter **nicht leerer `str`** sein. Übergibt ein
direkter Aufrufer trotz Transportvertrag einen leeren oder falsch typisierten
Wert, ist die Transaktion **bereits fail-closed geclaimt**; der Aufruf endet
neutral mit `None`, ohne Verifier und **ohne** Exception, die den Codeinhalt
tragen könnte. **Keine** Normalisierung, **kein** Trimmen, **kein** Logging.

### 4. Verifikationsobjekt

Gebaut **ausschließlich** aus dem Query-Code und den vier
verifikationsrelevanten Werten des geclaimten Records (LQ-157 §3):

```python
OidcAuthorizationCodeVerification(
    authorization_code=authorization_code,
    expected_issuer=transaction.expected_issuer,
    expected_nonce=transaction.expected_nonce,
    code_verifier=transaction.code_verifier,
    redirect_uri=transaction.redirect_uri,
)
```

**Keine** aktive Konfiguration und **keine** Browserwerte werden ergänzt. Der
`state` verlässt die Bindungs- und Store-Ebene nicht.

### 5. Drei Verifier-Ergebnisse

| Ergebnis | Verhalten |
|---|---|
| `None` | fachliche Ablehnung → Anwendungsfall gibt `None` zurück |
| `ExternalIdentity` | Erfolg → `VerifiedOidcCallback(...)` |
| `OidcVerificationUnavailable` | **unverändert propagiert**, nicht abgefangen |

Der Verifier wird **genau einmal** aufgerufen. Technische Nichtverfügbarkeit
wird bewusst **nicht** in `None` umgedeutet: sie ist keine fachliche Ablehnung
und muss für den Aufrufer unterscheidbar bleiben (LQ-157).

### 6. Erfolgsergebnis

`identity` exakt aus dem Verifier, `admission_id` und `return_path` **verbatim**
aus dem geclaimten Pending-Record. **Keine** Normalisierung und **keine** neue
Berechtigungsentscheidung.

Alle drei Felder sind `repr`-frei, sodass `repr(...)` nur
`VerifiedOidcCallback()` zeigt: Die Identität kann einen personenbezogenen
externen Identifikator tragen, die Admission-ID ist ein Capability-Handle, und
der Return-Path ist interne Navigationsmetadaten. `ExternalIdentity` verbirgt
seine eigenen Felder **nicht** — das Ausblenden **dieses** Feldes ist also das,
was Issuer und Subject aus der Objektrepräsentation heraushält.

Das Ergebnis erzeugt **weder** User oder Identity-Binding, **noch**
Workspace-Mitgliedschaft oder Rolle, **noch** Session, CSRF, Redirect oder
HTTP-Antwort. Es bedeutet ausschließlich: *Diese externe Identität wurde für
genau diese Login-Transaktion verifiziert.*

## Verhältnis zu LQ-155, LQ-157 und LQ-158

- **LQ-155** legt die Ebenen fest; LQ-163 setzt Ebene 2 (atomarer Claim) und
  den Übergang zu Ebene 3 um, ohne Ebene 3 selbst zu implementieren.
- **LQ-157** liefert Eingabeobjekt, Port und die neutrale
  `OidcVerificationUnavailable`; LQ-163 baut das Objekt und ruft den Port.
- **LQ-158** beschreibt den HTTP-Ingress. Query-Form, Cookie-Vergleich und
  Cookie-Löschung bleiben **dort** und sind **nicht** Teil dieses
  Anwendungsfalls.

## Bewusst nicht enthalten

Keine Query- oder Cookieprüfung, kein Cookie-Löschaufruf, keine Route oder
HTTP-Statuscodes, kein Verifikationsadapter, kein Token-/JWKS-Netzwerk, kein
JWT-/JOSE-Aufruf, keine aktive Konfigurationsauflösung, keine Identity-Auflösung
oder Admission-Konsumierung, keine Session-/CSRF-Erzeugung, keine
Redirect-Ziele, kein Production-Wiring und keine Dependency-, Lockfile-, CI-,
Container-, Grype- oder Deployment-Änderung.

## Nächster Schritt

Unverändert die Reihenfolge aus LQ-158 §15, alle noch nicht begonnen: der
Verifikationsadapter nach LQ-160/LQ-162, die Session-/CSRF-Ausgabeentscheidung,
validierte interne Ziele und zuletzt die Callback-Route, die diesen
Anwendungsfall aufruft. Identitätsauflösung über LQ-131/LQ-133 und
Session-Erzeugung folgen erst danach.
