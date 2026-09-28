# LQ-226 — User and Workspace Lifecycle End-to-End Audit

## 1. Ergebnis

LQ-226 auditiert die vollständige User- und Workspace-Lifecycle-Kette aus
LQ-219 bis LQ-225 unabhängig end-to-end.

Der in LQ-218 benannte vorgelagerte Control-Plane-Blocker ist geschlossen:
Ein leerer migrierter Bestand kann unterstützt den ersten Actor bootstrappen,
einen zweiten internen Nutzer regulär erzeugen und diesen als ersten
Onboarding-Manager eines regulär erzeugten zweiten Workspace binden.

Der Slice ergänzt keine neue Produktfunktion. Er korrigiert einen überholten
historischen Auditnachweis und fügt PostgreSQL- sowie Architekturbelege hinzu.

## 2. Auditumfang

Geprüft wurden:

- der LQ-219-Vertrag;
- persistente Foundation und Migrationen aus LQ-220;
- leerer Bootstrap und einmalige Bestandsverankerung aus LQ-221;
- getrennte Lifecycle-Authority-Sets aus LQ-222;
- Nutzer- und Workspace-Mutationen aus LQ-223 und LQ-224;
- beide owner-only Operatoren aus LQ-225;
- PostgreSQL-Konkurrenz und die reale PostgreSQL-Operator-Kette;
- Runtime-Isolation und fehlende Ersatzwege.

## 3. Korrektur des historischen LQ-218-Nachweises

LQ-218 enthielt absichtlich einen Test, nach dem weder Lifecycle-Ports noch
Operator-Kommandos für reguläre Nutzer und Workspaces existieren durften.

Diese Aussage belegte damals den konkreten Restblocker. Nach LQ-223 bis LQ-225
ist sie historisch überholt und würde die korrekte Schließung selbst als
Regression markieren.

Der Test verlangt nun die beiden expliziten Lifecycle-Ports und bestätigt
zugleich, dass ihre Offline-Operatoren nicht in HTTP-App oder Entrypoint
importiert werden.

## 4. Unterstützte Kette aus leerem Bestand

Der initiale Identity-Bootstrap erzeugt atomar:

- den ersten aktiven Nutzer;
- den ersten aktiven Workspace;
- dessen ersten Onboarding-Manager;
- beide ersten globalen Lifecycle-Authorities;
- vollständige erste Nutzer- und Workspace-Revisionen.

Migration, Startup und Login erzeugen keinen dieser Faktenbestände.

Der Bootstrap bleibt nach Erfolg geschlossen und dient nicht als reguläre
Mehrnutzer- oder Multi-Workspace-Grenze.

## 5. Reguläre zweite Nutzeranlage

Der User-Lifecycle-Operator akzeptiert Actor, stabile Change-ID und exakt
erwartete vollständige Nutzerrevision.

Er akzeptiert keine Ziel-UserId. Die persistente Mutation erzeugt diese erst
innerhalb derselben autorisierten Transaktion und speichert sie dauerhaft.

Der zweite Nutzer ist danach aktiver interner Fakt, besitzt aber keine
Identity-Bindung, Session, Admission, Membership, Permission oder Authority.

Damit ist er sicher als Ziel für getrennte spätere Onboarding-, Membership-
und Authority-Prozesse erreichbar, ohne Rechte aus seiner Existenz abzuleiten.

## 6. Reguläre zweite Workspaceanlage

Der Workspace-Lifecycle-Operator akzeptiert keine Ziel-WorkspaceId.

Er bindet den explizit benannten zweiten aktiven Nutzer als ersten
Onboarding-Manager und erzeugt Workspace sowie diese eine Authority atomar.

Der Audit bestätigt, dass dabei keine gewöhnliche Membership und keine
Research-Permission entsteht. Membership-Management-Bootstrap und reguläre
Membership-Mutation bleiben getrennte nachgelagerte Prozesse.

## 7. PostgreSQL-Nachweis

Ein markierter Integrationstest verwendet die disposable PostgreSQL-Grenze,
migriert auf den echten Head und führt beide LQ-225-Operatoren aus.

Die Kette startet mit dem atomaren Bootstrap, erzeugt den zweiten Nutzer über
den User-Operator und verwendet ausschließlich dessen private Resultat-ID als
ersten Manager der Workspace-Anlage.

Anschließend liest der Test den normativen Store und bestätigt:

- aktiven zweiten Nutzer;
- aktiven zweiten Workspace;
- exakt dessen aktive Onboarding-Manager-Bindung;
- weiterhin null gewöhnliche Memberships;
- owner-only Resultatdateien beider Prozesse.

## 8. Konkurrenz und Revisionen

Die bestehenden PostgreSQL-Nachweise konkurrieren je zwei Creates gegen
dieselbe erwartete User- beziehungsweise Workspace-Revision.

Genau ein konkurrierender Versuch erzeugt eine Folgerevision; der andere wird
neutral abgelehnt. Es entsteht kein verzweigter Current-Bestand.

Jede neue Entscheidung vergleicht die vollständige Persistenz erneut mit der
erwarteten Revision. Widerspruch wird nicht als fachlicher Teilbestand
fortgeschrieben, sondern detailfrei technisch geschlossen.

