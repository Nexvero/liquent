# LQ-197 — OIDC Process Runtime Contract

## Ergebnis

LQ-197 macht die sichere OIDC-Composition aus LQ-194 für den realen Control-
Plane-Prozess konfigurierbar. `PlatformSettings` definiert eine vollständige
opt-in Gruppe von Betriebswerten; `transport.http.main.build_app` erzeugt bei
vollständiger Gruppe genau einen ausgehenden HTTP-Client und aktiviert damit
Login-Start und Callback.

Ohne die gesamte Gruppe bleibt OIDC geschlossen. Eine teilweise Gruppe
verhindert den Prozessstart. Es gibt keine Library-Defaults für Policy, Origin,
Lifetimes oder Callback-Ziele.

## Atomare Settings-Gruppe

Die Prozesskonfiguration enthält elf Werte:

- vertrauenswürdiger Login-Origin,
- Login-Transaktions-Lifetime in Sekunden,
- Browser-Session-Lifetime in Sekunden,
- internes Callback-Rejection-Ziel,
- internes Callback-Unavailable-Ziel,
- Connect-, Read- und Total-Timeout in Sekunden,
- maximale Token-Response-Größe in Bytes,
- maximale JWKS-Response-Größe in Bytes,
- JWKS-Cache-TTL in Sekunden.

Jeder numerische Wert muss mindestens eins sein. Connect- und Read-Timeout
dürfen den Total-Timeout nicht überschreiten. Sind manche, aber nicht alle
Werte gesetzt, schlägt `PlatformSettings` mit einer wertfreien
Konfigurationsmeldung fehl.

Die Gruppe ist optional, nicht teilweise. `oidc_enabled` ist nur dann wahr,
wenn alle elf Werte vorhanden und validiert sind. Die öffentliche
Settings-Zusammenfassung enthält ausschließlich dieses Boolean als
`"true"`/`"false"`, niemals Origin, Ziele, Limits oder Datenbankwerte.

## Zweistufige Validierung

`PlatformSettings` validiert Vollständigkeit und numerische Beziehungen vor
dem App-Aufbau. Der Process-Entrypoint konstruiert anschließend die bestehenden
Domänenobjekte:

- `OidcVerificationPolicy` für technische Grenzen;
- `ValidatedInternalDestination` für beide Callback-Ziele;
- `timedelta` für Login-, Session-, Netzwerk- und Cache-Laufzeiten.

Die vorhandene `create_app`-Grenze validiert zusätzlich den exakten HTTPS-
Origin und ihre All-or-nothing-Dependency-Gates. Ungültige Pfade, Origins oder
Composition-Kombinationen scheitern daher vor dem Prozessstart, ohne Werte in
Fehlertexte zu übernehmen.

Die persistente `TrustedOidcClientConfiguration` bleibt getrennt im System of
Record. Issuer, Client-ID, Endpoints, Scopes und Algorithmen werden nicht über
Process-Environment oder Browserwerte eingespeist.

## HTTP-Client und Netzwerkgrenze

Der Entrypoint erzeugt bei aktivierter Gruppe genau einen synchronen
`httpx2.Client`. Token Exchange und JWKS Retrieval teilen dieses Objekt über
LQ-193/LQ-194.

Der Client wird mit `trust_env=False` aufgebaut. Proxy-, Zertifikats- oder
Credential-Umgebungsvariablen werden dadurch nicht stillschweigend als
Provider-Routing oder Authentisierung übernommen. `follow_redirects=False`
ist zusätzlich bereits am Client festgelegt; die einzelnen OIDC-Adapter
erzwingen dieselbe Regel weiterhin pro Request.

Es gibt keinen Request beim Client-Aufbau. Token- und JWKS-I/O beginnen erst
nach aktuellem persistentem Trust-Lookup und den bestehenden frühen
Verifikationsprüfungen.

## Ownership und Fehlerpfade

Der Process-Entrypoint übergibt den erzeugten Client mit explizitem App-Besitz
an `create_app`. Der App-Lifespan schließt ihn beim Shutdown genau über diese
Ownership-Entscheidung. Ein von Tests oder anderer Composition injizierter
Client bleibt standardmäßig extern besessen und wird nicht geschlossen.

Scheitert `create_app` nach der Client-Erzeugung, schließt `build_app` den
Client sofort und reicht den ursprünglichen Fehler unverändert weiter. Dabei
wird bewusst auch `BaseException` berücksichtigt: Kein abgebrochener
Factory-Aufbau darf den bereits erzeugten Netzwerkressourcenbesitz verlieren.

Beim normalen Lifespan-Shutdown wird zuerst der App-eigene OIDC-Client
geschlossen und die App-eigene Datenbank-Engine anschließend in einem
`finally` disposed. Ein Client-Close-Fehler darf den Datenbank-Pool daher nicht
liegen lassen.

## Runtime-Beispiel

`operations/compose/runtime.env.example` listet die vollständige Gruppe. Der
Beispiel-Origin verwendet die reservierte `.invalid`-Domain und ist kein
behaupteter Produktionsprovider. Ein Operator muss die gesamte Gruppe bewusst
für die reale öffentliche App-Grenze festlegen.

Die Beispielwerte sind keine Trust-Konfiguration: Sie aktivieren weder Issuer
noch Client. Eine leere oder inaktive persistente LQ-192-Konfiguration lässt
Login weiterhin neutral und ohne Netzwerkzugriff scheitern.

## Tests

Die LQ-197-Tests beweisen:

- vollständig abwesende Settings halten OIDC geschlossen;
- vollständige Settings aktivieren OIDC und erscheinen nur als Boolean in der
  öffentlichen Zusammenfassung;
- Teilgruppen und ungültige Timeout-/Größenbeziehungen scheitern vor App-Bau;
- der reale Entrypoint registriert mit vollständiger Gruppe beide OIDC-Routen;
- der App-Lifespan schließt den Process-eigenen Client;
- ein Factory-Fehler schließt den Client sofort;
- der Client wird ohne Environment-Inheritance und Redirect-Following erzeugt;
- das Runtime-Beispiel enthält jedes Feld der atomaren Gruppe.

## Bewusst nicht enthalten

- keine persistente OIDC-Konfigurationsmutation oder Trust-Aktivierung,
- kein Client Secret, privater Schlüssel oder Secret-Management-Slice,
- keine Discovery, Multi-Issuer- oder browsergesteuerte Providerwahl,
- keine Membership- oder Permission-Mutation,
- keine neue Route oder Änderung der bestehenden HTTP-Antwortverträge,
- kein Deployment und keine Behauptung betriebsbereiter OIDC-Werte.

## Folge für LQ-177

Der Process-Konfigurations- und HTTP-Client-Lifecycle-Blocker aus dem
LQ-177-Abschlussaudit ist behoben. LQ-177 bleibt nur wegen der fehlenden
unterstützten Control-Plane-Mutationen für aktive OIDC-Konfiguration sowie
reguläre Memberships und Research-Permissions teilweise blockiert.

Der nächste Slice sollte eine autorisierte, persistente OIDC-Trust-
Verwaltungsgrenze definieren. Membership-/Permission-Verwaltung folgt getrennt;
keine der beiden darf aus Environment, Login oder Bootstrap abgeleitet werden.
