# LQ-177 — Kontrollierte Wiederaufnahme des Production-Wirings

## 1. Status und Ziel

LQ-177 war blockiert, solange persistente Nutzer-, Workspace-, Authority-,
Admission-, Login-Transaktions- und Session-Grundlagen fehlten. LQ-184 bis
LQ-191 haben diese Grundlagen hergestellt. Dieser Slice nimmt das Wiring
bewusst nur für den vollständig entscheidbaren Runtime-Teil wieder auf:
persistentes Session-Lookup und persistente Logout-Revocation.

OIDC-Login-Start, Callback und geschützte Research-Routen bleiben geschlossen,
solange ihre übrigen Production-Abhängigkeiten fehlen. Der Slice erfindet keine
Trust-Konfiguration, Verifier-Composition oder Membership-Persistenz.

## 2. Eine Engine und klare Eigentümerschaft

`create_app` kann eine bereits besessene `database_engine` erhalten. Diese
Engine wird für Readiness und persistente Session-Fähigkeiten wiederverwendet.
Die App schließt eine injizierte Engine niemals.

Wird weiterhin ausschließlich `settings.database_url` verwendet, erzeugt
`create_app` genau eine Engine und besitzt sie. Nur diese intern erzeugte Engine
wird beim Ende des App-Lifespans disposed. Es gibt keine zweite Engine, keinen
zweiten Pool und keine erneute DSN-Lektüre für Sessions.

## 3. Automatisches persistentes Session-Wiring

Besitzt die App eine Engine und wurden weder `logout_sessions` noch
`logout_revocations` explizit injiziert, wird genau ein
`DatabaseBrowserSessions` erzeugt und für beide Ports verwendet. Lookup und
Revocation entscheiden dadurch über denselben persistenten Bestand.

Explizite vollständige Logout-Abhängigkeiten haben Vorrang und werden nicht
überschrieben. Eine partielle explizite Kombination bleibt wie bisher ein
fail-fast Konfigurationsfehler.

Die Logout-Route behält ihren bestehenden Sicherheitsvertrag: aktive Session
und serverseitiges CSRF müssen übereinstimmen; unbekannt, abgelaufen oder
entzogen antworten neutral; erfolgreiche Revocation löscht das Cookie und wirkt
auf spätere Lookups.

## 4. Bewusst geschlossene Routen

Eine Datenbank allein aktiviert weder OIDC-Login-Start noch Callback. Dafür
fehlen weiterhin mindestens persistente beziehungsweise vertrauenswürdig
komponierte aktive OIDC-Client-Konfiguration, Verifier und validierte
Destination-Policy. Das bestehende All-or-nothing-Dependency-Gate bleibt
unverändert.

Geschützte Research-Routen werden ebenfalls nicht durch Session-Persistenz
allein aktiviert. Ihnen fehlt die reguläre persistente Membership- und
Research-Permission-Auflösung. `SessionPrincipal` identifiziert nur und darf
kein Research-Recht ersetzen.

Bootstrap, internes Onboarding und Admission-Provisionierung erhalten keine
Route, CLI oder automatische Startup-Ausführung. Die internen Compositions aus
LQ-188/LQ-191 werden nicht versehentlich öffentlich gemacht.

## 5. Fehler- und Geheimnisgrenze

Die persistente Session-Grenze behält ihre detailfreie technische
Nichtverfügbarkeit. Keine DSN, Session-ID, UserId, CSRF, SQL- oder
Treiberinformation wird durch das Wiring geloggt oder in HTTP-Antworten
übernommen.

Readiness verwendet dieselbe Engine und verlangt weiterhin den exakten
Migration-Head. Eine veraltete Datenbank wird nicht als einsatzbereit gemeldet.
Es gibt keinen SQLite-Fallback in Production und keinen automatischen
Migration- oder Retry-Schritt beim App-Start.

## 6. Nachweis und Restfolge

Tests beweisen persistentes Logout über eine migrierte Datenbank, wirksame
Revocation, fortbestehende externe Engine-Eigentümerschaft, Vorrang expliziter
Dependencies und das Geschlossenbleiben unvollständiger OIDC-/Research-Routen.
Bestehende Route- und Architekturtests bleiben unverändert grün.

