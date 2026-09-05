# LQ-206 — Authorized Workspace Membership Management Contract

## 1. Status und Ziel

LQ-206 ist eine reine Architekturentscheidung vor regulärer Membership- und
Research-Permission-Mutation.

Der Slice implementiert keine Python-Typen, Ports, Adapter, Migration, Tabelle,
SQL-Strategie, Tests, Route, CLI, Settings, Operator-Authentisierung oder
Production-Verdrahtung.

LQ-195 kann persistente Memberships und Research-Permissions aktuell
fail-closed lesen. LQ-196 bindet diese Entscheidungen an Research-Routen. Offen
ist, wer Memberships regulär anlegen, deaktivieren, reaktivieren und deren
explizite Research-Permissions ersetzen darf.

Dieser Vertrag entscheidet Authority, Zielbindung, vollständige
Änderungssemantik, Revision, Konkurrenz, Retry, Entzug, Retention und
Fehlergrenzen, ohne das spätere Schema vorwegzunehmen.

## 2. Eigene workspacebezogene Management-Capability

Membership-Verwaltung erfordert eine dedizierte persistente Capability für
genau einen Workspace.

Keine bestehende Tatsache impliziert diese Capability:

- weder `research:read` noch `research:write`,
- keine aktive oder inaktive gewöhnliche Membership,
- keine workspacebezogene Onboarding-Management-Capability,
- keine globale OIDC-Trust-Management-Authority,
- kein Bootstrap-Nutzer oder Bootstrap-Workspace,
- keine Admission, Identity-Bindung, Session oder erfolgreicher Login.

Die Fähigkeit „interne Identitäten in diesem Workspace onboarden“ ist nicht
gleichbedeutend mit „Membership und Research-Zugriff verwalten“. Beide können
später derselben Person explizit gewährt werden, bleiben aber unabhängige
persistente Fakten und unabhängige Entscheidungsgrenzen.

Umgekehrt gewährt Membership-Management selbst keine Research-Permission,
gewöhnliche Membership, Onboarding-Authority oder globale Trust-Authority.

Es gibt keine allgemeine Admin-Rolle und keine Rangordnung, aus der diese
Capability abgeleitet wird.

## 3. Actor und aktuelle Authority-Auflösung

Eine reguläre Änderung erhält einen bereits authentifizierten
`SessionPrincipal`. Dieser identifiziert nur den Actor und trägt keine
Authority, Membership, Rolle oder Permission.

Die persistente Schreibgrenze löst in derselben konsistenten Entscheidung auf:

1. der Actor existiert und ist aktuell aktiv;
2. der Zielworkspace existiert und ist aktuell aktiv;
3. der Zielnutzer existiert und ist aktuell aktiv;
4. der Actor besitzt aktuell für exakt diesen Workspace die aktive
   Membership-Management-Capability.

Transport oder Aufrufer dürfen keinen alternativen Actor, Rollennamen,
Capability-Namen oder Allow-Boolean einspeisen. IdP-Claims, E-Mail-Adressen,
Header und Sessionbesitz sind kein Ersatz.

Die Ziel-UserId und WorkspaceId müssen aus einem kontrollierten internen
Managementvorgang stammen. Ihre Typisierung beweist Existenz und Authority
nicht; die Schreibgrenze bindet beide erneut an das System of Record.

Authority gilt nur für den exakt geprüften Workspace. Eine Capability in
Workspace A erlaubt keine Änderung in Workspace B.

## 4. Bootstrap der ersten Management-Authority

Die erste Membership-Management-Capability kann nicht durch den regulären
Mutationspfad entstehen, weil dieser sie bereits voraussetzt.

Dafür ist eine eigene spätere Offline-Bootstrap-Grenze erforderlich. Sie darf
nicht aus Onboarding-Authority, Research-Rechten oder globaler Trust-Authority
folgern.

Verbindliche Untergrenzen sind:

- Ziel sind ein bereits vorhandener aktiver interner Nutzer und Workspace;
- atomare Anlage genau der ersten workspacebezogenen Management-Authority;
- kein HTTP-, Login-, Environment- oder Migration-Seed-Bootstrap;
- dauerhafte zustandsbasierte Schließung für denselben initialisierten Scope;
- keine Wiederöffnung durch Deaktivierung, Restore oder Reimport;
- keine Membership oder Research-Permission als Nebenwirkung.

Ob die Bootstrap-Inventur global einmalig oder pro Workspace geschlossen wird,
und wie spätere reguläre Authority-Vergabe und Recovery funktionieren, muss der
nächste Foundation-Slice explizit entscheiden. LQ-206 erfindet dafür keine
Signatur oder Tabelle.

## 5. Vollständiger gewünschter Membership-Snapshot

Eine reguläre Änderung beschreibt den vollständigen gewünschten Zustand eines
einzigen UserId-/WorkspaceId-Paars.

