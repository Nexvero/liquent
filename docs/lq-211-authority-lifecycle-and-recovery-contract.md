# LQ-211 — Authority Lifecycle and Recovery Contract

## 1. Status und Ziel

LQ-211 auditiert die nach LQ-210 verbleibenden LQ-177-Blocker und entscheidet
den Vertrag für regulären Authority-Lifecycle und kontrollierte Recovery.

Der Slice implementiert keine Python-Typen, Ports, Adapter, Migration, Tabelle,
SQL-Strategie, Tests, Route, CLI, Settings, Operator-Credentials oder
Production-Verdrahtung.

Zwei Authority-Domänen benötigen noch reguläre Verwaltung:

- globale OIDC-Trust-Management-Authority;
- workspacebezogene Membership-Management-Authority.

Ihre Sicherheitsstruktur ist vergleichbar, ihre Scopes und persistenten Fakten
bleiben jedoch strikt getrennt. LQ-211 führt keine generische Admin-Rolle,
Capability-Tabelle oder domänenübergreifende Mutation ein.

## 2. Audit des aktuellen Stands

LQ-200 und LQ-208 implementieren sichere einmalige Bootstrap-Grenzen. Sobald
Authority-Historie existiert, bleiben sie dauerhaft geschlossen.

LQ-202 und LQ-209 lösen aktuelle Authority innerhalb ihrer jeweiligen
fachlichen Schreibtransaktion auf. Ein committierter Entzug würde deshalb auf
spätere Trust- beziehungsweise Membership-Änderungen wirken.

Es fehlt jedoch eine unterstützte Grenze, die Authority regulär gewährt,
deaktiviert oder reaktiviert. Tests können Status derzeit nur direkt über SQL
verändern; das ist kein zulässiger Betriebsworkflow.

LQ-203 und LQ-210 sind bewusst keine Authority-Lifecycle-Tools. Sie dürfen ihre
eigene erforderliche Authority weder erzeugen noch reparieren.

Der verbleibende Blocker ist daher konkret: Nach Bootstrap existiert ein
sicherer erster Manager, aber kein unterstützter Offboarding-, Vertretungs-,
Rotation- oder Recovery-Pfad für diese Managementfähigkeit.

## 3. Zwei strikt getrennte Authority-Domänen

Globale OIDC-Trust-Authority gilt systemweit und darf ausschließlich aktive
OIDC-Trust-Konfiguration verwalten.

Workspacebezogene Membership-Management-Authority gilt ausschließlich für
genau einen Workspace und darf dort gewöhnliche Memberships und Research-
Permissions verwalten.

Keine der beiden Authorities impliziert die andere. Ebenso wenig implizieren
sie:

- Onboarding-Management-Authority;
- gewöhnliche Workspace-Membership;
- `research:read` oder `research:write`;
- Nutzer- oder Workspace-Lifecycle-Authority;
- Deployment-, Datenbank- oder Betriebssystemzugriff.

Ein gemeinsamer Python-Algorithmus darf später intern wiederverwendet werden,
aber Ports, IDs, Persistenz, Change-Entscheidungen, Revisionen, Fehlergrenzen
und Operatorbefehle müssen domänenspezifisch bleiben.

## 4. Regulärer handelnder Actor

Jede reguläre Authority-Änderung erhält einen bereits authentifizierten
`SessionPrincipal`. Dieser identifiziert nur den Actor.

Die jeweilige persistente Schreibgrenze löst aktuell auf:

1. Actor existiert und ist aktiv;
2. Zielnutzer existiert und ist aktiv;
3. bei Membership-Management: Zielworkspace existiert und ist aktiv;
4. Actor besitzt aktuell die aktive Authority derselben Domäne und desselben
   Scopes;
5. die erwartete Authority-Set-Revision ist aktuell.

Transport darf keinen alternativen Actor, Rollenwert, Capability-Namen,
Allow-Boolean, IdP-Claim, E-Mail-Match oder Environment-Flag einspeisen.

Eine globale Trust-Authority kann keine workspacebezogene Authority vergeben.
Ein Workspace-Manager kann nur Authorities im exakt gleichen Workspace-Scope
verwalten.

