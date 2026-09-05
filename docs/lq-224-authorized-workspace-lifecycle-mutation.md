# LQ-224 — Authorized Workspace Lifecycle Mutation

## Ergebnis

LQ-224 implementiert die reguläre persistente Workspace-Lifecycle-Mutation
aus LQ-219.

Die neue Grenze unterstützt genau:

- Anlage eines neuen aktiven internen Workspace;
- terminale Deaktivierung eines aktiven historischen Workspace.

Create bindet atomar genau einen expliziten bestehenden aktiven Nutzer als
ersten Onboarding-Manager. Es gibt keine reguläre Workspace-Reaktivierung.

Jede erfolgreiche Änderung erzeugt eine vollständige neue Workspace-Revision
und eine immutable Change-Entscheidung.

## Getrennte Portoperationen

`AuthorizedWorkspaceLifecycleStore` besitzt zwei Operationen.

`create_workspace` akzeptiert Change-ID, `SessionPrincipal`, den expliziten
ersten Onboarding-Manager und die erwartete aktuelle Workspace-Revision. Es
akzeptiert keine Ziel-WorkspaceId.

`deactivate_workspace` akzeptiert einen bestehenden Zielworkspace und die
erwartete Revision. Es akzeptiert keinen Manager und keine Statusauswahl.

Ein Reactivate-Port existiert nicht. Die Persistenzfoundation erlaubt ebenfalls
nur `create` und `deactivate`.

## Aktuelle Autorisierung

Der `SessionPrincipal` identifiziert ausschließlich den Actor.

Für jede neue Change-ID prüft die Schreibtransaktion:

- Actor existiert und ist aktiv;
- Actor besitzt aktive Workspace-Lifecycle-Management-Authority;
- erwartete Workspace-Revision ist exakt der Current-Pointer;
- vollständige erwartete Revision entspricht dem operativen Workspacebestand.

Caller-supplied Rolle, Allow-Boolean, Authority-Snapshot, Statusbehauptung oder
alternativer Actor werden nicht akzeptiert.

Ein späterer Entzug von Actor oder Authority sperrt jede neue Entscheidung.

## Workspace-Anlage

Nach erfolgreicher Autorisierung erzeugt der Adapter intern eine neue stabile
`WorkspaceId`.

Die ID muss ein nichtleerer exakter String sein. Der Caller kann sie weder
vorgeben noch aus fachlichen Werten ableiten lassen. Primärschlüssel und
historische Revisionen verhindern Wiederverwendung.

Der explizit angegebene erste Onboarding-Manager muss im selben aktuellen
Systembestand als aktiver interner Nutzer bestätigt werden.

Erfolg erzeugt atomar:

- den neuen aktiven Workspace;
- genau eine aktive Onboarding-Management-Authority dieses Managers im neuen
  Workspace;
- die vollständige neue Workspace-Revision;
- den neuen Current-Pointer;
- die immutable Create-Entscheidung.

Kann der Manager nicht als aktuell aktiv bestätigt werden, werden weder
Workspace- noch Revisions-IDs gezogen.

## Keine implizite weitere Authority

Create erzeugt keine:

- gewöhnliche Workspace-Membership;
- Research-Permission;
- Membership-Management-Authority;
- OIDC-Trust-Authority;
- User- oder Workspace-Lifecycle-Authority;
- Admission, Identitätsbindung oder Session.

Der Actor erhält nicht automatisch Onboarding-Authority. Nur der explizit
gebundene aktive Zielnutzer erhält sie.

Der getrennte Membership-Management-Bootstrap bleibt für den neuen Workspace
erforderlich.

## Terminale Deaktivierung

Deactivate ist nur für einen bekannten aktuell aktiven Workspace zulässig.

Erfolg ändert ausschließlich den Workspace-Status auf inaktiv und schreibt die
vollständige neue Revision sowie Change-Entscheidung.

Memberships, Permissions, Onboarding- und Membership-Management-Authorities
werden weder gelöscht noch statusverändert. Sie bleiben historische Fakten,
sind aber wegen des aktuellen inaktiven Workspace an den bestehenden
Lookup-Grenzen fail-closed unwirksam.

Da weder Port noch Persistenz-Intent eine Reaktivierung erlauben, können diese
erhaltenen Unterfakten nicht durch eine pauschale Workspace-Reaktivierung
unbemerkt wieder wirksam werden.

Ein zweites Deactivate desselben bereits inaktiven Workspace wird neutral
abgelehnt. Die WorkspaceId bleibt dauerhaft reserviert.

## Vollständige Revisionsintegrität

Vor jeder Mutation liest der Adapter den vollständigen Member-Satz der
erwarteten Current-Revision und den vollständigen operativen Workspacebestand
in stabiler ID-Reihenfolge.

Beide Bestände müssen exakt übereinstimmen. Fehlende, zusätzliche oder
statusabweichende Fakten werden als technische Inkonsistenz behandelt und
nicht mit einer neuen Revision überdeckt.