LQ-177 ist damit **teilweise und sicher wiederaufgenommen**, nicht vollständig
abgeschlossen. Die nächsten notwendigen Slices sind persistente aktive
OIDC-Client-Konfiguration samt Production-Verifier-Composition sowie reguläre
Membership-Persistenz. Erst danach dürfen Login-/Callback- und geschützte
Research-Routen über dieselbe Engine aktiviert werden.

## 7. Abschlussaudit nach LQ-192 bis LQ-196

Die damals benannten Adapter- und Factory-Blocker sind inzwischen behoben:

- LQ-192 speichert genau eine aktuelle aktive OIDC-Konfiguration persistent;
- LQ-193 komponiert aktuellen Trust, Token Exchange, JWKS und Verifier;
- LQ-194 verdrahtet Login-Start und Callback in `create_app` all-or-nothing;
- LQ-195 löst reguläre Membership und Research-Permissions persistent auf;
- LQ-196 bindet persistente Sessions und Memberships an Research-Read/-Start.

Die App-Factory ist damit sicher komponierbar. Der reale Process-Entrypoint
`transport.http.main.build_app` verwendet diese neue OIDC-Composition jedoch
noch nicht: Er übergibt ausschließlich Settings und optional den lokalen
Research-Resolver. `PlatformSettings` und `runtime.env.example` besitzen keine
Felder für Verification-Policy, vertrauenswürdigen Login-Origin, Login- und
Session-Lifetime oder Callback-Ziele. Der Entrypoint erzeugt und besitzt auch
keinen synchronen OIDC-HTTP-Client.

Diese Werte dürfen nicht mit Library-Defaults, Host-/Forwarded-Headern oder
hartcodierten Produktionsannahmen ergänzt werden. Ein extern erzeugter Client
braucht außerdem eine explizite Lifecycle-Entscheidung; LQ-194 behandelt ihn
absichtlich als extern besessen und schließt ihn nicht.

## 8. Verbleibende Control-Plane-Lücken

Auch die Datenbestände sind absichtlich noch read-only. Es gibt keine
unterstützte Grenze zum erstmaligen Setzen, Rotieren, Aktivieren oder
Deaktivieren der persistenten OIDC-Konfiguration und keine reguläre Grenze zum
Erzeugen, Ändern oder Entziehen von Memberships und Research-Permissions.

Bootstrap und internes Onboarding erzeugen diese Tatsachen ausdrücklich nicht.
Direktes SQL, Migration-Seeds, Environment-Bootstrap oder Login-basierte
Selbstfreischaltung sind kein zulässiger Ersatz. Ohne spätere explizite
Control-Plane-Grenzen kann ein sauber migriertes System daher sicher geschlossen
sein, aber nicht über einen unterstützten Workflow vollständig in Betrieb
genommen oder regulär verwaltet werden.

## 9. Auditentscheidung

LQ-177 bleibt **teilweise umgesetzt und konkret blockiert**. Die Blockade liegt
nicht mehr in fehlenden Runtime-Adaptern oder Route-Composition, sondern an:

1. fehlender Process-Konfiguration und HTTP-Client-Ownership für LQ-194;
2. fehlender OIDC-Konfigurationsverwaltung;
3. fehlender regulärer Membership-/Permission-Verwaltung.

Die sichere Reihenfolge ist: zuerst ein eigener Slice für den vollständigen
Process-Vertrag der OIDC-Betriebswerte und den Lifecycle des ausgehenden
HTTP-Clients; danach getrennte autorisierte Mutationsgrenzen für OIDC-Trust und
Memberships. Erst wenn diese Grenzen implementiert und Ende-zu-Ende geprüft
sind, darf LQ-177 als vollständig abgeschlossen oder ein Shared Environment als
betriebsbereit bezeichnet werden.

## 10. Fortschritt durch LQ-197