## 5. Authority-Set statt unabhängiger Blindschreibvorgänge

Authority-Lifecycle betrifft nicht nur eine Zielzeile. Ob Deaktivierung sicher
ist, hängt vom gesamten aktuell wirksamen Authority-Set des Scopes ab.

Darum erhält jeder Scope eine stabile aktuelle Authority-Set-Revision:

- genau eine globale Revision für OIDC-Trust-Management;
- genau eine unabhängige Revision pro Workspace für Membership-Management.

Eine Revision bezeichnet den vollständigen Satz aller Authority-Zuordnungen
und ihrer active/inactive-Status nach einem Commit. Sie ist intern erzeugt,
nicht wiederverwendbar, repr-frei und nicht aus IDs, Zeit oder Hash abgeleitet.

Jede reguläre Änderung verlangt die exakt erwartete aktuelle Set-Revision.
Fehlend oder abweichend endet neutral fail-closed. Es gibt kein Last-write-wins
und kein blindes Upsert.

Die Änderung selbst darf als zielbezogene Absicht formuliert werden; die
persistente Entscheidung erzeugt daraus atomar eine neue vollständige
Authority-Set-Revision. Der Aufrufer liefert niemals einen vollständigen
caller-kontrollierten Allow-Satz.

## 6. Erlaubte reguläre Übergänge

Eine spätere reguläre Grenze darf genau folgende Absichten kennen:

- `GRANT`: erstmalige aktive Authority für einen bestehenden aktiven Zielnutzer;
- `DEACTIVATE`: vorhandene aktive Authority auf inaktiv setzen;
- `REACTIVATE`: vorhandene inaktive historische Authority wieder aktiv setzen.

Es gibt kein physisches Löschen, Überschreiben der Ziel-UserId, Rollen-Upgrade,
Transfer durch Umdeutung oder automatische Vererbung.

Ein Transfer erfolgt als zwei explizite geordnete Fakten: zuerst Grant oder
Reaktivierung eines zweiten aktiven Managers, danach Deaktivierung des alten
Managers mit der dadurch neu entstandenen erwarteten Set-Revision.

Grant auf bereits vorhandene aktive oder inaktive Historie ist kein Upsert.
Aktive Wiederholung verlangt technischen Retry derselben Change-ID; inaktive
Historie verlangt ausdrücklich `REACTIVATE`.

## 7. Schutz vor Authority-Lockout

Eine reguläre Deaktivierung darf niemals dazu führen, dass im betroffenen Scope
kein wirksamer Manager mehr verbleibt.

Nach der geplanten Änderung muss mindestens eine Authority aktiv sein, deren
gebundener Nutzer aktuell aktiv ist. Bei Membership-Management muss zusätzlich
der Workspace aktuell aktiv sein.

Die Prüfung und Deaktivierung erfolgen in derselben Schreibtransaktion unter
derselben Konkurrenzordnung wie die neue Set-Revision und Change-Entscheidung.

Selbstdeaktivierung ist zulässig, wenn mindestens ein anderer aktuell wirksamer
Manager verbleibt. Sie ist neutral abgelehnt, wenn der Actor der letzte
wirksame Manager ist.

Eine spätere Nutzerdeaktivierung außerhalb dieser Grenze kann dennoch alle
Authority-Actors unwirksam machen. Deshalb bleibt eine getrennte Recovery-
Grenze erforderlich; Authority-Lifecycle darf Nutzer-Lifecycle nicht heimlich
kontrollieren.

## 8. Bootstrap-Verankerung ohne erfundene Historie

Die bestehenden Bootstrap-Tabellen enthalten Authority-Status, aber noch keine
Authority-Set-Revision.

Eine Migration darf ihnen nicht kommentarlos eine generierte Revision
zuweisen. Das würde einen historischen autorisierten Lifecycle-Commit erfinden.

Der spätere Foundation-Slice muss daher einen expliziten einmaligen
Verankerungsvorgang pro bereits gebootstrapptem Scope vorsehen.

Verankerung ist nur zulässig, wenn:

