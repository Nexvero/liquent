# LQ-178 — Admission-Provisionierung und Persistenzvertrag

## 1. Status, Ziel und Systemgrenze

Architekturentscheidung, **nur Vertrag**: kein Code, Modell, Port, Adapter, keine
Migration, kein Test. LQ-132 verlangt, dass eine Admission aus einem „expliziten
internen Onboarding-/Einladungsprozess" stammt, entscheidet diesen aber nicht —
und im Repository existiert er nicht: `IdentityAdmissionRecord` wird
ausschließlich in Tests konstruiert, es gibt keinen administrativen
Anwendungsfall, keine persistente Nutzer- oder Workspace-Entität und keine
Business-Tabelle. LQ-178 schließt diese Lücke — **Erzeugungsgrenze** und
**beobachtbare Persistenzinvarianten** — und blockiert alles Weitere, damit keine
Migration eine Architektur festschreibt, deren Voraussetzung fehlt.

## 2. Autorisierte Erzeugungsquelle

Eine `IdentityAdmissionRecord` darf **ausschließlich** durch eine getrennte
interne **Provisioning-Anwendungsgrenze** entstehen, die von einem bereits
autorisierten Onboarding-/Einladungsprozess aufgerufen wird. Sie ist **nicht**
Teil des OIDC-Callbacks und **nicht** Teil des Login-Starts; ausgeschlossen sind
Self-Sign-up, ein automatisches „erster Login erzeugt Nutzer und Admission", ein
HTTP-Endpunkt in LQ-178, ein Environment-Bootstrap, ein Migration-Seed, direkter
Datenbankzugriff aus Transportcode und jede Administrationsmethode am
Runtime-Port `ExternalIdentityAdmissionStore`.

Der konkrete autorisierte Aufrufer bleibt ein **eigener Slice**; **solange er
fehlt, wird die Provisioning-Grenze in Production nicht verdrahtet.**

## 3. Vertrauensgrenze der Zielidentifikatoren

Die Provisioning-Grenze erhält `target_user_id` und `target_workspace_id`
ausschließlich aus einer bereits autorisierten internen Onboarding-Entscheidung.
Sie erzeugt **keinen** Nutzer, Workspace, Membership, Rolle oder Berechtigung,
prüft keine Berechtigung anhand frei gelieferter HTTP-Werte, akzeptiert **keine**
OIDC-Claims als Zielnutzer und übernimmt **keinen** `UserId` aus Callback, Token
oder Providerantwort. Da heute weder eine persistente User- noch eine
Workspace-Tabelle existiert, schreibt LQ-178 **keinen fiktiven Foreign Key** fest;
beide bleiben typisierte interne Referenzen, und LQ-177 bleibt blockiert, bis die
autorisierte Quelle dieser Referenzen vorhanden ist.

## 4. AdmissionId, Zeit und Ablauf

Die Provisioning-Anwendungsgrenze erzeugt **selbst**:

- die `IdentityAdmissionId` über einen **kryptografisch sicheren, injizierten**
  Generator,
- `expires_at` aus einer **injizierten aware-UTC-Serveruhr** plus einer positiv
  validierten Admission-Lifetime.

Der Aufrufer darf weder AdmissionId noch Ablaufzeit frei setzen. Keine versteckte
Systemuhr, keine Normalisierung, kein Ersatzwert, keine Wiederverwendung einer
früheren AdmissionId. **`IdentityAdmissionRecord` besitzt kein `created_at`, und
dieses Feld wird hier nicht erfunden**: Der Erzeugungszeitpunkt trägt allein die
Ableitung von `expires_at`, wird nicht zusätzlich gespeichert, und der Record
bleibt unverändert.

### Wiederholungsidentität des Aufrufers

Weil die Grenze die AdmissionId selbst erzeugt, kann sie einen Retry nur dann von
einem neuen Vorgang unterscheiden, wenn der Aufrufer eine **stabile
Wiederholungsidentität** mitbringt. Der autorisierte Onboarding-Prozess erzeugt
deshalb **vor** dem ersten Aufruf einen kryptografisch zufälligen internen
**Provisioning-Request-Handle** und sendet ihn bei **jeder** technischen
Wiederholung desselben fachlichen Vorgangs unverändert mit.