Der aktive Zustand enthält:

- `MembershipStatus.ACTIVE`,
- eine explizite Menge aus null bis zwei bestehenden Research-Permissions.

Eine aktive Membership ohne Permission ist zulässig und gewährt nichts.
`research:write` wird persistent nicht automatisch um `research:read` ergänzt;
die bestehende reine Policy bleibt allein für Write-impliziert-Read zuständig.

Der inaktive gewünschte Zustand enthält zwingend eine leere explizite
Permission-Menge. Deaktivierung entfernt damit alle aktuellen Permission-
Fakten atomar und bewahrt keine schlafenden Rechte für spätere Reaktivierung.

Reaktivierung ist eine neue vollständige Änderung. Sie muss die künftig
gewünschten Permissions erneut ausdrücklich nennen.

Es gibt kein partielles Grant-/Revoke-Patch, keine Rolle, kein Merge mit dem
aktuellen Bestand, keine abgeleitete Default-Permission und kein Kopieren aus
einem anderen Nutzer oder Workspace.

## 6. Erlaubte Zustandsübergänge

Die spätere Grenze unterstützt fachlich:

- erstmalige Anlage einer aktiven Membership mit vollständiger Permission-Menge;
- vollständigen Ersatz der Permissions einer aktiven Membership;
- Deaktivierung mit atomarem Entfernen aller Permissions;
- Reaktivierung mit neu explizit gesetzter vollständiger Permission-Menge.

Physisches Löschen und Wiederanlegen unter derselben UserId-/WorkspaceId-
Bedeutung ist kein regulärer Übergang. Die historische Membership-Tatsache
bleibt erhalten.

Eine Änderung darf weder Nutzer noch Workspace erzeugen, aktivieren oder
reaktivieren. Sie darf ebenso keine Onboarding- oder Membership-Management-
Authority vergeben oder entziehen.

Selbstverwaltung ist nicht automatisch verboten oder erlaubt. Besitzt der
Actor für denselben Workspace die dedizierte aktuelle Management-Capability,
darf die spätere Policy eine Änderung seiner gewöhnlichen Membership wie jede
andere Zieländerung behandeln. Die Management-Capability selbst bleibt davon
unberührt.

## 7. Stabile Membership-Revision

Jeder erfolgreich committete vollständige Membership-Zustand erhält eine neue
intern erzeugte, global nicht wiederverwendbare Revision.

Die Revision bezeichnet genau UserId, WorkspaceId, Membership-Status und die
explizit gespeicherte Permission-Menge dieses Commits. Sie wird nicht aus IDs,
Zeit, Status, Permission-Liste oder Hash abgeleitet und nicht vom Browser
gewählt.

Auch das erneute Setzen fachlich identischer Werte als neuer Vorgang erzeugt
eine neue Revision. Eine alte Revision wird niemals auf neue Werte umgebogen.

Erstmalige Anlage verlangt als Vorbedingung neutrale Abwesenheit einer
Membership-Revision. Jede spätere Änderung muss die exakt erwartete aktuelle
Revision nennen.

Fehlt die aktuelle Revision oder weicht sie ab, endet der Vorgang neutral. Es
gibt keinen Last-write-wins-Fallback und kein blindes Upsert.

Bestehende revisionslose Legacy-Membership-Zeilen dürfen nicht stillschweigend
einer erfundenen Revision zugeordnet werden. Migration, kontrollierte Adoption
oder fail-closed Ausschluss müssen später separat entschieden werden.

## 8. Stabile Änderungsidentität und Retry

Jeder fachliche Wechsel besitzt eine intern erzeugte, persistente,
nicht wiederverwendbare Change-ID. Sie ist kein öffentlicher Idempotency-Key,
keine Revision und keine Authority.

Eine exakte technische Wiederholung derselben Change-ID liefert die bereits
committete Entscheidung ohne zweite Revision und ohne erneute aktuelle
Authority-Auflösung. So bleibt ein unklarer Commit-Ausgang auflösbar, selbst
wenn Actor oder Authority danach deaktiviert wurden.

Dieselbe Change-ID mit anderem Actor, Zielnutzer, Workspace, erwarteter
Revision, Status oder Permission-Menge ist ein detailfreier Konflikt.

Eine fachlich neue Änderung benötigt eine neue intern kontrollierte Change-ID.
Transport erzeugt bei einem Retry nicht spontan eine Ersatz-ID.

Abgelehnte neue Änderungen werden nicht als erfolgreiche Entscheidung
gespeichert und erzeugen keine Revision.

## 9. Atomarität und Konkurrenz

Für eine neue Änderung werden in genau einer persistenten Schreibordnung
entschieden:

