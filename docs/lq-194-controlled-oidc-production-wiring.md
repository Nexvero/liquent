# LQ-194 — Controlled OIDC Production Wiring

## Ergebnis

LQ-194 bindet die persistenten Identity-, Login-, Session- und OIDC-Trust-
Bausteine kontrolliert an die bereits bestehenden Login-Start- und Callback-
Routen von `create_app`.

Die Verdrahtung ist opt-in. Eine Datenbank allein aktiviert weiterhin nur das
bereits vorhandene persistente Logout. OIDC wird erst aktiviert, wenn ein
äußerer synchroner HTTP-Client, eine explizite Verification-Policy und alle
transportbezogenen Betriebsentscheidungen gemeinsam vorliegen.

## Neue Composition-Eingaben

`create_app` akzeptiert additiv:

- `oidc_http_client`: extern besessener synchroner `httpx2.Client`;
- `oidc_verification_policy`: vollständig validierte technische Grenzen;
- `oidc_monotonic_clock`: optional injizierbare technische Testuhr.

Die drei Werte sind keine Browser-, Request- oder Providerparameter. Client und
Policy müssen gemeinsam mit einer App-Datenbank vorliegen. Eine monotone Uhr
allein gilt ebenfalls als unvollständiger Auto-Wiring-Versuch und scheitert
beim Factory-Aufbau.

## Vollständige Aktivierung

Automatisches OIDC-Wiring verlangt zusätzlich die bereits vorhandenen
transportbezogenen Entscheidungen:

- Login-Transaktions-Lifetime von mindestens einer ganzen Sekunde,
- exakt validierten vertrauenswürdigen HTTPS-Origin,
- Session-Lifetime von mindestens einer ganzen Sekunde,
- validiertes neutrales Rejection-Ziel,
- validiertes neutrales Unavailable-Ziel.

Die Wall Clock kann weiterhin explizit injiziert werden; sonst verwendet die
Composition aware UTC. Kein Host-, Forwarded-, Query-, Cookie- oder Body-Wert
liefert eine dieser Entscheidungen.

Fehlt ein Teil, wird die App nicht gebaut. Es entsteht keine halb aktive
Login- oder Callback-Route und kein Fallback auf geschätzte Limits, Ziele oder
Origins.

## Gemeinsam verdrahtete Persistenz

Bei vollständiger Aktivierung entstehen um genau dieselbe App-Engine:

- der aktuelle persistente OIDC-Konfigurations-Lookup aus LQ-192,
- persistente Login-Transaction-Creation und -Claim aus LQ-189,
- der kontrollierte Verifier aus LQ-193,
- persistentes Identity-Lookup und Admission-Consumption,
- persistente Session-Creation aus LQ-190,
- getrennte sichere Generatoren für OIDC-State/Nonce/PKCE und Session/CSRF.

Login-Start und Callback teilen denselben Transaction-Store. Identity-Lookup
und Admission-Consumption teilen denselben persistenten Adapter. Callback-
Session-Creation und das bereits verdrahtete Logout greifen auf dieselbe
Sessiontabelle und dieselbe Engine zu.

Die Trennung der Materialgeneratoren ist absichtlich: OIDC-State, Nonce und
PKCE-Verifier werden nicht aus Session-ID oder CSRF-Token abgeleitet und
umgekehrt.

## Kein Mischbetrieb

Sobald das automatische Wiring angefordert wird, dürfen seine verwalteten
Ports nicht gleichzeitig explizit injiziert sein. Das betrifft Konfiguration,
beide Transaction-Ports, beide Materialgeneratoren, Verifier, Identity-Lookup,
Admission-Store und Session-Creation.

Die Factory verweigert einen solchen Mischbetrieb, statt beispielsweise den
Login-Start an eine andere Trust- oder Transaction-Quelle als den Callback zu
binden. Der bestehende vollständig explizite Modus ohne Auto-Wiring bleibt für
isolierte Tests und bewusst manuelle Composition unverändert verfügbar.

## Ownership und Lifecycle

Eine injizierte Engine bleibt extern besessen. Eine aus `database_url`
erzeugte Engine bleibt App-eigen und wird wie bisher beim Lifespan-Ende
disposed. Die Auto-Wiring-Pflichtwerte werden geprüft, bevor eine solche Engine
erzeugt wird, sodass ein Factory-Konfigurationsfehler keinen App-eigenen Pool
außerhalb des Lifespans zurücklässt.

Der HTTP-Client ist immer extern besessen. Die Factory erzeugt keinen zweiten
Client und schließt den übergebenen Client auch beim App-Shutdown nicht. Token-
und JWKS-Zugriff verwenden dasselbe Objekt; die bestehenden Redirect-, Retry-,
Credential-, Größen- und Timeout-Grenzen bleiben maßgeblich.

Der Factory-Aufbau führt keinen Datenbank-Lookup und keinen OIDC-Netzwerkzugriff
aus. Eine leere oder inaktive persistente OIDC-Konfiguration lässt die Routen
zwar vorhanden, aber Login-Start endet neutral und ohne Providerzugriff. Damit
bleibt Deployment von Trust-Aktivierung getrennt.

## Fehler- und Antwortsemantik

Factory-Konfigurationsfehler sind detailfreie `ValueError` mit Feldgruppen-
statt Wertangaben. Kein DSN, Origin, Ziel, Issuer oder Client-Inhalt erscheint
in der Meldung.

Zur Laufzeit bleiben die bestehenden Routenverträge unverändert:

- Login-Start ohne aktive Konfiguration antwortet leer und `no-store` mit 503;
- Callback-Ablehnung und technische Nichtverfügbarkeit bleiben getrennte,
  vorab validierte interne Redirect-Ziele;
- nach Browser-Bindung wird die Login-Transaktion genau einmal beansprucht;
- weder Verifier noch Route wiederholen Code Exchange oder Claim;
- Session- und OIDC-State-Cookies behalten ihre bestehenden Sicherheitsregeln.

## Tests

Die LQ-194-Tests beweisen:

- vollständige Composition aktiviert Login- und Callback-Route,
- Aufbau verursacht weder Netzwerkzugriff noch Ressourcenabschluss,
- injizierte Engine und HTTP-Client bleiben nach App-Lifespan verwendbar,
- leerer Trust ergibt neutralen 503 ohne Providerzugriff,
- Client, Policy und monotone Uhr scheitern einzeln fail-fast,
- automatisches und explizites managed Wiring können nicht gemischt werden.

Die bestehenden Login-Start-, Callback- und LQ-177-Logout-Suiten laufen
unverändert weiter und belegen die Rückwärtskompatibilität des expliziten
Dependency-Modus.

## Bewusst nicht enthalten

- keine OIDC-Konfigurationsmutation, kein Seed, CLI oder Operator-Endpunkt,
- keine Client Secrets, private Schlüssel oder Secret-Management-Entscheidung,
- keine Discovery, Multi-Issuer- oder browsergesteuerte Providerwahl,
- keine neue Route und keine Änderung an Callback- oder Cookie-Verträgen,
- kein Bootstrap- oder Onboarding-Transport,
- keine automatische Research-Autorisierung,
- kein Deployment und keine konkreten Produktionswerte für Policy oder Ziele.

## Nächster Schritt

OIDC-Start und Callback besitzen nun eine sichere persistente Production-
Composition. Der nächste getrennte Slice sollte reguläre persistente Workspace-
Membership und Research-Capability-Auflösung implementieren. Erst danach dürfen
die geschützten Research-Routen automatisch an persistente Sessions und
Autorisierung gebunden und LQ-177 vollständig abgeschlossen werden.
