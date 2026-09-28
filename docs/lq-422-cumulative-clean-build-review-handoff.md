# LQ-422 — Cumulative Clean Build and Review Handoff

## Zweck

LQ-422 inventarisiert den kumulierten Arbeitsbaum nach Abschluss des lokalen
Preflightpfads erneut und bereitet den sauberen Build- und Review-Handoff vor.

Der Slice erzeugt keinen Branch, staged oder committed nichts und führt keinen
echten Build oder externen Lauf aus.

## Git-Ausgangspunkt

Der Arbeitsbaum steht weiterhin detached auf Commit `83699b1`.

Es ist kein Branch ausgecheckt.

Es sind null Dateien gestaged.

Der Bestand ist weder committed, gepusht noch deployed.

## Zwei unterschiedliche Git-Inventare

Vor LQ-422 meldet das normale Porcelain-Format:

- 24 veränderte getrackte Dateien;
- 575 ungetrackte Status-Einträge;
- insgesamt 599 Status-Einträge.

Mit `--untracked-files=all` ergibt die tatsächliche Dateiinventur:

- 24 veränderte getrackte Dateien;
- 639 ungetrackte Dateien;
- insgesamt 663 uncommitted Dateien.

Beide Zahlen sind korrekt, messen aber nicht dasselbe.

## Ursache der Differenz

Das normale Statusformat fasst das vollständig neue Verzeichnis
`src/liquent_platform/operators/` als einen ungetrackten Eintrag zusammen.

Die Dateiinventur zählt dort 65 Pythondateien einzeln.

Dadurch ist die Dateizahl um 64 höher als die Zahl der normalen
Status-Einträge.

Frühere LQ-411- und Fortschrittsangaben verwendeten die Status-Einträge und
nannten sie teilweise verkürzt Pfade.

LQ-422 friert für Review und Staging ausschließlich die dateigenaue Zählung
ein.

## Dateigenaue Top-Level-Verteilung

Die 663 uncommitted Dateien verteilen sich vor LQ-422 auf:

- 240 unter `docs`;
- 232 unter `tests`;
- 167 unter `src`;
- 18 unter `operations`;
- fünf unter `tools`;
- `pyproject.toml`.

Es existiert keine ungetrackte Datei außerhalb dieser erlaubten Ziele.

## Getrackter Diff

Der getrackte Anteil umfasst 24 Dateien mit:

- 4890 Einfügungen;
- 37 Löschungen.

Die Roadmap ist mit Abstand die größte getrackte gemeinsame Datei.

Weitere gemeinsame Grenzen sind:

- `pyproject.toml`;
- Compose-Konfiguration und Runtimebeispiel;
- Identity-Ports und persistente Fehlergrenzen;
- Application- und HTTP-Wiring;
- bestehende Migration-, OIDC- und Identitytests.

Diese Dateien enthalten Fortschreibungen vieler Slices und sind nicht sicher
nach dem jeweils letzten Slice teilbar.

## Aktuelles Paket- und Migrationsinventar

Der unveränderte Paketbestand umfasst:

- 58 Console Entry Points;
- 64 Operatorimplementierungs- und Hilfsmodule;
- zusätzlich `operators/__init__.py`, also 65 gepackte Operator-Pythondateien;
- 27 lineare Migrationen;
- Head `20260819_0027`.

LQ-422 ergänzt keine dieser Kategorien.

## Read-only Dateiprüfungen

Die erneute Dateiprüfung findet:

- null Konfliktmarkerdateien;
- null symbolische Dateien unter `docs`, `operations`, `src`, `tests` und
  `tools`;
- null ungetrackte Dateien größer als 1 MiB;
- null ungetrackte Dateien außerhalb des erlaubten Scopes;
- einen bestandenen `git diff --check`.

Diese Prüfungen verändern den Arbeitsbaum nicht.

## Secret-Pattern-Triage

Der begrenzte Patternscan findet zwei Dateien:

- `tests/test_operational_release_bundle.py`;
- `tests/test_lq304_research_worker_staging_evidence.py`.

Beide enthalten absichtlich den Header `BEGIN PRIVATE KEY` als
Negativtest-Fixture für fail-closed Secret-Erkennung.

Es wurde kein Schlüsselbody und kein Credentialwert gefunden.

Der finale Review muss diese beiden Treffer als erwartete Testfixtures
bestätigen; sie dürfen nicht still aus einem Scan herausgefiltert werden.

