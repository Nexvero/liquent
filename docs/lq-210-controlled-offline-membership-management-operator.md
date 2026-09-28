# LQ-210 — Controlled Offline Membership Management Operator

## Ergebnis

LQ-210 stellt LQ-208 und LQ-209 über den separaten Console Entry Point
`liquent-membership-management` bereit.

Der Prozess besitzt drei getrennte Operationen:

- `new-change-id` erzeugt eine sichere interne Change-ID;
- `bootstrap-authority` ruft den einmaligen workspacebezogenen LQ-208-Port auf;
- `apply` delegiert einen vollständigen Membership-Snapshot an LQ-209.

Es entsteht keine HTTP-Route, Runtime-Settings-Option, Environment-Authority,
Startup-Ausführung oder Migration.

## Sichere Change-ID-Erzeugung

`new-change-id` verwendet den bestehenden sicheren LQ-207-Materialgenerator
und führt keinen Datenbank- oder Dateizugriff aus.

Die ausgegebene `WorkspaceMembershipChangeId` muss vor `apply` in der
kontrollierten Request-Datei bewahrt werden.

`apply` erzeugt niemals spontan eine Change-ID. Ein technisch unklarer Ausgang
wird ausschließlich durch Wiederholung derselben unveränderten Request-Datei
aufgelöst.

Eine neue Change-ID bezeichnet einen neuen fachlichen Snapshot. Sie ist kein
Authority-Token und kein öffentlicher Idempotency-Key.

## Authority-Bootstrap-Request

Der Bootstrap-Request enthält exakt:

- vorhandene interne UserId,
- vorhandene interne WorkspaceId.

Unbekannte oder fehlende Felder werden abgelehnt. Actor, Session, Membership,
Permission, Rolle, Capability-Name und Allow-Boolean können nicht angegeben
werden.

Die Operation ruft ausschließlich
`DatabaseInitialWorkspaceMembershipManagementAuthorityBootstrap` auf.

Ist der Port bereits geschlossen, rekonstruiert die Operatorgrenze nur dann
`recovered`, wenn in diesem Workspace genau eine aktive Authority für exakt
dieselbe aktive UserId existiert und der Workspace aktiv ist.

Anderes, zusätzliches oder inaktives Inventar bleibt neutral `rejected`. Es
gibt kein Überschreiben, Reaktivieren oder Force-Flag.

## Membership-Request

Der Apply-Request enthält exakt:

- Actor-UserId,
- bewahrte Change-ID,
- Ziel-UserId,
- WorkspaceId,
- erwartete Revision oder `null`,
- `active` oder `inactive`,
- vollständige Permission-Liste.

Strings werden nicht getrimmt, normalisiert oder case-gefaltet. Unbekannte,
fehlende, doppelte oder falsch typisierte Werte werden abgelehnt.

Die Permission-Liste akzeptiert ausschließlich die bestehenden Werte
`research:read` und `research:write`. Doppelte Einträge werden nicht zu einer
Menge normalisiert, sondern als unklare Eingabe abgelehnt.

Inaktive Requests müssen eine leere Liste enthalten. Aktive Requests dürfen
leer sein oder eine beziehungsweise beide expliziten Permissions enthalten.

Es gibt keinen Patch, Grant-/Revoke-Befehl, Rollennamen, Merge, Default oder
Übernahme aus dem aktuellen Membership-Bestand.

## Authority bleibt in LQ-209

Die Actor-UserId im Request identifiziert nur. Der Operator prüft keine
Membership-Management-Capability vorab und akzeptiert keinen Authority-Beleg.

Aktiver Actor, Zielnutzer, Workspace, dedizierte Authority, erwartete Revision,
Snapshot und Change-Entscheidung werden ausschließlich in der atomaren
LQ-209-Persistenzgrenze entschieden.

Onboarding-Authority, Research-Permission und globale OIDC-Trust-Authority
werden nicht umgedeutet.

## Private Datei- und Ergebnisgrenze

Datenbank-URL und Request müssen vorhandene owner-only reguläre Dateien sein.
Symbolische Links sowie Group-/World-Rechte werden fail-closed abgelehnt.

Die DSN wird weder als Prozessargument noch als Environment-Variable
akzeptiert. Trust-, Membership- und Authority-Werte werden nicht als einzelne
CLI-Argumente angenommen.

Jede schreibende Operation verlangt einen noch nicht vorhandenen Result-Pfad in
einem owner-only Verzeichnis. Das Ergebnis wird exklusiv als temporäre
0600-Datei geschrieben, synchronisiert und atomar an den Zielpfad verschoben.

Vorhandene Ergebnisse werden niemals überschrieben. Ergebnisdateien enthalten:

- beim Bootstrap nur UserId und WorkspaceId,
- bei Apply nur Change-ID und resultierende Membership-Revision.

Diese Dateien sind keine Capabilities. Sie bewahren die internen Fakten für
Recovery und die nächste explizit geprüfte Änderung.

## Retry nach unklarem Ausgang

Ein erfolgreicher DB-Commit kann vor dem Schreiben der Ergebnisdatei erfolgt
sein. Der Operator erzeugt deshalb Ergebnisse erst aus dem Portresultat und
erlaubt eine Wiederholung mit identischem Request und neuem absent Result-Pfad.

Beim Authority-Bootstrap wird nur exakt kanonischer gleicher Bestand read-only
rekonstruiert.

Bei Membership-Apply erkennt LQ-209 die Change-ID, vergleicht Actor, Ziel,
Workspace, Vorgängerrevision, Status und vollständige Permissions und liefert
dieselbe Ergebnisrevision zurück.

Der Retry bleibt auch nach späterem Authority-Entzug auflösbar und erzeugt
keine zweite Revision.

## Ausgaben und Fehler

Erfolg gibt ausschließlich `bootstrapped`, `recovered` oder `applied` mit Exit
0 aus.

Neutrale fachliche Ablehnung gibt ausschließlich `rejected` mit Exit 5 aus und
unterscheidet Authority-, Foundation-, Membership- oder Revisionsbestand nicht.

Ungültige Operator-Eingabe, Change-ID-Konflikt und technische
Nichtverfügbarkeit besitzen getrennte konstante detailfreie Fehlercodes und
non-zero Exits.

Keine Ausgabe enthält Actor, Zielnutzer, Workspace, Permission, Revision,
Change-ID, DSN, SQL, Tabelle, Constraint oder ursprüngliche Exception.
`BaseException` bleibt ungefangen.

## Prozessbesitz

Jeder schreibende Aufruf erzeugt genau eine Process-eigene Engine und disposed
sie in `finally`.

Der Prozess migriert nicht, startet keinen HTTP-Client, importiert keine ASGI-
App und führt keinen Startup- oder Providerzugriff aus.

Transportfreie Parsing-, Bootstrap- und Apply-Funktionen behalten injizierte
Engines im Besitz des Aufrufers.

## Runbook und Tests

Das Runbook `operations/runbooks/workspace-membership-management.md`
beschreibt private Vorbereitung, Bootstrap, Change-ID-Erzeugung, Erstanlage,
Folgeänderung, Deaktivierung, Reaktivierung, Retry und Cleanup.

Die Tests belegen:

- exaktes owner-only Parsing ohne Normalisierung,
- Ablehnung unbekannter, doppelter und unzulässiger Werte,
- sichere Change-ID-Erzeugung,
- vollständige Bootstrap- und Apply-Kette,
- owner-only atomare Ergebnisdatei mit resultierender Revision,
- exakten Apply-Retry nach Authority-Entzug ohne zweite Revision,
- Bootstrap-Recovery nur für exakt dasselbe Ziel,
- neutrale Ablehnung eines anderen Bootstrap-Ziels,
- fehlendes Überschreiben vorhandener Resultate,
- separaten paketierten Console Entry Point.

Die bestehenden PostgreSQL-Konkurrenznachweise von LQ-208 und LQ-209 bleiben
für die normative Schreibordnung maßgeblich.

## Wirkung auf LQ-177

Der Membership-/Research-Permission-Mutationsblocker ist operativ geschlossen.
Ein Shared Environment kann die erste workspacebezogene Management-Authority
bootstrapen und Membership-Snapshots unterstützt anlegen, ändern, deaktivieren
und reaktivieren.

Offen bleiben der reguläre Membership-Management-Authority-Lifecycle/Recovery,
der globale OIDC-Trust-Authority-Lifecycle/Recovery und der vollständige
End-to-End-Inbetriebnahmenachweis.

## Bewusst nicht enthalten

- keine reguläre Authority-Vergabe, -Deaktivierung, -Übertragung oder Recovery,
- keine Nutzer-, Workspace-, Onboarding- oder OIDC-Trust-Mutation,
- keine Legacy-Adoption,
- keine HTTP- oder Startup-Grenze,
- kein Deployment oder finaler LQ-177-Abschluss.

## Nächster Schritt

LQ-211 sollte die verbleibenden Authority-Lifecycle- und Recovery-Anforderungen
für workspacebezogenes Membership-Management und globales OIDC-Trust-
Management gemeinsam auditieren, aber ihre getrennten Authority-Domänen nicht
zu einer allgemeinen Admin-Rolle zusammenführen.
