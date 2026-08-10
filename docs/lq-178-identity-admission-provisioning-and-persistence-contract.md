# LQ-178 — Admission-Provisionierung und Persistenzvertrag

## 1. Status, Ziel und Systemgrenze

Architekturentscheidung, **nur Vertrag**. Kein Code, kein Modell, kein Port,
keine Migration, kein Adapter, kein Test.

LQ-132 verlangt, dass eine Admission aus einem „expliziten internen Onboarding-/
Einladungsprozess" stammt, entscheidet diesen aber nicht — und im Repository
existiert er nicht: `IdentityAdmissionRecord` wird ausschließlich in Tests
konstruiert, es gibt keinen administrativen Anwendungsfall, keine persistente
Nutzer- oder Workspace-Entität und keine Business-Tabelle. LQ-178 schließt diese
Lücke — **Erzeugungsgrenze** und **beobachtbare Persistenzinvarianten** — und
blockiert alles Weitere, damit keine Migration eine Architektur festschreibt,
deren Voraussetzung fehlt.

## 2. Autorisierte Erzeugungsquelle

Eine `IdentityAdmissionRecord` darf **ausschließlich** durch eine getrennte
interne **Provisioning-Anwendungsgrenze** entstehen, die von einem bereits
autorisierten Onboarding-/Einladungsprozess aufgerufen wird.

Sie ist **nicht** Teil des OIDC-Callbacks und **nicht** Teil des Login-Starts.
Ausgeschlossen sind Self-Sign-up, ein automatisches „erster Login erzeugt Nutzer
und Admission", ein HTTP-Endpunkt in LQ-178, ein Environment-Bootstrap, ein
Migration-Seed, direkter Datenbankzugriff aus Transportcode und jede
Administrationsmethode am Runtime-Port `ExternalIdentityAdmissionStore`.

Der konkrete autorisierte Aufrufer — Admin-Oberfläche oder anderer interner
Prozess — bleibt ein **eigener Slice**; **solange er fehlt, wird die
Provisioning-Grenze in Production nicht verdrahtet.**

## 3. Vertrauensgrenze der Zielidentifikatoren

Die Provisioning-Grenze erhält `target_user_id` und `target_workspace_id`
ausschließlich aus einer bereits autorisierten internen Onboarding-Entscheidung.
Sie erzeugt **keinen** Nutzer, Workspace, Membership, Rolle oder Berechtigung,
prüft keine Berechtigung anhand frei gelieferter HTTP-Werte, akzeptiert **keine**
OIDC-Claims als Zielnutzer und übernimmt **keinen** `UserId` aus Callback, Token
oder Providerantwort.

Da heute weder eine persistente User- noch eine Workspace-Tabelle existiert,
schreibt LQ-178 **keinen fiktiven Foreign Key** fest. Beide bleiben typisierte
interne Referenzen. Der Production-Wiring-Slice (LQ-177) bleibt blockiert, bis
die autorisierte Quelle dieser Referenzen tatsächlich vorhanden ist.

## 4. AdmissionId, Zeit und Ablauf

Die Provisioning-Anwendungsgrenze erzeugt **selbst**:

- die `IdentityAdmissionId` über einen **kryptografisch sicheren, injizierten**
  Generator,
- `expires_at` aus einer **injizierten aware-UTC-Serveruhr** plus einer positiv
  validierten Admission-Lifetime.

Der Aufrufer darf weder AdmissionId noch Ablaufzeit frei setzen. Keine versteckte
Systemuhr, keine Normalisierung, kein Ersatzwert, keine Wiederverwendung einer
früheren AdmissionId. **`IdentityAdmissionRecord` besitzt kein `created_at`, und
dieses Feld wird hier nicht erfunden**: Der Erzeugungszeitpunkt ist allein die
Grundlage der Ableitung von `expires_at`, wird nicht zusätzlich gespeichert, und
der Record bleibt unverändert.

## 5. Identitätsbezug und Zustandsfolge

Bei der Provisionierung ist die spätere `ExternalIdentity` **bewusst unbekannt**:
kein Issuer, Subject, erwarteter Provider oder vorab gebundener OIDC-Claim — die
Admission autorisiert eine erstmalige Bindung, nicht eine bestimmte Identität.
Erst die **erste erfolgreiche atomare Konsumoperation** bindet sie an genau eine
`(issuer, subject)`-Identität und legt **gleichzeitig** die
External-Identity-Bindung auf `target_user_id` an; der bestehende
`IdentityAdmissionRecord`-Vertrag bleibt unverändert.

