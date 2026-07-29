# LQ-143 — In-Memory OIDC Login Transaction Creation

## Ergebnis

`InMemoryOidcLoginTransactions` erfüllt jetzt in **derselben lokalen Instanz**
sowohl `OidcLoginTransactionCreationStore` (LQ-142) als auch
`OidcLoginTransactionClaimStore` (LQ-139). Keine Route und kein
Login-Start-Anwendungsfall.

## Zustandsmodell

Der Adapter hält intern:

| Attribut | Inhalt |
|---|---|
| `_transactions` | aktuell pending Records |
| `_reserved_states` | **alle** States, die in dieser Adapterinstanz bereits belegt wurden |

Regeln:

- Beim Konstruktor werden **alle Keys** des initialen Transaction-Mappings
  automatisch reserviert.
- Ein erfolgreicher **oder** abgelaufener Claim entfernt **nur** den
  Pending-Record.
- Der State **bleibt reserviert**.
- Ein reservierter State darf **niemals** erneut hinzugefügt werden.
- Ein neuer State wird beim erfolgreichen Add **gleichzeitig** pending und
  reserviert.
- Der lokale Adapter speichert **rohe `OidcLoginState`-Objekte** im Speicher.
  Diese sind weiterhin **sensible Handles**; der Reserved-Satz ist daher
  **nicht** als „secret-free" zu bezeichnen.
- **Keine** Ausgabe oder Protokollierung reservierter States.
- Persistentes Hashing oder Tombstones bleiben **außerhalb** dieses Slices.

## Signaturen

Die Konstruktorsignatur bleibt **unverändert** — keine zusätzliche öffentliche
Seed-/Reserved-Option:

```
def __init__(
    self,
    transactions: Mapping[
        OidcLoginState,
        PendingOidcLoginTransaction,
    ],
    *,
    now: Callable[[], datetime],
) -> None:
    self._transactions = dict(transactions)
    self._reserved_states = set(self._transactions)
    self._now = now

def add_transaction(
    self,
    state: OidcLoginState,
    transaction: PendingOidcLoginTransaction,
) -> bool: ...

def claim_transaction(
    self,
    state: OidcLoginState,
) -> PendingOidcLoginTransaction | None: ...
```

## Übergänge

| Aufruf | Uhr | `_transactions` | `_reserved_states` | Rückgabe |
|---|---|---|---|---|
| `add`, freier State | **nicht gelesen** | + Record | + State | `True` |
| `add`, reservierter State (pending **oder** verbraucht) | nicht gelesen | unverändert | unverändert | `False` |
| `claim`, unbekannt | nicht gelesen | unverändert | **unverändert** | `None` |
| `claim`, gültig | genau 1× | − Record | **bleibt** | Record, einmalig |
| `claim`, abgelaufen | genau 1× | − Record | **bleibt** | `None` |
| `add` nach Claim (Erfolg oder Ablauf) | nicht gelesen | unverändert | unverändert | `False` |

Ein **fehlgeschlagener** Claim auf einen unbekannten State reserviert ihn
**nicht**; ein späteres `add` desselben zuvor unbekannten State darf gelingen.

`claim_transaction` bleibt inhaltlich unverändert gegenüber LQ-141: Sie mutiert
ausschließlich `_transactions`, wodurch die Reservierung automatisch bestehen
bleibt.

## Atomarität im lokalen synchronen Adapter

- Für `add` werden **beide** Snapshots vollständig vorbereitet, **bevor** ein
  Attribut ersetzt wird.
- Es gibt **keine** Threads, Locks, `await`-Punkte oder öffentliche Beobachtung
  des Zwischenzustands.
- **Keine** zusätzliche State-Klasse oder Orchestrierungsabstraktion.

## Tests

`tests/test_in_memory_oidc_login_transactions.py` — erweitert von 26 auf 46
fokussierte Tests.