LQ-197 hat Blocker 1 behoben: `PlatformSettings` besitzt nun eine atomare,
explizite OIDC-Betriebsgruppe, der reale Entrypoint konstruiert Policy und
validierte Ziele, und genau ein Process-eigener HTTP-Client wird ohne
Environment-Inheritance erzeugt und im App-Lifespan geschlossen.

LQ-177 bleibt weiterhin teilweise blockiert, aber nur noch an den Punkten 2
und 3: unterstützte autorisierte Mutation der aktiven OIDC-Konfiguration sowie
reguläre Membership-/Permission-Verwaltung. Die Runtime erfindet diese
persistenten Trust- und Authority-Fakten weiterhin nicht.

## 11. Erneuter Abschlussaudit durch LQ-204

LQ-198 bis LQ-203 haben den früheren OIDC-Konfigurationsblocker vollständig in
getrennten Schichten geschlossen: globale Authority- und Revisionsgrundlage,
einmaliger Authority-Bootstrap-Port, revisionsgebundener Login, atomare
autorisierte Trust-Mutation und owner-only Offline-Operatorgrenze sind
implementiert.

Der reale Runtime-Prozess importiert diese Operatorgrenze nicht und besitzt
weiterhin keine Management-Route. Das ist die richtige Trennung und kein
offener OIDC-Runtime-Wiring-Fehler.

LQ-177 ist dennoch noch nicht vollständig abgeschlossen. Ein frisch migriertes
Shared Environment kann die Voraussetzungen der Operatorgrenze nicht über
einen unterstützten Prozess herstellen: InitialIdentityAuthorityBootstrap und
InitialOidcTrustAuthorityBootstrap existieren nur als interne Ports/Adapter,
nicht als kontrollierte Offline-Prozedur. LQ-203 kann ohne bereits vorhandenen
aktiven Actor und globale Trust-Authority absichtlich nichts aktivieren.

Zusätzlich bleiben Workspace-Membership und Research-Permissions read-only.
Es gibt keinen autorisierten regulären Workflow zum Anlegen, Ändern,
Deaktivieren oder Entziehen dieser Tatsachen. Damit können Research-Routen
sicher prüfen, aber ein Shared Environment nicht unterstützt verwalten.

Auch die globale Trust-Authority besitzt nach dem einmaligen Bootstrap noch
keine reguläre Transfer-, Vergabe-, Deaktivierungs- oder Recovery-Grenze. Das
blockiert nicht den ersten Trust-Wechsel, ist aber ein Recovery- und
Offboarding-Blocker für dauerhaften Betrieb.

Der Audit verbietet weiterhin direkte SQL-Prozeduren, Migration-Seeds,
Environment-Allow-Werte, automatische Startup-Bootstraps und Login-basierte
Selbstfreischaltung als Ersatz.

Die verbleibende Reihenfolge ist daher:

1. kontrollierte Offline-Grenzen für den bereits implementierten initialen
   Identity- und Trust-Authority-Bootstrap;
2. eigener Authority-Vertrag und persistente atomare Mutation für Memberships
   und Research-Permissions;
3. reguläre Trust-Authority-Lifecycle-/Recovery-Grenze;
4. Ende-zu-Ende-Inbetriebnahme aus leerem migriertem Bestand;
5. erst danach endgültige LQ-177-Abschlussfreigabe.

Auditentscheidung: **OIDC-Trust-Runtime und -Mutation sind geschlossen, LQ-177
als betrieblicher Gesamtpfad bleibt wegen Bootstrap-, Membership- und Recovery-
Control-Plane-Grenzen konkret blockiert.**

## 13. End-to-End-Audit durch LQ-218

LQ-205 bis LQ-217 schließen inzwischen die dort genannten Bootstrap-,
Membership- und Authority-Lifecycle-/Recovery-Fähigkeiten einschließlich
getrennter owner-only Operatorgrenzen.

Der unterstützte leere Startpfad erzeugt jedoch weiterhin genau einen internen
Nutzer und Workspace. Ohne reguläre Nutzer- und Workspace-Lifecycle-Grenzen
kann kein zweiter aktiver Manager für sichere Rotation, Membership-
Provisionierung oder vorbereitete Recovery entstehen. Der letzte-Manager-
Schutz lehnt die Deaktivierung des einzigen Bootstrap-Managers korrekt ab.

