# LQ-225 — Controlled User and Workspace Lifecycle Operators

## 1. Status und Ziel

LQ-225 stellt zwei getrennte owner-only Offline-Prozessgrenzen für die in
LQ-223 und LQ-224 implementierten regulären Lifecycle-Entscheidungen bereit.

Ein Tool verwaltet ausschließlich Nutzerbestand. Das andere verwaltet
ausschließlich Workspacebestand und dessen erste Onboarding-Management-
Bindung.

Beide Werkzeuge bleiben manuell überwachte Betriebsprozesse. HTTP, Browser,
App-Start, Migration, Deployment und periodische Tasks rufen sie nicht auf.

## 2. Separate Entry Points

Die Nutzerdomäne erhält:

```text
liquent-user-lifecycle
```

Die Workspace-Domäne erhält:

```text
liquent-workspace-lifecycle
```

Kein Entry Point besitzt eine caller-gesteuerte Domänen-, Tabellen- oder
Authority-Auswahl.

## 3. Nutzerkommandos

Der Nutzeroperator bietet genau:

- `new-change-id`;
- `create`;
- `deactivate`;
- `reactivate`.

Das Kommando bestimmt den Intent. Ein Request kann keinen freien Intent,
Status, Allow-Wert, Rolle oder Capability-Namen liefern.

## 4. Workspacekommandos

Der Workspaceoperator bietet genau:

- `new-change-id`;
- `create`;
- `deactivate`.

Workspace-Deaktivierung ist terminal. Es gibt kein Reactivate-, Delete-,
Cascade-, Force-, Reset-, Drain- oder Reopen-Kommando.

## 5. Private Prozessinputs

Jede Mutation verlangt eine owner-only reguläre Datenbank-URL-Datei, eine
owner-only reguläre JSON-Requestdatei und einen neuen Resultatpfad in einem
owner-only Verzeichnis.

Symlinks, Gruppen- oder Weltzugriff, ungültiges UTF-8, NUL-Bytes, leere Werte,
unbekannte Felder und unvollständige Shapes werden fail-closed verworfen.

Es gibt keinen Environment-Fallback und keine Normalisierung interner IDs.
Nur äußerer Whitespace der Datenbank-URL wird vor Engine-Aufbau entfernt.

## 6. Strukturell sichere Nutzeranlage

`create` akzeptiert ausschließlich:

- Actor-UserId;
- stabile User-Lifecycle-Change-ID;
- exakt erwartete vollständige User-Lifecycle-Revision.

Eine Ziel-UserId ist in diesem Shape nicht darstellbar. Sie wird erst innerhalb
der autorisierten LQ-223-Persistenztransaktion sicher erzeugt.

Die Anlage erzeugt einen aktiven internen Nutzer, aber keine Identitätsbindung,
Admission, Session, Membership, Permission, Rolle oder Authority.

## 7. Nutzerstatusänderung

`deactivate` und `reactivate` akzeptieren zusätzlich genau eine bestehende
interne Ziel-UserId.

Das Kommando bindet den Übergang. Caller können keinen Zielstatus liefern.

Deactivate delegiert alle LQ-223-Drain-Prüfungen und führt keinen Cascade aus.
Reactivate stellt ausschließlich Nutzerstatus wieder her und gewährt keine
frühere abhängige Fähigkeit erneut.

## 8. Strukturell sichere Workspaceanlage

Workspace-`create` akzeptiert ausschließlich:

- Actor-UserId;
- stabile Workspace-Lifecycle-Change-ID;
- eine bestehende aktive interne UserId als ersten Onboarding-Manager;
- exakt erwartete vollständige Workspace-Lifecycle-Revision.

Eine Ziel-WorkspaceId ist nicht darstellbar. LQ-224 erzeugt sie innerhalb der
autorisierten Transaktion und bindet den bestätigten ersten Manager atomar.

Die Anlage erzeugt keine gewöhnliche Membership, Research-Permission,
Membership-Management-, Trust- oder Lifecycle-Authority.

## 9. Workspace-Deaktivierung

`deactivate` akzeptiert zusätzlich genau die bestehende Ziel-WorkspaceId.

Der Operator verändert keine Child-Fakten. Historische Onboarding-,
Membership- und Permission-Fakten bleiben erhalten und wegen des inaktiven
Workspace fail-closed.

Es gibt weder automatische Bereinigung noch implizite Wiederaktivierung.

## 10. Persistente Autorisierungsgrenze

