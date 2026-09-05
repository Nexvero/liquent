# LQ-195 — Persistent Workspace Membership and Research Capabilities

## Ergebnis

LQ-195 implementiert den bestehenden `WorkspaceMembershipLookup` persistent.
Der Adapter löst für genau einen internen Nutzer und genau einen Workspace den
aktuellen Membership-Status und die explizit gespeicherten Research-
Permissions auf.

Der Slice ergänzt ausschließlich eine additive Migration, einen read-only
Adapter und Tests. Er erzeugt, verändert, deaktiviert oder löscht keine
Membership und keine Permission und öffnet noch keine Research-Route
automatisch.

## Bestehender Vertrag bleibt maßgeblich

Der Port behält seine Signatur unverändert:

```python
get_membership(user_id, workspace_id) -> WorkspaceMembership | None
```

Beide IDs sind erforderlich. Es gibt keine Abfrage nur nach Nutzer oder nur
nach Workspace, kein Listing, keine Suche und keinen caller-supplied Allow-
Boolean oder Rollennamen.

Die Rückgabe ist weiterhin der bestehende unveränderliche Snapshot aus
`UserId`, `WorkspaceId`, `MembershipStatus` und `frozenset[Permission]`.
Die reine Policy aus LQ-087 bleibt allein für die Entscheidung zuständig:
`research:write` impliziert `research:read`, nicht umgekehrt.

## Persistente Form

Revision `20260812_0008` ergänzt zwei Tabellen:

- `workspace_memberships` bindet Nutzer, Workspace und active/inactive;
- `workspace_membership_permissions` bindet null bis zwei explizite Research-
  Permissions an genau diese Membership.

Die Membership hat den zusammengesetzten Primärschlüssel aus UserId und
WorkspaceId und verweist auf die persistenten Foundation-Fakten aus LQ-184.
Permission-Zeilen verweisen mit demselben zusammengesetzten Schlüssel auf ihre
Membership. Ihr Primärschlüssel verhindert doppelte Permissions.

Schema-Constraints erlauben ausschließlich `active`/`inactive` sowie
`research:read`/`research:write`. Die Migration erzeugt keinerlei Membership,
Permission oder Seed-Daten und verändert keine bestehende Tabelle.

Die normalisierte Form speichert keine Rolle und keine abgeleitete Permission.
Eine reine `research:write`-Zeile bleibt genau eine Write-Permission; erst die
bestehende Autorisierungspolicy leitet daraus Lesbarkeit ab.

## Fail-closed Foundation-Auflösung

Ein Lookup bindet die angefragten IDs serverseitig an genau dieselben
persistenten Nutzer- und Workspace-Fakten wie die Membership. Nutzer und
Workspace müssen aktuell aktiv sein.

Unbekannter oder inaktiver Nutzer, unbekannter oder inaktiver Workspace und
fehlende Membership ergeben dasselbe neutrale `None`. Der Adapter verrät nicht,
welche dieser Tatsachen fehlt oder inaktiv ist.

Eine vorhandene inaktive Membership wird als inaktiver Snapshot geliefert.
Dadurch bleibt der Port seinem bestehenden Datenvertrag treu; die bestehende
Policy verweigert unabhängig von enthaltenen Permission-Zeilen fail-closed.

Eine aktive Membership ohne Permission ist ein gültiger sichtbarer Snapshot
mit leerem `frozenset`. Sie gewährt weder Lesen noch Schreiben.

## Aktuelle Entscheidung und Entzug

Jeder Lookup liest Membership, Foundation-Status und Permissions neu in einer
Datenbankabfrage. Es gibt keinen Cache, In-Process-Lock oder langlebigen
Authority-Snapshot.

Eine committete Deaktivierung von Nutzer, Workspace oder Membership und ein
committierter Permission-Entzug wirken daher auf jede spätere Entscheidung.
Bereits abgeschlossene Research-Aktionen werden nicht rückwirkend verändert;
jede neue Read- oder Start-Autorisierung löst den aktuellen Zustand erneut auf.

