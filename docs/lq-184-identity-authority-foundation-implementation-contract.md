# LQ-184 — Implementierungsvertrag der Identity-Autoritätsgrundlage

## 1. Status und Ziel

Dieser Slice entscheidet die konkrete Form der in LQ-183 geforderten
Persistenzmodelle und Migration, enthält selbst aber noch keine Python-
Implementierung, Tests, CLI, Route oder Production-Verdrahtung.

LQ-184 schließt insbesondere eine gefährliche Abkürzung aus: Es entsteht kein
allgemeiner `has_authority`-, Status- oder Verwaltungs-Lookup, mit dem ein
Anwendungsfall erst lesen und später getrennt schreiben könnte. Bootstrap und
reguläre Onboarding-Entscheidung erhalten in eigenen Slices jeweils eine
atomare, transaktionstragende Operation.

## 2. Endgültige Python-Modelle

Der Implementierungsslice legt im Identity-Paket drei getrennte Status-Enums
an:

- `InternalUserStatus`: `ACTIVE = "active"`, `INACTIVE = "inactive"`;
- `WorkspaceStatus`: `ACTIVE = "active"`, `INACTIVE = "inactive"`;
- `WorkspaceOnboardingAuthorityStatus`: `ACTIVE = "active"`, `REVOKED = "revoked"`.

Die getrennten Typen sind beabsichtigt: Die heute ähnlichen Ausprägungen sind
keine austauschbaren fachlichen Zustände; ein gemeinsames Enum würde spätere
Lifecycle-Entscheidungen unnötig koppeln.

Hinzu kommen drei unveränderliche Wertformen:

- `InternalUserRecord(user_id, status)`;
- `WorkspaceRecord(workspace_id, status)`;
- `WorkspaceOnboardingAuthorityRecord(user_id, workspace_id, status)`.

Alle sind `frozen=True`, `slots=True`, hashbar und haben nur Pflichtfelder.
Jeder Identifier ist `repr=False`; kein `repr` enthält User- oder Workspace-
Werte. Die Konstruktoren nehmen nur die bereits bestehenden
`UserId`- und `WorkspaceId`-Typen sowie das jeweils exakte Status-Enum. Es gibt
keine Namen, E-Mail-Adressen, Providerdaten, Rollen, Permissions, Zeitstempel,
Metadaten oder frei gesetzten Autoritäts-Booleans.

## 3. Endgültiges persistentes Schema

Die Folgemigration trägt Revision `20260811_0003` und folgt ausschließlich auf
`20260811_0002`. Sie legt genau diese drei Tabellen an:

`internal_users`

- `user_id` als nicht-nullbares `LargeBinary`, Primärschlüssel;
- `status` als nicht-nullbarer String mit Check auf `active` oder `inactive`;
- Check `length(user_id) > 0`.

`workspaces`

- `workspace_id` als nicht-nullbares `LargeBinary`, Primärschlüssel;
- `status` als nicht-nullbarer String mit Check auf `active` oder `inactive`;
- Check `length(workspace_id) > 0`.

`workspace_onboarding_authorities`

- `user_id` und `workspace_id` als nicht-nullbares `LargeBinary`;
- `status` als nicht-nullbarer portabler String mit Check auf `active` oder
  `revoked`;
- zusammengesetzter Primärschlüssel aus `user_id` und `workspace_id`;
- benannte, restriktive Foreign Keys auf `internal_users.user_id` und
  `workspaces.workspace_id`;
- Nichtleer-Checks für beide Identifier.

Es gibt keinen Surrogatschlüssel für die Verwaltungszuordnung: Für ein
Nutzer-Workspace-Paar existiert genau eine historische Zuordnung, deren
widerrufener Zustand erhalten bleibt. Dieser Slice entscheidet weder eine
Reaktivierung noch eine zweite Vergabe nach Entzug.

## 4. Foreign Keys zu vorhandenen Identity-Tabellen

Da Nutzer und Workspaces nun echte persistente Ziele erhalten, ergänzt dieselbe
Migration restriktive Foreign Keys:

- `external_identity_bindings.user_id` auf `internal_users.user_id`;
- `identity_admissions.target_user_id` auf `internal_users.user_id`;
- `identity_admissions.target_workspace_id` auf `workspaces.workspace_id`.

Die Migration erzeugt keine fehlenden Nutzer oder Workspaces und bereinigt
keine verwaisten Daten. Trifft sie auf eine bestehende unverbürgte Referenz,
muss sie laut und atomar scheitern. Das ist die fail-closed Auflösung der in
LQ-178 und LQ-180 bewusst vertagten Foreign Keys.

Alle Identifier bleiben bytegenaues `LargeBinary`. Es gibt keine
Unicode-Normalisierung, Kollationsabhängigkeit, Groß-/Kleinschreibung oder
Konvertierung durch Anzeigenamen. Statuswerte sind dagegen eine geschlossene,
nicht identitätstragende ASCII-Aufzählung.

## 5. Migration und Rückbau

Die Migration enthält keine Seed-Zeile und insbesondere keinen ersten Nutzer,
Workspace, Administrator, Bootstrap-Marker oder Schalter. Sie öffnet keinen
Bootstrap und entscheidet nicht, wer ihn ausführen darf.

Beim Upgrade entstehen zuerst Nutzer und Workspaces, dann die
Verwaltungszuordnung; anschließend werden die drei Foreign Keys an den
vorhandenen Tabellen ergänzt. Alles läuft in der Alembic-
Migrationstransaktion oder gar nicht.