- Authority-Historie vorhanden ist;
- noch keine Set-Revision und keine Lifecycle-Change-Entscheidung existiert;
- der Bestand strukturell gültig ist;
- mindestens ein wirksamer aktiver Manager vorhanden ist;
- der aufrufende Actor aktuell genau diese bestehende Authority besitzt.

Die Verankerung erzeugt atomar die erste unveränderliche Set-Revision, ohne
Authority-Status zu ändern. Sie ist eine eigene stabile Change-Entscheidung und
kein Re-Bootstrap.

Teilbestand, bereits verankerter oder widersprüchlicher Bestand und Scope ohne
wirksamen Manager enden neutral beziehungsweise technisch fail-closed gemäß
späterem konkretem Vertrag.

## 9. Stabile Lifecycle-Change-ID

Jede Verankerung, Grant-, Deactivate- oder Reactivate-Entscheidung besitzt eine
intern erzeugte, persistente und nicht wiederverwendbare domänenspezifische
Change-ID.

Eine exakte technische Wiederholung derselben Change-ID liefert die bereits
committete Ergebnisrevision ohne zweite Mutation und ohne erneute aktuelle
Authority-Auflösung.

Damit bleibt ein unklarer Commit-Ausgang auflösbar, auch wenn Actor oder
Authority danach deaktiviert wurden.

Dieselbe Change-ID mit anderem Actor, Scope, Zielnutzer, Intent oder erwarteter
Set-Revision ist ein detailfreier Konflikt.

OIDC-Trust-Authority-Change-IDs und Workspace-Membership-Authority-Change-IDs
sind getrennte Typen und Inventare. Eine ID aus einer Domäne ist in der anderen
strukturell unbrauchbar.

## 10. Atomarität und Konkurrenz

Für eine neue reguläre Änderung werden atomar geordnet:

1. bestehende Change-Entscheidung oder neuer Vorgang;
2. aktive Actor-, Zielnutzer- und gegebenenfalls Workspace-Foundation;
3. aktuelle Authority des Actors im exakten Scope;
4. exakt erwartete Authority-Set-Revision;
5. zulässiger Zielübergang;
6. bei Deaktivierung mindestens ein verbleibender wirksamer Manager;
7. neuer Authority-Status;
8. neue unveränderliche vollständige Set-Revision;
9. persistente Change-Entscheidung.

Alles committet oder nichts. Es gibt keinen Check-then-act über getrennte
Transaktionen, In-Process-Lock, Authority-Cache oder automatischen Retry.

Gleichzeitige Grant-, Deactivate-, Reactivate-, Foundation-Deaktivierungs- und
fachliche Trust-/Membership-Änderungen müssen vom normativen Persistenzsystem
in eine sichtbare Reihenfolge gebracht werden.

Nach Commit sperrt Entzug jede später neu begonnene fachliche Mutation, ohne
bereits committete technische Retries unauflösbar zu machen.

## 11. Kontrollierte Offline-Recovery

Recovery ist keine reguläre Authority-Mutation und öffnet Bootstrap niemals
wieder.

Sie ist nur erforderlich, wenn ein Scope Authority-Historie besitzt, aber kein
aktiver bestehender Nutzer daraus aktuell Authority ausüben kann.

Eine spätere Offline-Recovery darf ausschließlich eine bereits historisch für
diesen exakten Scope autorisierte UserId reaktivieren. Sie darf keine neue
Person auswählen und keine Authority in einen anderen Scope übertragen.

Der Zielnutzer muss weiterhin als interner Nutzer existieren und aktiv sein.
Bei workspacebezogener Recovery muss auch der Workspace aktiv sein.

Ist kein historisch autorisierter Nutzer aktiv, bleibt Recovery geschlossen.
Die Reaktivierung eines Nutzers gehört zu einer separaten Nutzer-Lifecycle-
Grenze und darf nicht als Nebenwirkung erfolgen.

Recovery verlangt:

- owner-only Offline-Prozess und Eingabedateien;
- explizite domänenspezifische Recovery-ID;
- exakt erwartete aktuelle oder zuletzt bekannte Set-Revision;
- persistente unveränderliche Recovery-Entscheidung;
- atomare Reaktivierung und neue Set-Revision;
- sichere exakte Wiederholung nach unklarem Ausgang;
- detailfreie Ablehnung und technische Fehler.