LQ-177 bleibt daher nicht wegen Runtime-Wiring oder Authority-Lifecycle,
sondern wegen fehlender regulärer Nutzer-/Workspace-Control-Plane und des
darauf aufbauenden Mehrnutzer-End-to-End-Nachweises blockiert. Direkte SQL-
Anlage, OIDC-Self-Sign-up, Bootstrap-Wiederöffnung und Recovery einer nie
historisch autorisierten Person bleiben unzulässige Ersatzwege.

## 12. Fortschritt durch LQ-205

LQ-205 schließt den operativen Bootstrap-Blocker aus LQ-204. Der separate
owner-only Offline-Prozess ruft ausschließlich die bestehenden einmaligen
Identity- und Trust-Authority-Bootstrap-Ports auf und kann einen unklaren
Ausgang nur aus exakt kanonischem Bestand read-only rekonstruieren.

Ein leerer migrierter Bestand kann damit unterstützt die erste Identity-
Foundation, globale Trust-Authority und anschließend über LQ-203 aktiven OIDC-
Trust herstellen. HTTP-Runtime, Startup und Deployment erhalten keinen
Bootstrap-Shortcut.

LQ-177 bleibt noch blockiert durch reguläre Membership-/Research-Permission-
Mutation, Trust-Authority-Lifecycle/Recovery nach dem einmaligen Bootstrap und
den vollständigen End-to-End-Inbetriebnahmenachweis.

## 13. Fortschritt durch LQ-206 bis LQ-210

LQ-206 bis LQ-210 schließen den regulären Membership-/Research-Permission-
Mutationsblocker: dedizierte workspacebezogene Authority, historische
Revisionen, einmaliger Authority-Bootstrap, atomare vollständige Mutation und
owner-only Offline-Operatorgrenze sind implementiert.

Der HTTP-Prozess importiert diese Managementgrenze nicht. Research-Requests
sehen Änderungen weiterhin ausschließlich über den aktuellen LQ-195-Lookup.

LQ-177 bleibt nun an den getrennten regulären Authority-Lifecycle-/Recovery-
Pfaden für Membership-Management und globales OIDC-Trust-Management sowie am
vollständigen End-to-End-Inbetriebnahmenachweis blockiert.

## 14. Lifecycle-Audit durch LQ-226

LQ-219 bis LQ-225 schließen inzwischen auch die in LQ-218 benannte reguläre
User-/Workspace-Control-Plane. LQ-226 bestätigt gegen PostgreSQL den
unterstützten Weg vom ersten Bootstrap über einen systemgenerierten zweiten
Nutzer bis zu einem systemgenerierten zweiten Workspace mit atomar gebundenem
ersten Onboarding-Manager.

Damit verbleibt kein konkret benannter Produktfähigkeitsblocker aus den
bisherigen LQ-177-Audits. Die Production-Freigabe bleibt dennoch offen, bis ein
letzter integrierter Mehrnutzer-Nachweis Bootstrap, Rotation, Membership,
Entzug, Recovery und beobachtbare Runtime-Wirkung in einer Kette verbindet.

Direktes SQL, Seeds, Startup-Bootstrap und Self-Sign-up bleiben auch für diesen
abschließenden Nachweis unzulässig.

## 15. Integrierter Audit durch LQ-227

LQ-227 findet einen letzten operativen Übergabeblocker: Der initiale
Identity-Bootstrap erzeugt sichere zufällige User- und Workspace-Lifecycle-
Revisionen, gibt im owner-only Resultat aber nur UserId und WorkspaceId aus.

Die regulären Lifecycle-Operatoren benötigen die jeweilige exakte
Current-Revision bereits für den ersten zweiten Nutzer beziehungsweise
Workspace. Kein unterstützter Offline-Lookup stellt diese Werte bereit. Der
LQ-226-PostgreSQL-Test kennt sie nur durch direkt injizierte Testgeneratoren
und bildet diesen Betriebsübergang daher nicht ab.

