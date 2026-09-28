# LQ-220 — Persistent User and Workspace Lifecycle Foundation

## Ergebnis

LQ-220 implementiert die additive persistente Foundation aus LQ-219.

Der Slice ergänzt:

- getrennte globale User- und Workspace-Lifecycle-Authorities;
- stabile IDs für beide vollständigen Lifecycle-Revisionen;
- stabile IDs für beide Change-Entscheidungen;
- unveränderliche vollständige Nutzer- und Workspace-Snapshots;
- je einen eindeutigen Current-Pointer;
- leere persistente Change-Entscheidungsbestände;
- zwei aktuelle read-only Authority-Lookups.

Die Foundation startet vollständig leer. Sie führt weder Bootstrap noch
Verankerung oder reguläre Lifecycle-Mutation aus.

## Stabile interne IDs

`UserLifecycleRevisionId` und `WorkspaceLifecycleRevisionId` identifizieren je
einen unveränderlichen vollständigen Statusbestand.

`UserLifecycleChangeId` und `WorkspaceLifecycleChangeId` identifizieren je
eine spätere persistente Lifecycle-Entscheidung.

Alle vier Typen sind frozen, slotted und repr-frei. Sie akzeptieren nur einen
nichtleeren exakten String und enthalten keine Person, Rolle, Authority,
Statusentscheidung oder Workspace-Auswahl.

Der bestehende sichere Materialgenerator erzeugt alle vier IDs über getrennte
Zufallsziehungen mit mindestens 32 Byte Entropie. Keine ID wird aus einer
anderen ID, einem Zeitstempel oder einem fachlichen Wert abgeleitet.

## Getrennte globale Authorities

Die Migration ergänzt `user_lifecycle_management_authorities` und
`workspace_lifecycle_management_authorities`.

Jede Tabelle bindet genau eine bestehende interne `UserId` an den Status aktiv
oder inaktiv. Die Tabellen sind weder Rollen- noch Membership-Tabellen und
besitzen keinen Workspace-Schlüssel.

Es gibt keine gegenseitige Implikation und keine Ableitung aus:

- `SessionPrincipal` oder Browser-Session;
- Workspace-Onboarding-Management;
- Membership-Management oder gewöhnlicher Membership;
- Research-Permissions;
- OIDC-Trust-Management;
- Datenbank- oder Prozesszugriff.

Die Migration erzeugt keine Authority-Zeile und wertet keinen vorhandenen
Bootstrap-Nutzer automatisch auf.

## Aktuelle Authority-Auflösung

`UserLifecycleManagementAuthorityLookup` und
`WorkspaceLifecycleManagementAuthorityLookup` nehmen jeweils ausschließlich
einen `SessionPrincipal` entgegen.

Der Principal identifiziert nur den Actor. Es können weder Rolle, Allow-Wert,
Zielnutzer, Zielworkspace noch Authority-Snapshot übergeben werden.

Die beiden Datenbankadapter lesen bei jedem Aufruf den aktuellen Nutzerstatus
und ausschließlich die passende dedizierte Authority-Tabelle.

Nur aktiver Actor und aktive passende Authority ergeben `True`. Unbekannter
oder inaktiver Actor sowie fehlende oder inaktive Authority ergeben neutral
`False`.

Ein committierter Entzug wirkt deshalb auf den nächsten Lookup. Es gibt keinen
Cache und keine Fortgeltung aus einer früheren Sessionentscheidung.

## Vollständige Nutzerrevisionen

`user_lifecycle_revisions` hält nur die stabile Identität eines vollständigen
historischen Snapshots.

`user_lifecycle_revision_members` bindet darin jeden enthaltenen historischen
Nutzer an genau einen aktiven oder inaktiven Status. Nutzerreferenzen zeigen
auf die dauerhaften Foundation-Fakten und werden nicht als freie Strings
dupliziert.

`user_lifecycle_current_revision` ist ein Singleton-Pointer auf genau eine
Revision. Eine leere Foundation besitzt noch keinen Pointer.

Die Tabellen enthalten keine Update-, Delete-, Cascade-Deaktivierungs- oder
automatische Snapshot-Erzeugungslogik.

## Vollständige Workspace-Revisionen

`workspace_lifecycle_revisions` hält die stabile Identität eines vollständigen
historischen Workspace-Snapshots.

`workspace_lifecycle_revision_members` bindet jeden enthaltenen Workspace an
genau einen aktiven oder inaktiven Status und referenziert den dauerhaften
Workspace-Fakt.

`workspace_lifecycle_current_revision` ist ein eigener Singleton-Pointer. Er
ist vollständig von der Nutzerrevision und allen Authority-Set-Revisionen
getrennt.

