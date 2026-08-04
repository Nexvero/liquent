# LQ-149 — Claim-Port-Vertragstest auf den eigenen Vertrag begrenzen

Kleiner Test-Wartungsslice. **Keine** Produktionscodeänderung, **keine** Datei
unter `src/`, **keine** Änderung an `ports.py`.

## Ausgangsproblem

`tests/test_oidc_login_transaction_claim_port.py` enthielt:

```python
def test_ports_module_has_no_token_trust_http_or_persistence_logic() -> None:
    source = inspect.getsource(ports_mod)

    for forbidden in ("jwt", "jwks", "fastapi", "sqlalchemy", "requests", "httpx"):
        assert forbidden not in source.lower()
    assert "router" not in source.lower()
    assert "def claim_transaction" in source  # declaration only, no adapter
```

## Falsche Kopplung an das gesamte Modul

Der Test las über `inspect.getsource(ports_mod)` die **gesamte** Datei
`identity/ports.py` und suchte case-insensitiv nach Substrings. Damit koppelte
ein LQ-139-Test an **jeden** späteren, unabhängigen Portvertrag derselben Datei.

Er konnte nicht unterscheiden zwischen:

- tatsächlicher Implementierungslogik,
- Importen für spätere legitime Ports,
- Typnamen,
- Docstrings, die etwas ausdrücklich **ausschließen**,
- anderen unabhängigen Portverträgen.

**Konkreter Schaden:** LQ-148 wurde blockiert. Dessen Docstring sagte
ausdrücklich „loads no JWKS" — also das **Gegenteil** einer Nutzung — und die
Substring-Suche wertete das als Verstoß. Die Formulierung musste damals auf
„loads no signing key set" ausweichen, nur um einen defekten Test zu passieren.

## Fokussierter Ersatz

```python
def test_claim_port_declares_only_claim_transaction_without_a_body() -> None:
    tree = ast.parse(inspect.getsource(OidcLoginTransactionClaimStore))
    methods = [
        node for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)
    ]

    assert [node.name for node in methods] == ["claim_transaction"]
    # ... Rumpf ist ausschließlich Ellipsis (Docstring ausgenommen)
```

Der Test untersucht **ausschließlich** `inspect.getsource(
OidcLoginTransactionClaimStore)` und folgt damit dem bereits bei LQ-142 und
LQ-148 etablierten Muster. Er belegt:

- der Protocol-Typ deklariert **genau** die Methode `claim_transaction`,
- deren Rumpf ist ein reiner `...`-Deklarationsrumpf,
- im Port selbst steckt **keine** Adapter- oder Ausführungslogik.

Er ist **nicht** leerlaufend: Gegen einen Port mit Ausführungslogik im Rumpf
**und** gegen einen Port mit einer zusätzlichen Methode schlägt dieselbe Logik
nachweislich fehl.

**Der Ersatz trifft bewusst keine Aussage über** andere Klassen, Importe,
Docstring-Wortwahl, die gesamte Modulfläche, die Zahl anderer Portklassen oder
das Vorhandensein künftiger Adapter.

Ein `textwrap.dedent` ist nicht nötig: Der Protocol-Typ steht auf Modulebene,
`inspect.getsource` liefert daher spaltenbündigen Quelltext.

## Weiterhin zuständig bleiben die vorhandenen Tests

Signatur exakt `["self", "state"]` · ausgeschlossene Clock- und
Transaktionsmaterialparameter · Rückgabeannotation · strukturelle
Kompatibilität · Test-Stub nicht exportiert. Diese wurden **nicht** dupliziert
und **nicht** neu geschrieben.

Der Import `import liquent_platform.identity.ports as ports_mod` bleibt
erhalten, weil `test_stub_is_test_only_and_not_exported_by_the_identity_package`
ihn weiterhin benötigt. Neu hinzu kam ausschließlich `import ast`.

## Fachliche Semantik unverändert

Die LQ-139-Vertragssemantik ist **unverändert**. Angepasst wurde nur die
überbreite Zusicherung in `docs/lq-139-oidc-login-transaction-claim-port.md`;
die frühere Formulierung ist dort als durch LQ-149 korrigiert markiert, statt
gelöscht zu werden.

## Testzahl

Ein Test entfernt, ein fokussierter Test ergänzt — **netto null**:

| Umfang | vorher | nachher |
|---|---|---|
| `tests/test_oidc_login_transaction_claim_port.py` | 35 | **35** |
| Vollständige Suite | 1494 | **1494** |

## Bewusst nicht enthalten

- keine Änderung am Claim-Port oder an anderen Ports,
- kein Adapter, kein In-Memory-Konfigurationsadapter,
- keine Login-Start-Route, keine Trust-Registry, keine OIDC-Implementierung,
- keine globale Bereinigung aller Tests,
- keine Umbenennung unabhängiger Docstrings,
- keine CI-/Grype-Änderung, keine Änderung der CPython-Ausnahmen,
- keine Dependabot-PRs.

## Nachbemerkung

Die bei LQ-148 erzwungene Formulierung „loads no signing key set" in `ports.py`
bleibt unverändert stehen. Sie ist sachlich korrekt, und ein Zurückändern wäre
eine Produktionscodeänderung — die dieser Test-Wartungsslice ausdrücklich nicht
vornimmt.
