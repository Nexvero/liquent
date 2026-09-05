# LQ-209 — Authorized Workspace Membership Mutation

## Ergebnis

LQ-209 implementiert die reguläre persistente Grenze zur autorisierten Anlage,
vollständigen Änderung, Deaktivierung und Reaktivierung einer
Workspace-Membership samt expliziter Research-Permissions.

Aktuelle Foundation und dedizierte workspacebezogene Management-Authority,
erwartete Vorgängerrevision, neue unveränderliche Revision, aktueller
Membership-Snapshot und persistente Change-Entscheidung werden in genau einer
Datenbanktransaktion geordnet.

Der Slice ergänzt keine Migration, Route, CLI, Settings-Option oder
Operator-Authentisierung. Er nutzt ausschließlich die LQ-207-Foundation.

## Vollständige Eingabe

Der neue `AuthorizedWorkspaceMembershipChangeStore` erhält:

- stabile interne `WorkspaceMembershipChangeId`,
- authentifizierten `SessionPrincipal`,
- interne Ziel-UserId,
- internen Ziel-Workspace,
- erwartete Revision oder `None`,
- `MembershipStatus.ACTIVE` oder `INACTIVE`,
- vollständige explizite `frozenset[Permission]`.

Es gibt keinen Rollennamen, Allow-Boolean, Capability-Namen, partiellen Patch,
Grant-/Revoke-Befehl oder Merge mit dem aktuellen Bestand.

Die Erstanlage verlangt `expected_revision=None` und vollständige Abwesenheit
einer Membership für genau dieses Zielpaar.

Jede Folgeänderung verlangt eine typisierte erwartete Revision. Sie muss exakt
der aktuell am Membership-Datensatz gebundenen Revision entsprechen.

Eine vorhandene revisionslose Legacy-Membership kann weder als Erstanlage noch
als Folgeänderung übernommen werden. Sie endet neutral fail-closed und erhält
keine erfundene Historie.

## Snapshot-Invarianten

Eine aktive Membership kann null, eine oder beide expliziten Research-
Permissions tragen.

Eine aktive Membership ohne Permission ist ein gültiger Snapshot, der keinen
Research-Zugriff gewährt.

`research:write` wird nicht persistent um `research:read` ergänzt. Die
bestehende reine Policy bleibt allein für Write-impliziert-Read zuständig.

Eine inaktive Membership muss eine leere Permission-Menge tragen. Jede
Deaktivierung entfernt alle aktuellen Permission-Zeilen in derselben
Transaktion.

Reaktivierung ist eine neue vollständige Änderung und muss alle künftig
gewünschten Permissions erneut nennen. Frühere Rechte leben nicht automatisch
wieder auf.

Falsch typisierte Status-/Permission-Eingaben und inaktive Snapshots mit
Permissions werden vor jeder Schreibwirkung detailfrei technisch abgewiesen.

## Aktuelle Authority

`SessionPrincipal` identifiziert ausschließlich den Actor.

Für jede neue Änderung löst der Adapter aus dem System of Record auf:

- aktiven Actor,
- aktiven Zielnutzer,
- aktiven Zielworkspace,
- aktive dedizierte Membership-Management-Authority des Actors für exakt
  diesen Workspace.

Onboarding-Management, gewöhnliche Membership, Research-Permissions und
globale OIDC-Trust-Authority werden nicht ausgewertet und können die dedizierte
Capability nicht ersetzen.

Unbekannt, inaktiv, fehlend und entzogen ergeben dasselbe neutrale `None` und
verursachen weder Generatorziehung noch Schreibwirkung.

Eine Authority in Workspace A erlaubt keine Mutation in Workspace B.

## Neue unveränderliche Revision

Jede erfolgreiche neue Änderung erzeugt genau eine interne
`WorkspaceMembershipRevisionId` über den injizierten sicheren Generator.

Die historische Revision speichert unverändert:

- Ziel-UserId,
- WorkspaceId,
- Membership-Status,
- vollständige explizite Permission-Menge.

Auch ein neuer Vorgang mit fachlich identischen Werten erhält eine neue
Revision. Revisionen werden nicht aus Inhalt, IDs, Zeit oder Hash abgeleitet.

Historische Revisionen und ihre Permission-Zeilen werden bei späteren
Änderungen nicht aktualisiert oder gelöscht.

Die neue Revision wird gemeinsam mit Status und aktuellen Permissions an die
operative `workspace_memberships`-Zeile gebunden. Der bestehende LQ-195-Lookup
sieht nach Commit den vollständigen neuen Zustand.

## Change-Entscheidung und exakter Retry

Jede erfolgreiche Änderung speichert in
`authorized_workspace_membership_changes`:

- Change-ID,
- Actor-UserId,
- Ziel-UserId,
- WorkspaceId,
- erwartete Vorgängerrevision oder `NULL`,
- erzeugte Ergebnisrevision.

Eine exakte technische Wiederholung derselben Change-ID rekonstruiert Status
und vollständige Permissions aus der unveränderlichen Ergebnisrevision.

Der Retry erzeugt keine zweite Revision und prüft aktuelle Authority oder
Foundation nicht erneut. Ein unklarer Commit-Ausgang bleibt daher auch nach
späterem Authority-Entzug auflösbar.

