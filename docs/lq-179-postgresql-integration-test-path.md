# LQ-179 — Wegwerfbarer PostgreSQL-Integrationstestpfad

## Zweck

LQ-178 §11 verlangt, dass die atomare Sicherheitsgrenze der Identitätsbindung
**zusätzlich** gegen eine wegwerfbare PostgreSQL-Instanz geprüft wird und dieser
Nachweis **nicht** durch In-Process-Locks, serialisierte Test-Doubles oder
stillschweigendes SQLite ersetzt werden darf. Diesen Pfad gab es nicht:
`quality.yml` enthielt in keinem Job einen `services:`-Block, es gab keinen
Test-DSN, kein `conftest.py` und keine Datenbank-Fixture.

Dieser Slice liefert **ausschließlich** den Pfad. **Keine** Business-Migration,
**kein** Identity-, Admission-, Session- oder OIDC-Baustein, **kein** Port und
**keine** Vorwegnahme der späteren SQL-Strategie.

## Eigener CI-Job

Der neue Job `postgres-integration` läuft auf Pull Requests und Pushes zu `main`
und führt **ausschließlich** die markierten Tests aus:

```
python -m pytest -m postgres_integration -q
```

Er verwendet dieselben gepinnten Actions und dieselbe Installation aus
`requirements/ci.lock` wie der `test`-Job. **Keine neue Dependency, kein
Lockfile-Eingriff.** Die Zugangsdaten sind fest, nicht produktiv und leben nur in
diesem Job; **kein** Repository-Secret wird benötigt und **kein**
Deployment-Secret wiederverwendet. `operations/compose` und `operations/deploy`
bleiben unberührt.

### Service-Image

```
postgres@sha256:9a8afca54e7861fd90fab5fdf4c42477a6b1cb7d293595148e674e0a3181de15
```

Digest-gepinnt wie jede Action in diesem Repository; ein floating Tag würde den
Nachweis gegen ein ungeprüftes Image laufen lassen. Aufgelöst über die Docker-
Registry-API aus `library/postgres:18-alpine`; der OCI-Index enthält
`linux/amd64` und ist damit auf `ubuntu-24.04` lauffähig. Der Healthcheck nutzt
`pg_isready` mit begrenztem Intervall, Timeout und Retry-Zahl. Das
Deployment-PostgreSQL-Image bleibt unverändert.

## Fail-loud statt stilles Skip

Zwei Umgebungsvariablen steuern den Pfad:

| Variable | Wirkung |
|---|---|
| `LIQUENT_TEST_DATABASE_URL` | der einzige DSN; ein anderes Backend als PostgreSQL ist ein Fehler |
| `LIQUENT_REQUIRE_POSTGRES_TESTS=1` | macht den Pfad **verpflichtend** |

Ohne DSN und ohne `REQUIRE` werden die markierten Tests lokal regulär
übersprungen. Ist `REQUIRE=1` gesetzt und fehlt der DSN, ist er unbrauchbar oder
adressiert kein PostgreSQL, **schlägt der Lauf fehl** — kein Skip, keine
SQLite-Ausweichdatenbank, kein In-Memory-Fallback, keine Umdeutung eines
Verbindungsfehlers in Erfolg.

Der Job setzt beide Variablen. Sammelt `pytest -m postgres_integration` keine
Tests, endet es mit Exit-Code 5 und der Job wird rot; ein `--no-tests-ok`-artiger
Mechanismus kommt nicht zum Einsatz.

## Isolation

`tests/conftest.py` legt **je Test eine eigene wegwerfbare Datenbank** an
(`liquent_test_<zufall>`), führt `upgrade_to_head(...)` darauf aus, liefert eine
Engine und löscht die Datenbank danach zuverlässig wieder. Kein Test sieht die
Objekte eines anderen, und Alembic läuft gegen exakt die Isolation, die geprüft
wird. Es gibt **keine** geteilte Business-Datenbank.

Die Fixture braucht **keine** Shell, kein `psql`, kein Docker und kein Compose —
nur die gepinnten SQLAlchemy- und psycopg-Werkzeuge und den vorhandenen
`build_engine`. Fehlermeldungen nennen die **Variable**, nie ihren Wert; ein DSN
mit Zugangsdaten erscheint weder in `repr`, Assertiontext noch Log. Eine zweite
Engine auf derselben URL liefert genuin getrennte Connections, sodass ein Rennen
der Server entscheidet und nicht dieser Prozess.

## Die drei Nachweise

`tests/test_postgresql_integration_path.py`, drei Testfunktionen:

1. **Server und Migration.** Der Dialekt ist tatsächlich `postgresql`,
   `SELECT version()` beginnt mit `PostgreSQL`, und eine **zweite unabhängige**
   Engine sieht den committeten Alembic-Revisionsstand als `expected_head()`.
   Kein SQLite.
2. **Echtes Rennen.** Eine nur für den Test angelegte temporäre Tabelle hält
   einen einzigen offenen Claim. Zwei getrennte Engines fahren zwei echte
   Transaktionen und führen gleichzeitig dasselbe bedingte `UPDATE … WHERE
   taken_by IS NULL` aus. Genau **eine** Operation erhält `rowcount == 1`, und
   der Endzustand trägt genau deren Kennung. Eine `threading.Barrier` koordiniert
   **ausschließlich den gleichzeitigen Start**; sie entscheidet nichts. Es gibt
   keine geteilte SQLAlchemy-Session und kein Python-Lock im Entscheidungspfad —
   die Serialisierung leistet die Zeile selbst.
3. **Isolation und Sichtbarkeit.** Uncommitteter Zustand ist für eine zweite
   Connection unsichtbar, ein Rollback hinterlässt keinen Teilzustand, und ein
   Commit wird anschließend gesehen.

Keine Identity- oder Admission-Tabelle, keine Vorwegnahme der LQ-180-Strategie.

## Was SQLite weiterhin leistet — und was nicht

Der bestehende `test`-Job und `test_persistence_migration_gate.py` bleiben
unverändert: SQLite prüft Migrationssyntax, portable Constraints und
grundlegende Semantik. Es beweist **weder** PostgreSQL-Kollation **noch**
Mehrprozess-Atomarität. Ein späterer Bericht darf „Concurrency bewiesen"
niemals allein aus SQLite ableiten.

## CI-Gate

Ein Fehler in `postgres-integration` macht den Workflow rot. Der
`provenance`-Job hängt jetzt an `[container, postgres-integration]`, sodass auf
einem Push zu `main` nichts attestiert wird, dessen Mehrprozessnachweis
fehlgeschlagen ist oder nie lief. Auf Pull Requests bleibt `provenance`
planmäßig übersprungen. `wheel` und `container` warten nicht künstlich auf den
neuen Job; SBOM- und Grype-Regeln bleiben unverändert.

## Nicht enthalten

Keine Business-Migration, kein Adapter, kein Port, kein Modell, keine Änderung an
Runtime-Dependencies, Lockfile, Alembic-Migrationen, Persistence-Produktionscode,
Identity-/Admission-/Session-/OIDC-Modulen, `Dockerfile`, `operations/` oder
`.grype.yaml`. LQ-180 (persistente Bindung und Admission) bleibt ungestartet,
LQ-177 bleibt blockiert.
