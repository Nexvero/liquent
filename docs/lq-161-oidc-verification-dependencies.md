# LQ-161 — OIDC Verification Dependencies

## Ergebnis

Die in LQ-160 priorisierte schmale Bibliotheksgrundlage wird als **geprüfte
Laufzeitabhängigkeit** aufgenommen:

```toml
"PyJWT[crypto]>=2.13,<3",
"httpx2>=2,<3",
```

**Die Bibliotheken werden noch nicht verwendet und nicht verdrahtet.** Kein
Verifikationsadapter, kein Tokenaustausch, kein JWKS-Fetch, kein Cache, kein
Netzwerkaufruf, keine JWT-Prüflogik.

## Warum PyJWT mit `[crypto]`

LQ-160 §2 verbietet eigene Kryptografie. PyJWT ist die schmalste Oberfläche für
genau diesen Zweck: JWT-Verifikation plus Schlüsselauswahl.

Das **`crypto`-Extra ist nicht optional**, sondern der Punkt: **bares PyJWT kann
keine asymmetrischen Signaturen prüfen**. Das Extra bindet die gepflegte
`cryptography`-Implementierung ein. Nachgewiesen durch aufgelöste Installation:
mit `[crypto]` kommt `cryptography` hinzu, ohne das Extra löst PyJWT **allein**
auf. Im installierten Ergebnis ist `jwt.algorithms.has_crypto` `True`.

Die Abhängigkeit ist **nach oben begrenzt** (`<3`), damit ein Major-Sprung nicht
unbemerkt einzieht.

## Warum `httpx2`

`httpx2` war bereits Dev-Abhängigkeit und ist bereits im CI-Lock gepinnt. Es
wird **von Dev nach Runtime verschoben**, nicht doppelt geführt, und dient
später als **kontrollierbarer** Client für Token-Endpunkt und JWKS.

Kontrollierbarkeit ist der Auswahlgrund: LQ-160 §4 verlangt ein Redirect-Verbot,
explizite Verbindungs-, Lese- und Gesamtzeitgrenzen sowie eine begrenzte
Antwortgröße. Das setzt einen Client voraus, dessen Verhalten pro Aufruf
festgelegt werden kann.

Die Verschiebung ist unkritisch: `starlette` deklariert `httpx2` selbst unter
seinem `full`-Extra für den TestClient, und ein bares `httpx` ist im Lock
überhaupt nicht enthalten. Als Laufzeitabhängigkeit bleibt `httpx2` für die
Tests weiterhin installiert.

## Eingebaute JWKS-Fetcher werden nicht automatisch genutzt

LQ-160 §12a hält fest, dass PyJWTs `PyJWKClient` das JWKS über
`urllib.request.urlopen` lädt und dabei **weder Redirect-Verhalten noch eine
Antwortgrößengrenze** konfiguriert.

**Verbindlich bleibt:** Der spätere Adapter setzt Redirect-Verbot, Größenlimit,
Timeouts und Cacheverhalten **selbst** durch — typischerweise, indem er das JWKS
über einen eigenen kontrollierten Client lädt und der Bibliothek **fertiges
Schlüsselmaterial** übergibt. Die Aufnahme der Bibliothek in LQ-161 erlaubt
**nicht**, ihren eingebauten Fetcher zu verwenden.

Ebenso unverändert: **keine eigene Kryptografie**, keine selbst implementierte
JWT-, JWS-, ASN.1-, RSA-, EC- oder Signaturprüfung und keine manuelle
Interpretation von Schlüsselmaterial.

## Dependency-Diff

```diff
 dependencies = [
     "alembic>=1.16,<2",
     "fastapi>=0.115,<1",
+    "httpx2>=2,<3",
     "prometheus-client>=0.22,<1",
     "psycopg[binary]>=3.2,<4",
     "pydantic-settings>=2.7,<3",
+    "PyJWT[crypto]>=2.13,<3",
     "sqlalchemy>=2.0,<2.1",
     "uvicorn>=0.34,<1",
 ]
 dev = [
     "build>=1.3,<2",
-    "httpx2>=2,<3",
     "pytest>=7.0",
```

Keine andere Abhängigkeit wurde geändert.

## Lockfile

`requirements/ci.lock` erhält **genau vier** neue exakte Pins an ihrer
namenssortierten Position:

```
PyJWT==2.13.0
cffi==2.1.1
cryptography==50.0.0
pycparser==3.0
```

`cffi` und `pycparser` sind die transitive Kette von `cryptography` auf CPython.
**Kein bestehender Pin wurde nebenbei aktualisiert**, `httpx2==2.9.1` und
`httpcore2==2.9.1` bleiben unverändert. Die Auflösung lief unter dem
**bestehenden** Lock als Constraint — dass sie ohne Konflikt gelang, ist der
Beleg, dass keine Änderung an vorhandenen Pins nötig war.