Eine Migration erfindet weder aktuelle Revision noch Historie für bestehende
Workspaces.

## Vorbereitete Change-Entscheidungen

`user_lifecycle_changes` reserviert persistente immutable Entscheidungen für
`create`, `deactivate` und `reactivate`.

Jede Zeile bindet stabile Change-ID, Actor, Zielnutzer, erwartete Revision und
resultierende Revision. Erwartete und resultierende Revision sind immer
vorhanden; die reguläre Grenze kann daher keinen revisionslosen Start
vortäuschen.

`workspace_lifecycle_changes` reserviert ausschließlich `create` und
`deactivate`. Eine Reaktivierungsform ist strukturell ausgeschlossen.

Workspace-Create verlangt genau einen referenzierten ersten Onboarding-
Manager. Workspace-Deactivate verbietet diesen Wert. Damit kann eine spätere
Mutation weder einen managerlosen Workspace anlegen noch bei Deaktivierung
eine neue Authority einschleusen.

Die Foreign Keys binden Actor, Ziel und ersten Manager an interne Foundation-
Fakten. Sie ersetzen nicht die spätere transaktionale Prüfung auf aktuellen
Status und Authority.

## Leerer Start und bestehende Installationen

Revision `20260813_0014` ist vollständig additiv und erzeugt keine fachlichen
Zeilen.

Insbesondere entstehen keine:

- Lifecycle-Authority;
- Nutzer- oder Workspace-Revision;
- Current-Pointer;
- Change-Entscheidung;
- neue UserId oder WorkspaceId;
- Membership, Permission oder Onboarding-Authority.

Vorhandene Nutzer und Workspaces werden nicht stillschweigend verankert. Der
bestehende initiale Bootstrap bleibt geschlossen.

Eine spätere kontrollierte Bootstrap-Erweiterung beziehungsweise Verankerung
muss die ersten Authorities und vollständigen Ausgangsrevisionen bewusst und
atomar erzeugen.

## Technische Nichtverfügbarkeit

Die read-only Lookups trennen neutrale fachliche Abwesenheit von technischer
Nichtverfügbarkeit.

Fehlende Migration, Datenbankfehler, ungültige Eingabeencoding oder nicht
auswertbare Persistenz verlassen den Adapter als eine gemeinsame detailfreie
Lifecycle-Authority-Nichtverfügbarkeit.

Exception und Adapter-Repr enthalten keine UserId, Authority, Tabelle, SQL,
Constraint, Host, Port oder DSN.

## Tests

Die neuen Foundation-Tests prüfen:

- unveränderliche, slotted und repr-freie IDs;
- Ablehnung leerer und falsch typisierter IDs;
- vier unabhängige sichere Materialziehungen;
- strukturelle Erfüllung beider Authority-Ports;
- strikt getrennte aktive Authority-Auflösung;
- fail-closed Abwesenheit und Actor-Inaktivität;
- Wirkung eines committierten Actor-Entzugs auf spätere Entscheidungen;
- vollständig leere Tabellen nach Migration;
- Constraint-Schutz für Workspace-Create, Deactivate und verbotene Reactivate;
- detailfreie technische Nichtverfügbarkeit;
- den eindeutigen neuen Migration-Head.

PostgreSQL bleibt die normative Runtime. Dieser Slice führt noch keine
konkurrierende Mutation ein und benötigt deshalb keinen neuen
PostgreSQL-Serialisierungsnachweis.

## Bewusst nicht enthalten

- kein Seed, Bootstrap oder Authority-Set-Anchor;
- keine Authority-Vergabe, Rotation, Deaktivierung oder Recovery;
- keine Nutzer- oder Workspace-Anlage beziehungsweise Statusmutation;
- keine Drain-Prüfung oder Mutation fremder Domänen;
- keine Workspace-Reaktivierung oder physische Löschung;
- keine CLI, Requestdatei, Route, Settings- oder Runtime-Verdrahtung;
- keine automatische OIDC-, Admission-, Session- oder Membership-Provisionierung.

## Nächster Schritt

LQ-221 sollte die bestehende einmalige Initial-Bootstrap-Transaktion eng
erweitern: Beim vollständig leeren Start erzeugt sie beide ersten Lifecycle-
Authorities und beide vollständigen Ausgangsrevisionen atomar mit den bereits
erzeugten ersten Nutzer- und Workspace-Fakten.

Für bereits bootstrapped Bestände braucht derselbe Slice eine getrennte,
zustandsgebundene einmalige Verankerungsgrenze ohne Migration-Seed. Reguläre
Lifecycle-Mutationen bleiben danach ein weiterer separater Slice.