LQ-177 bleibt bis zu einer kontrollierten minimalen Revision-Beobachtbarkeit
blockiert. Direktes SQL, feste Initialrevisionen und revisionslose erste
Mutation bleiben unzulässig.

## 16. Observability-Vertrag durch LQ-228

LQ-228 entscheidet die kleinste sichere Schließung: Das bestehende owner-only
Identity-Bootstrap-Resultat soll neben UserId und WorkspaceId genau die beiden
beim Commit erzeugten Lifecycle-Revisionen ausgeben.

Frischer Erfolg und exakte kanonische Retry-Rekonstruktion müssen denselben
Vier-Felder-Shape liefern. Es entsteht kein allgemeiner Current-State-
Operator, keine revisionslose erste Mutation und keine neue Authority.

LQ-177 bleibt bis zur Implementierung in LQ-229 und dem danach erneut
ausgeführten integrierten Mehrnutzernachweis blockiert.

## 17. Implementierung durch LQ-229

LQ-229 implementiert den Vier-Felder-Shape ohne Domain-, Port- oder
Persistenzsignaturänderung. Frischer Bootstrap bewahrt exakt die atomar
gezogenen Revisionen; kanonische Recovery liest dieselben Current-Pointer.

Ein integrierter Test verwendet diese owner-only Ausgabe ohne injiziertes
Revisionswissen für reguläre zweite Nutzer- und Workspace-Anlage. Der konkrete
Revision-Übergabeblocker ist geschlossen.

LQ-177 wartet nun nur noch auf den erneut vollständigen LQ-230-Nachweis über
Authority-Rotation, Membership, Entzug, Recovery-Einordnung und beobachtbare
Runtime-Wirkung.

## 18. Integrierter Nachweis durch LQ-230

LQ-230 ergänzt einen durchgängigen markierten PostgreSQL-Test ohne direkte
SQL-Provisionierung fachlicher Fakten. Er verbindet Bootstrap, zweiten Nutzer,
zweiten Workspace, beide Authority-Rotationen, Membership-/Research-Vergabe,
persistente Session, erfolgreichen Runtime-Zugriff und späteren neutralen
Entzug im selben App-Prozess.

Recovery bleibt bei vorhandenem wirksamem Manager neutral geschlossen; der
getrennte Disaster-Fall bleibt durch LQ-217 belegt.

Es ist kein weiterer Produktfähigkeitsblocker bekannt. LQ-177 bleibt nur noch
bis zum tatsächlichen verpflichtenden Lauf dieser integrierten Kette in einer
mit PostgreSQL und Testabhängigkeiten ausgestatteten Umgebung unverifiziert.

## 19. Abschlussverifikation durch LQ-231

LQ-231 hat den LQ-230-Einzelnachweis, alle 74 markierten PostgreSQL-
Integrationen und anschließend die vollständige Suite tatsächlich ausgeführt.

Nach Aktualisierung zweier veralteter Testfixtures bestanden 2887 Tests ohne
Fehler. Die PostgreSQL-Suite lief mit Pflicht-DSN und ohne Skip- oder SQLite-
Fallback.

Damit ist LQ-177 auf Code-, Persistenz-, Control-Plane- und Runtime-Ebene
verifiziert abgeschlossen. Konkretes Deployment, Secrets, IdP-Konfiguration,
Monitoring und organisatorische Freigabe bleiben environmentbezogene separate
Aufgaben und wurden nicht ausgeführt.

## 20. Release-Handoff durch LQ-232

LQ-232 bestätigt den technisch abgeschlossenen LQ-177-Stand als bereit für
kontrollierten menschlichen Review. Migrationen sind linear, Operator-Runbooks
vollständig, Runtime und Control Plane getrennt und die gesamte Suite grün.

Der kumulierte Worktree ist jedoch nicht gestaged oder committed und befindet
sich auf detached HEAD. Diese Git-Publikationsschritte sowie jedes reale
Deployment bleiben außerhalb von LQ-177 und wurden nicht automatisch
ausgeführt.