**Konstruktion:** initiale Pending-States sind automatisch reserviert ·
Eingabe-Mapping wird kopiert · spätere Änderungen am Eingabe-Mapping wirken
weder auf Records noch auf die Reservierung.

**Creation:** freier State → `True` · exakt derselbe unveränderliche Record ist
gespeichert · State danach reserviert · Uhr wird **nicht** gelesen (auch nicht
bei Ablehnung) · bereits pending/reserviert → `False` · Kollision überschreibt
nicht · anderer freier State bleibt speicherbar · State und Record bleiben
exakt/opak, eine normalisierte State-Variante trifft den Eintrag nicht.

**Zusammenspiel mit Claim:** Add → Claim liefert den Record genau einmal · nach
erfolgreichem Claim bleibt der State reserviert · Re-Add danach → `False` · nach
abgelaufenem Claim bleibt der State reserviert · Re-Add danach → `False` · ein
fehlgeschlagener Claim eines unbekannten State reserviert ihn nicht und ein
späteres Add gelingt · andere Pending- und Reserved-States bleiben bei Claim und
bei abgelehntem Add unverändert.

**Struktur:** strukturelle Kompatibilität mit **beiden** Ports, auch als **eine**
Instanz gleichzeitig · `add_transaction`-Signatur exakt
`["self", "state", "transaction"]` · `claim_transaction`-Signatur exakt
`["self", "state"]` · keine weitere öffentliche Verwaltungs- oder
Inspektions-API · Modul ohne Thread-, Lock-, Async-, Persistenz- oder
Tombstone-Simulation.

Zustandsprüfungen laufen über **ausschließlich lokale, read-only** Testhelfer
(`_stored_states`, `_reserved_states`, `_stored_record`); am Adapter wurde
**keine** produktive Verwaltungs-API ergänzt.

## Angepasste frühere Zusicherungen

Zwei bereits gemergte Tests sicherten ausdrücklich zu, dass dieser Adapter
**keine** Creation-Methode besitzt. Genau das hebt LQ-143 auf, daher waren beide
anzupassen:

- `tests/test_in_memory_oidc_login_transactions.py` — der parametrisierte Test
  „keine Add-/Create-Methode" enthielt `"add_transaction"`. Der Parameter
  entfällt; der Test heißt jetzt
  `test_adapter_has_no_further_management_or_inspection_api` und deckt weiterhin
  `create_transaction`, `add`, `create`, `put`, `store` sowie `reserved_states`
  ab.
- `tests/test_oidc_login_transaction_creation_port.py` — die Zeile
  `assert not hasattr(InMemoryOidcLoginTransactions, "add_transaction")` war
  ausdrücklich „in diesem Slice" formuliert und wurde entfernt. Diese Datei
  stand nicht in der LQ-143-Dateiliste; die Änderung war zwingend, weil die
  Suite sonst fehlschlägt.

In `docs/lq-141-in-memory-oidc-login-transaction-claims.md` sind die
widersprechenden Aussagen als **überholt** markiert statt umgeschrieben, damit
die historische Slice-Dokumentation lesbar bleibt.

## Bewusst nicht enthalten

- kein Generator-Port,
- kein Login-Start-Anwendungsfall,
- keine automatische Kollisionswiederholung,
- keine Login-Start-/Callback-Route,
- keine OIDC-/OAuth-Bibliothek,
- keine Token-, Discovery-, JWKS- oder Trust-Logik,
- keine Datenbank, Hashpersistenz oder Migration,
- keine Threads oder Locks,
- kein Production-Wiring oder Deployment,
- keine Änderung am Grype-/CI-Workflow,
- keine Bereinigung des älteren LQ-139-Substring-Tests.

## Nächster Schritt

Ein späterer Slice kann den **Login-Start-Anwendungsfall** definieren: Material
erzeugen (LQ-137), den Record bauen (LQ-138), die Nicht-Ablauf-Bedingung prüfen
und ihn über den Creation-Port ablegen.
