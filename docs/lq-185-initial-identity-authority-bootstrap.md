# LQ-185 — Einmaliger Identity-Authority-Bootstrap

## 1. Ziel und Systemgrenze

Dieser Slice implementiert die einmalige Offline-Control-Plane-Grenze aus
LQ-182 auf der persistenten LQ-184-Foundation. Sie erzeugt atomar den ersten
aktiven Nutzer, den ersten aktiven Workspace und die aktive
Onboarding-Management-Capability dieses Nutzers für diesen Workspace.

Es entstehen kein HTTP-Endpunkt, keine öffentliche API, kein Admin-Header, kein
Environment-Bootstrap, kein Migration-Seed, kein Self-Sign-up und kein
First-login-Provisioning. Eine konkrete Operator-CLI, deren Authentisierung und
Production-Wiring bleiben spätere Entscheidungen.

## 2. Strukturell begrenzter Port

`InitialIdentityAuthorityBootstrap.bootstrap()` nimmt keine fachlichen
Argumente entgegen. Insbesondere akzeptiert die Grenze keine `UserId`,
`WorkspaceId`, Rolle, Permission, Capability oder Allow-Entscheidung vom
Aufrufer.

Die beiden IDs stammen aus getrennten injizierten internen Generatoren. Der
Adapter akzeptiert nur nicht leere eingebaute Zeichenketten und speichert deren
UTF-8-Bytes exakt, ohne Normalisierung, Trimming oder Case-Folding. Generatoren
werden erst nach bestätigter Leere und bei einem geschlossenen Bestand gar
nicht aufgerufen.

## 3. Zustandsbasierte Schließung

Bootstrap ist ausschließlich zulässig, wenn `identity_users`,
`identity_workspaces` und `workspace_onboarding_management` gemeinsam leer
sind. Bereits ein Nutzer, ein Workspace oder eine Management-Capability
schließt die Grenze. Aktivstatus und Herkunft des vorhandenen Eintrags ändern
daran nichts.

Die Schließung besitzt kein Flag, keinen Konfigurationswert und keine
Umgebungsvariable. Sie folgt allein aus dem persistenten Bestand. Deaktivieren,
Entziehen, Restore oder Reimport öffnen Bootstrap nicht wieder, weil die
historischen Foundation-Tatsachen erhalten bleiben.

`None` ist die neutrale fachliche Antwort für den bereits geschlossenen
Bestand. Sie unterscheidet weder Art, Anzahl noch Status vorhandener Tatsachen
und erzeugt oder verändert nichts.

## 4. Atomarer erster Bestand

Bei bestätigter Leere werden innerhalb derselben Datenbanktransaktion:

1. eine interne `UserId` und `WorkspaceId` erzeugt und validiert;
2. der aktive Nutzer gespeichert;
3. der aktive Workspace gespeichert;
4. die aktive workspacebezogene Onboarding-Management-Capability gespeichert.

Alle drei Tatsachen committen gemeinsam oder keine. Ein Generator-,
Validierungs-, Constraint-, Verbindungs- oder Commitfehler lässt keinen
Teilbestand zurück. Der erfolgreiche Rückgabewert
`BootstrappedIdentityAuthority` enthält exakt die beiden intern erzeugten IDs;
er gewährt selbst keine zusätzliche Autorität.

## 5. Konkurrenz

PostgreSQL ist die normative Konkurrenzgrenze. Vor der Leerheitsprüfung sperrt
der Adapter die drei Foundation-Tabellen in einer Transaktion. Gleichzeitige
Bootstrap-Versuche werden dadurch geordnet: genau einer kann den leeren
Bestand sehen und anlegen, jeder spätere sieht Bestand und erhält neutral
`None`.

Es gibt keinen In-Process-Lock, keinen globalen Anwendungsmutex, keinen
Check-then-act über getrennte Transaktionen und keinen automatischen Retry.
SQLite dient nur dem sequenziellen Vertrags- und Rollbacknachweis und wird
nicht als gleichwertiger Konkurrenzbeweis ausgegeben.

## 6. Fehler- und Datenschutzgrenze

Ein bereits geschlossener Bestand ist keine technische Störung. Eine
unbrauchbare ID-Quelle, fehlendes Schema, unbekannter Datenbankdialekt sowie
Datenbank-, Transaktions-, Struktur- oder Commitfehler sind dagegen
detailfreie technische Nichtverfügbarkeit.

Die technische Fehlerform trägt weder Identifier, Generatorwert, SQL,
Tabellen-, Constraint-, Engine-, Host- noch DSN-Details und verlässt die Grenze
ohne Cause oder Context. Der Adapter hat ein konstantes wertfreies `repr`,
schließt die injizierte Engine nicht und fängt `BaseException` nicht.

## 7. Nicht enthalten

Keine Migration und keine Schemaänderung: LQ-185 nutzt ausschließlich die
LQ-184-Tabellen. Nicht enthalten sind reguläre Nutzer-, Workspace-,
Membership-, Rollen- oder Capability-Anlage und -Mutation, Admission-
Provisionierung, Identity-Bindung, Onboarding-Entscheidung, Login, Session,
HTTP, CLI und Production-Wiring.

Der Bootstrap erzeugt insbesondere keine gewöhnliche Membership und keine
Research-Permission. Seine Management-Capability bleibt exakt die getrennte
workspacebezogene Fähigkeit aus LQ-183/LQ-184.

## 8. Nachweis und Folgeordnung

Porttests sichern die argumentlose Grenze. SQLite beweist Erfolg, aktive
Tatsachen, dauerhafte Schließung durch jeden Bestand, unterlassene Generatoren
bei Schließung, vollständigen Rollback und detailfreie technische Fehler. Der
markierte PostgreSQL-Test beweist zwei echte gleichzeitige Versuche mit exakt
einem Erfolg und einer neutralen Schließungsantwort.

Als nächster Slice folgt der reguläre autorisierte Onboarding-Anwendungsfall:
Er muss Akteur, Zielnutzer und Zielworkspace aus persistenten Tatsachen binden,
Authority-Prüfung und unveränderliche Entscheidung atomar machen und dieser
Entscheidung einen stabilen `ProvisioningRequestId` zuordnen. Reguläre
Membership- und Capability-Mutation bleiben weiterhin eigene spätere Slices.
