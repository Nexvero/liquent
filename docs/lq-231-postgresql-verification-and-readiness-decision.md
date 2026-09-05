# LQ-231 — PostgreSQL Verification and Readiness Decision

## 1. Ergebnis

LQ-231 führt das in LQ-230 offen gelassene Release-Gate tatsächlich aus.

Ein isolierter PostgreSQL-16-Cluster wurde ausschließlich für den Testlauf in
einem temporären Verzeichnis initialisiert, über einen lokalen Unix-Socket
gestartet und nach Abschluss kontrolliert entfernt.

Der neue integrierte Shared-Environment-Test besteht. Nach Korrektur zweier
veralteter Testvorbedingungen besteht auch die vollständige PostgreSQL-Suite
und anschließend die gesamte Testsuite.

LQ-177 ist damit auf Code-, Persistenz-, Control-Plane- und Runtime-Ebene
verifiziert abgeschlossen. Diese Entscheidung ist keine automatische
Deployment- oder konkrete Infrastrukturfreigabe.

## 2. Verifikationsumgebung

Verwendet wurden:

- PostgreSQL 16.14;
- Python 3.12 aus der vorhandenen Projekt-`.venv`;
- pytest 9.1.1;
- SQLAlchemy 2.0.51;
- FastAPI 0.140.0;
- psycopg 3.3.4.

Der aktuelle Quellbaum des isolierten LQ-183-Worktrees wurde getestet. Die
`.venv` aus dem Schwester-Worktree stellte nur die installierte Laufzeit bereit.

## 3. Isolierter PostgreSQL-Cluster

Der lokale Standardserver war nicht erreichbar. LQ-231 verwendete deshalb
keine unbekannte bestehende Datenbank.

Ein neuer Cluster wurde unter einem eindeutig begrenzten `/tmp`-Pfad mit
Trust-Authentisierung für den lokalen Testprozess initialisiert.

Der Server lauschte ausschließlich auf einem Unix-Socket; TCP-Listen war
deaktiviert. Die Test-Fixture erzeugte weiterhin pro Test eine eigene
disposable Datenbank und migrierte sie auf den exakten Head.

## 4. Erzwungene PostgreSQL-Pflicht

Jeder normative Lauf setzte:

- `LIQUENT_TEST_DATABASE_URL` auf den isolierten PostgreSQL-Socket;
- `LIQUENT_REQUIRE_POSTGRES_TESTS=1`.

Damit konnte ein fehlender oder unbrauchbarer DSN weder zu einem Skip noch zu
einem SQLite-Fallback werden.

Der registrierte Marker `postgres_integration` blieb die Auswahlgrenze für den
gezielten Datenbanklauf.

## 5. Integrierter LQ-230-Einzelnachweis

Zuerst wurde ausschließlich
`tests/test_lq230_shared_environment_end_to_end.py` ausgeführt.

Ergebnis:

```text
1 passed in 0.60s
```

Damit ist die konkrete durchgängige Kette isoliert grün, bevor Ergebnisse der
größeren Suite mögliche Zuordnungsfehler verdecken konnten.

## 6. Erster vollständiger PostgreSQL-Lauf

Der erste Lauf aller markierten Integrationstests ergab:

```text
72 passed, 2 failed, 2813 deselected
```

Beide Fehler waren reproduzierbare veraltete Testvorbedingungen. Kein Fehler
trat im LQ-230-Pfad oder in einer Produktmutation auf.

LQ-231 dokumentiert diese Fehler statt sie aus dem finalen Ergebnis zu
entfernen.

## 7. Veralteter Onboarding-Composition-Test

Der PostgreSQL-Test verwendete einen deterministischen Material-Sentinel aus
der Zeit vor LQ-221.

Seit LQ-221 benötigt die Bootstrap-Composition zusätzlich getrennte Generatoren
für User- und Workspace-Lifecycle-Revisionen. Der entsprechende SQLite-Test war
bereits aktualisiert, der PostgreSQL-Zwilling jedoch nicht.

Die Testfixture erhielt dieselben zwei typisierten deterministischen Methoden.
Produktionscode und Sicherheitsvertrag wurden nicht verändert.

## 8. Veralteter Login-/Session-Composition-Test

Der zweite Test versuchte eine Browser-Session für `user-191` anzulegen, ohne
diesen Nutzer zuvor persistent zu erzeugen.

Seit LQ-223 prüft Sessionanlage fail-closed den aktuellen aktiven Nutzer. Der
Fehler bestätigte deshalb die Sicherheitswirkung und war kein Grund, sie zu
lockern.

Der Test bootstrapped nun vor Sessionausgabe einen aktiven Nutzer und Workspace
über `DatabaseInitialIdentityAuthorityBootstrap` samt typisierten Revisionen.
Es wurde kein direkter SQL-Seed ergänzt.

