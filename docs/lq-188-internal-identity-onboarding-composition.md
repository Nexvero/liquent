# LQ-188 — Interne Identity-Onboarding-Composition

## 1. Ziel und Grenze

Dieser Adapter-Composition-Slice verdrahtet die mit LQ-184 bis LQ-187
implementierte interne Identity-Onboarding-Kette zu einer kontrollierten
Composition. Sie umfasst den
einmaligen Bootstrap, die persistente autorisierte Entscheidung und die
retry-sichere Admission-Provisionierung.

Die Composition ist keine öffentliche Schnittstelle. Sie ergänzt keine Route,
CLI, Session, Membership, Research-Permission oder Transportabbildung und wird
nicht automatisch beim Prozessstart ausgeführt.

## 2. Engine-Eigentümerschaft

`compose_identity_onboarding` erhält eine bereits erzeugte SQLAlchemy-Engine.
Die Composition erzeugt keine zweite Engine, liest keine DSN und schließt die
injizierte Engine niemals. Erstellung und Disposal bleiben bei der äußeren
Process-Composition, die bereits den Datenbank-Lifecycle besitzt.

Dadurch verwenden Bootstrap, Decision-Store und Admission-Provisionierung exakt
dasselbe normative Persistenzsystem, ohne konkurrierende Connection-Pools oder
verdeckte Zugangsdaten einzuführen.

## 3. Sichere interne Identifikatoren

`SecureIdentityAuthorityMaterialGenerator` zieht jeden Identifier unabhängig
über `secrets.token_urlsafe` aus Betriebssystem-Zufall. Die Mindestentropie ist
32 Byte pro Ziehung. Schwächere, boolesche oder nicht-ganzzahlige Konfiguration
wird verworfen.

Getrennte Ziehungen erzeugen:

- `UserId` für den ersten Bootstrap-Nutzer;
- `WorkspaceId` für den ersten Bootstrap-Workspace;
- `OnboardingDecisionId` für einen neuen internen Vorgang;
- `ProvisioningRequestId` innerhalb der autorisierten Entscheidung;
- `IdentityAdmissionId` innerhalb der Admission-Provisionierung.

Kein Identifier wird aus E-Mail, OIDC-Claim, Subject, Anzeigename, Zeit,
Workspace, Nutzer oder einem anderen Identifier abgeleitet. Der Generator
normalisiert nichts und führt bei Kollision keinen eigenen Retry aus.

## 4. Zusammengesetzte Fähigkeiten

`IdentityOnboardingComposition` stellt intern genau bereit:

1. `bootstrap` als argumentlose, zustandsbasiert einmalige LQ-185-Grenze;
2. `onboarding` als LQ-187-Workflow über LQ-186 und LQ-181;
3. `new_decision_id()` für die vor dem ersten Versuch stabil anzulegende
   interne Wiederholungsidentität.

Die Composition gewährt selbst keine Authority. Eine erzeugte Decision-ID ist
kein Capability-Handle. Der Onboarding-Workflow verlangt weiterhin einen
authentifizierten `SessionPrincipal` und intern kontrollierte Ziele; Authority
und aktive Foundation-Fakten werden aus der Datenbank entschieden.

## 5. Zeit und Lifetime

Der Admission-Adapter erhält eine injizierte aware-UTC-Serveruhr. Ohne explizite
Testuhr verwendet die Composition `datetime.now(UTC)`. Browser-, Request-,
Token- oder Claim-Zeit wird nicht akzeptiert.

Die positive Admission-Lifetime ist eine explizite vertrauenswürdige
Composition-Policy. Sie wird einmal an den LQ-187-Workflow gebunden und steht
nicht als variabler Parameter einzelner Onboarding-Aufrufe zur Verfügung.
Ungültige Lifetime stoppt die Composition ohne Identifier-Ziehung oder
Datenbankzugriff.

## 6. Geheimnis- und Fehlergrenze

Generator und Composition besitzen konstante wertfreie `repr`. Engine, Uhr,
Lifetime, Identifier und Adapter werden darin nicht sichtbar. Die Composition
loggt nichts, erzeugt keine Metriklabels und fängt keine fachlichen oder
technischen Fehler ihrer Fähigkeiten ab.

Damit bleiben die bestehenden neutralen Ablehnungen, Konflikte und
detailfreien technischen Fehler aus LQ-181 sowie LQ-184 bis LQ-187 unverändert.
Es gibt keinen Composition-seitigen Retry und keinen Ersatzgenerator.

## 7. Nicht enthalten

Keine Migration oder Tabelle. Keine reguläre Nutzer-, Workspace-, Membership-,
Rollen- oder Capability-Mutation. Kein HTTP-Endpunkt, Admin-Header,
Environment-Bootstrap, Migration-Seed, Self-Sign-up, First-login-Provisioning,
OIDC-Callback, Session-Wiring oder automatischer Startup-Aufruf.

Eine spätere Operator- oder Transport-Grenze muss separat entscheiden, wie der
Operator authentisiert wird, wie intern kontrollierte Ziele entstehen und wie
eine Decision-ID vor dem ersten Versuch dauerhaft gehalten wird. Sie darf die
internen Stores nicht direkt öffentlich machen.

## 8. Nachweis und Folgeordnung

Unit-Tests beweisen unabhängige sichere Ziehungen, Mindestentropie,
Composition-Struktur, feste Lifetime, wertfreie Repräsentation und fehlende
Engine-Eigentümerschaft. Der markierte PostgreSQL-Test führt die komponierte
Kette vom leeren Bestand über Bootstrap und autorisierte Entscheidung bis zur
persistenten Admission auf dem normativen Runtime-Pfad aus.

Als nächste Slices bleiben persistente Login-Transaktionen und Sessions, bevor
LQ-177 Production-Wiring wieder aufgenommen werden kann. Eine Operator-Grenze
für Bootstrap oder reguläres Onboarding benötigt weiterhin einen eigenen
Sicherheitsvertrag und ist keine implizite Folge dieser Composition.
