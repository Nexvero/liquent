# LQ-156 — OIDC Verification Configuration

## Ergebnis

**Additive Erweiterung von `TrustedOidcClientConfiguration` (LQ-146)** um exakt
die vier serverseitigen Verifikationswerte, die LQ-155 §5 als **harte
Vorbedingung** festgehalten hat.

Damit ist die dort benannte Konfigurationslücke geschlossen. **Kein**
Verifikationsport, **kein** Adapter, **kein** Callback, **kein** HTTP-Client,
**kein** JWKS-Download, **keine** Signatur- oder Claimprüfung.

## Signatur

`src/liquent_platform/identity/oidc_client_configuration.py`

```python
@dataclass(frozen=True, slots=True)
class TrustedOidcClientConfiguration:
    issuer: str
    authorization_endpoint: str
    client_id: str
    redirect_uri: str
    scopes: tuple[str, ...]
    token_endpoint: str
    jwks_uri: str
    allowed_signing_algorithms: tuple[str, ...]
    clock_skew: timedelta
```

**Neun Felder**, keine optionalen, **keine Defaults**. Die bestehenden fünf
bleiben in **Reihenfolge und Semantik unverändert**; die vier neuen folgen
danach. Das Modell bleibt `frozen=True`, `slots=True` und hashbar — `timedelta`
und `tuple[str, ...]` sind beide hashbar.

**Keine Defaults ist eine Sicherheitsentscheidung, keine Stilfrage.** Ein
Default-Algorithmus oder eine Default-Skew wäre eine Trust-Annahme, die niemand
bewusst getroffen hat. Jeder Wert muss beim serverseitigen Aufbau ausdrücklich
angegeben werden; ein fehlendes Feld ist ein gewöhnlicher `TypeError` des
Konstruktors.

## Token-Endpunkt und JWKS-Quelle

Beide Felder verwenden den **bereits vorhandenen** fokussierten Validator
`_require_https_url(value, name, allow_query=False)` — **unverändert**:

| Regel | `token_endpoint` | `jwks_uri` |
|---|---|---|
| nicht leer | ✓ | ✓ |
| absolut `https` mit Host | ✓ | ✓ |
| Port und Pfad erlaubt | ✓ | ✓ |
| kein Userinfo (auch nicht leer) | ✓ | ✓ |
| keine Query, auch kein leerer `?` | ✓ | ✓ |
| kein Fragment, auch kein leerer `#` | ✓ | ✓ |
| keine Whitespace-/Steuerzeichen | ✓ | ✓ |
| exakt und unverändert gespeichert | ✓ | ✓ |

Der Validator passt **exakt** auf die geforderten Invarianten, deshalb wurde
**keine Zeile** an ihm geändert. Die Semantik von `issuer`,
`authorization_endpoint` und `redirect_uri` bleibt dadurch nachweislich
unberührt — die bestehenden Nachbartests laufen unverändert durch.

Er trägt zwei Härtungen, die hier unmittelbar mitgelten und bewusst am
**Rohwert** statt am Parse-Ergebnis prüfen:

- `urlsplit` entfernt Tab, Zeilenumbruch und Carriage Return **überall**, auch
  **im Host**. `https://idp.example\n.test/token` parst zu einem sauberen Host,
  während das Modell den unsicheren Originalstring speichern würde.
- Bei `…/token?` und `…/token#` sind `parsed.query` und `parsed.fragment`
  **beide leere Strings**; eine Truthiness-Prüfung ließe den leeren Trenner
  durch.

**Keine Ableitung, keine Discovery, kein Netzwerk.** Weder Token-Endpunkt noch
JWKS-URI werden aus `issuer` oder `authorization_endpoint` gebildet. Beide
dürfen ausdrücklich auf **anderen Hosts** liegen und bleiben exakt erhalten —
getestet mit drei verschiedenen Hosts in einer Konfiguration. Es findet **kein**
Abruf, **keine** DNS-Auflösung und **keine** Discovery statt.

### Bekannte, unveränderte Eigenschaft

