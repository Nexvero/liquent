# LQ-230 — Integrated Shared Environment Audit

## 1. Ergebnis

LQ-230 wiederholt den integrierten LQ-177-Shared-Environment-Audit nach
Schließung der Revision-Übergabelücke durch LQ-229.

Ein neuer markierter PostgreSQL-Test bildet die unterstützte Kette aus einem
leeren migrierten Bestand bis zur beobachtbaren Runtime-Autorisierung und
deren späterem Entzug ab.

Der Audit findet keinen weiteren fehlenden Produktpfad. Die lokale isolierte
Arbeitsumgebung kann den Test jedoch mangels installierter Runtime- und
Testabhängigkeiten nicht ausführen. Eine Production-Freigabe bleibt deshalb an
den erfolgreichen verpflichtenden PostgreSQL-Lauf in einer ausgestatteten
Verifikationsumgebung gebunden.

## 2. Auditprinzip

Fachliche Produktfakten werden ausschließlich über vorhandene kontrollierte
Operatorgrenzen erzeugt oder verändert.

Der Test verwendet kein direktes SQL für:

- Nutzer oder Workspaces;
- Lifecycle-Revisionen oder Authorities;
- OIDC-Trust- oder Membership-Authority;
- gewöhnliche Membership oder Research-Permissions;
- Entzug oder Recovery-Zustand.

Die disposable PostgreSQL-Fixture migriert vor Testbeginn regulär auf Head.

## 3. Initialer Bootstrap

Die Kette startet mit `liquent-initial-bootstrap identity`.

Das owner-only Vier-Felder-Resultat liefert:

- ersten Actor;
- ersten Workspace;
- initiale User-Lifecycle-Revision;
- initiale Workspace-Lifecycle-Revision.

Keine ID und keine Revision wird im Test vorgegeben oder aus Persistenz
gelesen.

## 4. Zweiter Nutzer

Der Test übergibt Actor und `user_revision_id` aus dem Bootstrap-Resultat an
`liquent-user-lifecycle create`.

Die zweite UserId wird vom sicheren Materialgenerator innerhalb der
autorisierten Persistenztransaktion erzeugt und ausschließlich aus dem
owner-only Resultat gelesen.

Der neue Nutzer erhält aus seiner Existenz keine Membership oder Authority.

## 5. Zweiter Workspace

`liquent-workspace-lifecycle create` erhält die initiale
`workspace_revision_id` und bindet die systemgenerierte zweite UserId als
ersten Onboarding-Manager.

Auch die zweite WorkspaceId entsteht intern. Der Test gibt sie nicht vor.

Die Anlage bleibt von gewöhnlicher Membership, Research-Permission und
Membership-Management-Authority getrennt.

## 6. Globale Trust-Authority-Kette

Der initiale Actor erhält über den getrennten einmaligen Bootstrap die erste
OIDC-Trust-Management-Authority.

Der reguläre Authority-Operator verankert den vollständigen Set-Bestand,
erteilt anschließend dem zweiten Nutzer Authority und deaktiviert erst danach
den ursprünglichen Actor.

Damit bleibt zu jedem regulären Schritt mindestens ein wirksamer Manager
vorhanden und der Last-Manager-Schutz wird nicht abgeschwächt.

## 7. Workspacebezogene Membership-Authority-Kette

Für den ersten Workspace bootstrapped die getrennte Membership-Grenze die
erste Management-Authority des ursprünglichen Actors.

Nach Set-Verankerung wird der zweite Nutzer hinzugefügt. Erst gegen die neue
vollständige Set-Revision wird der ursprüngliche Actor deaktiviert.

Scope, Actor, Ziel und erwartete Revision stammen aus den geschützten
Operatorresultaten; keine Rolle oder Allow-Aussage wird injiziert.

## 8. Reguläre Membership und Research-Permissions

Der nun wirksame zweite Membership-Manager erzeugt für sich im ersten
Workspace eine aktive gewöhnliche Membership mit den expliziten Permissions:

- `research:read`;
- `research:write`.

Die erste Membership-Revision verwendet vertragsgemäß `expected_revision:
null`, weil für diesen Workspace noch kein gewöhnlicher Membership-Snapshot
existiert.

Dieser revisionslose Anfang gehört ausschließlich zur LQ-209-Membership-
Foundation und lockert keine User- oder Workspace-Lifecycle-Revision.

## 9. Persistente Session als Runtime-Eingang

Der Test legt für den zweiten Nutzer eine aktive Browser-Session über
`DatabaseBrowserSessions.add_session` an.

Das ist derselbe persistente Port, den der OIDC-Callback nach erfolgreicher
Admission verwendet. Es wird weder eine Sessionzeile per SQL erzeugt noch ein
caller-supplied Principal direkt an die Research-Route übergeben.

Session-ID, Principal, CSRF und Ablauf bleiben serverseitige persistente
Fakten.

