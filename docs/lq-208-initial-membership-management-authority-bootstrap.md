# LQ-208 — Initial Membership Management Authority Bootstrap

## Ergebnis

LQ-208 implementiert die einmalige Offline-Bootstrap-Grenze für die erste
dedizierte Membership-Management-Authority eines bestehenden Workspace.

Sie bindet genau einen bereits vorhandenen aktiven internen Nutzer an genau
einen bereits vorhandenen aktiven Workspace und legt dort die erste aktive
Authority-Tatsache an.

Der Slice ergänzt keine Migration, Route, CLI, Settings-Option oder automatische
Startup-Ausführung. Er erzeugt keine Membership, Research-Permission, Revision
oder Change-Entscheidung.

## Neuer Bootstrap-Port

`InitialWorkspaceMembershipManagementAuthorityBootstrap` besitzt genau eine
Operation:

```python
bootstrap(user_id, workspace_id)
```

Beide Parameter sind typisierte interne Foundation-IDs. Die Grenze nimmt
keinen Actor, `SessionPrincipal`, Membership-Status, Permission-Satz,
Rollennamen, Capability-Namen oder Allow-Boolean entgegen.

Sie ist eine Offline-Control-Plane-Fähigkeit und kein regulärer
authentifizierter Runtime-Anwendungsfall. Die Zielwerte autorisieren sich nicht
selbst und werden innerhalb der Transaktion erneut an das System of Record
gebunden.

Der erfolgreiche Rückgabewert
`BootstrappedWorkspaceMembershipManagementAuthority` enthält nur die bestätigte
interne UserId und WorkspaceId. Er ist kein übertragbarer Authority-Token und
keine Session.

## Aktive bestehende Foundation

Bootstrap ist nur zulässig, wenn Zielnutzer und Zielworkspace bereits
persistent existieren und aktuell aktiv sind.

Unbekannter oder inaktiver Nutzer sowie unbekannter oder inaktiver Workspace
ergeben dasselbe neutrale `None`. Es wird keine Authority reserviert, kein Ziel
erzeugt und keine Foundation-Tatsache reaktiviert.

Onboarding-Management, gewöhnliche Membership, Research-Permissions und globale
OIDC-Trust-Authority sind weder Voraussetzung noch Ersatz für die neue
dedizierte Capability.

## Workspacebezogene einmalige Schließung

Die Bootstrap-Grenze ist für genau einen Workspace geöffnet, solange in
`workspace_membership_management_authorities` keine einzige Authority-Tatsache
für diesen Workspace existiert.

Bereits eine aktive oder inaktive Authority schließt diesen Workspace-Scope
dauerhaft. Deaktivierung, Entzug, Restore, Reimport oder Verlust des initialen
Managers öffnen ihn nicht wieder.

Bei geschlossenem Scope liefert jeder spätere Versuch neutral `None`. Die
vorhandene Authority wird niemals überschrieben, übertragen oder reaktiviert.

Ein anderer aktiver Workspace ohne eigene Authority-Historie besitzt einen
eigenen einmaligen Bootstrap-Scope. Diese Entscheidung ist notwendig, weil die
Capability workspacebezogen ist und ein Manager in Workspace A keine Authority
für Workspace B besitzt.

Es gibt kein globales „erster Workspace gewinnt“-Flag und keinen
Environment-Zähler.

## Atomarität

In genau einer Datenbanktransaktion werden geordnet:

1. Sperre der Nutzer-, Workspace- und Authority-Inventare;
2. Prüfung, dass der Zielworkspace noch keine Authority-Historie besitzt;
3. Bestätigung des aktiven Zielnutzers;
4. Bestätigung des aktiven Zielworkspace;
5. Anlage der aktiven dedizierten Authority.

Alles committet oder nichts. Es gibt keinen Check-then-act über getrennte
Transaktionen, In-Process-Lock oder automatischen Retry.

PostgreSQL sperrt die drei Tabellen in fester Reihenfolge und serialisiert
gleichzeitige Versuche für denselben Workspace. Genau ein Versuch kann die
erste Authority anlegen; jeder später geordnete sieht Bestand und liefert
`None`.