Der Validator prüft `parsed.scheme`, und `urlsplit` schreibt das Scheme klein —
`HTTPS://host` wird deshalb akzeptiert. Das ist das **bestehende** LQ-146-
Verhalten aller drei URL-Felder. Es hier zu verschärfen würde die Semantik
bestehender Felder ändern und liegt außerhalb dieses Slices; es wird bewusst
**nicht** stillschweigend mitkorrigiert, sondern hier festgehalten.

(Anders als bei der vertrauenswürdigen Origin in LQ-154: dort wird das Scheme am
Rohwert geprüft, weil ein `Origin`-Header **byteweise exakt** verglichen wird.)

### Warum `jwks_uri` und kein eingebettetes Schlüsselset

Für diesen ersten providerneutralen Slice ist die JWKS-Quelle **eine explizit
konfigurierte HTTPS-Referenz** auf das vertrauenswürdige Schlüsselset — ein
`str`, **kein** Union-Typ und **kein** zweites Modell.

Ein **statisch eingebettetes** Schlüsselset bleibt eine **spätere, ausdrückliche
Erweiterung**. Ein Union-Typ jetzt würde jede spätere Verwendungsstelle zu einer
Fallunterscheidung zwingen, ohne dass ein Anwendungsfall dafür existiert.

Das Modell enthält damit **weiterhin kein Schlüsselmaterial** — nur die Angabe,
**wo** das vertrauenswürdige Set liegt. `jku`, `x5u` und `jwk` aus Tokenheadern
werden gemäß LQ-155 §8 **niemals** befolgt, und `kid` darf später
**ausschließlich innerhalb** des über `jwks_uri` geladenen Sets auswählen.

## Erlaubte Signaturalgorithmen

`allowed_signing_algorithms: tuple[str, ...]`

Prüfreihenfolge, konsistent mit der bestehenden Scope-Validierung: Tupel-Typ →
nicht leer → je Eintrag (String, nicht leer, kein Whitespace, nicht `none`,
nicht doppelt).

- muss ein **Tupel** sein — eine Liste wird abgewiesen, nicht konvertiert,
- darf **nicht leer** sein,
- jeder Eintrag ein **nicht leerer String**,
- **kein Whitespace** — ein JOSE-`alg` ist ein bloßes Token; ein Eintrag mit
  Leerzeichen könnte niemals einem echten Header entsprechen,
- **keine Duplikate**,
- **Reihenfolge exakt bewahrt**, **nicht sortiert**,
- **nicht normalisiert, nicht ergänzt, nicht abgeleitet** — insbesondere wird
  **kein `RS256`** und kein anderer Algorithmus automatisch hinzugefügt.

### Allowlist, keine Algorithmuswahl

Verbindlich dokumentiert:

- Diese Konfiguration ist eine **Allowlist**, **keine** dynamische
  Algorithmuswahl.
- Ein späterer Adapter darf **nur die Schnittmenge** aus dieser konfigurierten
  Allowlist und seinen **fest eingebauten, unterstützten sicheren**
  Algorithmen akzeptieren.
- Ein **Tokenheader darf die Allowlist niemals erweitern**. Der `alg`-Wert darf
  höchstens **auswählen**, welcher der erlaubten Algorithmen gilt.
- **`kid`** darf später **nur innerhalb** des über `jwks_uri` geladenen
  vertrauenswürdigen Schlüsselsets auswählen.
- LQ-156 entscheidet **keine** konkrete Kryptobibliothek und führt **keine**
  Signaturprüfung aus.

### `none` wird in jeder Schreibweise abgewiesen

`none` ist der Algorithmus des **unsignierten** JWT. Ihn zuzulassen machte jede
Signaturprüfung zu einem No-op — der klassische JWT-Bypass. Abgewiesen werden
`none`, `NONE`, `None`, `nOnE` und jede andere Schreibweise.

