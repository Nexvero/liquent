# LQ-207 — Persistent Membership Management Foundation

## Ergebnis

LQ-207 implementiert die erste Persistenzgrundlage aus LQ-206:

- eine eigene workspacebezogene Membership-Management-Authority,
- stabile interne IDs für Membership-Revisionen und Change-Entscheidungen,
- unveränderliche historische Membership-Snapshots,
- leere persistente Change-Entscheidungen,
- eine nullable Bindung der aktuellen Membership an eine Revision.

Der Slice bleibt read-only. Er erzeugt keine Authority, Membership, Permission,
Revision oder Change-Entscheidung und mutiert keinen vorhandenen fachlichen
Membership-Zustand.

## Stabile interne Identitäten

`WorkspaceMembershipRevisionId` identifiziert genau einen vollständigen
historischen Membership-Snapshot.

`WorkspaceMembershipChangeId` identifiziert genau eine spätere persistente
technische Änderungsentscheidung.

Beide Typen sind frozen, slotted und repr-frei. Sie akzeptieren ausschließlich
einen nichtleeren exakten String und enthalten weder UserId, WorkspaceId,
Status, Permission, Rolle, Zeit noch Hash.

Der bestehende `SecureIdentityAuthorityMaterialGenerator` erzeugt beide IDs
über getrennte Betriebssystem-Zufallsziehungen mit mindestens 32 Byte Entropie.
Es gibt keine Ableitung voneinander oder aus Membership-Inhalt.

Eine ID autorisiert nichts und ist kein öffentlicher Idempotency-Key.

## Dedizierter Authority-Port

`WorkspaceMembershipManagementAuthorityLookup` besitzt genau eine Operation:

```python
permits_workspace_membership_management(principal, workspace_id) -> bool
```

Die Signatur nimmt ausschließlich einen authentifizierten
`SessionPrincipal` und den exakt zu verwaltenden internen Workspace.

Sie akzeptiert keinen Zielnutzer, Membership-Status, Permission-Satz,
Rollennamen, Capability-Namen oder Allow-Boolean. Die Authority-Entscheidung
kann daher nicht durch den gewünschten Änderungsinhalt gesteuert werden.

`SessionPrincipal` identifiziert nur den Actor. Der persistente Adapter löst
Actor, Workspace und dedizierte Capability gemeinsam aus dem System of Record
auf.

Actor, Workspace und Authority müssen aktuell aktiv sein. Unbekannt, inaktiv,
fehlend und entzogen ergeben dasselbe neutrale `False`.

## Strikte Capability-Trennung

Die Authority wird ausschließlich aus
`workspace_membership_management_authorities` gelesen.

Folgende Tatsachen werden weder gejoint noch als Ersatz ausgewertet:

- `workspace_onboarding_management`,
- `workspace_memberships`,
- `workspace_membership_permissions`,
- globale OIDC-Trust-Management-Authority,
- Admission, Identity-Bindung oder Sessionbestand.

Ein Actor mit aktiver Onboarding-Authority und `research:write` bleibt ohne die
neue dedizierte Capability neutral nicht autorisiert.

Umgekehrt erzeugt oder verleiht die neue Authority keine gewöhnliche
Membership, Research-Permission oder Onboarding-Fähigkeit.

## Aktuelle Auflösung und Entzug

Jeder Lookup liest die persistenten Foundation-Fakten neu. Es gibt keinen
Cache, Session-Snapshot oder In-Process-Lock.

Ein committierter Entzug der Authority oder die Deaktivierung von Actor oder
Workspace sperrt den nächsten Lookup.

Der read-only Port entscheidet noch keine konkrete Membership-Änderung. Der
spätere Mutationsadapter muss dieselben Foundation- und Authority-Fakten in
seiner eigenen atomaren Schreibtransaktion erneut binden; ein vorheriger
positiver Lookup darf nicht als langlebige Freigabe verwendet werden.

## Additive Migration

Migration `20260812_0012` ergänzt vier leere Inventare und eine nullable
Spalte.

`workspace_membership_management_authorities` bindet eine interne Actor-UserId
an genau einen Workspace und `active`/`inactive`.

Der zusammengesetzte Primärschlüssel verhindert mehrere Bedeutungen derselben
Zuordnung. Foreign Keys binden an bestehende dauerhafte Nutzer- und Workspace-
Fakten.

`workspace_membership_revisions` speichert unveränderlich:

- Revision-ID,
- Ziel-UserId,
- WorkspaceId,
- `active` oder `inactive`.

`workspace_membership_revision_permissions` speichert null bis zwei explizite
Research-Permissions für genau diese Revision. Doppelte und unbekannte
Permissions werden durch Schlüssel und Constraints verhindert.

