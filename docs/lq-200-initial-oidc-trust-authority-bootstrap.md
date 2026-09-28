# LQ-200 — Initial OIDC Trust Authority Bootstrap

## Ergebnis

LQ-200 implementiert die einmalige Offline-Bootstrap-Grenze aus LQ-198 auf der
persistenten LQ-199-Foundation. Sie gewährt genau einem bereits vorhandenen
aktiven internen Nutzer die erste globale OIDC-Trust-Management-Authority.

Der Slice erzeugt keinen Nutzer, keine Trust-Revision und keine aktive OIDC-
Konfiguration. Er ergänzt keine Migration, Route, CLI, Environment-Einstellung
oder automatische Startup-Ausführung.

## Port und Eingabegrenze

`InitialOidcTrustAuthorityBootstrap.bootstrap(user_id)` erhält ausschließlich
eine typisierte interne `UserId` als Ziel der initialen Authority.

Die Grenze nimmt keinen handelnden Actor, keine Session, Rolle, Permission,
Capability, Allow-Entscheidung, WorkspaceId, Konfiguration, Revision, Issuer
oder Provider entgegen. Sie ist eine spätere Offline-Control-Plane-Fähigkeit,
kein regulärer authentifizierter Runtime-Anwendungsfall.

Die Ziel-ID muss einen bereits persistenten Nutzer bezeichnen. LQ-200 erzeugt
keine ID und ruft keinen Materialgenerator auf. Der exakte nichtleere String
wird als UTF-8 gespeichert, ohne Normalisierung, Trimming oder Case-Folding.

Der erfolgreiche Rückgabewert `BootstrappedOidcTrustAuthority` enthält nur die
bestätigte interne UserId. Er ist eine Ergebnis-Fakt, kein übertragbarer
Authority-Token und keine Session.

## Aktiver vorhandener Nutzer

Bootstrap ist nur zulässig, wenn der ausgewählte Nutzer bereits im
`identity_users`-System of Record existiert und aktuell aktiv ist.

Ein unbekannter oder inaktiver Nutzer ergibt neutrales `None`. Es wird keine
Authority reserviert, kein Nutzer reaktiviert und keine alternative ID
ausgewählt. Die Antwort unterscheidet nicht, ob der Zielnutzer unbekannt oder
inaktiv ist.

Workspace, Membership, Research-Permission und Onboarding-Management-
Capability des Nutzers sind irrelevant. Keine davon ist Vorbedingung oder
Ersatz für die globale Trust-Authority.

## Zustandsbasierte dauerhafte Schließung

Die Grenze ist nur geöffnet, solange
`oidc_trust_management_authorities` vollständig leer ist. Bereits eine einzige
Authority-Tatsache schließt sie dauerhaft, unabhängig von deren active/inactive-
Status oder Zielnutzer.

Die Schließung folgt ausschließlich aus dem persistenten Bestand. Es gibt kein
Flag, keine Settings-Option, kein Environment-Allow und keinen Zähler.
Deaktivierung, Entzug, Restore, Reimport oder Wechsel der aktiven OIDC-
Konfiguration öffnen Bootstrap nicht wieder.

Bei geschlossenem Bestand liefert jeder spätere Versuch neutral `None`, ändert
nichts und prüft keinen alternativen Zielnutzer auf Eignung. Die vorhandene
Authority wird niemals überschrieben oder auf einen anderen Nutzer umgebogen.

## Atomarität und Konkurrenz

Prüfung der leeren Authority-Tabelle, Bestätigung des aktiven Zielnutzers und
Anlage der aktiven Authority laufen in genau einer Datenbanktransaktion.

PostgreSQL sperrt `identity_users` und
`oidc_trust_management_authorities` vor der Leerheitsprüfung in einer
festgelegten Reihenfolge. Gleichzeitige Bootstrap-Versuche werden dadurch vom
System of Record serialisiert: genau ein Versuch kann gewinnen, alle später
geordneten sehen Bestand und liefern `None`.

