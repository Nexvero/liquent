# LQ-193 — Controlled OIDC Verifier Composition

## Ergebnis

LQ-193 komponiert die persistente aktive OIDC-Konfiguration aus LQ-192 mit den
bereits abgeschlossenen Bausteinen für Authorization-Code-Austausch, begrenzte
JWKS-Abfrage, Single-Slot-JWKS-Cache und ID-Token-Verifikation.

Die Composition ist intern und transportfrei. Sie ergänzt keine Kryptografie,
keinen JOSE-Parser, keine Discovery, keine Route und kein automatisches
`create_app`-Wiring.

## Signatur

```python
compose_oidc_verifier(
    engine,
    client,
    policy,
    *,
    now=None,
    monotonic=None,
) -> OidcVerifierComposition
```

Die drei Pflichtabhängigkeiten sind eine bereits erzeugte Datenbank-Engine, ein
bereits erzeugter synchroner `httpx2.Client` und eine vollständig validierte
`OidcVerificationPolicy`. Tests können beide Uhren explizit injizieren.

Die Rückgabe stellt genau zwei Fähigkeiten bereit:

- `configurations`: den aktuellen persistenten parameterlosen Lookup;
- `verifier`: den zusammengesetzten `OidcAuthorizationCodeVerifier`.

Token-Endpoint-Client, JWKS-Loader und Cache bleiben interne Mitarbeiter des
Verifiers. Die Composition fügt keine Netzwerk-, Cache-, Schlüssel- oder
Konfigurationsinspektion hinzu.

## Ressourcen-Ownership

Engine und HTTP-Client bleiben Eigentum der äußeren Process-Composition.
LQ-193 erzeugt keinen zweiten Pool, liest keine DSN, erzeugt keinen weiteren
HTTP-Client und ruft weder `dispose()` noch `close()` auf.

Der Aufbau ist vollständig seiteneffektfrei: keine Datenbankabfrage, kein
Token-Request, kein JWKS-Request, keine Discovery und kein Clock-Read. I/O
beginnt erst, wenn eine bestehende Anwendungsgrenze den Verifier aufruft.

Ein gemeinsamer HTTP-Client bedient Token Endpoint und JWKS Endpoint. Das
ändert deren bestehende Schutzverträge nicht: kein Redirect, kein Retry,
begrenzte Antworten und Laufzeiten; der JWKS-Request entfernt geerbte Cookie-
und Authorization-Header weiterhin explizit.

## Policy und Uhren

Dieselbe unveränderliche `OidcVerificationPolicy` wird unverändert an
Token-Endpoint-Client, JWKS-Loader und JWKS-Cache gegeben. Die Composition
erfindet keine Default-Limits und überschreibt keine Timeout-, Größen- oder
TTL-Entscheidung.

Die Wall Clock entscheidet ausschließlich ID-Token-Zeitclaims. Standard ist
aware UTC aus `datetime.now(UTC)`. Die Monotonic Clock begrenzt Netzwerkdauer
und Cache-Frische; Standard ist `time.monotonic`.

Browser-, Provider-, Token-, Claim- oder Datenbankzeit wird nicht als Uhr
übernommen. Beide Uhren bleiben getrennt, weil Kalenderzeit und technische
Dauer unterschiedliche Sicherheitsfragen beantworten.

## Aktueller Trust

Der `ComposedOidcAuthorizationCodeVerifier` erhält exakt den persistenten
LQ-192-Lookup. Bei jeder Codeverifikation liest er die aktive Konfiguration
neu. Leer oder inaktiv ergibt die bestehende neutrale Ablehnung, ohne Token-
oder JWKS-Netzwerkzugriff und ohne Clock-Read.

Der gespeicherte `expected_issuer` der bereits beanspruchten Login-Transaktion
muss bytegenau zum aktuell aktiven Issuer passen. Eine Rotation oder
Deaktivierung nach Login-Start sperrt den Callback deshalb fail-closed, bevor
der Authorization Code extern präsentiert wird.

Für einen einzelnen Verifier-Aufruf wird genau das einmal gelesene
Konfigurationsobjekt durch Token Exchange, JWKS Cache und ID-Token-Prüfung
gereicht. Eine parallele Rotation kann somit keine Endpoints, Schlüsselquelle,
Client-ID oder Issuer aus unterschiedlichen Konfigurationen vermischen.

## Fehlergrenze

Neutrale Ablehnungen bleiben `None`: keine aktive Konfiguration,
Issuer-Mismatch, abgelehnter Code oder nicht verifizierbares Token werden nach
außen nicht unterschieden.

Konfigurations-, Datenbank-, Netzwerk-, Clock-, Cache-, Parser-, Bibliotheks-
oder Kryptografiefehler werden an der bestehenden Verifier-Grenze einheitlich
zu detailfreier `OidcVerificationUnavailable`. Kein ursprünglicher Fehlertext,
Cause oder Context verlässt sie. Es gibt keinen automatischen Retry: Die
Login-Transaktion wurde vor dem Verifier bereits atomar beansprucht.

`OidcVerifierComposition()` ist ein konstanter wertfreier `repr`. Engine,
Client, Policy, URLs, Issuer, Client-ID, Schlüssel und Uhren erscheinen nicht.

## Tests

Die fokussierten Tests belegen:

- genau einen persistenten Lookup und einen gemeinsamen externen HTTP-Client;
- identische Policy- und Clock-Objekte in allen zuständigen Bausteinen;
- keinen I/O und keinen Ressourcenabschluss beim Aufbau;
- neutrale frühe Ablehnung bei leerer oder inaktiver Konfiguration;
- Issuer-Mismatch vor Netzwerk und Wall Clock;
- detailfreie technische Nichtverfügbarkeit bei defekter Persistenz;
- strukturelle Zusammensetzung ohne neue Port- oder Signaturänderung.

## Bewusst nicht enthalten

- keine Migration oder Änderung am LQ-192-Schema,
- keine OIDC-Konfigurationsmutation, kein Seed und kein Operatorzugang,
- keine Client Secrets, private Schlüssel oder Client-Assertion,
- keine Discovery, Multi-Issuer-Registry oder Providerwahl,
- keine Route, Cookie-, Origin-, Redirect- oder Callback-Antwortentscheidung,
- keine automatische Verdrahtung in `create_app`,
- keine Admission-, Identity-Binding-, Session- oder Membership-Änderung,
- kein Deployment und keine Environment-Konfiguration.

## Nächster Schritt

LQ-194 kann diese Composition kontrolliert in die bestehenden OIDC-Start- und
Callback-Abhängigkeiten von `create_app` einbinden. Das darf nur mit vollständig
expliziter Verification-Policy, äußerem HTTP-Client und den bereits
persistent komponierten Login-/Session-Stores geschehen. Geschützte
Research-Routen bleiben weiterhin geschlossen, bis reguläre persistente
Membership-Auflösung separat implementiert ist.
