# LQ-139 — OIDC Login Transaction Claim Port

## Ergebnis

Der opake `state`-Schlüssel und die minimale Portgrenze für den **atomaren
Einmal-Claim** einer pending OIDC-Login-Transaktion: `OidcLoginState` in
`src/liquent_platform/identity/oidc_login_transaction.py` und
`OidcLoginTransactionClaimStore` in `src/liquent_platform/identity/ports.py`.
Kein Adapter, kein Creation-Port und keine Route. Setzt die LQ-136-Konsumregel
über dem LQ-138-Modell als Grenze um.

## OidcLoginState

```
@dataclass(frozen=True, slots=True)
class OidcLoginState:
    value: str = field(repr=False)
```

- `value` darf **nicht leer** sein (`login state must not be empty`).
- Der Wert wird **exakt und opak** behandelt: kein Trimmen, kein Lowercasing,
  keine Normalisierung.
- Unveränderlich und hashbar — damit als Store-Schlüssel verwendbar.
- Der Wert erscheint **nicht** im `repr`.
- Enthält **keine** Transaktions-, Admission-, Token-, User- oder Session-Daten.
- Dieser Wert entspricht dem beim Login-Start erzeugten OIDC-`state` und dient
  später als Store-Schlüssel.
- Seine **Präsentation allein beweist weder Identität noch Berechtigung**; sie
  korreliert lediglich einen Callback mit genau einer serverseitigen
  Login-Transaktion.

## OidcLoginTransactionClaimStore

```
class OidcLoginTransactionClaimStore(Protocol):
    def claim_transaction(
        self,
        state: OidcLoginState,
    ) -> PendingOidcLoginTransaction | None: ...
```

### Verbindliches Verhalten

- Der Claim ist **atomar und einmalig**.
- Vor Erfolg prüft der Store:
  - Transaktion **vorhanden**,
  - noch **pending**,
  - **nicht abgelaufen**.
- Erfolg **entfernt beziehungsweise konsumiert** den pending Zustand
  **fail-closed** und liefert den `PendingOidcLoginTransaction` **genau einmal**
  an den Callback-Prozess.
- Ein **zweiter Claim** desselben State liefert neutral `None`.
- **Unbekannt, abgelaufen oder bereits konsumiert** liefern nach außen
  **identisch** `None`.
- Eine **vorhandene, aber abgelaufene** Pending-Transaktion liefert nach außen
  neutral `None`; ihr geheimnistragender Pending-Zustand wird dabei **atomar
  entfernt** beziehungsweise **dauerhaft als konsumiert** behandelt.
  `expected_nonce` und `code_verifier` dürfen danach **nicht erneut** über diesen
  State verfügbar sein. Ein persistenter Adapter kann stattdessen einen
  **geheimnisfreien** Konsumnachweis/Tombstone hinterlassen. In einem
  abgelaufenen Pending-Zustand bleiben **keine Geheimnisse** erhalten.
- Fehlerfälle geben **keine** Information über Admission, Issuer, User oder
  Transaktionszustand preis.
- Der Store liest seine **Uhr intern**; der Aufrufer liefert weder `now` noch
  eine Ablaufentscheidung.
- Der Aufrufer liefert **keinen** Issuer, Nonce, Verifier, Admission-Handle oder
  sonstiges Transaktionsmaterial — die Signatur kennt ausschließlich `state`.
- Der Claim-Port prüft **keine** OIDC-Tokens und **keine** aktuelle
  Issuer-Trust-Konfiguration; letztere bleibt eine separate Callback-Prüfung
  gegen die aktive Konfiguration.
- Das erfolgreiche Claim-Ergebnis enthält **kurzfristig** die für genau diesen
  Callback benötigten Geheimnisse; deren weitere Verwendung bleibt einem
  späteren Anwendungsfall vorbehalten.
- Persistente Implementierungen können separat einen **Konsumnachweis oder
  Tombstone** führen; **kein** Tombstone-Modell in diesem Slice.

## Tests

`tests/test_oidc_login_transaction_claim_port.py` — 35 fokussierte Tests.

