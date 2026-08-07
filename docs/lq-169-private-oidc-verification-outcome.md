# LQ-169 — Private OIDC Verification Outcome

## Zweck

Der Offline-Verifikationskern unterscheidet **modulintern** einen eng
definierten unbekannten-`kid`-Miss von einer endgültigen neutralen Ablehnung.
Damit existiert der Zustand, den LQ-168 §5 für den späteren Adapter verlangt —
**ohne** JWKS-Refresh, Cachezugriff oder Adapter.

## Öffentlicher Vertrag unverändert

```python
def verify_oidc_id_token(
    id_token, jwks, configuration, verification, now
) -> ExternalIdentity | None: ...
```

Signatur, Annotation und Semantik bleiben exakt: Erfolg → `ExternalIdentity`,
jede belastbare Ablehnung **einschließlich unbekanntem `kid`** → `None`,
technische Unverfügbarkeit → `OidcVerificationUnavailable`, naive Zeit →
bestehender `ValueError`. Keine neue öffentliche Exception, kein neuer
Rückgabetyp, keine Portänderung.

Die Funktion ist jetzt ein dünner neutraler Wrapper: Sie ruft den einen internen
Durchlauf **genau einmal** auf und gibt nur dessen `identity` zurück. Miss und
endgültige Ablehnung kollabieren dabei gleichermaßen zu `None`, sodass kein
Aufrufer sie unterscheiden kann.

## Private Ergebnisform

```python
@dataclass(frozen=True, slots=True)
class _OidcIdTokenVerificationResult:
    identity: ExternalIdentity | None = field(repr=False)
    refreshable_key_miss: bool = field(repr=False)
```

Genau drei Zustände: **verifiziert** (`identity` gesetzt, `refreshable_key_miss`
`False`), **endgültig abgelehnt** (beide leer beziehungsweise `False`) und
**intern refreshbar** (`identity is None`, `refreshable_key_miss is True`). Die
Kombination aus Identität und Miss ist strukturell ausgeschlossen und ergibt
`ValueError`, dessen Meldung weder Identität noch Token nennt.

Beide Felder sind `repr`-frei, `repr(...)` zeigt nur den Klassennamen. Die
Klasse bleibt underscore-privat: nicht aus `identity/__init__.py` exportiert,
nicht in `ports.py`, nie serialisiert oder geloggt, und sie trägt kein Token,
`kid`, Algorithmus, Header, Claim, JWKS, URI oder Konfigurationsobjekt.

Die beiden identitätslosen Zustände sind geteilte Modul-Singletons, was durch
frozen und slots sicher ist.

## Miss-Regel

`refreshable_key_miss=True` entsteht an **genau einer** Stelle: dort, wo die
bestehende Schlüsselauswahl keinen eindeutigen Schlüssel liefert. Bis dahin sind
nicht leerer Token-String, zuverlässig gelesener JOSE-Header, Abwesenheit von
`jku`/`x5u`/`jwk`, `alg` als nicht leerer String, `alg` in der privaten
asymmetrischen Allowlist, `alg` in `configuration.allowed_signing_algorithms`
und die strukturelle Lesbarkeit des `keys`-Arrays bereits geprüft. Ergänzt wird
nur eine **Anwesenheitssonde über dieselbe Sequenz**:

```python
def _kid_is_provably_absent(keys, kid) -> bool:
    if not isinstance(kid, str) or not kid:
        return False
    return all(
        isinstance(entry, Mapping) and entry.get("kid") != kid for entry in keys
    )
```

Keine zweite Auswahlmatrix, keine semantische JWK-Prüfung, keine zweite
Header-Dekodierung und kein zweiter `jwt.decode`. Öffentlicher Wrapper und
private Funktion teilen denselben einzigen Ablauf.

Daraus folgt:

| Situation | Intern |
|---|---|
| gültiges String-`kid`, lesbares Set ohne dieses `kid` | **Miss** |
| gültiges String-`kid`, lesbares aber leeres `keys`-Array | **Miss** |
| `kid` bytegenau vorhanden — auch bei ungeeignetem `use`/`key_ops`/`alg`, Mehrfachvorkommen, inkompatibler Familie oder Kurve, gescheiterter Signatur | endgültig |
| mindestens ein Nicht-Mapping-Eintrag im Set | endgültig |
| `kid` fehlt, leer oder falsch typisiert | endgültig |
| `jku`, `x5u`, `jwk`, nicht allowlisteter, symmetrischer oder `none`-Algorithmus | endgültig |
| Issuer-, Audience-, `azp`-, Zeit-, Nonce-, Subject-Ablehnung, Issuer-Mismatch, leeres Token | endgültig |
| unbrauchbares vertrauenswürdiges JWKS, Bibliotheks- oder Kryptofehler | `OidcVerificationUnavailable` |

Ein technischer Fehler wird **niemals** zum Miss. Ein unlesbarer Eintrag lässt
die Sonde sofort `False` liefern, sodass Abwesenheit nicht behauptet wird und
kein Netzwerkhinweis entsteht.

Ohne `kid` bleibt die Auswahl unverändert: Genau ein eindeutiger Kandidat
verifiziert weiterhin erfolgreich; fehlt er, ist das eine endgültige Ablehnung.

## Bedeutung

Der Miss heißt nur: *Der Token nennt einen Schlüsselbezeichner, der im aktuellen
vertrauenswürdigen Snapshot fehlt.* Er beweist **keine** Identität, gewährt
**keine** Berechtigung und kürzt **keine** Prüfung ab. Ob daraus ein Refresh
folgt, entscheidet allein der spätere Adapter nach LQ-168.


## Nicht-Ziele

Kein Netzwerk, kein Token-Endpunkt-Aufruf, kein JWKS-Load, kein Cachezugriff,
keine Cache-Invalidierung oder Refresh-Methode, kein zweiter Verifikations-
versuch, keine Retry-Schleife, keine LQ-157-Portimplementierung, keine
Callback-Route, keine Session-/CSRF-Ausgabe, keine Composition, kein
Production-Wiring, keine Dependency-, Lockfile-, CI-, Container- oder
Grype-Änderung, keine Änderung an `identity/ports.py` und kein Export der
privaten Ergebnisform.