Die Session identifiziert weiterhin nur den Akteur. Sie speichert keine
Membership und keine Permission und friert keine Autorität bis zum Sessionende
ein.

## Trennung von Onboarding-Management

Workspace-Membership und Research-Permissions bleiben strikt getrennt von der
workspacebezogenen Onboarding-Management-Capability aus LQ-184.

Keine der folgenden Tatsachen erzeugt in diesem Slice eine Membership oder
Research-Permission:

- Bootstrap-Nutzer oder Bootstrap-Workspace,
- Onboarding-Management-Capability,
- autorisierte Onboarding-Entscheidung,
- Admission oder deren Konsum,
- externe Identitätsbindung,
- erfolgreiche OIDC-Anmeldung oder Browser-Session.

Umgekehrt verleiht eine Research-Membership keine Onboarding-Management-
Capability. `research:write` ist keine Administrationsrolle.

## Neutrale Abwesenheit und technische Nichtverfügbarkeit

`None` bedeutet ausschließlich, dass für das angefragte Paar jetzt keine
autorisierbare Foundation-gebundene Membership sichtbar ist. Es enthält keine
Detailursache und keinen Hinweis auf frühere Zustände.

Fehlende Migration, Datenbank- oder Transaktionsfehler und gespeicherte Werte,
die nicht als bestehender Status oder bestehende Permission rekonstruierbar
sind, werden nicht zu `None`. Sie verlassen den Adapter als detailfreie
`WorkspaceMembershipStoreUnavailable` ohne Cause oder Context.

Die Ausnahme und der konstante Adapter-`repr` enthalten weder UserId,
WorkspaceId, Permission, SQL, Tabellen-, Constraint-, Treiber-, Host-, Port-
noch DSN-Informationen.

## Tests

Die SQLite-Tests beweisen:

- strukturelle Erfüllung des bestehenden Ports,
- exakte Rekonstruktion beider Permissions als unveränderliche Menge,
- aktive Membership ohne Permission und deren fail-closed Policy-Ergebnis,
- unveränderte Write-impliziert-Read-Regel,
- neutrale Abwesenheit für unbekannte und inaktive Foundation-Fakten,
- sichtbaren, aber nicht autorisierenden inactive-Snapshot,
- Wirkung eines späteren Permission-Entzugs ohne Cache,
- detailfreie technische Nichtverfügbarkeit bei fehlender Migration.

Der markierte PostgreSQL-Test beweist zusätzlich, dass ein committierter
Permission-Entzug von einer späteren Autorisierungsentscheidung gesehen wird.
PostgreSQL bleibt die normative Runtime; SQLite beweist Migration und portable
read-only Semantik.

## Bewusst nicht enthalten

- keine Membership- oder Permission-Creation, Mutation oder Löschgrenze,
- keine Rollen, Teams, Gruppen, Organisationen oder generische Policy Engine,
- keine Einladung und keine automatische Membership aus Admission oder Login,
- keine Audit- oder Historientabelle und keine zeitbasierte Permission,
- kein HTTP-, CLI-, Operator- oder Bootstrap-Zugang,
- kein automatisches `create_app`-Wiring der Research-Routen,
- keine Änderung an Session-, CSRF-, OIDC- oder Onboarding-Verträgen,
- kein Deployment und keine Freigabe eines Shared Environments.

## Nächster Schritt

LQ-196 kann persistente Sessions und diesen Membership-Lookup kontrolliert an
die bestehenden Research-Read- und Research-Start-Grenzen binden. Dabei müssen
explizite Testabhängigkeiten Vorrang behalten, unvollständige Kombinationen
fail-fast scheitern und der lokale nicht autorisierte Entwicklungsmodus darf
nicht versehentlich als Production-Fallback bestehen bleiben. Eine spätere
Membership-Mutationsgrenze bleibt davon getrennt und weiterhin erforderlich.
