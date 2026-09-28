# LQ-199 — Persistent OIDC Trust Authority and Revision Foundation

## Ergebnis

LQ-199 implementiert die erste Persistenzgrundlage aus LQ-198: eine eigene
systemweite OIDC-Trust-Management-Authority, stabile interne IDs für
Trust-Revision und Änderungsentscheidung sowie einen unveränderlichen
historischen Revisionsbestand.

Der Slice bleibt read-only. Er erzeugt weder die erste Authority noch eine
Revision und aktiviert, rotiert oder deaktiviert keine OIDC-Konfiguration.

## Stabile interne Identitäten

`OidcTrustRevisionId` identifiziert genau einen unveränderlichen Satz aller
neun `TrustedOidcClientConfiguration`-Werte. `OidcTrustChangeId` identifiziert
genau eine spätere technische Trust-Änderungsentscheidung.

Beide Typen sind frozen, slotted und repr-frei. Sie akzeptieren ausschließlich
einen nichtleeren exakten String. Sie enthalten keinen Issuer, Client-ID,
Zeitstempel, Hash, Provider- oder Workspacewert und treffen selbst keine
Authority- oder Trust-Entscheidung.

Der bestehende `SecureIdentityAuthorityMaterialGenerator` erzeugt beide IDs
über unabhängige Betriebssystem-Zufallsziehungen mit mindestens 32 Byte
Entropie. Es gibt keine Ableitung voneinander oder aus Konfigurationswerten.

## Systemweite Authority

Der neue `OidcTrustManagementAuthorityLookup` besitzt genau eine Operation:

```python
permits_oidc_trust_management(principal) -> bool
```

Die Signatur nimmt nur den bereits authentifizierten `SessionPrincipal`.
Workspace, Issuer, Provider, Revision, Konfiguration, Rolle, Capability-Name
und Allow-Boolean können strukturell nicht übergeben werden.

`DatabaseOidcTrustManagementAuthority` löst den Actor und dessen dedizierte
globale Authority gemeinsam aus dem System of Record auf. Actor und Authority
müssen aktuell aktiv sein. Unbekannt, inaktiv, fehlend und entzogen ergeben
dasselbe neutrale `False`.

Jeder Aufruf liest neu. Ein committierter Actor- oder Authority-Entzug sperrt
die nächste Entscheidung ohne Cache, Session-Snapshot oder In-Process-Lock.
`SessionPrincipal` identifiziert nur und trägt weiterhin keine Capability.

## Additive Persistenz

Revision `20260812_0009` ergänzt zwei leere Tabellen.

`oidc_trust_management_authorities` bindet genau einen vorhandenen internen
UserId an active/inactive. Der Primärschlüssel verhindert mehrere Bedeutungen
derselben Zuordnung; der Foreign Key bindet an die dauerhafte Nutzer-Fakt aus
LQ-184.

`oidc_trust_revisions` speichert unter einem nichtleeren, nicht
wiederverwendbaren `revision_id` alle neun Konfigurationswerte:

- Issuer und Authorization Endpoint,
- Client-ID, Redirect-URI und Scopes,
- Token Endpoint und JWKS URI,
- erlaubte Signaturalgorithmen und Clock Skew.

Die Revisionstabelle besitzt keinen active-Status und keine Update-Semantik.
Aktivierung gehört zur späteren atomaren Management-Entscheidung, nicht zum
historischen Revisionsobjekt. Der Clock Skew behält die bestehende Grenze von
null bis fünf Minuten.

Die Migration erzeugt keine Authority, Revision, Konfiguration oder
Änderungsentscheidung. Eine frisch migrierte Installation bleibt vollständig
geschlossen.

## Strikte Trennung bestehender Authorities

Die globale Authority wird weder in `workspace_onboarding_management` noch in
`workspace_memberships` oder deren Research-Permissions gespeichert.