**OidcLoginState:** gültiger Wert exakt bewahrt · leerer Wert abgewiesen · Case,
Slashes und Whitespace werden nicht normalisiert (parametrisiert) ·
unveränderlich · hashbar und als Dict-Schlüssel verwendbar · Wert fehlt im
`repr` · exakt nur das Feld `value` · keine Transaktions-, Admission-, Token-,
Issuer-, User- oder Session-Felder.

**Claim-Port:** strukturelle Protocol-Kompatibilität mit einem minimalen
Test-Stub · Signatur exakt `["self", "state"]` · kein `now`-, `clock`-, Issuer-,
Nonce-, Verifier-, Admission- oder User-Parameter (parametrisiert) ·
erfolgreicher Claim liefert den pending Record und bleibt unverändert einmalig ·
zweiter Claim liefert `None` · unbekannt, abgelaufen und bereits konsumiert sind
ununterscheidbar `None` · erfolgreiches Ergebnis trägt die Callback-Geheimnisse
genau einmal · Rückgabeannotation ist ausschließlich
`PendingOidcLoginTransaction | None` · `OidcLoginTransactionClaimStore`
deklariert ausschließlich `claim_transaction` mit einem reinen Protocol-Rumpf
und enthält selbst keine Adapter- oder Ausführungslogik.

> **Korrigiert durch LQ-149:** Die letzte Zusicherung lautete früher
> „`ports.py` enthält keine Token-, Trust-, HTTP- oder Persistenzlogik" und war
> als globale Substring-Suche über die **gesamte** Datei umgesetzt. Sie koppelte
> damit einen LQ-139-Test an jeden späteren, unabhängigen Portvertrag und konnte
> echte Logik nicht von legitimen Importen, Typnamen oder Docstrings
> unterscheiden, die etwas ausdrücklich **ausschließen** — sie blockierte
> deshalb LQ-148, dessen Docstring gerade sagte, dass keine JWKS-Logik
> ausgeführt wird. Der globale Test wurde bewusst entfernt und durch einen
> fokussierten AST-Test ersetzt, der ausschließlich diesen Protocol-Typ
> untersucht. Die fachliche LQ-139-Semantik bleibt unverändert; siehe
> `docs/lq-149-scope-oidc-claim-port-contract-test.md`.

**Abgelaufener Pfad:** abgelaufener State liefert `None` · der abgelaufene
Pending-Record ist danach aus dem Stub **entfernt** · ein zweiter Claim liefert
weiterhin `None` · seine Callback-Geheimnisse sind über den Store **nicht mehr
verfügbar**.

Der Stub liest seine Uhr **intern** (fest bei Konstruktion) und belegt damit,
dass der Aufrufer keine Ablaufentscheidung liefert. Sein abgelaufener Pfad
entfernt den Record **im selben Schritt** wie die neutrale Rückgabe und bildet so
den fail-closed Claim ab. Die Test-only Methode `remaining_states()` macht den
verbleibenden Pending-Zustand prüfbar. Der Stub bleibt **ausschließlich** in der
Testdatei und wird weder von `ports.py` noch vom `identity`-Paket exportiert —
**kein produktiver Adapter**.

## Bewusst nicht enthalten

- kein Creation-/Add-Port,
- kein In-Memory- oder persistenter Adapter,
- kein Tombstone-Modell,
- kein Login-Start-Anwendungsfall,
- kein Callback-Anwendungsfall,
- keine Login-/Callback-Route,
- keine OIDC-/OAuth-Bibliothek,
- keine Token-, Discovery- oder JWKS-Logik,
- keine aktuelle Issuer-Trust-Prüfung,
- keine Datenbank oder Migration,
- kein Production-Wiring oder Deployment.

## Nächster Schritt

Ein späterer Slice kann den zugehörigen **Creation-Pfad** (Login-Start bindet
`OidcLoginState` an eine `PendingOidcLoginTransaction`) und danach einen
konkreten Adapter definieren — jeweils mit eigener Persistenz- und
Tombstone-Entscheidung.