```
provisioniert   target_user_id, target_workspace_id, expires_at gesetzt
                consumed_at = NULL, bound_identity = NULL
      │
      │  erster erfolgreicher Konsum: atomar mit der Bindungsanlage
      ▼
konsumiert      consumed_at = Serverzeit, bound_identity = (issuer, subject)
                → autorisiert nie wieder eine Bindung
```

Es gibt keinen Rückweg.

## 6. Duplikate und Wiederholung

**Provisionierung.** Jede AdmissionId ist global eindeutig; eine erzeugte
Admission wird genau einmal gespeichert. Eine technische Wiederholung darf
**keine** zweite Admission mit neuer ID erzeugen, sofern der Aufrufer keine eigene
idempotente Grenze besitzt; LQ-178 erfindet **keinen** öffentlichen
Idempotency-Key. Die Kollision eines intern generierten Handles ist ein
**technischer** Fehler und wird nie durch Überschreiben aufgelöst.

**Runtime-Konsum.** Offen → genau einmal konsumiert und gebunden. Eine **exakte**
idempotente Wiederholung — dieselbe Admission, dieselbe Identität, dieselbe
bestehende Bindung — darf denselben `UserId` liefern. Jede **abweichende**
Wiederholung bleibt `None`. Ein bestehendes Binding hat **Vorrang** und
verbraucht keine Admission (LQ-131/132, umgesetzt in LQ-173). Kein Rebinding und
kein Account-Merge.

## 7. Store-seitige Invarianten

Verbindlich für den späteren persistenten Adapter:

- Issuer und Subject **bytegenau** verglichen — keine Normalisierung, kein
  Case-Folding, kein Trimming;
- höchstens **eine** Bindung je `(issuer, subject)` und, dem bestehenden Vertrag
  entsprechend, höchstens **eine** ExternalIdentity je `UserId`;
- **eindeutige** AdmissionId; `target_user_id`, `target_workspace_id` und
  `expires_at` bei der Erzeugung vollständig;
- `consumed_at`, `bound_issuer` und `bound_subject` **entweder gemeinsam gesetzt
  oder gemeinsam leer**;
- Konsum und Bindungsanlage **atomar in einer Datenbanktransaktion**, ohne
  Check-then-act als Sicherheitsgrenze;
- **keine** In-Process-Locks und **keine** globalen Anwendungsmutexe; mehrere
  Prozesse und App-Instanzen bleiben korrekt (LQ-130).

Bedingte Schreiboperationen nutzen die reguläre **Zeilensynchronisation der
Datenbank**; das ist ausdrücklich erwünscht. Ob der spätere Adapter ein bedingtes
`UPDATE`, einen Constraint-gesteuerten Insert, `SELECT … FOR UPDATE` oder eine
andere transaktional korrekte Strategie wählt, entscheidet **LQ-179** anhand des
tatsächlichen PostgreSQL-Verhaltens und der Tests. LQ-178 schreibt ausschließlich
die **beobachtbaren Invarianten** fest.

### Ablauf und Uhr beim Konsum

Der Runtime-Port bleibt unverändert und erhält **kein** `now`. Der persistente
Adapter verwendet eine injizierte aware-UTC-Uhr, exakt wie der bestehende
In-Memory-Vertrag: eine unbekannte oder bereits endgültig unbrauchbare Admission
braucht **keinen** Uhrzugriff; eine offene Admission wird gegen die
vertrauenswürdige Zeit geprüft; `now >= expires_at` gilt als abgelaufen — auch
exakt am Ablaufzeitpunkt — und bleibt **fachliche Ablehnung** ohne Bindung.
**Keine** vom Request, Browser, Provider, Token oder Claim gelieferte Zeit.

## 8. Fehlerklassifikation

**Fachliches `None`:** Admission unbekannt, abgelaufen oder abweichend
konsumiert; bestehendes oder kollidierendes Binding; Zielnutzer bereits an eine
andere Identität gebunden; jede andere normale Konkurrenzentscheidung. Alle Fälle
bleiben nach außen **ununterscheidbar**, damit kein Existenzorakel für Nutzer,
Bindung oder Admission entsteht.

**Technische, detailfreie Nichtverfügbarkeit:** Datenbank nicht erreichbar;
Transaktion nicht sicher abschließbar; gespeicherter Datensatz verletzt
strukturelle Invarianten; unerwartete Constraint-Verletzung, die **nicht**
eindeutig als normale Konkurrenzentscheidung klassifizierbar ist.