## 10. Beobachtbare positive Runtime-Wirkung

`create_app` erhält dieselbe externe PostgreSQL-Engine und einen Research-Job,
dessen gespeicherter Workspace exakt der erste Workspace ist.

Der Browser sendet nur das Session-Cookie. Die Runtime löst daraus aktuell:

- aktive persistente Session;
- aktiven internen Nutzer;
- aktiven Workspace;
- aktive Membership;
- aktuelle `research:read`-Permission.

Der erste Request liefert 200 und den geschützten Job.

## 11. Autorisierter Entzug

Während derselbe App-Prozess läuft, setzt der zweite Manager die Membership
über `liquent-membership-management apply` gegen die exakte resultierende
Revision auf inaktiv und liefert eine leere Permissionmenge.

Der Operator mutiert ausschließlich die Membership-Domäne. Session, Nutzer,
Workspace und Job bleiben unverändert.

Es gibt keinen Cache-Flush oder App-Neustart im Test.

## 12. Beobachtbare spätere Verweigerung

Der nächste Request verwendet dasselbe Session-Cookie und denselben Job.

Die Runtime liest die Membership erneut aus PostgreSQL. Der committierte
Entzug wirkt deshalb sofort auf diese spätere Entscheidung.

Die Route antwortet neutral mit 404 `research_job_not_found` und verrät weder
Membership- noch Permissionbestand.

## 13. Recovery-Einordnung

Nach beiden Authority-Rotationen besitzt der zweite Nutzer weiterhin die
wirksame Trust- beziehungsweise Membership-Management-Authority.

Recovery des historischen ursprünglichen Actors wird deshalb in beiden
Domänen neutral abgelehnt und erzeugt keine Resultatdatei.

Das ist der korrekte gesunde Betriebsfall. Erfolgreiche Disaster-Recovery
bleibt durch die getrennten LQ-217-PostgreSQL-Nachweise unter exakt fehlendem
wirksamem Manager belegt.

## 14. Warum kein künstlicher Disaster-Zustand entsteht

Reguläre APIs verhindern durch Last-Manager- und User-Drain-Schutz, dass der
Test einen managerlosen Bestand absichtlich herstellt.

Eine direkte SQL-Deaktivierung des letzten Managers wäre kein unterstützter
Workflow und würde den integrierten Nachweis verfälschen.

LQ-230 verbindet deshalb neutral geschlossene Recovery im gesunden Pfad mit
dem separaten eng begrenzten Disaster-Recovery-Nachweis, statt Schutzregeln zu
umgehen.

## 15. Datei- und Prozessgrenzen

Jeder Operator erhält die DSN aus derselben owner-only Datei und schreibt in
einen neuen exklusiven Resultatpfad.

Alle vorhandenen Resultate werden im Test auf Modus 0600 geprüft. IDs und
Revisionen werden nur zwischen geschützten JSON-Dateien und Requests
weitergegeben.

HTTP-App und Operatorprozesse bleiben getrennt. Die injizierte Engine bleibt
extern besessen.

## 16. Verifikationsstatus

Syntaxprüfung und `git diff --check` bestehen in der isolierten Arbeitsumgebung.

Der Test ist als `postgres_integration` markiert und verwendet die bestehende
disposable PostgreSQL-Fixture ohne SQLite-Fallback.

Die lokale Python-Installation enthält weder `pytest` noch `sqlalchemy` und
kann den Test daher nicht starten. Das ist kein beobachteter Testfehler, aber
der erfolgreiche normative Lauf bleibt ein explizites Release-Gate.

## 17. LQ-177-Entscheidung und nächster Schritt

Der Audit findet keinen verbleibenden fachlichen oder architektonischen
Produktfähigkeitsblocker aus der LQ-177-Kette.

LQ-177 darf dennoch erst nach erfolgreichem verpflichtendem PostgreSQL-Lauf
des neuen integrierten Tests als verifiziert abgeschlossen markiert werden.

LQ-231 soll diesen Verifikationslauf in einer vollständig ausgestatteten
Umgebung ausführen, alle markierten PostgreSQL-Nachweise gemeinsam prüfen und
danach die finale Shared-Environment-Readiness-Entscheidung dokumentieren.

Es darf keine Freigabe allein aus Syntaxprüfung oder Testcode-Inspektion
ableiten.

## 18. Verifikation durch LQ-231

LQ-231 hat das Release-Gate mit einem isolierten lokalen PostgreSQL-16-Cluster
tatsächlich ausgeführt. Der LQ-230-Einzelnachweis bestand mit 1 Test.

Nach Korrektur zweier historisch veralteter PostgreSQL-Testvorbedingungen
bestand die vollständige Marker-Suite mit 74 Tests und die gesamte Suite mit
2887 Tests. Der in Abschnitt 16 beschriebene Ausführungsblocker ist damit
aufgehoben.