Die Foundation speichert keine Rolle und keine abgeleitete Read-Permission.
Eine Write-Zeile bleibt exakt `research:write`.

`authorized_workspace_membership_changes` bindet künftig eine Change-ID an:

- Actor-UserId,
- Ziel-UserId,
- WorkspaceId,
- optionale erwartete Vorgängerrevision,
- verpflichtende Ergebnisrevision.

Die Tabelle enthält noch keine Entscheidung und implementiert keine Mutation.
Ihr Inhalt wird erst vom späteren atomaren Anwendungsfall geschrieben.

## Aktuelle Membership-Bindung

`workspace_memberships` erhält eine nullable `revision_id` mit Foreign Key auf
den unveränderlichen historischen Bestand.

Die Spalte ist nullable, damit die additive Migration bestehende read-only
Membership-Zeilen nicht einer erfundenen Revision zuordnet.

Eine neue Installation bleibt vollständig leer. Die Migration erzeugt weder
Revision noch aktuelle Membership und setzt keinen Default.

Der bestehende LQ-195-Lookup liest Status und Permissions weiterhin
unverändert. LQ-207 ändert keine aktuelle Research-Autorisierungsentscheidung.

Die spätere reguläre Mutationsgrenze muss revisionslose Memberships fail-closed
behandeln oder über eine separat entschiedene kontrollierte Adoption führen.
Sie darf beim ersten Schreiben keine historische Vorgängerrevision erfinden.

## Historische Unveränderlichkeit

Revisionstabellen besitzen keinen active-Status und keine Update-Semantik für
ihren Snapshot.

Eine spätere Membership-Deaktivierung erzeugt eine neue inaktive Revision;
alte aktive Revisionen und ihre Permission-Fakten bleiben historisch
unverändert.

Das Schema kann die LQ-206-Regel „inaktive Revision hat keine Permissions“
nicht mit einem einfachen tabellenübergreifenden Check Constraint beweisen.
Diese Invariante bleibt verbindlich und muss von der späteren atomaren
Schreibgrenze innerhalb derselben Transaktion erzwungen und getestet werden.

Physisches Löschen, Restore oder Reimport darf Revisionen und Change-IDs nicht
unter neuer Bedeutung wiederverwenden.

## Neutralität und technische Fehler

`False` bedeutet nur, dass der Actor für diesen Workspace jetzt nicht als
aktiver Membership-Manager bestätigt werden kann.

Fehlende Migration, Datenbank-, Encoding-, Decoding- oder Strukturfehler werden
nicht als `False` getarnt. Sie verlassen den Adapter als detailfreie
`WorkspaceMembershipManagementAuthorityUnavailable` ohne Cause oder Context.

Exception und Adapter-`repr` enthalten weder Actor, Workspace, Status,
Permission, Capability, Revision, Change-ID, SQL, Tabelle, Constraint, Host,
Port noch DSN.

## Tests

Die SQLite-Tests beweisen:

- unveränderliche repr-freie Revision- und Change-IDs,
- Ablehnung leerer und falsch typisierter Identifikatoren,
- getrennte sichere Materialziehungen,
- strukturelle Erfüllung des neuen Authority-Ports,
- positive Entscheidung nur für aktiven Actor, Workspace und Authority,
- fail-closed Abwesenheit, Inaktivität und falschen Workspace,
- keine Substitution durch Onboarding-Authority oder Research-Permissions,
- Wirkung committierten Authority-Entzugs auf den nächsten Lookup,
- detailfreie technische Nichtverfügbarkeit,
- leere Foundation nach Migration,
- keine automatische Revision für bestehende Membership-Zeilen.

Der markierte PostgreSQL-Test belegt zusätzlich die Sichtbarkeit eines
committierten Authority-Entzugs auf dem normativen Persistenzsystem.

## Bewusst nicht enthalten

- kein Bootstrap der ersten Membership-Management-Authority,
- keine reguläre Authority-Vergabe, -Deaktivierung oder Recovery,
- keine Membership- oder Permission-Mutation,
- keine Revision- oder Change-Entscheidungsanlage,
- keine Legacy-Adoption,
- keine Route, CLI, Settings- oder Startup-Ausführung,
- keine Änderung an Research-, Session-, OIDC- oder Onboarding-Wiring,
- kein Deployment und keine Shared-Environment-Freigabe.

## Nächster Schritt

LQ-208 sollte die einmalige kontrollierte Offline-Bootstrap-Grenze für die
erste Membership-Management-Authority implementieren. Sie muss einen bereits
vorhandenen aktiven Nutzer und Workspace exakt binden, zustandsbasiert dauerhaft
schließen und darf weder Membership noch Permission oder Revision erzeugen.
