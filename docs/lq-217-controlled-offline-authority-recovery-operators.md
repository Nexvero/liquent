# LQ-217 — Controlled Offline Authority Recovery Operators

## 1. Status und Ziel

LQ-217 stellt die LQ-216-Recovery-Mutationen über zwei separate owner-only
Offline-Prozessgrenzen bereit.

Die globale OIDC-Trust-Authority und workspacebezogene Membership-Management-
Authority behalten getrennte Commands, Requestmodelle, IDs, Adapter,
Ergebnisdateien, Fehlercodes und Runbooks.

Die Prozesse sind ausschließlich für einen bereits verankerten Scope ohne
wirksamen Manager vorgesehen. Sie sind kein regulärer Verwaltungsweg.

## 2. Separate Entry Points

Die globale Recovery verwendet:

```text
liquent-oidc-trust-authority-recovery
```

Die Workspace-Recovery verwendet:

```text
liquent-membership-authority-recovery
```

Beide Entry Points sind von Bootstrap-, Anchor-, regulären Lifecycle-, Trust-
Konfigurations- und Membership-Management-Tools getrennt.

## 3. Minimaler Kommandosatz

Jeder Prozess besitzt genau zwei Kommandos:

- `new-recovery-id` erzeugt eine sichere domänenspezifische Recovery-ID;
- `recover` delegiert exakt eine LQ-216-Recovery-Anfrage.

Es gibt kein Grant-, Deactivate-, Reactivate-, Anchor-, Bootstrap-, Force-,
Reset-, Reopen-, Delete-, List-, Dump- oder Inspect-Kommando.

Dadurch kann ein Recovery-Prozess nicht als allgemeines Authority-
Administrationstool verwendet werden.

## 4. Globale Requestform

Der globale Request enthält ausschließlich:

- `recovery_id`;
- `target_user_id`;
- `expected_revision`.

Die Ziel-UserId muss bereits historische Authority besitzen. Der Operator
akzeptiert keine neue Person, keinen Actor und keine resultierende Revision.

## 5. Workspace-Requestform

Der Workspace-Request enthält ausschließlich:

- `recovery_id`;
- `target_user_id`;
- `workspace_id`;
- `expected_revision`.

Der explizite Workspace ist Teil der stabilen Recovery-Entscheidung. Authority
oder Historie aus einem anderen Workspace kann ihn nicht ersetzen.

## 6. Verbotene Eingaben

Beide Parser lehnen unbekannte oder zusätzliche Felder ab. Strukturell nicht
akzeptiert werden insbesondere:

- `actor_user_id` oder `SessionPrincipal`;
- Intent oder gewünschter Authority-Status;
- Rolle, Capability-Name oder Allow-Boolean;
- vollständiger Authority-Satz;
- User- oder Workspace-Status;
- Bootstrap-, Anchor- oder Lifecycle-Change-ID;
- resultierende Revision;
- Membership, Permission oder OIDC-Konfiguration.

Die Prozesse treffen keine eigene Eligibility- oder Autorisierungsentscheidung.

## 7. Owner-only Dateigrenze

`recover` verlangt:

- eine owner-only reguläre Datei mit der Datenbank-URL;
- eine owner-only reguläre JSON-Requestdatei;
- einen neuen abwesenden Resultatpfad in einem owner-only Verzeichnis.

Symbolische Links, Gruppen- oder Weltzugriff, leere Dateien, ungültiges UTF-8,
NUL-Bytes, unsichere Verzeichnisse und vorhandene Resultatpfade scheitern
fail-closed.

IDs und Scopewerte werden weder getrimmt noch normalisiert oder aus Environment-
Variablen ergänzt.

## 8. Recovery-ID-Erzeugung

`new-recovery-id` verwendet den bestehenden sicheren Materialgenerator und
zieht eine unabhängige domänenspezifische ID mit mindestens 32 Byte Entropie.

Nur der opake Wert wird auf stdout ausgegeben. Er muss genau einmal in die
geprüfte Requestdatei übernommen und für technische Wiederholungen bewahrt
werden.

`recover` erzeugt niemals spontan eine Ersatz-Recovery-ID.

## 9. Persistente Entscheidung bleibt maßgeblich

Der Operator delegiert direkt an den getrennten LQ-216-Adapter. Er prüft oder
überschreibt keine fachliche Vorbedingung.

Das normative Persistenzsystem entscheidet atomar:

- ob der Scope tatsächlich keinen wirksamen Manager besitzt;
- ob Zielnutzer und gegebenenfalls Workspace aktiv sind;
- ob der Zielnutzer im exakten Scope historisch autorisiert und inaktiv ist;
- ob die erwartete Revision aktuell oder eindeutig terminal ist;
- ob operativer Bestand und vollständiger Snapshot übereinstimmen.

Besitz des Tools, der Datei oder Datenbankzugang ist kein Ersatz für diese
Eligibility.

## 10. Resultatdatei

Erfolg erzeugt exklusiv und atomar eine owner-only Datei mit Modus 0600. Sie
enthält ausschließlich:

- die bewahrte `recovery_id`;
- die resultierende `revision_id`.

Ein vorhandener Pfad wird nie überschrieben. Der temporäre Inhalt wird
synchronisiert und anschließend atomar an den Zielpfad verschoben.

Die Datei enthält weder Zielnutzer noch Workspace oder Authority-Bestand.

## 11. Exakte technische Wiederholung

Bei technisch unklarem Ausgang wird dieselbe Requestdatei mit einem neuen
abwesenden Resultatpfad erneut ausgeführt.

Die persistente Recovery-ID wird vor aktuellen Eligibility-Prüfungen
aufgelöst. Ein exakter Retry liefert dieselbe resultierende Revision, auch wenn
Nutzer-, Workspace- oder Authority-Zustand nach dem Commit verändert wurde.

Eine Wiederholung mit anderem Ziel, Workspace oder erwarteter Revision ist ein
detailfreier Konflikt. Der Operator überschreibt keine frühere Entscheidung.

## 12. Konsolenausgaben und Exit-Codes

Erfolg lautet ausschließlich `recovered` und verwendet Exit-Code 0.

Neutrale Ablehnung lautet ausschließlich `rejected` mit Exit-Code 5. Sie
unterscheidet weder vorhandenen Manager, ineligible Target, Scope, Foundation,
Historie noch stale Revision.

Malformed Input, Recovery-ID-Konflikt und technische Nichtverfügbarkeit nutzen
konstante detailfreie Codes und Exit-Codes 2, 3 beziehungsweise 4.

Keine Ausgabe enthält Ziel, Workspace, Recovery-ID, Revision, Authority-
Bestand, SQL, DSN, Tabelle, Constraint oder Treiberdetail.

## 13. Prozess- und Engine-Besitz

Jeder Prozess baut genau eine Engine aus der privaten URL-Datei und disposed
sie auf jedem normalen oder fehlerhaften Ausgang.

Der Prozess migriert kein Schema, liest keine Environment-Konfiguration,
öffnet keinen Socket, startet keinen Server und erzeugt keinen Hintergrundtask.

HTTP-Prozess, Login, Callback, Sessionauflösung und Application-Startup
importieren oder komponieren diese Recovery-Tools nicht.

## 14. Keine Nebenmutation

Die Operatoren ändern ausschließlich über LQ-216 den historisch inaktiven
Authority-Fakt, die neue Set-Revision, den Current-Pointer und die Recovery-
Entscheidung.

Sie erstellen oder aktivieren keine Nutzer oder Workspaces. Sie ändern keine
Trust-Konfiguration, Membership, Permission, Session oder Onboarding-
Authority.

Bootstrap bleibt geschlossen. Ein unverankerter Scope bleibt auch über diese
Tools nicht recoverbar.

## 15. Runbooks und lokale Governance

Zwei getrennte Runbooks dokumentieren den Notfallprozess:

- `operations/runbooks/oidc-trust-authority-recovery.md`;
- `operations/runbooks/workspace-membership-authority-recovery.md`.

Sie verlangen unabhängige Prüfung, lokale Emergency-Freigabe, private
Vorbereitung, stabile ID-Bewahrung, exakt unveränderten Retry und sichere
Bereinigung.

Der Repository-Code definiert keine konkrete Person, Freigabegruppe,
Ticketplattform oder reale Credentialquelle.

## 16. Bewusst nicht enthalten

LQ-217 implementiert keine:

- Migration oder neue Persistenz;
- reguläre Lifecycle-, Anchor- oder Bootstrap-Funktion;
- Recovery-Credential im HTTP- oder Sessionmodell;
- Nutzer-, Workspace-, Membership-, Permission- oder Trust-Mutation außerhalb
  von LQ-216;
- Route, API, UI, Scheduler, Settings- oder Startup-Verdrahtung;
- Environment-Allow, Admin-Header oder generische Rolle;
- automatische Recovery oder Deployment-Aktion.

## 17. Nachweis

Tests belegen exakte repr-freie Requestmodelle, Ablehnung von Actor-, Intent-,
Rollen- und Allow-Feldern, sichere getrennte Recovery-ID-Erzeugung und separate
Console Entry Points.

CLI-End-to-End-Nachweise decken Recovery, Workspace-Scope, atomare 0600-
Resultate, exakten Retry nach späterer Foundation-Änderung,
Nichtüberschreiben und fehlende automatische Migration ab.

Ein PostgreSQL-Nachweis führt beide getrennten Recovery-Operatorpfade gegen
das normative Persistenzsystem aus.

## 18. Nächster Slice

LQ-218 soll einen End-to-End-Inbetriebnahme-, Rotation-, Entzugs- und Recovery-
Nachweis über Bootstrap, Verankerung, regulären Lifecycle und Offline-Recovery
beider Domänen erstellen.

Der Slice soll keine neue Capability einführen, sondern die vollständigen
Ketten und die verbleibenden LQ-177-Blocker evidenzbasiert auditieren.