Aufgelöst wurde auf **Python 3.12**, passend zum CI (`python-version: "3.12"`)
und zur Kopfzeile des Locks. Das ist relevant: eine Auflösung unter Python 3.9
ergibt `cffi==2.0.0`/`pycparser==2.23`, unter 3.12 dagegen `cffi==2.1.1`/
`pycparser==3.0`.

Keine Indizes, Credentials, direkten URLs, Plattformpfade oder Hash-Ausnahmen.

## Supply-Chain-Ergebnis

Geprüft vor dem Commit:

| Schritt | Ergebnis |
|---|---|
| Saubere Umgebung, CI-Schrittfolge (Build-Frontend, dann `--no-build-isolation --constraint requirements/ci.lock -e ".[dev]"`) | erfolgreich |
| `pip check` | keine defekten Abhängigkeiten |
| `import jwt`, `import cryptography`, `import httpx2` | alle erfolgreich (2.13.0 / 50.0.0 / 2.9.1) |
| `jwt.algorithms.has_crypto` | `True` — das Extra wirkt |
| Installierte Versionen gegen den Lock | identisch |
| Vollständige Suite in der sauberen Lock-Umgebung | bestanden |
| Wheel-Bau (`--wheel --no-isolation`, `SOURCE_DATE_EPOCH`) | erfolgreich |
| Wheel in **zweiter** sauberer Umgebung installiert, außerhalb des Quellbaums importiert | erfolgreich |
| `Requires-Dist` | `PyJWT[crypto]<3,>=2.13` und `httpx2<3,>=2` als **Runtime** deklariert, `httpx2` **nicht** mehr unter `extra == "dev"` |
| Entry Points | `liquent-control-plane`, `liquent-health-check`, `liquent-migrate` vorhanden |

**Keine Netzwerk-, Token-, JWKS- oder Kryptografieoperation gegen reale
Systeme.** Es fand ausschließlich Paketinstallation aus dem Index statt.

Container-, SBOM- und Grype-Gate werden vollständig über die PR-CI beobachtet.
`.grype.yaml` wurde **nicht** geändert; bei einem blockierenden High-/
Critical-Befund wird gestoppt und berichtet, statt eine Ausnahme einzuführen.

## Tests

Der bestehende zentrale Vertrag in `tests/test_ci_release_gate.py` prüft exakte
Pins, Stabilität und Eindeutigkeit bereits **für den gesamten Lock**; Versionen
werden deshalb **nicht** zusätzlich an anderer Stelle festgeschrieben. Ergänzt
wurden nur drei enge Prüfungen:

- PyJWT ist Laufzeitabhängigkeit **und trägt das `crypto`-Extra**,
- `httpx2` ist Laufzeitabhängigkeit,
- **genau diese beiden** Anforderungen sind begrenzt, ohne direkte URL und ohne
  Preview-Release,
- weder `httpx2` noch PyJWT stehen zusätzlich im Dev-Extra,
- PyJWT, `httpx2` und die Kryptokette sind vom Lock **abgedeckt**.

Die Prüfungen sind **auf diese beiden Bibliotheken begrenzt** und stellen
**keine** allgemeine Regel für jede Laufzeitabhängigkeit auf: Ein späterer
legitimer Slice könnte eine andere Abhängigkeit anders, aber weiterhin
kontrolliert spezifizieren, ohne an einem OIDC-Test zu scheitern.

`pyproject.toml` wird mit **`tomllib`** gelesen und die beiden Anforderungen mit
**`packaging.requirements.Requirement`** geparst — kein selbst gebauter
TOML-Parser und keine Namenserkennung über Stringpräfixe.

## Bewusst nicht enthalten

- kein Verifikationsadapter, kein Tokenaustausch, kein JWKS-Fetch, kein Cache,
- kein Netzwerkaufruf, keine JWT-Prüflogik,
- keine Port- oder Modelländerung, keine Route, keine Callback-Logik,
- kein Provider, kein Production-Wiring,
- keine Änderung an `.grype.yaml`,
- keine CI-, Container-, Deployment-, CORS- oder Shared-Environment-Änderung.

Ein ausführlicher Paketvergleich steht bereits in LQ-160 §12 und wird hier
nicht wiederholt.

## Nächster Schritt

Unverändert die Reihenfolge aus LQ-158 §15 — **alle noch nicht begonnen**: der
Verifikationsadapter nach LQ-160, danach der transportfreie
Callback-Anwendungsfall, die Session-/CSRF-Ausgabeentscheidung, validierte
interne Ziele und zuletzt die Callback-Route.