Ein Environment-Allow, Admin-Header, Datenbankbesitz, Deployment-Skript oder
direktes SQL ist kein Recovery-Credential.

## 12. Recovery bei fehlender Set-Verankerung

Bootstrap-Bestand ohne erste Set-Revision ist kein regulärer Recovery-Fall.

Solange mindestens ein Bootstrap-Manager wirksam ist, muss dieser zuerst die
kontrollierte Verankerung ausführen.

Ist bereits vor Verankerung kein historischer Bootstrap-Manager mehr als
aktiver Nutzer verfügbar, kann die Authority-Grenze allein nicht sicher
fortfahren. Sie darf weder eine neue UserId wählen noch Nutzerstatus ändern.

Dieser Zustand ist ein expliziter manueller Security-/Identity-Lifecycle-
Blocker und kein Anlass für Re-Bootstrap oder SQL-Reparatur in diesem Vertrag.

## 13. Ablehnung, Konflikt und technische Nichtverfügbarkeit

Unbekannter oder inaktiver Actor, Zielnutzer oder Workspace, fehlende aktuelle
Authority, stale Set-Revision, unzulässiger Übergang und Schutz des letzten
wirksamen Managers ergeben dieselbe detailfreie fachliche Ablehnung.

Sie verrät weder Nutzer-, Scope-, Authority-, Status- noch Revisionsbestand.

Wiederverwendung einer Change- oder Recovery-ID mit anderem Inhalt bleibt ein
eigener detailfreier Konflikt.

Datenbank-, Transaktions-, Generator-, Encoding-, Decoding-, Constraint- oder
Strukturfehler sind getrennte detailfreie technische Nichtverfügbarkeit.

Keine Antwort oder Exception enthält Actor, Zielnutzer, Workspace, Authority,
Status, Revision, Change-/Recovery-ID, SQL, DSN, Tabellen- oder ursprüngliche
Fehlerdetails. `BaseException` bleibt ungefangen.

## 14. Retention und Nichtwiederverwendung

Authority-Zuordnungen werden nicht physisch gelöscht oder unter neuer Bedeutung
wiederverwendet.

Set-Revisionen, Lifecycle-Change- und Recovery-Entscheidungen bleiben
mindestens so lange unterscheidbar, wie fachliche Mutation, technischer Retry,
Security-Auswertung oder Audit darauf verweisen kann.

Restore oder Reimport darf inaktive Authority, alte Set-Revision oder
verwendete ID nicht als neue aktive Tatsache umdeuten.

Konkrete Fristen, Auditfelder, Genehmigungsnachweise und Datenschutzverfahren
bleiben späteren Slices vorbehalten, müssen aber diese Untergrenzen erhalten.

## 15. Folgeordnung und LQ-177

Die sichere Implementierungsreihenfolge lautet:

1. getrennte stabile IDs und persistente Set-Revision-/Change-Foundation je
   Authority-Domäne;
2. kontrollierte einmalige Verankerung bestehender Bootstrap-Fakten;
3. reguläre atomare Grant-/Deactivate-/Reactivate-Grenzen;
4. getrennte owner-only Operatorgrenzen;
5. eng begrenzte domänenspezifische Offline-Recovery;
6. End-to-End-Inbetriebnahme- und Offboarding-Nachweis;
7. erneuter finaler LQ-177-Abschlussaudit.

LQ-177 bleibt bis zu diesen Lifecycle-/Recovery-Pfaden und dem End-to-End-
Nachweis konkret blockiert. Runtime-, Trust-, Membership-, Bootstrap- und
Operator-Grundfunktionen sind dagegen nicht mehr die Ursache.

## 16. Bewusst nicht enthalten

- keine Modelle, Ports, Exceptions, Tabellen, Migrationen oder SQL,
- keine Authority-, Nutzer-, Workspace-, Membership- oder Trust-Mutation,
- keine Verankerung oder Recovery-Implementierung,
- keine Route, CLI, Settings- oder Environment-Option,
- keine generische Admin-Rolle oder domänenübergreifende Capability,
- kein Deployment, Audit-Log oder finaler Production-Readiness-Claim.