Es gibt keinen In-Process-Lock, Check-then-act über mehrere Transaktionen,
automatischen Retry oder Last-write-wins. SQLite beweist nur sequenzielle
Semantik und Rollback; PostgreSQL bleibt die normative Konkurrenzgrenze.

## Kein Trust als Nebenwirkung

Der Bootstrap schreibt ausschließlich eine aktive Zeile in
`oidc_trust_management_authorities`.

Insbesondere bleiben leer:

- `oidc_trust_revisions`,
- der aktive LQ-192-Konfigurations-Singleton,
- spätere Trust-Change-Entscheidungen.

Die erste autorisierte Person kann daher Trust später verwalten, aber Bootstrap
behauptet keinen Issuer, Client oder Provider. OIDC-Login bleibt nach dem
Bootstrap geschlossen, bis eine eigene autorisierte Aktivierungsgrenze eine
vollständige Revision atomar aktiviert.

Der Bootstrap erzeugt ebenso keine Membership, Research-Permission,
Onboarding-Management-Capability, Admission, Identity-Bindung oder Session.

## Fehler- und Datenschutzgrenze

Geschlossener Bestand sowie unbekannter oder inaktiver Zielnutzer sind neutrale
fachliche Ergebnisse. Sie sind keine technische Störung.

Ungültige UserId-Repräsentation, fehlendes Schema, unbekannter Dialekt sowie
Datenbank-, Transaktions-, Constraint- oder Commitfehler werden als
detailfreie `OidcTrustAuthorityBootstrapUnavailable` gemeldet.

Die Ausnahme verlässt die Grenze ohne Cause oder Context und enthält weder
UserId, Status, Authority, SQL, Tabelle, Constraint, Engine, Host, Port noch
DSN. Der Adapter besitzt einen konstanten wertfreien `repr`, schließt die
injizierte Engine nicht und fängt `BaseException` nicht.

## Tests

Die SQLite-Tests beweisen:

- strukturelle Erfüllung des Bootstrap-Ports,
- einmalige Authority-Anlage für einen vorhandenen aktiven Nutzer,
- neutrales Ergebnis für unbekannte und inaktive Nutzer ohne Schreibwirkung,
- dauerhafte Schließung auch nach Deaktivierung der ersten Authority,
- keine Trust-Revision und keine aktive OIDC-Konfiguration als Nebenwirkung,
- detailfreie technische Nichtverfügbarkeit bei ungültiger ID und fehlendem
  Schema.

Der markierte PostgreSQL-Test startet zwei echte konkurrierende Versuche für
zwei aktive Nutzer. Exakt einer erhält die Authority, der andere neutral
`None`; kein technischer Fehler und keine zweite Authority entstehen.

## Bewusst nicht enthalten

- keine Migration oder Schemaänderung,
- keine Nutzeranlage oder Auswahl eines „ersten“ Nutzers,
- keine reguläre Authority-Vergabe, -Übertragung, -Reaktivierung oder Entzug,
- keine Trust-Revision, Aktivierung, Rotation oder Deaktivierung,
- keine revisionsgebundene Login-Transaktion oder Callback-Prüfung,
- keine Route, CLI, Operator-Authentisierung oder Startup-Ausführung,
- keine Environment-Authority, Admin-Header oder Login-basierte Freischaltung,
- keine Membership-/Permission-Verwaltung und kein Deployment.

## Nächster Schritt

LQ-201 sollte die Trust-Revision in den aktiven Konfigurations-Lookup und die
Pending-Login-Transaktion einführen. Login-Start muss die aktuelle Revision
speichern; Callback muss sie vor jedem Token- oder JWKS-Zugriff erneut prüfen.
Erst nach dieser fail-closed Rotationsgrundlage darf die reguläre autorisierte
Trust-Mutation implementiert werden.
