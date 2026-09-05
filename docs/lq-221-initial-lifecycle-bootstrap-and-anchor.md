# LQ-221 — Initial Lifecycle Bootstrap and Anchor

## Ergebnis

LQ-221 macht die LQ-220-Foundation sicher erreichbar.

Ein vollständig leerer Initial-Bootstrap erzeugt nun atomar:

- den ersten aktiven internen Nutzer;
- den ersten aktiven internen Workspace;
- dessen erste Onboarding-Management-Authority;
- die erste globale User-Lifecycle-Management-Authority;
- die erste globale Workspace-Lifecycle-Management-Authority;
- die vollständige erste Nutzer-Lifecycle-Revision samt Current-Pointer;
- die vollständige erste Workspace-Lifecycle-Revision samt Current-Pointer.

Für einen bereits vor LQ-220 kanonisch erzeugten Ein-Nutzer-/Ein-Workspace-
Bestand existiert eine getrennte einmalige Anchor-Grenze. Sie erfindet keine
Bootstrap-Herkunft für beliebigen Bestand.

## Erweiterter leerer Bootstrap

`DatabaseInitialIdentityAuthorityBootstrap` bleibt argumentlos auf seiner
fachlichen Portgrenze. Der Caller kann weiterhin weder UserId, WorkspaceId,
Rolle, Authority noch Allow-Entscheidung wählen.

Zusätzlich zu den getrennten UserId- und WorkspaceId-Generatoren erhält der
Adapter zwei getrennte Generatoren für die initialen vollständigen Lifecycle-
Revisionen.

Alle vier IDs werden erst nach bestätigter vollständiger Leere gezogen. Sie
werden strikt validiert und atomar mit dem gesamten Anfangsbestand gespeichert.

Ein Generator-, Validierungs-, Constraint-, Transaktions- oder Commitfehler
lässt weder Nutzer, Workspace, Authority, Revision noch Pointer zurück.

## Erweiterte zustandsbasierte Schließung

Bootstrap prüft neben den ursprünglichen Identity- und Onboarding-Tabellen auch
beide Lifecycle-Authority- und Revisionsbestände.

Bereits irgendein Nutzer, Workspace, Onboarding-Manager, Lifecycle-Manager oder
eine Lifecycle-Revision schließt den Bootstrap neutral.

Deaktivierung, Entzug, Restore oder spätere Verankerung öffnen ihn nicht wieder.
Es gibt weiterhin kein Flag, Environment-Allow, Force, Reset oder Reopen.

PostgreSQL sperrt alle beteiligten Foundation-Tabellen gemeinsam vor der
Leerheitsprüfung. Zwei konkurrierende Versuche können deshalb weiterhin
höchstens einen vollständigen Anfangsbestand erzeugen.

## Initiale Authorities

Der erste Nutzer erhält atomar beide neuen globalen Lifecycle-Authorities.

Diese Zuweisung ist auf den vollständig leeren Initial-Bootstrap begrenzt. Sie
ist keine Regel, nach der ein Onboarding-Manager, Trust-Manager oder erster
Nutzer generell Lifecycle-Authority erhält.

Die beiden Authority-Fakten bleiben getrennt gespeichert und später getrennt
widerrufbar. Keine der Authorities erzeugt Membership, Research-Permission,
OIDC-Trust-Authority oder Membership-Management-Authority.

## Initiale vollständige Revisionen

Die erste Nutzerrevision enthält exakt den erzeugten ersten Nutzer mit Status
aktiv.

Die erste Workspace-Revision enthält exakt den erzeugten ersten Workspace mit
Status aktiv.

Beide Current-Pointer werden in derselben Bootstrap-Transaktion gesetzt. Es
entsteht keine Change-Entscheidung, weil diese Revisionen den kontrollierten
Ausgangspunkt und keine reguläre Lifecycle-Mutation darstellen.

Die Revisionen bleiben stabil und historisch erhalten. Der Bootstrap
aktualisiert oder ersetzt sie bei Wiederholung nicht.

## Getrennte Anchor-Grenze

`InitialIdentityLifecycleFoundationAnchor.anchor()` nimmt keine fachlichen
Argumente entgegen.

Der Anchor akzeptiert ausschließlich einen exakten kanonischen Altbestand:

- genau einen aktiven internen Nutzer;
- genau einen aktiven internen Workspace;
- genau eine aktive Onboarding-Management-Authority;
- diese verbindet exakt den einen Nutzer mit dem einen Workspace;
- beide Lifecycle-Authority-Tabellen sind leer;
- beide Lifecycle-Revisions-, Member-, Current- und Change-Bestände sind leer.

Leerstand, Inaktivität, zusätzliche Nutzer, Workspaces oder Authorities,
partielle Lifecycle-Foundation und bereits erfolgte Verankerung ergeben
neutral `None`.