SQLite belegt ausschließlich sequenzielle Fach- und Rollback-Semantik.
PostgreSQL bleibt die normative Konkurrenzgrenze.

## Keine Membership als Nebenwirkung

Der Bootstrap schreibt ausschließlich eine aktive Zeile in
`workspace_membership_management_authorities`.

Insbesondere bleiben unverändert oder leer:

- `workspace_memberships`,
- `workspace_membership_permissions`,
- `workspace_membership_revisions`,
- `workspace_membership_revision_permissions`,
- `authorized_workspace_membership_changes`,
- Onboarding- und OIDC-Trust-Authorities.

Der initiale Manager kann deshalb später Memberships verwalten, besitzt aber
durch Bootstrap selbst keine Research-Berechtigung und keine gewöhnliche
Membership.

## Dauerhafter Entzug und Recovery

LQ-208 implementiert keine Deaktivierung, Übertragung, zweite Authority oder
Recovery. Die zustandsbasierte Schließung darf für diese Fälle nicht erneut
verwendet werden.

Reguläre Authority-Vergabe, Entzug und Recovery benötigen eine eigene spätere
Lifecycle-Grenze mit eigener aktueller Autorisierung und stabiler
Änderungsentscheidung.

Eine verlorene initiale Authority führt daher nicht zu Re-Bootstrap. Das ist
fail-closed und verhindert eine Übernahme durch den nächsten Offline-Aufruf.

## Neutralität und technische Fehler

Geschlossener Workspace-Scope sowie unbekannte oder inaktive Foundation-Fakten
sind neutrale fachliche Ergebnisse. Die Antwort unterscheidet diese Gründe
nicht.

Ungültige Identifier-Repräsentation, fehlendes Schema, unbekannter Dialekt sowie
Datenbank-, Transaktions-, Constraint- oder Commitfehler werden als detailfreie
`WorkspaceMembershipManagementBootstrapUnavailable` gemeldet.

Die Exception verlässt die Grenze ohne Cause oder Context. Sie und der
konstante Adapter-`repr` enthalten weder UserId, WorkspaceId, Status,
Capability, Membership, Permission, SQL, Tabelle, Constraint, Host, Port noch
DSN. `BaseException` bleibt ungefangen.

## Tests

Die SQLite-Tests beweisen:

- strukturelle Erfüllung des neuen Bootstrap-Ports,
- Anlage für aktiven vorhandenen Nutzer und Workspace,
- neutrales Ergebnis für unbekannte und inaktive Foundation-Fakten,
- dauerhafte workspacebezogene Schließung auch nach Authority-Deaktivierung,
- unabhängigen Bootstrap-Scope eines anderen leeren Workspace,
- keine Membership-, Permission-, Revision- oder Change-Nebenwirkung,
- detailfreie technische Nichtverfügbarkeit bei ungültiger ID und fehlendem
  Schema.

Der markierte PostgreSQL-Test startet zwei echte konkurrierende Versuche für
denselben Workspace. Exakt einer gewinnt; der andere endet neutral, und genau
eine Authority-Tatsache entsteht.

## Bewusst nicht enthalten

- keine Migration oder Schemaänderung,
- keine reguläre Authority-Vergabe, -Deaktivierung, -Übertragung oder Recovery,
- keine Membership- oder Permission-Mutation,
- keine Revision oder Change-Entscheidung,
- keine Route, CLI, Operator-Authentisierung oder Startup-Ausführung,
- kein Environment-Allow, Seed, Force-, Reset- oder Reopen-Flag,
- kein Deployment oder Shared-Environment-Abschluss.

## Nächster Schritt

LQ-209 sollte die atomare autorisierte Membership-Mutation aus LQ-206
implementieren: vollständiger gewünschter Snapshot, exakte erwartete Revision,
aktuelle dedizierte Authority, unveränderliche neue Revision und idempotente
Change-Entscheidung in einer persistenten Schreibordnung.