## 9. Retry nach Authority-Entzug

Die LQ-225-End-to-End-Nachweise wiederholen einen bereits committeten Create
nach committiertem Entzug der Actor-Authority.

Die stabile Change-ID löst dasselbe historische Resultat einschließlich
derselben intern erzeugten Ziel-ID auf.

Eine neue Change-ID bleibt dagegen gesperrt. Damit behauptet der Retry keine
fortbestehende Authority und Widerruf wirkt auf spätere Entscheidungen.

## 10. Deaktivierung und Drain

Nutzerdeaktivierung bleibt an vollständigen Drain aller lebenden Sessions,
Admissions, Memberships und Management-Authorities gebunden.

Der Lifecycle-Adapter verändert keine dieser fremden Domänen selbst.
Reactivate stellt ausschließlich Nutzerstatus wieder her.

Workspace-Deaktivierung ist terminal. Sie bewahrt historische Child-Fakten,
deren Wirksamkeit wegen des inaktiven Workspace fail-closed endet.

Diese asymmetrische Entscheidung verhindert eine gemeinsame stillschweigende
Wiederbelebung alter Workspace-Fähigkeiten.

## 11. Nichtwiederverwendung und Retention

Der Audit findet keinen Delete- oder ID-Reassignment-Pfad in beiden regulären
Lifecycle-Adaptern.

UserId, WorkspaceId, Change-ID und Revision-ID bleiben historische interne
Fakten. Statusänderung überschreibt ihre Bedeutung nicht.

Immutable Change-Entscheidungen und vollständige Revisionen bilden weiterhin
die untere Retention-Grenze für Retry und Audit. LQ-226 ergänzt keine
Aufbewahrungsfrist und keinen Löschprozess.

## 12. Runtime-Isolation

HTTP-App und realer Entrypoint importieren weder die beiden Operatoren noch
deren autorisierte Persistenzadapter.

Es gibt keine Lifecycle-Route, Browserrolle, Admin-Header-, Environment-Allow-
oder Startup-Ausführung.

Die Entry Points bleiben getrennte kontrollierte Offline-Prozesse und
besitzen keine Bootstrap-, Anchor-, Recovery- oder Migrationskommandos.

## 13. Fehlergrenzen

Neutrale Abwesenheit, fehlende Authority, falscher Status, nicht erfüllter
Drain und stale Revision bleiben einheitliches `rejected` ohne Detail.

Malformed Input, abweichende Change-ID-Wiederverwendung und technische
Nichtverfügbarkeit bleiben getrennte detailfreie Prozessausgänge.

Resultate enthalten ausschließlich Change-ID, Revision-ID und systemgebundene
Ziel-ID. Sie sind owner-only, exklusiv und werden nicht überschrieben.

## 14. Keine neue Migration oder Produktmutation

Der aktuelle Migration-Head bleibt `20260813_0016`.

LQ-226 ergänzt keine Tabelle, Spalte, Constraint, SQL-Entscheidung, Port-,
Modell-, Adapter- oder Operatorfunktion.

Die einzige Verhaltensänderung im Testbestand ist die zeitgerechte Korrektur
der überholten LQ-218-Negativbehauptung.

## 15. LQ-177-Entscheidung

Der nach LQ-218 verbliebene reguläre Nutzer-/Workspace-Lifecycle-Blocker ist
geschlossen.

Damit sind alle bislang konkret benannten notwendigen Produktfähigkeiten für
die kontrollierte Shared-Environment-Kette implementiert: Runtime-Wiring,
Bootstrap, Trust, Membership, Authority-Lifecycle/Recovery sowie regulärer
Nutzer- und Workspace-Lifecycle.

LQ-226 erklärt ein Shared Environment dennoch nicht isoliert für freigegeben.
Es fehlt der letzte integrierte Nachweis, der diese unterstützten Grenzen in
einer einzigen Mehrnutzer-Kette bis Rotation, Membership, Entzug, Recovery und
Runtime-Wirkung zusammensetzt.

## 16. Bewusst nicht enthalten

LQ-226 implementiert keine:

- neue Nutzer-, Workspace-, Membership- oder Authority-Mutation;
- Migration oder Datenreparatur;
- HTTP-, UI-, Settings- oder Startup-Verdrahtung;
- Bootstrap-Wiederöffnung oder Recovery-Erweiterung;
- automatische Drain-, Cascade- oder Cleanup-Funktion;
- Deployment-Aktion oder Production-Freigabe;
- Aussage über konkrete Infrastruktur, Credentials oder Providerdaten.

## 17. Nächster Slice

LQ-227 soll den abschließenden integrierten LQ-177-Shared-Environment-Audit
ausführen.

Er muss die unterstützte Kette aus leerem migriertem PostgreSQL-Bestand über
zweiten Nutzer, zweiten Workspace, Authority-Rotation, Membership/Research-
Vergabe und Entzug bis zur beobachtbaren Runtime-Wirkung verbinden.

Er darf fehlende Schritte nicht durch direktes SQL, Seeds, Startup-Bootstrap,
Self-Sign-up oder Abschwächung von Lockout- und Recovery-Regeln ersetzen.
