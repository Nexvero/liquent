# LQ-205 — Controlled Initial Bootstrap Operator

## Ergebnis

LQ-205 macht die bereits implementierten einmaligen LQ-185- und LQ-200-
Bootstrap-Grenzen über einen separaten kontrollierten Offline-Prozess
erreichbar.

`liquent-initial-bootstrap` kann zuerst die initiale Identity-Foundation und
danach die erste globale OIDC-Trust-Authority anlegen. Er erzeugt weder aktive
OIDC-Konfiguration noch Membership oder Research-Permission.

Der HTTP-Prozess importiert diese Grenze nicht. Es entstehen keine Route,
Settings-Option, Environment-Authority, Startup-Ausführung oder Migration.

## Zwei getrennte Operationen

`identity` ruft den argumentlosen
`DatabaseInitialIdentityAuthorityBootstrap.bootstrap()` auf. UserId und
WorkspaceId stammen weiterhin aus dem sicheren internen Materialgenerator.

`oidc-trust-authority` liest genau eine interne UserId aus einer geschützten
Datei und ruft den bestehenden LQ-200-Port auf.

Die zweite Operation erzeugt keinen Nutzer und wählt keinen Bestand
automatisch. Das Ziel muss bereits existieren und aktiv sein. Workspace,
Membership, Rolle, Permission, Provider und Allow-Boolean werden nicht
akzeptiert.

Beide Operationen bleiben durch den persistenten Bestand dauerhaft
zustandsbasiert geschlossen. LQ-205 ergänzt kein Reopen-, Force-, Reset- oder
Overwrite-Flag.

## Verpflichtende Ergebnisdatei

Jede Operation verlangt einen noch nicht vorhandenen `--result-file` in einem
owner-only Verzeichnis.

Nach erfolgreichem Datenbankergebnis schreibt der Prozess eine JSON-Datei mit
Modus 0600 und ersetzt sie atomar aus einer exklusiv erzeugten temporären Datei.

Identity schreibt ausschließlich die erzeugte interne UserId und WorkspaceId.
Trust-Authority schreibt ausschließlich die bestätigte Ziel-UserId. Diese IDs
erscheinen nicht auf stdout oder stderr.

Eine vorhandene Ergebnisdatei wird niemals geöffnet, verändert oder
überschrieben. Symbolische Links werden abgelehnt. Die Ergebnisdatei ist kein
Authority-Token, sondern dokumentiert nur persistente interne Fakten.

## Unklarer Ausgang und Recovery

Die ursprünglichen Bootstrap-Ports sind absichtlich nicht idempotent nach
Operations-ID. Sobald irgendein Foundation-Bestand existiert, liefern sie
neutral `None`.

Ein Datenbank-Commit kann erfolgreich gewesen sein, obwohl der Prozess vor dem
Schreiben der Ergebnisdatei endet. LQ-205 löst diesen Fall ohne neue Mutation
durch eine eng begrenzte read-only Rekonstruktion.

Identity-Recovery ist ausschließlich zulässig, wenn gemeinsam exakt vorhanden
sind:

- genau ein aktiver interner Nutzer,
- genau ein aktiver Workspace,
- genau eine aktive Onboarding-Management-Authority,
- diese Authority verbindet exakt diesen Nutzer mit diesem Workspace.

Teilbestand, zusätzliche Nutzer oder Workspaces, zusätzliche Authority,
Inaktivität oder andere Beziehung ergeben neutrales `closed`. Der Operator
behauptet dann keine Bootstrap-Herkunft und gibt keine ID aus.

Trust-Authority-Recovery ist ausschließlich zulässig, wenn genau eine globale
Authority-Tatsache existiert, sie aktiv ist, ihr Nutzer aktiv ist und ihre
UserId exakt der erneut angeforderten Ziel-ID entspricht.

Ein anderes Ziel, zusätzliche oder inaktive Authority und inaktiver Nutzer
ergeben ebenfalls `closed`. Es gibt kein Umschreiben oder Reaktivieren.

## Warum keine Bootstrap-Operations-Tabelle

LQ-205 ergänzt bewusst keine neue Bootstrap-ID und keine Migration. Die
dauerhafte Schließung aus LQ-185/LQ-200 bleibt unverändert und die kanonische
Foundation selbst genügt für diese eng begrenzte initiale Recovery.

Eine neue Operations-ID könnte nicht nachträglich beweisen, ob bereits
vorhandener fremder Bestand zu ihr gehört. Die sichere Entscheidung ist daher
nur exakte kanonische Rekonstruktion oder neutrales `closed`.

Reguläre spätere Mutation benötigt weiterhin eigene Änderungsentscheidungen;
sie darf diese einmalige Recovery nicht wiederverwenden.

## Datei- und Geheimnisgrenze

