# LQ-180 — Persistente Identitätsbindung und Admission-Konsum

## Scope

Die Persistenz der LQ-178-Invarianten für den **Runtime-Pfad**: Lookup einer
bestehenden Bindung und der atomare Konsum einer Admission mit gleichzeitiger
erstmaliger Bindung. Die **Provisionierung** — Handle-Typ, eigener Port,
Erzeugungsmethode und AdmissionId-Generator — bleibt vollständig **LQ-181**
vorbehalten. Kein Production-Wiring, keine OIDC-, Callback-, Session- oder
Transportänderung.

Die Migration ist trotzdem **vollständig**: Sie legt auch die
Provisioning-Spalten und deren Eindeutigkeit an. Damit landet keine Invariante in
einem halb durchgesetzten Zwischenzustand, und LQ-181 fügt nur Code hinzu, kein
Schema. Da dieser Slice keine einzige Admission schreibt, findet der Adapter
ohne LQ-181 stets null Admissions und antwortet ausnahmslos `None` —
fail-closed, nicht unsicher.

## Tabellen

Revision `20260811_0002` auf `20260726_0001`; Baseline unverändert, keine
Seed-Daten, kein `created_at`, keine Foreign Keys auf nicht vorhandene Nutzer-
oder Workspace-Tabellen.

**`external_identity_bindings`** — `issuer`, `subject`, `user_id`, alle
`LargeBinary NOT NULL` mit Nichtleer-Check; `pk_external_identity_bindings` auf
`(issuer, subject)`; `uq_external_identity_bindings_user_id`. Kein
Surrogatschlüssel, keine Auditfelder.

**`identity_admissions`** — `admission_id` (PK), `provisioning_request`
(`UNIQUE`), `target_user_id`, `target_workspace_id`, `lifetime_microseconds`
(`BigInteger`, `CHECK > 0`), `expires_at`, `consumed_at`, `bound_issuer`,
`bound_subject`. Der Gruppencheck
`ck_identity_admissions_consumption_group` erzwingt, dass `consumed_at`,
`bound_issuer` und `bound_subject` **gemeinsam** leer oder **gemeinsam** gesetzt
sind: Konsum ist eine unteilbare Tatsache.

`lifetime_microseconds` hält die ursprünglich angeforderte Lebensdauer
verlustfrei, damit LQ-181 einen Retry ohne ein fachliches `created_at`
vergleichen kann.

## Warum `LargeBinary`

Jede identitätstragende Schlüsselspalte geht in eine **Eindeutigkeits- oder
Gleichheitsentscheidung** ein. Textgleichheit hängt in PostgreSQL an der
Kollation der Datenbank; unter einer nicht-deterministischen Kollation würden
verschiedene Werte gleichgesetzt und eine Unique-Grenze stillschweigend
aufgeweicht. Bytes machen die Entscheidung von jeder Datenbankkonfiguration
unabhängig und sind portabel — `BYTEA` unter PostgreSQL, `BLOB` unter SQLite.

Adapterseitig gilt **striktes UTF-8**: kein Trimming, kein Case-Folding, keine
Normalisierung, kein Error-Replacement. Ein nicht dekodierbarer gespeicherter
Wert, ein falscher Datenbanktyp und ein leerer Wert sind **technische
Nichtverfügbarkeit**, niemals stille Ersetzung und niemals `None`.

## PostgreSQL ist die normative Runtime

SQLite trägt weder einen Zeitzonen-Offset noch strukturierte
Constraint-Diagnosen. Es beweist deshalb ausschließlich: dass die Migration
läuft, dass Tabellen und portable Constraints existieren, den bytegenauen
Lookup und die technische Fehlergrenze. **Konsum, Ablauf, Idempotenz und
Nebenläufigkeit werden ausschließlich auf PostgreSQL bewiesen.** Es gibt keine
produktive Dialektverzweigung, die eine andere Datenbank als gleichwertig
ausgeben würde; der Adapter sperrt unbedingt mit `FOR UPDATE`.

## Adapter

`persistence/identity_store.py`, Klasse `DatabaseExternalIdentities` — erfüllt
`ExternalIdentityLookup` und `ExternalIdentityAdmissionStore` **strukturell**,
ohne Vererbung. Konstruktor: injizierte Engine und keyword-only aware-UTC-Uhr;
kein Generator, kein DSN, keine Provisioning-Abhängigkeit. `repr` ist konstant
`DatabaseExternalIdentities()` — ohne Engine, DSN, Uhr oder gespeicherte Werte.
Die Engine wird **nie** vom Adapter geschlossen; ihr Lifecycle gehört dem
späteren Composition-Root.