1. aktuelle Actor-, Zielnutzer- und Workspace-Aktivität;
2. aktuelle dedizierte Management-Authority für diesen Workspace;
3. aktuelle Membership-Abwesenheit oder erwartete Revision;
4. Anlage der unveränderlichen neuen Membership-Revision;
5. vollständiger Membership-Status und vollständige Permission-Menge;
6. unveränderliche Change-Entscheidung.

Alles committet oder nichts. Ein Check-then-act über getrennte Transaktionen,
In-Process-Lock, Authority-Cache oder automatischer Retry ist unzulässig.

Gleichzeitige Membership-Änderungen, Authority-Entzug und Foundation-
Deaktivierung werden vom normativen Persistenzsystem in eine sichtbare
Reihenfolge gebracht. Nach Commit sieht jeder spätere LQ-195-Lookup den neuen
vollständigen Zustand.

Bereits autorisierte Research-Aktionen werden nicht rückwirkend verändert.
Jede spätere Anfrage löst den aktuellen Zustand erneut auf.

## 10. Entzug und Deaktivierung

Ein committierter Entzug der Membership-Management-Capability sperrt jede
danach neu begonnene Änderung für diesen Actor und Workspace.

Deaktivierung des Actors, Zielnutzers oder Workspace wirkt ebenso fail-closed.
Keine Membership-Operation reaktiviert eine Foundation-Tatsache implizit.

Membership-Deaktivierung und Permission-Entzug wirken auf den nächsten
Research-Lookup. SessionPrincipal und bestehende Session frieren frühere Rechte
nicht ein.

Entzug der Management-Capability verändert keine bereits committierte
Membership und verhindert nicht die exakte technische Wiederholung einer
bereits gespeicherten Change-ID.

Reguläre Vergabe, Entzug und Recovery der Management-Capability benötigen eine
eigene spätere Authority-Lifecycle-Grenze. Membership-Mutation darf diese
Capability niemals selbst verändern.

## 11. Ablehnung, Konflikt und technische Nichtverfügbarkeit

Unbekannter oder inaktiver Actor, Zielnutzer oder Workspace, fehlende oder
entzogene Management-Authority, unzulässiger Zustandsübergang und fehlende oder
abweichende erwartete Revision ergeben dieselbe detailfreie fachliche
Ablehnung.

Sie verrät weder Foundation-, Authority-, Membership- noch Permission-Bestand.

Wiederverwendung einer Change-ID mit anderem Inhalt bleibt ein eigener
detailfreier Konflikt.

Datenbank-, Transaktions-, Generator-, Encoding-, Decoding-, Constraint- oder
Strukturfehler sind davon getrennte detailfreie technische Nichtverfügbarkeit.
Sie dürfen nicht als Ablehnung, Konflikt oder Erfolg getarnt werden.

Keine Antwort oder Exception enthält Actor, Zielnutzer, Workspace, Status,
Permission, Revision, Change-ID, SQL, DSN, Tabellen- oder ursprüngliche
Fehlerdetails. `BaseException` bleibt ungefangen.

## 12. Retention und Nichtwiederverwendung

UserId, WorkspaceId, Membership-Bedeutung, Revision und Change-ID dürfen nicht
so gelöscht oder wiederverwendet werden, dass eine alte Session, Research-
Referenz, technische Wiederholung oder Sicherheitsauswertung auf neue Fakten
zeigt.

Deaktivierte Memberships und historische Revisionen bleiben mindestens so
lange unterscheidbar, wie Entscheidungen, Jobs, Evidence, Retry oder Audit auf
sie verweisen können.

Konkrete Fristen, Löschverfahren, Auditfelder und Datenschutz-Workflows bleiben
späteren Slices vorbehalten. Restore oder Reimport darf keine inaktive
Membership, entzogene Permission oder alte Revision unter neuer Bedeutung
reaktivieren.

## 13. Nicht enthalten und Folgeordnung

Nicht enthalten sind Modell- und Portnamen, Signaturen, Exceptions, Tabellen,
Migrationen, SQL, Tests, Bootstrap- oder reguläre Operatorgrenze, HTTP, Rollen,
Einladungen, Gruppen, Teams, Organisationen, Audit-Log und Deployment.

Die sichere Folgeordnung lautet:

1. persistente Foundation für dedizierte Membership-Management-Authority,
   Membership-Revision und Change-Entscheidung;
2. einmaliger kontrollierter Bootstrap der ersten Authority;
3. atomare autorisierte vollständige Membership-Mutation;
4. kontrollierte Offline- oder interne Operatorgrenze;
5. regulärer Authority-Lifecycle/Recovery getrennt von Membership-Mutation;
6. End-to-End-Inbetriebnahmenachweis und erneuter LQ-177-Abschlussaudit.

Der globale OIDC-Trust-Authority-Lifecycle bleibt eine unabhängige Kette. Kein
Folgeslice darf beide Managementdomänen oder Onboarding-Management in eine
allgemeine Admin-Rolle zusammenführen.