## 9. Gezielter Regression-Retry

Nach den beiden Testkorrekturen wurden nur die betroffenen PostgreSQL-Tests
erneut ausgeführt.

Ergebnis:

```text
2 passed in 0.34s
```

Damit waren beide Ursachen isoliert bestätigt, bevor die Gesamtsuite erneut
gestartet wurde.

## 10. Vollständige PostgreSQL-Suite

Der zweite erzwungene Marker-Lauf ergab:

```text
74 passed, 2813 deselected in 7.87s
```

Es gab keine Fehler, Skips als Ersatz für PostgreSQL oder unerwartete
Ausnahmen.

Die 74 Tests umfassen Migration, Bootstrap, Konkurrenz, Sessions, Admission,
Trust, Membership, Authority-Lifecycle, Recovery und LQ-230-End-to-End.

## 11. Vollständige Testsuite

Danach wurde die gesamte Suite mit weiterhin verpflichtendem PostgreSQL-DSN
ausgeführt.

Ergebnis:

```text
2887 passed, 53 warnings in 19.68s
```

Damit sind sowohl alle normalen Regressionen als auch alle markierten
PostgreSQL-Integrationen in einem gemeinsamen Lauf grün.

## 12. Warnungen

Die 53 Warnungen stammen aus dem bekannten Python-3.12-/SQLite-Datetime-
Adapter-Deprecationpfad von SQLAlchemy.

Sie traten ausschließlich in bestehenden SQLite-Tests auf und verursachten
keinen Fehler. Der normative PostgreSQL-Pfad ist davon nicht betroffen.

Die Warnungen sind technischer Folgepflegebedarf, aber kein LQ-177-
Readiness-Blocker.

## 13. Bereinigung

Nach allen Testläufen wurde der temporäre PostgreSQL-Server mit Fast-Shutdown
kontrolliert gestoppt.

Anschließend wurde ausschließlich der vorher per `realpath` validierte
temporäre LQ-231-Pfad entfernt.

Es blieb kein Testserver, keine disposable Datenbank und kein temporäres
Clusterverzeichnis zurück. Die Bereinigung ist nicht wiederherstellbar, betraf
aber ausschließlich für diesen Slice erzeugte Testdaten.

## 14. LQ-177-Readiness-Entscheidung

Die vollständige kontrollierte Kette ist nun implementiert und ausgeführt
verifiziert:

- explizites Production-Wiring und Process-Ownership;
- persistente Sessions und aktuelle fail-closed Actorprüfung;
- OIDC-Trust-Konfiguration und Authority-Verwaltung;
- Membership-, Permission- und Authority-Verwaltung;
- initialer Bootstrap und regulärer User-/Workspace-Lifecycle;
- Lockout-Schutz und eng begrenzte Recovery;
- beobachtbare aktuelle Runtime-Autorisierung und späterer Entzug.

LQ-177 ist technisch abgeschlossen.

## 15. Grenze dieser Entscheidung

Technische Readiness bedeutet nicht, dass ein konkretes Shared Environment
bereits deployed, konfiguriert oder organisatorisch freigegeben ist.

Vor einem realen Deployment bleiben umgebungsspezifisch zu prüfen:

- Secrets und DSN;
- TLS, Origins und Callback-Ziele;
- IdP- und OIDC-Konfiguration;
- Backup, Restore und Monitoring;
- Operatorzugänge und Vier-Augen-Prozesse;
- tatsächlicher Migration- und Rolloutplan.

LQ-231 führt keine dieser externen Aktionen aus.

## 16. Keine Produktänderung aus dem Audit

LQ-231 ändert keine Produktlogik, Migration, Tabelle, Route, Authority oder
Runtime-Composition.

Die einzigen Codeänderungen betreffen zwei PostgreSQL-Testfixtures, die auf
bereits geltende Bootstrap- und Aktivnutzer-Vorbedingungen angehoben wurden.

Es gibt keinen Commit, Push, Deployment oder Serviceeingriff.

## 17. Nächster Slice

LQ-232 kann als kontrollierter Release-Handoff-Audit den kumulierten
Arbeitsbaum, Migrationspfad, Betriebsdokumente und Deployment-Voraussetzungen
prüfen.

Er darf ohne expliziten Auftrag weder committen noch pushen noch ein reales
Environment verändern.

## 18. Handoff-Audit durch LQ-232

LQ-232 bestätigt lineare Migrationen, konflikt- und whitespacefreien Scope,
vollständige Operator-Runbooks, Runtime-Isolation und die LQ-231-Testevidenz.

Der technische Stand ist reviewfähig, aber weiterhin vollständig uncommitted
auf detached HEAD. Branch, Staging, Commit, Push, Pull Request und Deployment
bleiben bewusst nicht ausgeführt und benötigen getrennte Autorisierung.