### `get_user_id`

Genau ein `SELECT` auf `(issuer, subject)`, bytegenau, **ohne Uhr** und ohne
jede Admission-Berührung. Ergebnis ist `UserId` oder `None`; keine
Existenzdetails. Zwei Adapterinstanzen auf derselben Datenbank sehen denselben
committeten Zustand.

### `consume_admission_and_bind`

Eine Transaktion, in fester Reihenfolge:

1. Admission-Zeile per `SELECT … FOR UPDATE` laden und sperren.
2. Unbekannt → `None`, **ohne Uhrzugriff**.
3. Bereits konsumiert → `bound_issuer`/`bound_subject` strikt dekodieren; exakt
   dieselbe Identity **und** eine bestehende Bindung auf `target_user_id` →
   derselbe `UserId`, weiterhin **ohne Uhr**; jede andere Wiederholung → `None`.
   Fehlt die Bindung zu einem konsumierten Datensatz oder zeigt sie auf einen
   anderen Nutzer, ist das **strukturelle Korruption** → technische
   Nichtverfügbarkeit, nicht `None`.
4. Offen → bestehende Bindung derselben Identity → `None`, Admission
   unangetastet; Zielnutzer bereits anderweitig gebunden → `None`; Uhr **genau
   einmal**; `now >= expires_at` → `None`, auch exakt am Ablaufzeitpunkt.
5. Bindung im **SAVEPOINT** einfügen, Admission mit **demselben** `now`
   konsumieren, beides **gemeinsam** committen.

Kein Rebinding, kein Account-Merge, kein zweiter Versuch.

### Konkurrenzklassifikation

Eine Verletzung von `pk_external_identity_bindings` oder
`uq_external_identity_bindings_user_id` ist normale Konkurrenz und wird zu
fachlichem `None`; die Admission bleibt durch den Savepoint-Rollback offen.
Gelesen wird der Constraintname aus den **strukturierten Treiberdiagnosen**,
niemals durch Parsen einer frei formulierten Meldung — ohne Namen wird nichts
klassifiziert, sodass eine unerwartete Verletzung nicht als fachliche
Entscheidung durchgehen kann. Nach einem `IntegrityError` wird der Savepoint
zurückgerollt; in einer abgebrochenen Transaktion wird nie weitergearbeitet.

**Sperrordnung:** immer zuerst die Admission-Zeile, danach jede
Bindungsentscheidung. Beide Teilnehmer ordnen sich damit identisch, und es
entsteht kein Zyklus. Deadlock-, Serialization- und Verbindungsfehler werden
**nicht** automatisch wiederholt; sie sind technische Nichtverfügbarkeit.

## Technische Fehlergrenze

`ExternalIdentityStoreUnavailable` mit dem stabilen Code
`external_identity_store_unavailable`, ohne freien Detailparameter. Normale
Exceptions werden ausschließlich an den äußeren Grenzen gefangen — Engine,
Transaktion, Resultat-Dekodierung, injizierte Uhr — und die neutrale Exception
entsteht **außerhalb** des Handlers, sodass austretende Instanzen
`__cause__ is None` **und** `__context__ is None` tragen. Eine bereits saubere
Instanz behält nur bei leerer Kette ihre Identität; eine schmutzige wird
ersetzt. `BaseException` bleibt objektidentisch und ungefangen. Kein breites
`except`, das einen Programmierfehler als fachliches `None` tarnt: `None`
entsteht ausschließlich aus benannten fachlichen Entscheidungen.

Kein SQL-Echo, keine werttragenden Logs, Traces oder Metriklabels; keine SQL-,
Tabellen-, Constraint-, Treiber-, Host-, Port-, DSN- oder Identifier-Werte in
Fehlern.

## Nicht enthalten

Provisioning-Handle-Typ, Provisioning-Port und -Methode, AdmissionId-Generator,
autorisierter Onboarding-Anwendungsfall, Production-Wiring, Änderungen an
`identity/ports.py`, an der LQ-179-Testinfrastruktur, an Dependencies,
Lockfile, CI, Container, `.grype.yaml` oder an OIDC-, Callback-, Session- und
Transportcode. Testseitige Direkt-Inserts von Admissions sind erkennbare
Fixture-Vorbereitung und **keine** produktive Seeding- oder Provisioning-API.
