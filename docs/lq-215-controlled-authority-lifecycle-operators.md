# LQ-215 — Controlled Authority Lifecycle Operators

## 1. Status und Ziel

LQ-215 stellt getrennte owner-only Offline-Prozessgrenzen für die in LQ-213
und LQ-214 implementierten Authority-Lifecycle-Funktionen bereit.

Ein Operator verwaltet ausschließlich globale OIDC-Trust-Management-
Authority. Der andere verwaltet ausschließlich workspacebezogene Membership-
Management-Authority.

Beide Tools sind explizite manuell überwachte Prozesse. Sie werden weder vom
HTTP-Prozess noch bei App-Start, Login, Callback, Migration oder Deployment
aufgerufen.

## 2. Separate Entry Points

Die globale Domäne erhält:

```text
liquent-oidc-trust-authority
```

Die Workspace-Domäne erhält:

```text
liquent-membership-authority
```

Die Entry Points teilen keine Kommandos mit den bestehenden fachlichen OIDC-
Trust- oder Membership-Management-Operatoren.

Insbesondere kann der Trust-Authority-Operator keine Providerkonfiguration
ändern und der Membership-Authority-Operator keine gewöhnliche Membership
oder Research-Permission setzen.

## 3. Erlaubte Kommandos

Jeder Operator bietet genau drei Kommandos:

- `new-change-id` erzeugt eine neue domänenspezifische Lifecycle-Change-ID;
- `anchor` delegiert die einmalige LQ-213-Verankerung;
- `apply` delegiert genau eine reguläre LQ-214-Änderung.

Es gibt kein Bootstrap-, Recover-, Force-, Reset-, Reopen-, Delete-, List-,
Dump- oder Inspect-Kommando.

Die Tools migrieren das Schema nicht und erzeugen keine Authority außerhalb
der autorisierten Persistenzgrenzen.

## 4. Private Eingaben

`anchor` und `apply` verlangen jeweils:

- eine owner-only reguläre Datei mit der Datenbank-URL;
- eine owner-only reguläre JSON-Requestdatei;
- einen neuen noch nicht existierenden Resultatpfad in einem owner-only
  Verzeichnis.

Symbolische Links, Gruppen- oder Weltzugriff, leere Dateien, ungültiges UTF-8,
NUL-Bytes, unbekannte JSON-Felder und unvollständige Shapes werden fail-closed
abgewiesen.

Kein Wert wird getrimmt, normalisiert, vervollständigt oder aus Environment-
Variablen übernommen. Nur die Datenbank-URL-Datei darf genau um äußeren
Whitespace für den Connection-String bereinigt werden, entsprechend den
bestehenden Offline-Operatoren.

## 5. Globale Anchor-Anfrage

Eine globale Anchor-Anfrage enthält ausschließlich:

- `actor_user_id`;
- `change_id`.

Der Operator akzeptiert weder Zielnutzer noch erwartete Revision. LQ-213
bindet den bestehenden vollständigen Bootstrap-Bestand selbst und setzt den
Actor intern zugleich als Anchor-Ziel.

## 6. Workspace-Anchor-Anfrage

Eine Workspace-Anchor-Anfrage enthält ausschließlich:

- `actor_user_id`;
- `change_id`;
- `workspace_id`.

Andere Workspace-Bestände werden nicht gelesen oder verändert. Rollen,
Memberships, Permissions und Allow-Werte sind strukturell nicht darstellbar.

## 7. Reguläre Lifecycle-Anfragen

Globale Requests enthalten genau:

- Actor-UserId;
- stabile Change-ID;
- Ziel-UserId;
- Intent `grant`, `deactivate` oder `reactivate`;
- exakt erwartete Authority-Set-Revision.

Workspace-Requests enthalten zusätzlich genau den WorkspaceId-Scope.

`anchor`, `recover`, freie Rollen- oder Capability-Namen und caller-gelieferte
Status- oder Mitgliedersätze werden beim Parsen abgewiesen.

## 8. Stable IDs und technische Wiederholung

`new-change-id` zieht genau eine sichere domänenspezifische ID mit mindestens
32 Byte Entropie und gibt nur deren opaken Wert aus.

Der Operator erzeugt bei `anchor` oder `apply` niemals spontan eine neue
Change-ID. Die geprüfte Datei bewahrt sie über technische Wiederholungen.

Nach unklarem Ausgang wird dieselbe Requestdatei mit einem neuen leeren
Resultatpfad erneut verwendet. Die Adapter lösen einen exakten Commit-Retry
vor aktueller Authority auf und liefern dieselbe Revision.

Eine andere Anfrage unter derselben Change-ID bleibt detailfreier Konflikt.

## 9. Sichere Resultatdateien

Erfolg erzeugt atomar und exklusiv eine Datei mit Modus 0600. Sie enthält nur:

- die bewahrte `change_id`;
- die resultierende `revision_id`.

Ein vorhandener Resultatpfad wird niemals überschrieben. Temporäre Dateien
werden exklusiv erzeugt, synchronisiert und atomar an den Zielpfad verschoben.

Schlägt das Schreiben nach einem Datenbank-Commit fehl, bleibt die stabile
Requestdatei die Recovery-Grenze für den technischen Retry. Der Operator
versucht keine kompensierende Authority-Mutation.

## 10. Konsolenausgaben

Erfolgreiche Ausgaben sind ausschließlich:

- `anchored`;
- `applied`.

Neutrale fachliche Ablehnung lautet ausschließlich `rejected` und verwendet
Exit-Code 5.

Malformed Input, Change-ID-Konflikt und technische Nichtverfügbarkeit besitzen
je Operator konstante detailfreie Codes und getrennte Exit-Codes 2, 3 und 4.

Keine Ausgabe enthält Actor, Zielnutzer, Workspace, Change-ID, Revision,
Authority-Bestand, Datenbank-URL, SQL, Tabelle, Constraint oder Treiberdetail.

## 11. Engine- und Prozessbesitz

Der Prozess baut genau eine Engine aus der privaten URL-Datei und disposed sie
auf jedem normalen oder fehlerhaften Ausgang.

Die Engine wird nicht an den HTTP-Prozess weitergereicht. Der Operator öffnet
keinen Socket, startet keinen Server und erzeugt keinen Hintergrundtask.

Schema-Migration, Providerzugriff, OIDC-Discovery, Sessionauflösung und
Application-Startup sind ausdrücklich nicht Teil des Prozesses.

## 12. Autorisierungsgrenze bleibt persistent

Die Operatoren entscheiden Authority nicht selbst. Sie konstruieren lediglich
einen `SessionPrincipal` aus der explizit geprüften internen Actor-UserId und
delegieren an LQ-213 beziehungsweise LQ-214.

Actor-Status, Zielstatus, Workspace-Status, aktuelle Authority, erwartete
Revision, Übergang und Lockout-Schutz werden weiterhin atomar aus dem System
of Record gebunden.

Ein lokaler Operatorprozess, Datenbankzugang oder Besitz der Requestdatei ist
kein Ersatz für persistente Actor-Authority.

## 13. Keine Recovery

Diese Operatoren sind keine Recovery-Credentials. Wenn kein historischer
Manager mehr aktuell wirksam ist, bleiben `anchor` und `apply` geschlossen.

Sie können keinen inaktiven Nutzer aktivieren, keinen neuen Recovery-Zielnutzer
wählen, Bootstrap wieder öffnen oder Authority per Force-Flag erzeugen.

Die getrennten Recovery-Inventare und Recovery-IDs aus LQ-212 werden nicht
gelesen oder geschrieben.

## 14. Betriebsanleitungen

Zwei getrennte Runbooks dokumentieren Vorbereitung, Review, Verankerung,
Grant, sichere Rotation, Retry, Ergebnisbewahrung und Cleanup:

- `operations/runbooks/oidc-trust-authority-lifecycle.md`;
- `operations/runbooks/workspace-membership-authority-lifecycle.md`.

Die Beispiele enthalten ausschließlich Platzhalter und keine realen IDs,
Credentials, Hosts oder Providerdaten.

## 15. Bewusst nicht enthalten

LQ-215 implementiert keine:

- Migration oder neue Persistenztabelle;
- Bootstrap- oder Recovery-Entscheidung;
- Nutzer-, Workspace- oder Session-Mutation;
- Trust-Konfigurationsmutation;
- gewöhnliche Membership- oder Permission-Mutation;
- HTTP-Route, UI, API, Scheduler oder Startup-Verdrahtung;
- Environment-Allow, Admin-Header oder generische Rolle;
- automatische Deployment- oder Produktionsaktion.

## 16. Nachweis

Tests belegen exakte private Request-Shapes, verbotene Felder und Intents,
repr-freie Requests, getrennte sichere Change-ID-Erzeugung sowie separate
Console Entry Points.

End-to-End-CLI-Nachweise decken Anchor, Grant, geschützte Resultate, exakten
Retry nach Actor-Entzug, Workspace-Scope, Nichtüberschreiben und fehlende
automatische Migration ab.

Ein PostgreSQL-Nachweis führt beide getrennten Operator-Ketten gegen das
normative Persistenzsystem aus.

## 17. Nächster Slice

LQ-216 soll die eng begrenzten domänenspezifischen Offline-Recovery-
Mutationsgrenzen implementieren.

Recovery muss historisch bereits autorisierte aktive interne Nutzer, exakten
Scope und erwartete Set-Revision binden, eine eigene Recovery-ID verwenden und
darf weder Bootstrap öffnen noch Nutzer- oder Workspace-Status ändern.