Dieselbe Change-ID mit anderem Actor, Ziel, Workspace, erwarteter Revision,
Status oder Permission-Menge erzeugt den detailfreien
`WorkspaceMembershipChangeConflict`.

Eine fachlich abgelehnte neue Änderung wird nicht als Entscheidung gespeichert.

## Atomare Schreibordnung

Für eine neue Änderung liegen in derselben Transaktion:

1. Prüfung des vorhandenen Change-Inventars;
2. aktuelle Actor-, Zielnutzer- und Workspace-Auflösung;
3. aktuelle dedizierte Authority-Auflösung;
4. Prüfung von Membership-Abwesenheit oder exakter Vorgängerrevision;
5. Anlage der unveränderlichen Revision und historischen Permissions;
6. vollständige Umschaltung der aktuellen Membership und Permissions;
7. Speicherung der unveränderlichen Change-Entscheidung.

Ein Fehler rollt Revision, historische Permissions, aktuelle Membership,
aktuelle Permissions und Change-Entscheidung gemeinsam zurück.

Es gibt keinen Check-then-act über mehrere Transaktionen, In-Process-Lock,
Authority-Cache oder automatischen Retry.

## Konkurrenz

PostgreSQL sperrt Change-, Membership-, Permission- und Revisionsinventare in
fester Reihenfolge. Actor, Zielnutzer, Workspace und Authority werden
anschließend mit Zeilensperren gebunden.

Gleichzeitige neue Änderungen erhalten eine sichtbare Reihenfolge. Eine stale
erwartete Revision verliert neutral und überschreibt keinen neueren Zustand.

Eine konkurrierende exakte Wiederholung liest nach dem Warten die committete
Entscheidung erneut und konvergiert auf dieselbe Revision.

SQLite belegt sequenzielle Fach-, Retry- und Rollback-Semantik. PostgreSQL
bleibt die normative Konkurrenzgrenze.

## Wirkung von Deaktivierung und Entzug

Membership-Deaktivierung entfernt alle aktuellen Permission-Fakten. Der nächste
LQ-195-Lookup liefert einen inaktiven Snapshot mit leerer Permission-Menge, den
die bestehende Policy fail-closed verweigert.

Permission-Änderung und Membership-Status wirken auf jede spätere Research-
Autorisierung. SessionPrincipal und Browser-Session speichern keine Rechte.

Actor-, Zielnutzer-, Workspace- oder Authority-Deaktivierung sperrt jede danach
neu begonnene Änderung.

Bereits committete historische Revisionen, Change-Entscheidungen und
technische Retries werden durch späteren Entzug nicht umgeschrieben.

## Ablehnung, Konflikt und technische Fehler

Neutrales `None` umfasst ohne Detailunterscheidung:

- unbekannte oder inaktive Foundation,
- fehlende oder entzogene dedizierte Authority,
- vorhandene Membership bei versuchter Erstanlage,
- fehlende, revisionslose oder abweichende aktuelle Revision.

Wiederverwendung einer Change-ID mit anderem Inhalt bleibt ein eigener
detailfreier Konflikt.

Ungültige Eingabeform, falsches Generatormaterial, beschädigte Persistenz sowie
Datenbank-, Constraint-, Encoding-, Decoding- oder Transaktionsfehler werden
als detailfreie `WorkspaceMembershipChangeStoreUnavailable` gemeldet.

Exceptions und Adapter-`repr` enthalten weder Actor, Ziel, Workspace, Status,
Permission, Revision, Change-ID, SQL, Tabelle, Constraint, Host, Port noch DSN.
`BaseException` bleibt ungefangen.

## Tests

Die SQLite-Tests belegen:

- strukturelle Erfüllung des neuen Ports,
- autorisierte Erstanlage mit vollständigem aktuellen und historischen Snapshot,
- exakten Retry nach Authority-Entzug ohne zweite Generatorziehung,
- Konflikt bei verändertem Snapshot,
- neutrale stale Revision und erfolgreiche exakte Folgeänderung,
- Deaktivierung mit Löschung aktueller Permissions und Erhalt der Historie,
- fail-closed fehlende Authority und revisionslose Legacy-Membership,
- technische Ablehnung inaktiver Snapshots mit Permissions,
- vollständigen Rollback bei Generatorfehler,
- detailfreie Nichtverfügbarkeit bei fehlendem Schema.

Der markierte PostgreSQL-Test startet zwei identische konkurrierende
Erstanlagen. Beide konvergieren auf genau eine Revision und eine
Change-Entscheidung.

## Bewusst nicht enthalten

- keine reguläre Membership-Management-Authority-Vergabe oder -Recovery,
- keine Bootstrap- oder reguläre Operatorgrenze,
- keine Legacy-Adoption,
- keine Route, CLI, Settings- oder Startup-Ausführung,
- keine Nutzer-, Workspace-, Onboarding- oder OIDC-Trust-Mutation,
- keine Einladung, Rolle, Gruppe, Team oder Organisation,
- kein Deployment und kein finaler LQ-177-Abschluss.

## Nächster Schritt

LQ-210 sollte LQ-208 und LQ-209 über eine kontrollierte Offline-
Operatorgrenze erreichbar machen. Stabile Change-IDs müssen vor Anwendung
bewahrt werden; Bootstrap, Authority und Membership-Änderung bleiben getrennte
Operationen ohne HTTP- oder Startup-Pfad.