Datenbank-URL und Ziel-UserId werden ausschließlich aus vorhandenen lokalen
regulären owner-only Dateien gelesen. Group-/World-Rechte und Symlinks werden
fail-closed abgelehnt.

Die DSN wird weder als Prozessargument noch als Environment-Variable
akzeptiert. Sie wird nicht ausgegeben und nur zum Aufbau einer Process-eigenen
Engine verwendet.

Das Ergebnisverzeichnis muss ebenfalls owner-only sein. Es gibt keine
Eingabedatei für selbst gewählte Identity-IDs; UserId und WorkspaceId der
Foundation bleiben intern erzeugt.

## Prozessbesitz

Jeder Aufruf erzeugt genau eine Datenbank-Engine und disposed sie in `finally`.
Die transportfreien Funktionen schließen eine injizierte Engine nicht.

Der Prozess migriert nicht, startet keinen HTTP-Client, greift auf keinen IdP
zu und importiert weder ASGI-App noch reguläre Trust-Mutation.

Fehlendes oder veraltetes Schema endet detailfrei. Es gibt keinen SQLite- oder
In-Memory-Fallback in Production.

## Ausgaben und Fehler

`bootstrapped` mit Exit 0 bedeutet, dass dieser Aufruf den einmaligen Port
erfolgreich abgeschlossen hat.

`recovered` mit Exit 0 bedeutet ausschließlich, dass der Port bereits
geschlossen war und der exakte kanonische Bestand read-only rekonstruiert
wurde.

`closed` mit Exit 5 verrät nicht, ob Bestand fehlt, partiell, zusätzlich,
inaktiv oder anders gebunden ist. Es wird keine Ergebnisdatei angelegt.

Input-, Dateisystem-, Schema-, Datenbank-, Generator-, Decoding-,
Transaktions- und Ergebnisdateifehler werden am Prozessrand als konstantes
`initial_bootstrap_operator_unavailable` mit Exit 2 vereinheitlicht.

Keine Ausgabe enthält UserId, WorkspaceId, DSN, SQL, Tabelle, Constraint,
Generatorwert oder ursprüngliche Exception. `BaseException` bleibt ungefangen.

## Runbook und Tests

Das neue Runbook beschreibt private Vorbereitung, beide Bootstrap-Stufen,
sichere Wiederholung, getrennte spätere Trust-Aktivierung und Cleanup.

Die SQLite-Tests belegen neue Foundation, exakte Recovery, geschlossenes
nichtkanonisches Inventar, identisches Trust-Authority-Ziel, die vollständige
CLI-Kette, atomare owner-only Ergebnisse, fehlendes Überschreiben, Recovery
nach Ergebnisdateifehler und fehlende automatische Migration.

Der markierte PostgreSQL-Test führt Bootstrap und Recovery beider Stufen auf
dem normativen Persistenzsystem aus. Bestehende Konkurrenztests bleiben
unverändert maßgeblich.

## Wirkung auf LQ-177

Der erste LQ-204-Restblocker ist geschlossen: Ein leerer migrierter Bestand
kann nun über einen unterstützten Offline-Prozess die initiale Identity-
Foundation und globale Trust-Authority herstellen und danach LQ-203 zur
Trust-Aktivierung verwenden.

LQ-177 bleibt blockiert durch reguläre Membership-/Research-Permission-
Mutation, Trust-Authority-Lifecycle/Recovery nach dem initialen Bootstrap und
den vollständigen End-to-End-Inbetriebnahmenachweis.

## Bewusst nicht enthalten

- keine reguläre Nutzer-, Workspace- oder Authority-Mutation,
- keine Membership oder Research-Permission,
- keine OIDC-Trust-Revision oder Providerkonfiguration,
- keine HTTP-Route, Runtime-Settings oder Startup-Ausführung,
- keine Migration, Seed-, Force-, Reset- oder Reopen-Funktion,
- kein Deployment und keine automatische Service-Steuerung.

## Nächster Schritt

LQ-206 sollte den Authority-Vertrag für reguläre workspacebezogene Membership-
und Research-Permission-Verwaltung entscheiden. Diese Capability muss von
Onboarding-Management, Research-Rechten und globaler OIDC-Trust-Authority
getrennt bleiben.

## Ergänzung durch LQ-229

LQ-229 erweitert das Identity-Resultat additiv um die beiden beim Bootstrap
erzeugten User- und Workspace-Lifecycle-Revisionen. Frischer Erfolg und exakte
kanonische Recovery liefern nun denselben Vier-Felder-Shape.

Die ursprüngliche Zwei-Felder-Aussage in diesem historischen Slice ist damit
für den aktuellen Operatorstand überholt. Datei-, Fehler-, Prozess- und
Kanonizitätsgrenzen bleiben unverändert.