Das ist der **einzige bewusst case-insensitive** Vergleich in diesem Modell.
Er trifft den **exakten** `alg`-Wert, nicht ein Vorkommen als Teilstring:
`none-like` und `NONEXISTENT` bleiben zulässig — sie sind keine gültigen
`alg`-Werte für ein unsigniertes Token. Ansonsten wird **nichts** normalisiert;
`rs256` und `RS256` bleiben zwei verschiedene konfigurierte Einträge.

## Clock-Skew

`clock_skew: timedelta`

- muss ein **`timedelta`** sein — `30`, `30.0`, `"30"`, `"PT30S"` und `None`
  werden abgewiesen,
- darf **nicht negativ** sein,
- **`timedelta(0)` ist zulässig** — die strengste sinnvolle Einstellung,
- **maximal `timedelta(minutes=5)`**; exakt fünf Minuten sind noch zulässig,
- größere Werte werden mit `ValueError` abgewiesen,
- wird **exakt bewahrt**, **nicht gerundet** und **nicht normalisiert** —
  Sub-Sekunden-Anteile bleiben erhalten.

Die Obergrenze von fünf Minuten ist die verbindliche „kleine, explizite"
Skew-Grenze aus LQ-155 §7, festgehalten als `MAXIMUM_CLOCK_SKEW`. Sie ist eine
**Sicherheitsregel, keine Bequemlichkeit**: Skew verbreitert das Fenster, in
dem ein abgelaufenes oder noch nicht gültiges Token weiterhin durchgeht.

**Kein Default** und **keine Ableitung aus Tokenclaims.**

## Sicherheitsgrenzen

Die vier Werte:

- stammen **ausschließlich** aus vertrauenswürdiger Serverkonfiguration,
- werden **nie** aus Browserinput, Pending-Transaktion, Tokenclaims oder
  Headern abgeleitet,
- frieren **keinen** dauerhaften Trust-Status ein,
- **ersetzen nicht** die erneute aktive Issuer-Prüfung beim Callback
  (LQ-136, LQ-155 §4).

Der bloße Besitz einer Konfiguration bleibt **kein** Beweis, dass der Issuer
weiterhin aktiviert ist.

Das Modell enthält **weiterhin nicht**: Client-Secret, private Schlüssel,
Tokens, Claims, `state`, `nonce`, `code_verifier`, `code_challenge`,
Admission-ID, Return-Path, User-, Workspace-, Rollen-, Session- oder
Berechtigungsdaten, ein `enabled`-/`trusted`-Flag sowie Providername oder
Branding.

## Bestehende Aufrufer

**Kein Produktionscode außerhalb von `oidc_client_configuration.py` wurde
geändert.** Die drei `src`-Module, die den Typ nennen
(`build_oidc_authorization_request.py`, `in_memory.py`, `ports.py`),
**importieren und annotieren** ihn nur — keines konstruiert eine Konfiguration.
Die neue Pflichtsignatur erzwingt dort daher keine Änderung.

Alle sieben Konstruktionsstellen liegen in Tests und wurden **rein mechanisch**
um vier gültige explizite Werte ergänzt; **keine fachliche Semantik** dieser
Nachbartests wurde verändert:

| Datei | Stellen |
|---|---|
| `tests/test_oidc_client_configuration.py` | 1 (Fixture) |
| `tests/test_active_oidc_client_configuration_lookup_port.py` | 1 |
| `tests/test_build_oidc_authorization_request.py` | 1 + `configuration_keys` |
| `tests/test_in_memory_active_oidc_client_configuration.py` | 2 |
| `tests/test_oidc_login_start_route.py` | 1 |
| `tests/test_prepare_oidc_login_authorization.py` | 1 |

In `test_build_oidc_authorization_request.py` musste zusätzlich die Menge
`configuration_keys` um die vier Namen wachsen, weil deren `_build(**overrides)`
sonst Konfigurationsschlüssel an `StartedOidcLogin` weiterreichen würde. Auch
das ist mechanisch, nicht semantisch.

## Tests

`tests/test_oidc_client_configuration.py` — von 89 auf **196** fokussierte
Tests.