Kein Bootstrap-Nutzer, Workspace-Admin, Research-Writer, Admission-Ziel,
Identity-Binding oder eingeloggter Nutzer erhält durch LQ-199 globale
Trust-Authority. Umgekehrt verleiht die neue Zuordnung keine Membership,
Research-Permission oder Onboarding-Management-Capability.

Diese Trennung ist auch im Port sichtbar: Der Lookup besitzt keinen Workspace-
Parameter. Eine globale Fähigkeit kann deshalb nicht versehentlich an den vom
Browser behaupteten oder an einen beliebigen Workspace gebunden werden.

## Neutralität und technische Fehler

`False` bedeutet ausschließlich, dass der Actor jetzt nicht als aktiver
OIDC-Trust-Manager bestätigt werden kann. Es verrät nicht, ob Nutzer oder
Authority existieren oder welchen historischen Status sie besitzen.

Fehlende Migration, Datenbank-, Transaktions-, Encoding- oder Strukturfehler
werden nicht als `False` getarnt. Sie verlassen den Adapter als detailfreie
`OidcTrustAuthorityStoreUnavailable` ohne Cause oder Context.

Exception und Adapter-`repr` enthalten weder UserId, Status, Capability,
Issuer, Revision, SQL, Tabelle, Constraint, Host, Port noch DSN.

## Noch keine Revisionsumschaltung

Der bestehende LQ-192-Singleton bleibt in diesem Slice unverändert. Ihm wird
noch keine erfundene Revision zugeordnet und der bestehende Lookup ändert seine
Signatur nicht.

Eine Migration, die einen vorhandenen aktiven Singleton ohne autorisierte
Änderungsentscheidung einer neuen Revision zuordnet, würde historischen Trust
erfinden. Eine sofort verpflichtende Revision ohne Bootstrap würde dagegen
jeden bestehenden Login technisch brechen. Beides bleibt ausgeschlossen.

Die spätere Umschaltgrenze muss Revisionsanlage, aktive Auswahl und persistente
Änderungsentscheidung atomar verbinden. Erst danach kann die Login-Transaktion
die aktuelle Revision sicher speichern.

## Tests

Die SQLite-Tests beweisen:

- unveränderliche repr-freie Revision- und Change-IDs,
- Ablehnung leerer und falsch typisierter Identifikatoren,
- unabhängige sichere Materialziehungen,
- strukturelle Erfüllung des neuen Authority-Ports,
- erlaubte Entscheidung nur bei aktivem Actor und aktiver Authority,
- fail-closed Abwesenheit, Actor-Inaktivität und Authority-Entzug,
- Wirkung committierten Entzugs auf den nächsten Lookup,
- detailfreie technische Nichtverfügbarkeit,
- leere Foundation nach Migration.

Der markierte PostgreSQL-Test belegt zusätzlich die Sichtbarkeit eines
committierten Authority-Entzugs in einer späteren Entscheidung. PostgreSQL
bleibt die normative Runtime.

## Bewusst nicht enthalten

- kein Authority-Bootstrap und keine reguläre Authority-Mutation,
- keine Trust-Aktivierung, Rotation oder Deaktivierung,
- keine persistente Change-Decision-Tabelle,
- keine Änderung am LQ-192-Singleton oder dessen Lookup-Port,
- keine revisionsgebundene Login-Transaktion oder Callback-Prüfung,
- keine Route, CLI, Operator-Credentials oder Environment-Authority,
- keine Discovery, Multi-Issuer-Unterstützung oder Client Secrets,
- keine Membership-/Permission-Verwaltung und kein Deployment.

## Nächster Schritt

LQ-200 sollte die einmalige Offline-Bootstrap-Grenze für die erste globale
OIDC-Trust-Authority implementieren. Sie muss zustandsbasiert dauerhaft
schließen, genau einen bereits vorhandenen aktiven internen Nutzer autorisieren
und darf weder Trust-Revision noch OIDC-Konfiguration aktivieren. Danach folgt
die revisionsgebundene Login-/Callback-Grundlage vor jeder regulären Mutation.
