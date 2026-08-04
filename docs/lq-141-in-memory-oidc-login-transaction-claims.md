# LQ-141 — In-Memory OIDC Login Transaction Claims

## Ergebnis

Ein lokaler, flüchtiger In-Memory-Adapter für den bestehenden
`OidcLoginTransactionClaimStore` (LQ-139): `InMemoryOidcLoginTransactions` in
`src/liquent_platform/identity/in_memory.py`. Kein Creation-Port, keine Route und
kein Production-Wiring. Der Adapter folgt dem Muster der vorhandenen lokalen
Adapter (`InMemoryBrowserSessions`, `InMemoryExternalIdentities`).

## Zielklasse

```
class InMemoryOidcLoginTransactions:
    def __init__(
        self,
        transactions: Mapping[
            OidcLoginState,
            PendingOidcLoginTransaction,
        ],
        *,
        now: Callable[[], datetime],
    ) -> None: ...

    def claim_transaction(
        self,
        state: OidcLoginState,
    ) -> PendingOidcLoginTransaction | None: ...
```

## Konstruktor

- kopiert das Eingabe-Mapping mit `dict(...)`,
- spätere Änderungen am übergebenen Mapping verändern den Adapter **nicht**,
- speichert die **injizierte** Uhr,
- **keine** globale Uhr und **kein** Netzwerk,
- die Transaktionen stehen bei Konstruktion fest: es gibt **keine** Methode zum
  nachträglichen Hinzufügen oder Erzeugen.
  **Überholt durch LQ-143** — der Adapter erfüllt inzwischen zusätzlich den
  Creation-Port und besitzt `add_transaction`; siehe
  `docs/lq-143-in-memory-oidc-login-transaction-creation.md`.

## Zustandsübergänge

| Eingang | Uhr | Zustand danach | Rückgabe |
|---|---|---|---|
| unbekannter oder bereits entfernter State | **nicht gelesen** | unverändert | `None` |
| vorhanden, `now < expires_at` | **genau 1×** | State entfernt | Record, **genau einmal** |
| vorhanden, `now >= expires_at` | **genau 1×** | State entfernt | `None` |
| jeder Folge-Claim beider Fälle | nicht gelesen | unverändert | `None` |

### Ablauf für einen vorhandenen State

1. Uhr **genau einmal** lesen.
2. Einen **vollständigen neuen Snapshot ohne diesen State** vorbereiten.
3. Den Snapshot **übernehmen, bevor** ein Ergebnis zurückgegeben wird.
4. Erst danach über Erfolg (`now < expires_at`) oder Ablauf entscheiden.

Weil Erfolg und Ablauf sich diesen Entfernungspfad teilen, ist der
geheimnistragende Pending-Zustand in **beiden** Fällen fail-closed entfernt. Die
Geheimnisse eines abgelaufenen Records bleiben damit **nicht** über den Store
erreichbar.

## Weitere Regeln

- **Keine** Unterscheidung zwischen unbekannt, abgelaufen und bereits konsumiert.
- **Keine** Token-, Issuer-Trust-, HTTP- oder Admission-Verarbeitung.
- **Keine** Mutation des zurückgegebenen unveränderlichen Records.
- **Keine** Threads oder Locks.
- **Kein** Tombstone im lokalen Adapter — persistente Implementierungen dürfen
  laut LQ-139 einen geheimnisfreien Konsumnachweis führen, dieser Adapter tut es
  nicht.
  **Teilweise überholt durch LQ-143** — der Adapter führt seither einen internen
  Reserved-State-Satz, der verbrauchte States festhält. Er ist **nicht**
  geheimnisfrei (er hält rohe `OidcLoginState`-Objekte) und **kein** persistenter
  Tombstone; persistentes Hashing bleibt weiterhin außerhalb.
- Die Uhr wird **höchstens einmal** und **nur** für einen vorhandenen
  Pending-Record gelesen.

## Tests

`tests/test_in_memory_oidc_login_transactions.py` — 26 fokussierte Tests.

**Konstruktion:** Eingabe-Mapping wird kopiert · spätere Änderungen am
ursprünglichen Mapping wirken nicht auf den Adapter.

**Erfolg:** exakt der gespeicherte Record wird zurückgegeben · Uhr genau einmal
gelesen · State entfernt · zweiter Claim `None` · zweiter Claim liest die Uhr
nicht erneut · der zurückgegebene Record ist unverändert.

**Unbekannt:** `None` **ohne** Uhr-Lesevorgang, Zustand unverändert.

**Ablauf:** `None` · exakt am Ablaufzeitpunkt `None` · Record dennoch entfernt ·
zweiter Claim bleibt `None` ohne weiteren Uhr-Lesevorgang · Geheimnisse nicht
mehr über den Store erreichbar · unbekannt, abgelaufen und bereits konsumiert
sind ununterscheidbar.

**Isolation:** andere Pending-Transaktionen bleiben bei Erfolg **und** bei
Ablauf unverändert und weiterhin claimbar.

**Struktur:** Kompatibilität mit `OidcLoginTransactionClaimStore` · Signatur
ausschließlich `state` · keine Add-/Create-Methode (parametrisiert) · Modul ohne
Thread-, Lock-, Async-, Persistenz- oder Tombstone-Simulation.

> **LQ-143:** Der Test „keine Add-/Create-Methode" prüft seither nur noch
> weitere Verwaltungs-/Inspektions-API; `add_transaction` ist der eine
> Creation-Einstiegspunkt.

Uhr-Lesevorgänge werden über eine zählende Test-Uhr belegt. Zustandsprüfungen
laufen über den **ausschließlich lokalen, read-only** Testhelfer
`_stored_states(store)`; am Adapter wurde **keine** produktive Verwaltungs-API
ergänzt.

## Bewusst nicht enthalten

- kein Creation-/Add-Port,
- keine Methode zum Erzeugen oder Einfügen von Transaktionen
  (**überholt durch LQ-143**),
- kein Login-Start-Anwendungsfall,
- kein Callback-Anwendungsfall,
- keine Login-/Callback-Route,
- keine OIDC-/OAuth-Bibliothek,
- keine Token-, Discovery-, JWKS- oder Trust-Logik,
- kein Tombstone,
- keine Datenbank oder Migration,
- keine Threads oder Locks,
- kein Production-Wiring oder Deployment,
- keine Änderung am Grype-/CI-Workflow.

## Nächster Schritt

Ein späterer Slice kann den zugehörigen **Creation-Pfad** definieren — einen
Login-Start-Anwendungsfall, der `OidcLoginState` und
`PendingOidcLoginTransaction` erzeugt und ablegt — mit eigener Port- und
Persistenzentscheidung.
