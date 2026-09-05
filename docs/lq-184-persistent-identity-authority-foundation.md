# LQ-184 — Persistente Identity- und Autoritätsgrundlage

## 1. Ziel und Grenze

Dieser Slice implementiert die in LQ-183 festgelegte Persistenzgrundlage für
interne Nutzer, Workspaces und die workspacebezogene Fähigkeit zur Anlage einer
Onboarding-Entscheidung. Er ergänzt eine additive Migration, stabiles
Lifecycle-Vokabular, einen read-only Port und einen Datenbankadapter.

Nicht enthalten sind Bootstrap, CLI, HTTP, Production-Wiring, Admission- oder
Onboarding-Anwendungsfall sowie reguläre Erzeugungs-, Vergabe-, Entzugs- oder
Membership-Schreibgrenzen. Tests setzen Bestandsdaten ausschließlich als
Fixtures direkt ein; daraus entsteht kein Produktions-Administrationsweg.

## 2. Persistente Tatsachen

`identity_users` und `identity_workspaces` speichern intern erzeugte IDs als
bytegenaue, nicht leere Primärschlüssel. Beide besitzen ausschließlich den
fail-closed Lifecycle `active` oder `inactive`. Die Migration erzeugt keine
Seed-Daten und ändert keine bestehende Admission oder Identity-Bindung.

Die Primärschlüssel sind die technische Nichtwiederverwendungs-Untergrenze:
Deaktivierte Einträge bleiben unter derselben Identität erhalten. Löschen,
Retention, Reaktivierung und ID-Erzeugung werden nicht implementiert. Spätere
Lifecycle-Grenzen dürfen alte IDs weder neu belegen noch durch Restore oder
Reimport unter neuer Bedeutung aktivieren.

## 3. Getrennte Management-Capability

`workspace_onboarding_management` bindet genau einen bestehenden Nutzer an
genau einen bestehenden Workspace. Ihr eigener Status ist `active` oder
`inactive`; ein inaktiver Eintrag hält den Entzug persistent fest und darf
keine spätere Entscheidung tragen.

Die Capability ist keine `WorkspaceMembership` und keine
`Permission.RESEARCH_READ` oder `Permission.RESEARCH_WRITE`. Sie erzeugt weder
Research-Zugriff noch gewöhnliche Membership. Umgekehrt erzeugen Membership,
Research-Recht, Identity-Bindung, Admission, Login oder Session keine
Management-Capability.

## 4. Port- und Vertrauensgrenze

`OnboardingManagementAuthorityLookup` erhält einen bereits authentifizierten
`SessionPrincipal`, einen intern ausgewählten Zielnutzer und Zielworkspace. Die
Signatur akzeptiert kein Allow-Boolean, keinen Rollennamen und keine frei
behauptete Capability.

`SessionPrincipal` identifiziert ausschließlich den Akteur. Der
Datenbankadapter löst bei jeder Entscheidung gemeinsam aus dem System of Record
auf:

1. der Akteur existiert und ist aktiv;
2. der Zielnutzer existiert und ist aktiv;
3. der Zielworkspace existiert und ist aktiv;
4. die Management-Capability bindet genau diesen Akteur aktiv an genau diesen
   Workspace.

Nur wenn alle Tatsachen vorliegen, ist das Ergebnis `True`. Der Workspace-Wert
autorisiert sich nie selbst; er selektiert lediglich die serverseitig
aufzulösende persistente Tatsache. Die spätere Onboarding-Grenze bleibt dafür
verantwortlich, den Zielworkspace aus einem serverseitig kontrollierten Vorgang
zu beziehen.

## 5. Fail-closed Entscheidung und Entzug

Unbekannter oder inaktiver Akteur, Zielnutzer oder Workspace sowie fehlende oder
inaktive Capability ergeben einheitlich `False`. Das Ergebnis verrät nicht,
welche Tatsache fehlt. Es gibt keinen Default-Workspace, keine Rollenabbildung,
keinen Cache und keinen Ersatz aus Research-Permissions.

Der Adapter liest für jeden Aufruf neu aus der Datenbank. Ein committeter Entzug
wirkt deshalb auf jede später begonnene Entscheidung. Dieser Slice speichert
noch keine Onboarding-Entscheidung und behauptet keine Atomizität zwischen
Authority-Prüfung und deren späterer Anlage; genau das gehört in den regulären
Onboarding-Anwendungsfall nach dem Bootstrap.

## 6. Technische Nichtverfügbarkeit

Ungültige Eingaben, Datenbank-, Verbindungs-, Transaktions- oder Strukturfehler
werden nicht als `False` getarnt. Sie verlassen den Adapter als getrennte,
detailfreie technische Nichtverfügbarkeit ohne Identifier, Status, SQL,
Constraint, Engine oder ursprüngliche Fehlerkette.

Der Adapter besitzt ein konstantes, wertfreies `repr`, schließt die injizierte
Engine nicht und führt keinen automatischen Retry aus. `BaseException` bleibt
ungefangen.

## 7. Migration und Nachweis

Revision `20260812_0003` folgt additiv auf `20260811_0002`. Sie erzeugt genau
die drei Foundation-Tabellen mit Lifecycle-Checks, Primärschlüsseln und
Foreign Keys der Capability auf Nutzer und Workspace. Es gibt keine Änderung
an bestehenden Tabellen, keine Backfill-Annahme und keine Seed-Daten.

SQLite beweist Migrationssyntax, leeren Anfangsbestand, Portstruktur und die
sequenzielle Semantik. Der markierte PostgreSQL-Test beweist auf dem normativen
Persistenzsystem, dass ein committeter Entzug in einer späteren Entscheidung
sichtbar ist. Nebenläufige atomare Onboarding-Anlage bleibt dem späteren
Anwendungsfall vorbehalten.

## 8. Folgeordnung

1. LQ-184 — diese persistente Foundation;
2. einmaliger atomarer Bootstrap des ersten Nutzers, Workspace und Managers;
3. reguläre autorisierte Onboarding-Entscheidung samt stabiler Request-ID;
4. reguläre Membership- und Capability-Mutation in eigenen Slices;
5. persistente Login-Transaktionen und Sessions;
6. danach Wiederaufnahme von LQ-177.