Dieser begrenzte Patternscan ersetzt keinen dedizierten Secret-Scanner.

## Reviewabschnitte

Der kumulierte Diff soll in sieben fachlichen Abschnitten reviewed werden:

1. persistente Identity, Authority und Membership, LQ-183 bis LQ-232;
2. Release Registry, Signing und Publication, LQ-234 bis LQ-288;
3. persistente Research Jobs und Worker, LQ-289 bis LQ-304;
4. Staging, Inspection und Recovery, LQ-305 bis LQ-328;
5. disposable Runtime Cleanup und Lineage, LQ-329 bis LQ-387;
6. PostgreSQL Volume-Disposition und -Deletion, LQ-388 bis LQ-410;
7. Integrations-, Bundle- und lokaler Preflightpfad, LQ-411 bis LQ-422.

Diese Abschnitte sind Reviewansichten, keine unabhängigen Commitgrenzen.

## Empfohlene Git-Grenze

Ein mechanischer Split nach Verzeichnis, Hunk oder Slice bleibt unsicher.

Ports, Migrationen, Wiring, Paketregistrierung, Tests, Tools und Roadmap bilden
einen linearen kumulierten Stand.

Empfohlen bleibt ein einzelner atomarer grüner Integrationscommit mit sieben
PR-Reviewabschnitten.

Der sichere technische Rollback ist danach der vollständige Revert dieses
Commits, nicht ein selektiver Migrations- oder Operatorrevert.

## Voraussetzungen vor Branch und Staging

Vor jeder Gitmutation müssen ausdrücklich vorliegen:

1. Benutzerfreigabe für Branch und Staging;
2. geeignete Python-3.12-Laufzeit;
3. gelockte Build- und Testwerkzeuge;
4. freigegebenes disposable PostgreSQL-Test-DSN;
5. Entscheidung für ein neues privates Preflightziel außerhalb des
   Sourcebaums;
6. erneute dateigenaue Inventur unmittelbar vor Staging.

LQ-422 erteilt keine dieser Freigaben.

## Vorgesehene grüne Reihenfolge

Nach Herstellung der Voraussetzungen lautet die Reihenfolge:

1. Branch vom exakten `83699b1` erstellen;
2. nur die bekannten 663-plus-LQ-422-Dateien inventarisieren;
3. den kontrollierten lokalen Preflight aus LQ-417 ausführen;
4. normale Tests, PostgreSQL, Wheel, sdist, Entry Points, Diff und Bundle aus
   dessen atomarer Evidenz prüfen;
5. Secret- und Konfliktmarkerscan gegen den exakten finalen Scope wiederholen;
6. erst danach die bekannten Dateien stagen;
7. `git diff --cached --check` und staged Inventar ausführen;
8. staged Diff in den sieben Reviewabschnitten prüfen;
9. erst nach erneuter ausdrücklicher Freigabe atomar committen.

Push, Pull Request und Deployment bleiben danach nochmals separate Aktionen.

## Aktuelle Buildblocker

Die LQ-414-Blocker bestehen unverändert:

- lokal nur Python 3.9.6;
- fehlende Module `build` und `pytest`;
- veraltete lokale Setuptools- und Wheel-Versionen;
- fehlendes PostgreSQL-Test-DSN;
- detached und uncommitted Sourcebaum.

Der LQ-415-bis-LQ-421-Pfad ist synthetisch geprüft, aber nicht real grün
ausgeführt.

## Nichtziele

LQ-422 installiert keine Dependency und nutzt kein Netzwerk.

Der Slice erzeugt keinen Branch, staged oder committed nichts und pusht nicht.

Er baut, signiert, promotet, publiziert oder deployed kein Artefakt.

Er löscht, verschiebt oder bereinigt keine vorhandene Datei.

## Entscheidung

Der kumulierte Bestand ist fachlich reviewbar, aber noch nicht build- oder
commitbereit.

Die nächste sinnvolle Arbeit ist keine neue Produktfunktion.

Erforderlich ist entweder die ausdrückliche Freigabe zur Herstellung eines
Branches und einer geeigneten Buildlaufzeit oder ein letzter read-only
Pre-Staging-Manifestlauf.

## Nächster Slice

LQ-423 sollte ohne Gitmutation ein deterministisches dateigenaues
Pre-Staging-Manifest für den erlaubten Scope erzeugen und gegen die sieben
Reviewabschnitte prüfen.

Das Manifest darf weder Staging noch Commit, Push oder Release autorisieren.