Der Handle ist ausschließlich intern: kein HTTP-Header und kein öffentlicher
API-Vertrag, **nicht** die `IdentityAdmissionId`, kein OIDC-State, kein
Admission-Capability-Handle, in Callback, Login-Start und Runtime-Store
unsichtbar, `repr`-frei, niemals in Logs, Traces, Metriklabels oder Fehlertexten
und in der Persistenz **global eindeutig**. Den endgültigen Python-Typnamen
entscheidet der Implementierungsslice. Beim ersten erfolgreichen Provisioning
werden Handle, erzeugte AdmissionId, `target_user_id`, `target_workspace_id`,
`expires_at` und der offene Consumption-Zustand **atomar gemeinsam** gespeichert.

## 5. Identitätsbezug und Zustandsfolge

Bei der Provisionierung ist die spätere `ExternalIdentity` **bewusst unbekannt**:
kein Issuer, Subject, erwarteter Provider oder vorab gebundener OIDC-Claim — die
Admission autorisiert eine erstmalige Bindung, nicht eine bestimmte Identität.
Erst die **erste erfolgreiche atomare Konsumoperation** bindet sie an genau eine
`(issuer, subject)` und legt **gleichzeitig** die Bindung auf `target_user_id`
an; der `IdentityAdmissionRecord`-Vertrag bleibt unverändert.

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

**Provisionierung.** Jede AdmissionId ist global eindeutig und wird genau einmal
gespeichert; die Kollision eines intern erzeugten Handles ist ein **technischer**
Fehler und wird nie durch Überschreiben aufgelöst. Retry-Sicherheit hängt
**allein** am Provisioning-Request-Handle: Derselbe Handle mit exakt denselben
fachlichen Eingaben erzeugt **keine** zweite Admission, sondern liefert dieselbe
bereits gespeicherte AdmissionId — ohne `expires_at` zu verlängern, ohne neue
Lifetime, ohne fachlich wirksamen Uhrzugriff, ohne Zustandsüberschreibung und
ohne eine bereits konsumierte Admission erneut zu öffnen. Derselbe Handle mit
abweichendem Zielnutzer, Workspace, abweichender Lifetime oder sonstigem
fachlichem Inhalt ist ein **detailfreier technischer Vertragskonflikt**: kein
Überschreiben, keine zweite Admission.

Bleibt der Ausgang eines Datenbankaufrufs **unklar** — möglicherweise committet,
Antwort verloren —, wiederholt der autorisierte Aufrufer mit **demselben** Handle;
die eindeutige gespeicherte Zuordnung entscheidet, und es entsteht höchstens eine
Admission. Kein Raten und kein neuer Handle. **Ohne denselben Handle darf ein
unklar abgeschlossener Vorgang nicht automatisch wiederholt werden.** LQ-178
erfindet weiterhin **keinen öffentlichen** Idempotency-Key: Der Handle ist intern
und gehört zur getrennten Provisioning-Grenze, nicht zum Runtime-Port.

**Runtime-Konsum.** Offen → genau einmal konsumiert und gebunden. Eine **exakte**
Wiederholung — dieselbe Admission, Identität und bestehende Bindung — darf
denselben `UserId` liefern; jede **abweichende** bleibt `None`. Ein bestehendes
Binding hat **Vorrang** und verbraucht keine Admission (LQ-131/132, umgesetzt in
LQ-173). Kein Rebinding, kein Account-Merge.

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
Datenbank**; das ist erwünscht. Ob der Adapter ein bedingtes `UPDATE`, einen
Constraint-gesteuerten Insert, `SELECT … FOR UPDATE` oder eine andere
transaktional korrekte Strategie wählt, entscheidet **LQ-179** anhand des
tatsächlichen PostgreSQL-Verhaltens. LQ-178 schreibt nur die **beobachtbaren
Invarianten** fest.

### Ablauf und Uhr beim Konsum

