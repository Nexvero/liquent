# LQ-163 — Verify OIDC Callback Use Case

## Systemgrenze

Die transportfreie Orchestrierung **nach** erfolgreicher Browserbindung. Der
Aufrufer hat die Query bereits duplikatsicher gelesen, genau einen nicht leeren
State bestimmt, ihn konstantzeitlich gegen `__Host-liquent_oidc_state`
verglichen und bei fehlendem oder abweichendem Cookie neutral abgebrochen —
**ohne** zu claimen (LQ-158).

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

Exakt vier Parameter — **keine Uhr**, keine Konfiguration und kein HTTP-,
Cookie- oder Requestwert.

Alle drei Ergebnisfelder sind `repr`-frei, sodass `repr(...)` nur
`VerifiedOidcCallback()` zeigt. Das ist nötig, weil `ExternalIdentity` seine
eigenen Felder **nicht** verbirgt.

## Reihenfolge

1. **Claim zuerst und genau einmal.** Ein neutrales `None` vereinheitlicht
   unbekannt, abgelaufen und bereits konsumiert und beendet den Aufruf ohne
   Verifier. Der Store liest seine eigene Uhr (LQ-139). Ab hier bleibt die
   Transaktion auf jedem Pfad verbraucht: **kein** Retry, **kein** zweiter
   Claim, **kein** Rollback.
2. **Providerfehler** (`authorization_code is None`) wird geclaimt, aber nie
   eingelöst; die Transaktion wird nicht zurückgegeben. `error`,
   `error_description` und `error_uri` sind **keine** Parameter.
3. **Codeprüfung:** ein vorhandener Code muss ein echter nicht leerer `str`
   sein. Ein Vertragsverstoß endet **nach** dem Claim neutral, ohne Verifier
   und ohne Exception mit Codeinhalt. Kein Trimmen, keine Normalisierung, kein
   Logging.
4. **Verifikationsobjekt** aus dem Code plus den vier Werten des geclaimten
   Records (LQ-157). Keine aktive Konfiguration, keine Browserwerte, kein
   `state`.
5. **Verifier genau einmal.**

## Drei Verifierausgänge

| Ergebnis | Verhalten |
|---|---|
| `None` | fachliche Ablehnung → `None` |
| `ExternalIdentity` | Erfolg → `VerifiedOidcCallback(...)` |
| `OidcVerificationUnavailable` | **unverändert propagiert**, nicht abgefangen |

Technische Nichtverfügbarkeit wird bewusst nicht in `None` umgedeutet: sie ist
keine fachliche Ablehnung und muss unterscheidbar bleiben.

## Erfolg

`identity` exakt aus dem Verifier, `admission_id` und `return_path` **verbatim**
aus dem geclaimten Record. Keine Normalisierung, keine neue
Berechtigungsentscheidung.

Das Ergebnis erzeugt **weder** User, Identity-Binding, Mitgliedschaft oder
Rolle **noch** Session, CSRF, Redirect oder HTTP-Antwort. Es bedeutet
ausschließlich: *Diese externe Identität wurde für genau diese
Login-Transaktion verifiziert.*

## Nicht-Ziele

Keine Query- oder Cookieprüfung, kein Cookie-Löschaufruf, keine Route oder
HTTP-Statuscodes, kein Verifikationsadapter, kein Token-/JWKS-Netzwerk, kein
JWT-/JOSE-Aufruf, keine aktive Konfigurationsauflösung, keine
Identity-Auflösung oder Admission-Konsumierung, keine Session-/CSRF-Erzeugung,
keine Redirect-Ziele, kein Production-Wiring und keine Dependency-, Lockfile-,
CI-, Container-, Grype- oder Deployment-Änderung.

## Nächster Schritt

Unverändert die Reihenfolge aus LQ-158 §15, alle noch nicht begonnen: der
Verifikationsadapter nach LQ-160/LQ-162, die Session-/CSRF-Ausgabeentscheidung,
validierte interne Ziele und zuletzt die Callback-Route, die diesen
Anwendungsfall aufruft. Identitätsauflösung und Session-Erzeugung folgen erst
danach.