Die Tools konstruieren aus der expliziten Actor-UserId nur einen
`SessionPrincipal`. Dieser identifiziert den Actor und erteilt keine Authority.

LQ-223 beziehungsweise LQ-224 lösen Actorstatus, dedizierte Lifecycle-
Authority, Zielbestand und Current-Revision atomar aus dem System of Record.

Lokaler Prozessbesitz, Dateibesitz und Datenbankzugang ersetzen diese
persistente Autorisierung nicht. Ein committierter Entzug sperrt jede spätere
neue Entscheidung.

## 11. Stabile Change-IDs

`new-change-id` erzeugt eine sichere domänenspezifische opake ID mit mindestens
32 Byte Entropie und gibt ausschließlich deren Wert aus.

Create und Statuskommandos erzeugen niemals still eine Change-ID. Nach einem
technisch unklaren Ausgang wird derselbe geprüfte Request mit demselben Wert
und einem neuen leeren Resultatpfad wiederholt.

Exakter Retry wird vor aktueller Authority aufgelöst und liefert dieselbe
Revision und dieselbe intern erzeugte Ziel-ID. Abweichende Wiederverwendung
bleibt detailfreier Konflikt.

## 12. Sichere Resultatdateien

Erfolg erzeugt atomar und exklusiv eine Datei mit Modus 0600.

Nutzerresultate enthalten nur Change-ID, Revision-ID und gebundene UserId.
Workspaceresultate enthalten nur Change-ID, Revision-ID und gebundene
WorkspaceId.

Vorhandene Ziele werden nicht überschrieben. Scheitert das Resultatschreiben
nach Commit, bleibt der unveränderte Request die technische Retry-Grenze; es
erfolgt keine kompensierende Mutation.

## 13. Detailfreie Prozessausgänge

Commit und exakter Commit-Retry liefern ausschließlich `applied` mit Exit 0.

Neutrale fachliche Abwesenheit oder Ablehnung liefert ausschließlich
`rejected` mit Exit 5. Sie verrät weder Actor-, Authority-, Ziel-, Manager-,
Drain- noch Revisionszustand.

Malformed Input, Change-ID-Konflikt und technische Nichtverfügbarkeit besitzen
konstante domänenspezifische Codes und die Exit-Codes 2, 3 und 4.

Keine Ausgabe enthält IDs, Datenbank-URL, SQL, Tabellen-, Constraint-, Treiber-
oder Infrastrukturdetails.

## 14. Engine- und Prozessbesitz

Jeder Aufruf baut genau eine Engine aus der privaten URL-Datei und disposed sie
auf normalen wie fehlerhaften Ausgängen.

Die Engine verlässt den Offline-Prozess nicht. Kein Tool öffnet einen Server,
Socket oder Hintergrundtask und führt kein Provider- oder Discovery-I/O aus.

Die Operatoren migrieren, bootstrappen, ankern oder recovern nichts.

## 15. Bewusst nicht enthalten

LQ-225 enthält keine:

- Schema-, Tabellen-, SQL- oder Migrationsentscheidung;
- Port-, Domainmodell- oder Persistenzsignaturänderung;
- Bootstrap-, Anchor- oder Recovery-Funktion;
- Identity-, Admission-, Session- oder OIDC-Trust-Mutation;
- gewöhnliche Membership-, Permission- oder Rollenmutation;
- HTTP-Route, UI, API, Scheduler oder Production-Wiring;
- automatische Deployment- oder Betriebsaktion.

## 16. Betriebsanleitungen und Nachweis

Getrennte Runbooks beschreiben sichere Vorbereitung, unabhängige Revision-
Prüfung, stabile ID-Bewahrung, Anwendung, Retry, Evidenz und Cleanup:

- `operations/runbooks/user-lifecycle.md`;
- `operations/runbooks/workspace-lifecycle.md`.

Tests belegen exakte private Shapes, verbotene caller-gesteuerte IDs und
Entscheidungsfelder, repr-freie Requests und getrennte sichere Change-IDs.

End-to-End-Nachweise decken Create, private Resultate, exakten Retry nach
Authority-Entzug, ausbleibende Membership-Erzeugung und fehlende automatische
Migration ab.

## 17. Nächster Slice

LQ-226 soll die vollständige User- und Workspace-Lifecycle-Kette gegen
PostgreSQL und die Betriebsgrenzen unabhängig end-to-end auditieren.

Der Audit darf keine neue Funktion, Recovery-Abkürzung, Migration oder
Runtime-Verdrahtung einführen, sondern muss verbleibende Blocker präzise
benennen.