Create ergänzt genau den neuen aktiven Workspace. Deactivate ändert genau den
Zielstatus auf inaktiv. Alle übrigen historischen Status werden unverändert
übernommen.

## Atomarität und Konkurrenz

Workspace-Fakt, erster Onboarding-Manager, vollständige Revision,
Current-Pointer und Change-Entscheidung committen gemeinsam oder gar nicht.

PostgreSQL sperrt Nutzer-, Workspace-, Lifecycle-Authority-, Revisions-,
Change- und Onboarding-Tabellen in einer festen Reihenfolge innerhalb einer
kurzen Transaktion. Es findet kein externes I/O statt.

Konkurrierende Creates gegen dieselbe erwartete Revision werden geordnet.
Genau einer kann committen; jeder spätere Versuch sieht eine stale Revision
und endet neutral.

Die PostgreSQL-Best-Practices-Gegenprüfung bestätigte kurze Transaktion,
geordnete Snapshot-Verarbeitung und fehlenden Bedarf für zusätzliche
redundante Indizes.

## Idempotenz und Konflikt

Jede Operation besitzt eine stabile `WorkspaceLifecycleChangeId`.

Eine exakte Wiederholung mit identischem Actor, Intent, erwarteter Revision und
den operationsspezifischen Eingaben liefert dasselbe committete Ergebnis.

Create liefert dabei dieselbe intern erzeugte WorkspaceId und bindet weiterhin
denselben ersten Onboarding-Manager. Kein Generator wird erneut verwendet.

Der Retry wird vor aktueller Authority aufgelöst und bleibt nach späterem
Actor-, Authority- oder Managerentzug verfügbar.

Wiederverwendung derselben Change-ID mit anderem Actor, Intent, Manager,
Zielworkspace oder erwarteter Revision endet als detailfreier Konflikt.

## Migration und Indizes

LQ-224 benötigt keine neue Migration.

Die mit LQ-220 eingeführten Workspace-Revisions-, Member-, Current- und
Change-Tabellen tragen den vollständigen Vertrag bereits. Ihr Constraint
verlangt bei Create genau einen Manager und verbietet bei Deactivate einen
Managerwert.

Die verwendeten Workspace- und Change-Zugriffe sind durch Primärschlüssel und
den Singleton-Current-Pointer abgedeckt. Zusätzliche Indizes würden in diesem
Slice nur Schreibkosten erzeugen.

## Ablehnung und technische Fehler

Unbekannter oder inaktiver Actor, fehlende Authority, stale Revision,
unbekannter oder inaktiver erster Manager, unbekannter Zielworkspace oder
falscher Zielstatus ergeben dieselbe neutrale Ablehnung ohne Bestandsdetails.

Abweichende Change-ID-Wiederverwendung ist ein eigener detailfreier Konflikt.

Ungültige Generatorwerte, inkonsistente vollständige Revision, Datenbank-,
Encoding-, Struktur-, Transaktions- oder Commitfehler enden als detailfreie
technische Nichtverfügbarkeit.

Keine Antwort oder Exception enthält Actor, Manager, Workspace, Status,
Authority, Revision, Change-ID, SQL, Tabelle, Constraint, Host, Port oder DSN.

## Nachweise

Die SQLite-Tests belegen:

- Create mit intern erzeugter WorkspaceId;
- atomare Bindung des expliziten aktiven ersten Onboarding-Managers;
- neutrale Ablehnung eines inaktiven Managers ohne Generatorzug;
- terminales Deactivate und neutralen zweiten Deactivate-Versuch;
- vollständige resultierende Workspace-Revisionen;
- Erhalt historischer Onboarding-Authority bei inaktivem Workspace;
- keine Membership oder Membership-Management-Authority durch Create;
- stale Revision fail-closed;
- exakten Create-Retry nach Authority-Entzug;
- Konflikt bei operationsfremder Wiederverwendung.

Der PostgreSQL-Test führt zwei echte gleichzeitige Creates gegen dieselbe
Revision aus und belegt genau einen Erfolg ohne technische Ausnahme.

## Bewusst nicht enthalten

- keine Workspace-Reaktivierung oder physische Löschung;
- keine automatische Mutation historischer Unterfakten;
- keine Membership oder Research-Permission;
- kein Membership-Management-Bootstrap als Nebenwirkung;
- keine User-Lifecycle-Mutation;
- keine Authority-Recovery;
- keine CLI, Request-/Resultatdatei oder Runbook;
- keine HTTP-Route, Settings-, Startup- oder Runtime-Verdrahtung.

## Nächster Schritt

LQ-225 sollte getrennte kontrollierte Offline-Operatoren für reguläre User-
und Workspace-Lifecycle-Entscheidungen bereitstellen. Requests müssen stabile
Change-ID und erwartete Revision bewahren, Create-IDs intern erzeugen und
Resultate owner-only ohne Überschreiben persistieren.

Danach folgt der Mehrnutzer-/Multi-Workspace-End-to-End-Nachweis mit erneutem
LQ-177-Audit.