**Struktur:** exakt neun Felder in vereinbarter Reihenfolge · `__slots__`
entsprechend · frozen · hashbar · alle neun Werte verbatim · für jedes der vier
neuen Felder einzeln nachgewiesen, dass es **weder** `default` **noch**
`default_factory` besitzt und sein Weglassen einen `TypeError` auslöst.

**Token-Endpunkt und JWKS-URI, über beide Felder parametrisiert:** gültige URL
mit Pfad · gültiger expliziter Port · exakte Bewahrung · vierzehn Ablehnungen
je Feld (leer, HTTP, relativ, schemalos, ohne Host, drei Userinfo-Varianten
inklusive leerer, Query, leerer `?`, Fragment, leerer `#`, nicht numerischer
Port, Port 65536) · fünf Whitespace-/Steuerzeichenvarianten einschließlich eines
Zeilenumbruchs **im Host** · Fehlertext beginnt mit dem Feldnamen und enthält
weder Rohwert, Hostnamen, Portwert noch Query-Inhalt.

**Nicht abgeleitet:** beide Werte auf drei verschiedenen Hosts bleiben exakt,
Issuer und Authorization Endpoint bleiben unberührt; ein blanker Issuer erhält
niemals einen Token- oder JWKS-Pfad.

**Algorithmen:** Reihenfolge exakt · nicht sortiert · nichts automatisch
ergänzt · elf Ablehnungen (leeres Tupel, Liste, String statt Tupel, zwei
Nicht-String-Varianten, leerer String, vier Whitespace-Varianten, Duplikat) ·
`none` in sechs Schreibweisen abgewiesen, auch als einziger Eintrag ·
`none-like` und `NONEXISTENT` bleiben zulässig · `rs256` bleibt exakt erhalten.

**Clock-Skew:** sechs akzeptierte Werte inklusive `0` und exakt fünf Minuten ·
Sub-Sekunden nicht gerundet · drei negative abgewiesen · fünf zu große
abgewiesen, darunter fünf Minuten plus eine Mikrosekunde · sechs
Nicht-`timedelta`-Werte abgewiesen.

**Strukturgrenzen:** zusätzlich `private_key`, `signing_key`, `jwks`, `keys`,
`provider`, `provider_name` als nicht vorhanden belegt · `jwks_uri` ist
nachweislich eine URL und kein Schlüsselmaterial.

Jede der vier neuen Validierungen wurde per **Gegenprobe** abgesichert: Wird
sie entfernt, scheitern die zugehörigen Tests (40, 8, 5 beziehungsweise 3
Fehlschläge). Tests bleiben eng auf dieses Modell begrenzt; es gibt **keine**
globalen AST-, Import- oder Substring-Verbote.

## Bewusst nicht enthalten

- kein Verifikationsport, kein Adapter, kein Tokenaustausch,
- kein HTTP-Client, kein JWKS-Download, kein Cache,
- keine Signatur- oder Claimprüfung, keine OIDC-/OAuth-/JOSE-Bibliothek,
- kein Callback-Transportvertrag, keine Callback-Route,
- keine Identity-Auflösung, keine Admission-Verarbeitung, keine
  Session-Erzeugung,
- keine Persistenz oder Migration,
- kein Client-Secret und kein privater Schlüssel,
- kein Discovery-Vertrag, kein eingebettetes Schlüsselset, kein Multi-Issuer,
- kein Production-Wiring,
- keine CORS-, Deployment-, CI-, Container-, Dependency- oder Grype-Änderung,
- keine Änderung an bestehenden Ports, Adaptern, Anwendungsfällen oder der
  LQ-154-Route.

## Nächster Schritt

Mit dieser Konfigurationsgrenze ist die Vorbedingung aus LQ-155 §5 erfüllt. Es
folgt der **Verifikationsport**: Eingabe nach LQ-155 §3 (Authorization Code plus
`expected_issuer`, `expected_nonce`, `code_verifier`, `redirect_uri`), Ergebnis
nach §9 (ausschließlich `ExternalIdentity`), Fehlerform nach §12. Danach der
Callback-Transportvertrag und erst zuletzt die Callback-Route.