Der Runtime-Port bleibt unverändert und erhält **kein** `now`; der Adapter
verwendet eine injizierte aware-UTC-Uhr wie der In-Memory-Vertrag. Eine unbekannte
oder endgültig unbrauchbare Admission braucht **keinen** Uhrzugriff; eine offene
wird gegen die vertrauenswürdige Zeit geprüft, und `now >= expires_at` gilt als
abgelaufen — auch exakt am Ablaufzeitpunkt — und bleibt **fachliche Ablehnung**
ohne Bindung. **Keine** vom Request, Browser, Provider, Token oder Claim
gelieferte Zeit.

## 8. Fehlerklassifikation

**Fachliches `None`:** Admission unbekannt, abgelaufen oder abweichend konsumiert;
bestehendes oder kollidierendes Binding; Zielnutzer bereits an eine andere
Identität gebunden; jede andere normale Konkurrenzentscheidung. Alle Fälle bleiben
nach außen **ununterscheidbar**, damit kein Existenzorakel entsteht.

**Technische, detailfreie Nichtverfügbarkeit:** Datenbank nicht erreichbar;
Transaktion nicht sicher abschließbar; gespeicherter Datensatz verletzt
strukturelle Invarianten; unerwartete Constraint-Verletzung ohne eindeutige
Deutung als normale Konkurrenzentscheidung.

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
- Der Provisioning-Request-Handle wird **nicht** so früh gelöscht oder
  wiederverwendet, dass ein späterer Retry dieselbe Operation erneut
  provisionieren könnte: keine Wiedervergabe, kein Restore, der eine
  Provisionierung reaktiviert oder dupliziert; Admission und Handle bleiben
  idempotent zuordenbar oder werden durch einen irreversiblen Tombstone vertreten.

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

Hinzu kommt der intern gespeicherte, **global eindeutige**
Provisioning-Request-Handle mit atomarer Zuordnung zu **genau einer** AdmissionId
und Schutz gegen denselben Handle mit abweichendem fachlichem Inhalt; ob Spalte in
`identity_admissions` oder getrennte Tabelle, entscheidet LQ-179 anhand von
Retention und PostgreSQL-Tests. Provisioning-Metadaten gelangen **nicht** in
`ExternalIdentityAdmissionStore`, Callback oder Session.

Endgültige SQL-Datentypen und Kollationen werden hier **nicht** behauptet; sie
prüft LQ-179 gegen das tatsächliche PostgreSQL-Verhalten. Die **bytegenaue
Semantik** bleibt verbindlich: eine kollationsabhängige Gleichheit für Issuer oder
Subject wäre ein Vertragsbruch.

## 11. Testtopologie für LQ-179

SQLite genügt für Migrationssyntax und grundlegende Portsemantik, wie
`test_persistence_migration_gate.py` es bereits nutzt, beweist aber **keine**
echte Mehrprozess-Nebenläufigkeit. Die atomare Sicherheitsgrenze muss deshalb
**zusätzlich** gegen eine wegwerfbare PostgreSQL-Instanz geprüft werden. LQ-179
darf das **nicht** durch In-Process-Locks oder serialisierte Test-Doubles
ersetzen; fehlt in CI eine PostgreSQL-Testinstanz, muss LQ-179 den kleinsten
isolierten Infrastrukturbedarf **offen ausweisen** statt stillschweigend SQLite
als Beweis zu verwenden. LQ-178 ändert CI nicht.

Der Testplan muss zusätzlich fordern: Ein erster Provisioning-Aufruf erzeugt
genau eine Admission; ein identischer Retry liefert dieselbe AdmissionId und
verlängert den Ablauf nicht; ein Retry nach bereits konsumierter Admission öffnet
nichts erneut; derselbe Request-Handle mit abweichenden Zieldaten wird abgelehnt;
zwei konkurrierende Prozesse mit demselben Handle erzeugen zusammen höchstens
eine Admission; ein unklarer Commit-Ausgang ist durch Wiederholung mit demselben
Handle auflösbar; und der Handle erscheint in keinem `repr`, keiner Exception,
keinem Log und keinem Metriklabel.

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