Beim Downgrade werden zuerst die drei ergänzten Foreign Keys entfernt, danach
die Verwaltungszuordnung und zuletzt Workspace- und Nutzertabelle. Es gibt
kein `CASCADE`, kein stilles Löschen abhängiger Identity-Daten und keinen
best-effort Rückbau.

## 6. Keine operative Portfläche in LQ-184

Der Implementierungsslice ergänzt `ports.py` bewusst um **keinen** Status-,
Existenz-, Autoritäts- oder CRUD-Lookup. Auch die drei Records werden nicht als
Freigabeentscheidung an einen Aufrufer ausgegeben.

Ein Ablauf `lookup_authority(...) -> True` gefolgt von
`store_decision(...)` wäre selbst mit korrekten Einzelabfragen unsicher: Ein
Entzug zwischen beiden Transaktionen könnte noch eine neue Entscheidung
erlauben. Ein Cache oder In-Process-Lock behebt dieses Rennen nicht.

Der Bootstrap-Slice erhält deshalb später eine einzige atomare Operation für
den vollständig leeren Bestand. Der reguläre Entscheidungs-Slice erhält eine
andere einzelne Operation, die Akteur, Zielnutzer, Workspace und Autorität in
derselben Datenbankentscheidung prüft, in der sie die unveränderliche
Onboarding-Entscheidung samt `ProvisioningRequestId` speichert. Erst diese
Operationen rechtfertigen eigene Ports.

## 7. Lifecycle und Nichtwiederverwendung

Die Migration schafft nur darstellbaren Zustand und keine allgemeine Mutation.
Kein Code aktiviert, deaktiviert, reaktiviert, widerruft oder vergibt Autorität.

Inaktive Nutzer und Workspaces sowie widerrufene Zuordnungen bleiben als
historische Zeilen erhalten. Ihre Primärschlüssel dürfen nicht gelöscht und
unter neuer Bedeutung wiederbelegt werden. Restriktive Foreign Keys verhindern,
dass bestehende Bindungen, Admissions oder Autoritätszuordnungen durch ein
Löschen ihres Ziels verwaisen.

Reaktivierung, Datenschutzlöschung, Retention-Fristen und autorisierte
Lifecycle-Operationen bleiben eigene Entscheidungen. Keine spätere Operation
darf aus dem bloßen Vorhandensein einer Zeile Aktivität oder Autorität ableiten.

## 8. PostgreSQL- und SQLite-Nachweis

PostgreSQL bleibt die normative Runtime. Der Implementierungsslice muss dort
Upgrade und Downgrade, alle Check- und Foreign-Key-Constraints, bytegenaue
Eindeutigkeit, restriktives Löschen sowie das laute Scheitern bei verwaisten
Bestandsreferenzen nachweisen.

SQLite darf die portable Migrationsform, Tabellen- und Constraintstruktur,
Modelldekodierung und einfache Constraintverletzungen belegen. Es beweist keine
Mehrprozess-Nebenläufigkeit, keine spätere Bootstrap-Serialisierung und keine
atomare Onboarding-Autorisierung. Der vorhandene PostgreSQL-CI-Pfad aus LQ-179
wird genutzt; LQ-184 ändert weder Workflow noch Service-Digest.

## 9. Fehler- und Datenschutzgrenze

Da LQ-184 keine operative Portmethode einführt, entsteht auch keine neue
öffentliche Exception. Modellvalidierung nennt nur das betroffene Feld oder den
neutralen Vertrag, niemals dessen Wert. Migration und Tests dürfen Identifier,
DSN, Treibertext oder Datenbankdetails nicht in neu definierte Fachfehler
übersetzen oder protokollieren.

Die späteren atomaren Operationen trennen einheitliche fachliche Ablehnung von
detailfreier technischer Nichtverfügbarkeit. LQ-184 nimmt weder deren konkrete
Python-Namen noch HTTP-, Log-, Trace- oder Metrikabbildung vorweg.

## 10. Ausdrücklich nicht enthalten

Nicht enthalten sind Bootstrap, Onboarding-Entscheidung, Admission-
Provisionierung, Membership, Rollen, Research-Permissions, Nutzer- oder
Workspace-Erzeugungs-API, Autoritätsvergabe oder -entzug, Session-/Login-
Persistenz, HTTP, CLI, Operator-Authentisierung, Production-Wiring und Änderungen
an LQ-180 oder LQ-181.

Es gibt keine Decision-Tabelle, keinen Bootstrap-Guard, keinen Seed, keinen
Konfigurationsschalter, keine Uhr, keinen Generator, keinen Retry und keine
automatische Reparatur von Bestandsdaten.

## 11. Verbindliche Folgeordnung

LQ-183 §7 bezeichnete den Bootstrap vorzeitig als LQ-184, während §11 Modelle
und Migration davor anordnet. LQ-184 löst die Nummerierungskollision auf: Die
sachliche Reihenfolge aus §11 gilt, der Bootstrap erhält die nächste Nummer.

1. LQ-184 — dieser Implementierungsvertrag;
2. Modelle, Migration und Constraint-Nachweise der Autoritätsgrundlage;
3. atomarer Offline-Bootstrap des ersten Nutzers, Workspaces und seiner Autorität;
4. reguläre atomare Onboarding-Entscheidung mit persistentem
   `ProvisioningRequestId`;
5. persistente Login-Transaktionen und Sessions;
6. erst danach Wiederaufnahme von LQ-177.
