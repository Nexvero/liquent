# LQ-183 — Persistente Identity- und Autoritätsgrundlage

## 1. Status und Ziel

Dieser Slice ist eine reine Architekturentscheidung. Er enthält keine
Python-Implementierung, Tests, Migration, Tabelle, SQL-Strategie, Portänderung,
CLI, Route oder Verdrahtung.

LQ-182 verlangt dauerhafte Nutzer und Workspaces sowie eine persistente,
workspacebezogene Verwaltungsautorität. Im Bestand sind `UserId` und
`WorkspaceId` jedoch nur typisierte Zeichenketten; `WorkspaceMembership` ist
nicht persistent implementiert und kennt ausschließlich Research-Rechte.
LQ-183 entscheidet deshalb die beobachtbaren Tatsachen, die ein späteres System
of Record garantieren muss, ohne dessen Schema vorwegzunehmen.

## 2. Nutzer als dauerhafte interne Tatsache

Ein `UserId` bezeichnet genau einen intern angelegten Nutzer. Die ID wird aus
einer internen, kryptografisch geeigneten Quelle erzeugt, nicht aus E-Mail,
Provider-Claim, Subject, HTTP-Eingabe oder Anzeigename abgeleitet. Sie ist
global eindeutig, wird niemals einem anderen Nutzer zugewiesen und bleibt auch
nach Deaktivierung als dieselbe historische Identität erhalten.

Ein Nutzer besitzt mindestens einen fail-closed auswertbaren Lebenszyklus:
**aktiv** oder **inaktiv**. Nur ein aktiver Nutzer darf als handelnder
Onboarding-Akteur oder Ziel einer neuen Onboarding-Entscheidung gelten. Ein
unbekannter oder inaktiver Nutzer ist fachliche Ablehnung, nicht ein Ersatz- oder
Auto-Creation-Pfad.

Deaktivierung löscht oder ersetzt die ID nicht und erzeugt keinen neuen Nutzer.
Ob eine spätere Reaktivierung zulässig ist, bleibt eine eigene Lifecycle-
Entscheidung; keine andere Operation reaktiviert implizit.

## 3. Workspace als dauerhafte interne Tatsache

Ein `WorkspaceId` bezeichnet genau einen intern angelegten Workspace. Auch
diese ID ist global eindeutig, nicht aus Host, Origin, Pfad, Header, Token,
Claim oder Anzeigename abgeleitet, nicht wiederverwendbar und nicht auf einen
anderen Workspace übertragbar.

Ein Workspace ist mindestens **aktiv** oder **inaktiv**. Nur ein aktiver
Workspace darf Ziel einer neuen Verwaltungs- oder Onboarding-Entscheidung sein.
Unbekannt und inaktiv bleiben nach außen ununterscheidbare fachliche Ablehnung.
Deaktivierung bewahrt die historische Identität und öffnet weder Bootstrap noch
ID-Wiederverwendung. Reaktivierung wird hier nicht entschieden und geschieht
niemals als Nebenwirkung.

## 4. Workspacebezogene Verwaltungsfähigkeit

Die für LQ-182 notwendige Fähigkeit bedeutet ausschließlich: **für diesen
Workspace eine interne Onboarding-Entscheidung anlegen dürfen**. Sie ist an
einen bestehenden aktiven Nutzer und einen bestehenden aktiven Workspace
gebunden und wird persistent vom System of Record entschieden.

Sie ist ausdrücklich getrennt von `Permission.RESEARCH_READ` und
`Permission.RESEARCH_WRITE`. Weder eines dieser Rechte noch ihre Kombination,
eine gewöhnliche `WorkspaceMembership`, eine Identity-Bindung, eine Admission,
eine Session oder ein erfolgreicher Login impliziert Verwaltungsautorität.
Umgekehrt gewährt die Verwaltungsfähigkeit keine Research-Berechtigung.

LQ-183 legt keinen Python-Enum-, Rollen- oder Tabellennamen fest. Die spätere
Modellierung darf die Fähigkeit als Capability oder administrative Zuordnung
ausdrücken, muss aber genau diese Trennung erhalten und darf sie nicht als
frei übergebenes Boolean behandeln.

## 5. Herkunft des handelnden Akteurs

Eine bereits geprüfte `SessionPrincipal` kann den handelnden `UserId` liefern;
sie beweist nur die Identität des Akteurs, nicht dessen Autorität. Die spätere
Entscheidungsgrenze muss Nutzerstatus, Workspace-Status und genau diese
workspacebezogene Verwaltungsfähigkeit aus dem System of Record auflösen.

Transport, Browser und Aufrufer dürfen keinen alternativen Akteur, kein
Autoritäts-Boolean, keinen Rollennamen und keine frei behauptete Capability
einschleusen. Ein Zielworkspace darf nur aus einem serverseitig kontrollierten
Onboarding-Vorgang stammen. Selbst wenn spätere Methoden IDs als typisierte
Parameter tragen, ist deren **Herkunft** verbindlich; der Wert autorisiert sich
nicht selbst.

## 6. Atomare autorisierte Entscheidung

Die spätere reguläre Grenze prüft in einer konsistenten Schreibentscheidung:

1. Akteur existiert und ist aktiv;
2. Zielworkspace existiert und ist aktiv;
3. Zielnutzer existiert und ist aktiv;
4. Akteur besitzt für genau diesen Workspace die Verwaltungsfähigkeit;
5. die unveränderliche Onboarding-Entscheidung und ihr
   `ProvisioningRequestId` werden gemeinsam gespeichert.

Alles fünf wird wirksam oder nichts. Ein Check-then-act über getrennte
Transaktionen genügt nicht: Eine zwischen Prüfung und Speicherung widerrufene
Autorität darf keine neue Entscheidung mehr ermöglichen. In-Process-Locks sind
kein Ersatz für die Persistenzentscheidung.

Nach erfolgreichem Commit ist die Entscheidung eine dauerhafte autorisierte
Tatsache. Eine spätere Deaktivierung oder ein späterer Autoritätsentzug sperrt
**neue** Entscheidungen, verändert aber weder den bereits zugeordneten
`ProvisioningRequestId` noch die idempotente technische Wiederholung des
bereits entschiedenen Vorgangs. Andernfalls wäre ein unklarer Commit-Ausgang
nicht mehr zuverlässig auflösbar.

## 7. Vergabe, Entzug und Konkurrenz

Verwaltungsfähigkeit wird nur durch eine eigene autorisierte
Management-Grenze vergeben oder entzogen. Onboarding und
Admission-Provisionierung dürfen sie weder erzeugen noch verändern. Die
Bootstrap-Grenze ist die einzige Ausnahme für den vollständig leeren Bestand
und bleibt LQ-184 vorbehalten.

Entzug wird für jede nachfolgende Entscheidung wirksam. Gleichzeitige Vergabe,
Entzug und Entscheidungsanlage müssen durch das spätere normative
Persistenzsystem serialisierbar entschieden werden. Es gibt keinen
prozesslokalen Cache, dessen veralteter Treffer Autorität fortschreibt, keinen
stale fallback und keinen automatischen Retry mit einer neuen Entscheidung.

## 8. Membership und Zugriff bleiben getrennt

Eine Verwaltungszuordnung ist keine allgemeine Workspace-Membership. Die
spätere reguläre Membership-Erzeugung, Membership-Status, Research-Permissions
und deren Persistenz bleiben eigene Verträge und Slices. LQ-183 erweitert die
bestehende `Permission`-Aufzählung nicht.

Insbesondere erzeugen die Anlage eines Nutzers, die Anlage eines Workspaces,
die Verwaltungszuordnung, eine Onboarding-Entscheidung und die spätere
Identity-Bindung jeweils nicht stillschweigend die anderen Tatsachen. Jeder
Übergang braucht seine eigene autorisierte Grenze.

## 9. Fehler- und Datenschutzgrenze

Unbekannter oder inaktiver Akteur, Nutzer oder Workspace sowie fehlende oder
widerrufene Autorität sind eine einheitliche fachliche Ablehnung. Die Antwort
verrät nicht, welche Tatsache fehlt oder inaktiv ist. Datenbank-,
Transaktions-, Decodierungs- und Strukturfehler sind davon getrennte technische
Nichtverfügbarkeit.

Beide Klassen bleiben detailfrei. Kein Identifier, Status, Rollenname,
Capability-Wert, Datenbankdetail oder ursprünglicher Fehlertext gelangt in
Exception, Log, Trace oder Metriklabel. Die spätere Python-Fehlerform wird hier
nicht benannt; `BaseException` bleibt außerhalb normaler Neutralisierung.

## 10. Retention und Nichtwiederverwendung

Nutzer-, Workspace- und Autoritäts-IDs werden nicht so gelöscht oder
wiederverwendet, dass eine alte Session, Entscheidung, Admission, Bindung oder
Auditreferenz auf eine neue Tatsache zeigen kann. Deaktivierung und Entzug
bleiben erkennbarer historischer Zustand. Der `ProvisioningRequestId` und seine
Entscheidungszuordnung bleiben mindestens so lange erhalten, wie ein technischer
Retry oder eine abhängige Admission noch auf sie verweisen kann.

Konkrete Aufbewahrungsfristen, Löschverfahren, Auditfelder und Datenschutz-
Workflows sind nicht Teil dieses Slices. Ein späteres Verfahren muss jedoch
fail-closed bleiben und darf durch Restore oder Reimport keine deaktivierte
Autorität oder alte ID unter neuer Bedeutung reaktivieren.

## 11. Nicht enthalten und Reihenfolge

Nicht enthalten sind Modelle, Ports, Adapter, Tabellen, Migrationen, SQL,
Foreign Keys, Tests, Bootstrap-CLI, Operator-Authentisierung, HTTP, Production-
Wiring, Membership- oder Admission-Erzeugung sowie Änderungen an LQ-181 oder
LQ-182.

Die Folgeordnung lautet:

1. LQ-183 — dieser Persistenz- und Autoritätsvertrag;
2. Migration, Modelle und Ports für Nutzer, Workspaces und Verwaltungsfähigkeit;
3. einmaliger atomarer Bootstrap des ersten Bestands;
4. reguläre autorisierte Onboarding-Entscheidung;
5. persistente Login-Transaktionen und Sessions;
6. erst danach Wiederaufnahme von LQ-177.
