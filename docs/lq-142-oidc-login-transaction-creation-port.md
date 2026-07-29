# LQ-142 — OIDC Login Transaction Creation Port

## Ergebnis

Die minimale Portgrenze zum **atomaren Speichern** einer neuen pending
OIDC-Login-Transaktion: `OidcLoginTransactionCreationStore` in
`src/liquent_platform/identity/ports.py`. Kein Adapter, kein Generator-Port, kein
Anwendungsfall und keine Route. Gegenstück zum LQ-139-Claim-Port über demselben
LQ-138-Modell und LQ-139-`OidcLoginState`.

## Creation-Port

```
class OidcLoginTransactionCreationStore(Protocol):
    def add_transaction(
        self,
        state: OidcLoginState,
        transaction: PendingOidcLoginTransaction,
    ) -> bool: ...
```

Die Imports für `OidcLoginState` und `PendingOidcLoginTransaction` bestehen seit
LQ-139 bereits; der Slice ergänzt ausschließlich das Protocol.

## Verbindlicher Vertrag

- Die Anlage erfolgt **atomar**.
- Erfolg liefert **`True`**.
- Der Store speichert **exakt** den übergebenen unveränderlichen Pending-Record
  unter dem **exakten/opaken** State.
- Der Store **normalisiert oder verändert** State und Record **nicht**.
- Der Store **überschreibt niemals** einen bestehenden Pending-Record.
- Ein State, der bereits **pending** ist, führt neutral zu `False`.
- Ein State, der bereits früher erfolgreich beansprucht, konsumiert oder wegen
  Ablauf entfernt wurde und durch einen **Konsumnachweis/Tombstone** bekannt ist,
  darf **nicht wiederverwendet** werden und führt neutral zu `False`.
- Damit kann ein **alter Callback niemals** durch Wiederbelegung desselben State
  auf eine **neue** Login-Transaktion treffen.
- Ein **persistenter** Store muss diese Nicht-Wiederverwendung **atomar**
  absichern.
- Ein späterer **lokaler Adapter** darf dafür einen ausschließlich internen,
  **geheimnisfreien** Reserved-/Used-State-Satz führen.
- `False` **unterscheidet nicht** zwischen Pending-Kollision und bereits
  verwendetem State.
- Der Aufrufer liefert **keinen `now`**-Wert.
- Der Creation-Port entscheidet **nicht** über Issuer-Trust, OIDC-Tokens,
  Admission oder Autorisierung.
- Der aufrufende **Login-Start-Anwendungsfall** muss später sicherstellen, dass
  der Record zum Erstellzeitpunkt noch nicht abgelaufen ist.
- **Keine** automatische Retry- oder Materialerzeugung im Store.
- **Keine** Geheimnisse loggen oder in Fehlerergebnisse aufnehmen.

### Kollisionsregeln

| Eingang | Rückgabe | Zustand |
|---|---|---|
| freier State | `True` | Record exakt unter dem exakten State abgelegt |
| State bereits **pending** | `False` | vorhandener Record **nicht überschrieben** |
| State bereits beansprucht/konsumiert/wegen Ablauf entfernt (Tombstone) | `False` | keine Wiederbelegung |

Der Zweck der zweiten Regel ist **Replay-Schutz**, nicht bloß
Kollisionsvermeidung.

## Tests

`tests/test_oidc_login_transaction_creation_port.py` — 25 fokussierte Tests, nur
Portvertrag und Test-Stub, **kein produktiver Adapter**.

**Erfolg:** freier State → `True` · gespeicherter Record ist **dasselbe**
unveränderliche Objekt · State und Record werden nicht normalisiert oder
verändert, und eine normalisierte State-Variante trifft den Eintrag nicht.

**Kollision:** bestehender Pending-State → `False` · bereits
verwendeter/reservierter State → `False` · Kollision überschreibt den vorhandenen
Record nicht · ein Used-State-Konflikt legt nichts ab · `False` ist für beide
Gründe identisch · ein anderer freier State bleibt danach speicherbar.

**Struktur:** Protocol-Kompatibilität · Signatur exakt
`["self", "state", "transaction"]` · kein `now`, Issuer, Nonce, Verifier,
Admission, User oder Workspace als separater Parameter (parametrisiert) ·
Rückgabeannotation ist ein reines `bool` · Stub weder aus `ports.py` noch aus dem
`identity`-Paket exportiert, und `InMemoryOidcLoginTransactions` erhält in diesem
Slice **keine** `add_transaction`-Methode.

**Keine Retry-, Generator-, Token-, Trust-, HTTP- oder Persistenzlogik** wird
**strukturell über den AST** belegt, nicht über Textsuche: Jede Portmethode in
`ports.py` besteht aus genau einem `...`-Rumpf, und das Modul importiert
ausschließlich `typing` und `liquent_platform.*`. Eine reine Textprüfung wäre
hier irreführend gewesen, weil der Vertragsdocstring Retries und Tokens
ausdrücklich benennt, um sie auszuschließen.

Der Stub führt neben dem Pending-Mapping einen **geheimnisfreien** `used`-Satz,
der einen Konsumnachweis/Tombstone vertritt — der Creation-Port selbst hat keine
Claim-Methode. Er bleibt ausschließlich in der Testdatei.

## Bewusst nicht enthalten

- keine Änderung an `InMemoryOidcLoginTransactions`,
- kein In-Memory- oder persistenter Creation-Adapter,
- kein Generator-Port,
- kein Login-Start-Anwendungsfall,
- keine automatische Kollisionswiederholung,
- keine Login-Start-/Callback-Route,
- keine OIDC-/OAuth-Bibliothek,
- keine Token-, Discovery-, JWKS- oder Trust-Logik,
- keine Datenbank oder Migration,
- kein Production-Wiring oder Deployment,
- keine Änderung am Grype-/CI-Workflow.

## Nächster Schritt

Ein späterer Slice kann einen lokalen Creation-Adapter mit internem,
geheimnisfreiem Used-State-Satz ergänzen und danach den
**Login-Start-Anwendungsfall** definieren, der Material erzeugt, die Nicht-Ablauf
-Bedingung prüft und den Record über diesen Port ablegt.