Keine Tabellen-, SQL-, Constraint-, Treiber-, Issuer-, Subject-, UserId-,
WorkspaceId- oder AdmissionId-Details in Exceptions, Logs, Traces oder
Metriklabels. **Einen neuen öffentlichen Exceptionnamen entscheidet LQ-178
nicht** — das gehört in den Adapter- und Anwendungsfallvertrag, der die Grenze
tatsächlich überschreitet.

## 9. Retention und Restore

Verbindliche Untergrenze, unabhängig von einer späteren Retention-Policy:

- Eine konsumierte Admission wird durch Restore, Reimport oder Wiederverwendung
  **niemals** erneut offen (LQ-130, fail-closed), und AdmissionIds werden
  **niemals** neu vergeben.
- Sie bleibt mindestens so lange als Datensatz oder **irreversibler Tombstone**
  erhalten, wie ihre Wiederverwendung oder die zugehörige Bindung relevant sein
  kann; naives Löschen mit späterer Wiedervergabe ist **verboten**.
- Kein Rollback einer konsumierten Admission ohne **atomaren** Rollback der
  gleichzeitig erzeugten Bindung.

Aufbewahrungsdauer und ein möglicher Tombstone-Slice bleiben offen, weil noch
keine allgemeine Retention-Policy existiert; das darf diese Untergrenze **nicht**
aufweichen.

## 10. Schema-Untergrenze

Mindestmodell, ohne die konkrete SQLAlchemy-/Alembic-Form vorwegzunehmen: die
Tabellen `external_identity_bindings` und `identity_admissions`; Eindeutigkeiten
für die Identität, den `UserId` und die AdmissionId; die drei
Consumption-Spalten als atomar zusammengehörige Gruppe; ausschließlich
timezone-aware Zeitspalten; **keine** Seed-Daten; **keine** fiktiven Foreign Keys
auf noch nicht vorhandene Tabellen; **keine** Änderung der Baseline-Migration.

Endgültige SQL-Datentypen und Kollationen werden hier **nicht** behauptet; sie
prüft LQ-179 gegen das tatsächliche PostgreSQL-Verhalten. Die **bytegenaue
Semantik** bleibt davon unberührt verbindlich: eine kollationsabhängige
Gleichheit für Issuer oder Subject wäre ein Vertragsbruch.

## 11. Testtopologie für LQ-179

SQLite-Tests genügen für Migrationssyntax und grundlegende Portsemantik, wie sie
`test_persistence_migration_gate.py` bereits nutzt; sie beweisen **keine** echte
Mehrprozess-Nebenläufigkeit. Die atomare Sicherheitsgrenze muss deshalb
**zusätzlich** gegen eine wegwerfbare PostgreSQL-Instanz geprüft werden. LQ-179
darf diesen Nachweis **nicht** durch In-Process-Locks oder serialisierte
Test-Doubles ersetzen; stellt CI noch keine PostgreSQL-Testinstanz bereit, muss
LQ-179 zuerst den kleinsten isolierten Test-Infrastrukturbedarf **offen
ausweisen** statt stillschweigend SQLite als Beweis zu verwenden. LQ-178 ändert
CI nicht.

## 12. Port-, Schichtgrenze und Reihenfolge

Unverändert bleiben `ExternalIdentityLookup`, `ExternalIdentityAdmissionStore`,
`complete_oidc_login`, `IdentityAdmissionRecord` und alle Identifier-Typen. Die
Provisionierung erhält später eine **getrennte** interne Anwendungsgrenze; der
Runtime-Store bekommt **keine** Administrationsmethode. Keine Persistence-Typen
in Application oder Transport, kein OIDC-Wiring in diesem Slice.

1. **LQ-178** — dieser Vertrag.
2. **LQ-179** — persistente Bindungs-/Admission-Migration und Adapter, inklusive
   PostgreSQL-Nebenläufigkeitsnachweis.
3. **Eigener Slice** — der autorisierte Onboarding-/Provisioning-Aufrufer.
4. Persistente Login-Transaktionen.
5. Persistente Sessions.
6. **Erst dann** Wiederaufnahme von LQ-177 Production-Wiring.

LQ-179 darf Adapter und Schema implementieren, aber **nicht** so tun, als gäbe es
bereits einen produktiv autorisierten Admission-Erzeuger.