Der Anchor akzeptiert keine UserId, WorkspaceId, Actor-ID, Session, Rolle,
Authority-Auswahl, Status- oder Allow-Entscheidung vom Caller.

## Atomare Verankerung

Nach exakter Bestätigung erzeugt der Anchor zwei interne Revisions-IDs und
speichert atomar:

- aktive User-Lifecycle-Authority für den kanonischen Nutzer;
- aktive Workspace-Lifecycle-Authority für denselben Nutzer;
- vollständige aktive Nutzerrevision und Current-Pointer;
- vollständige aktive Workspace-Revision und Current-Pointer.

Er verändert keinen bestehenden Nutzer-, Workspace- oder Onboarding-Fakt.

Fehler rollen sämtliche neuen Fakten zurück. Erfolgreiche Verankerung schließt
die Grenze dauerhaft; eine spätere Wiederholung liefert neutral `None` und
zieht keine neuen IDs.

## Konkurrenz

PostgreSQL sperrt Identity-, Onboarding-, Lifecycle-Authority-, Revisions-,
Current- und Change-Tabellen in einer gemeinsamen Transaktion.

Bei zwei konkurrierenden Anchor-Versuchen kann genau einer den kanonischen
Altbestand verankern. Der spätere Versuch sieht den nun geschlossenen Bestand
und liefert neutral `None`.

Es gibt keinen In-Process-Lock, keinen Check-then-act über mehrere
Transaktionen und keinen automatischen Retry.

## Operator-Recovery

Der vorhandene Initial-Bootstrap-Operator bleibt für neue leere Installationen
unverändert bedienbar und verwendet automatisch die neuen sicheren Generatoren.

Seine read-only Recovery nach verlorener Ergebnisdatei wurde verschärft. Sie
rekonstruiert Erfolg nur, wenn zusätzlich exakt beide aktiven Lifecycle-
Authorities, beide Einzelmember-Revisionen und beide Current-Pointer vorhanden
sind und keine Lifecycle-Change-Entscheidung existiert.

Ein alter noch nicht verankerter oder ein später bereits mutierter Bestand
wird nicht als erfolgreicher neuer Bootstrap ausgegeben.

Der Anchor selbst erhält in diesem Slice noch keinen CLI-Befehl. Seine spätere
Bedienung muss eine eigene kontrollierte Offline-Grenze bleiben.

## Neutralität und technische Fehler

Geschlossener oder nichtkanonischer Bestand ist eine neutrale fachliche
Ablehnung ohne Detail über Art, Anzahl oder Status der vorhandenen Fakten.

Unbrauchbare Generatoren, fehlendes Schema, nicht unterstützter Dialekt,
Encoding-, Datenbank-, Struktur-, Transaktions- oder Commitfehler enden als
detailfreie technische Nichtverfügbarkeit.

Anchor-Exception und Adapter-Repr enthalten keine IDs, Authority, Revision,
SQL-, Tabellen-, Constraint-, Host-, Port- oder DSN-Details.

## Tests

Die erweiterten Bootstrap-Tests prüfen den vollständigen atomaren Anfangsbestand,
beide aktive Authorities, beide Revisionen und beide Current-Pointer.

Die Anchor-Tests belegen:

- Erfolg nur für den exakten aktiven kanonischen Altbestand;
- neutrale Ablehnung bei Leerstand, Inaktivität und Zusatzbestand;
- dauerhafte Schließung nach Erfolg;
- vollständigen Rollback bei ungültiger Revisionserzeugung;
- detailfreie technische Nichtverfügbarkeit;
- PostgreSQL-Ordnung konkurrierender Anchor-Versuche mit genau einem Erfolg.

Bestehende Bootstrap-Konkurrenz- und Operator-Recovery-Tests bleiben maßgeblich
und verwenden jetzt den erweiterten kanonischen Bestand.

## Bewusst nicht enthalten

- keine reguläre Nutzer- oder Workspace-Lifecycle-Mutation;
- keine reguläre Vergabe oder Rotation der beiden Lifecycle-Authorities;
- keine Authority-Set-Revision, Lockout-Sicherung oder Recovery dafür;
- keine Drain-Prüfung, Session- oder Admission-Widerruf;
- keine Workspace-Reaktivierung oder physische Löschung;
- keine neue Migration, Seed- oder Datenübernahme;
- keine HTTP-Route, Runtime-Aktivierung oder automatische Startup-Ausführung;
- noch kein Anchor-CLI oder Deployment-Ablauf.

## Nächster Schritt

LQ-222 sollte die beiden Lifecycle-Authority-Domänen verankern und ihren
regulären Grant-/Deactivate-/Reactivate-Lifecycle mit letzter-Manager-Schutz
entscheiden beziehungsweise auf der bestehenden Authority-Lifecycle-Mechanik
implementieren.

Erst danach kann eine reguläre User-/Workspace-Mutation sicher auf dauerhaft
rotierbare Lifecycle-Manager vertrauen.
