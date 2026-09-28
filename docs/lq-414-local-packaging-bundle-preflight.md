# LQ-414 — Local Packaging and Bundle Preflight

## Ergebnis

LQ-414 führt den lokalen Packaging- und Bundle-Preflight bis zur ersten
verbindlichen Ablehnungsgrenze aus.

Der Preflight wird vor jeder Artefakterzeugung fail-closed abgebrochen.

Die aktuelle isolierte Laufzeit erfüllt die Buildvoraussetzungen nicht.

Es wurde kein Packaging- oder Bundlegate als bestanden ausgegeben.

## Quellstand

Der Arbeitsbaum steht detached auf Commit `83699b1`.

Zum Preflightzeitpunkt enthält er:

- 24 veränderte getrackte Pfade;
- 556 ungetrackte Pfade;
- insgesamt 580 uncommitted Pfade.

Der normale Bundle-Builder verlangt einen sauberen Quellbaum am exakten
Source-Commit.

Diese Voraussetzung ist nicht erfüllt.

Der unsaubere Baum wurde weder temporär bereinigt noch umkopiert, gestaged oder
committed.

## Verfügbare Python-Laufzeit

Lokal verfügbar ist:

- Python 3.9.6;
- Pip 21.2.4;
- Setuptools 58.0.4;
- Wheel 0.37.0.

Das Projekt verlangt Python `>=3.10`.

Der Build-Backendvertrag verlangt Setuptools `>=61.0`.

Der kontrollierte CI-Pfad verwendet:

- Python 3.12;
- Build 1.5.0;
- Setuptools 80.10.2;
- Wheel 0.47.0.

Die lokale Laufzeit ist daher weder versionskonform noch gleichwertig zum
kontrollierten Buildpfad.

## Fehlende Werkzeuge

Das Modul `build` ist nicht installiert.

Das Modul `pytest` ist nicht installiert.

Ein Aufruf von `python3 -m build --version` endet vor einem Build.

Ein Aufruf von `python3 -m pytest --version` endet vor einer Testsammlung.

LQ-414 installiert keine Pakete und löst keine Abhängigkeiten aus dem Netzwerk
auf.

Die vorhandene veraltete Setuptools-API wird nicht als Ersatzbuilder benutzt.

## Fehlende Gateeingaben

`LIQUENT_TEST_DATABASE_URL` ist nicht gesetzt.

Damit kann die PostgreSQL-Pflichtsuite nicht gegen einen freigegebenen
disposable Server ausgeführt werden.

`SOURCE_DATE_EPOCH` ist nicht gesetzt.

Ein kontrollierter Artefaktzeitstempel ist daher nicht gebunden.

Es liegt keine neue `verification.json` vor, die den kumulierten Source-Commit,
Teststand und alle Pflichtchecks belegt.

## Bewusst nicht ausgeführte Schritte

Aufgrund der ersten Ablehnungsgrenzen wurden nicht ausgeführt:

- Wheel-Build;
- Source-Distribution-Build;
- temporäre Wheel-Installation;
- Import aller 58 Console Entry Points;
- Scan des Wheels auf 65 Operator-Pythondateien;
- Migrationinventar- und Headprüfung am echten Wheel;
- Erzeugung neuer Verification Evidence;
- Operationsbundle-Build;
- Bundle-Verifikation;
- Signatur, Promotion oder Publication.

Nicht ausgeführt bedeutet ausdrücklich nicht bestanden.

## Artefaktzustand

LQ-414 erzeugt kein Repository-`dist/` und kein `build/`.

Es erzeugt kein `src/liquent.egg-info`.

Es verbleibt kein Wheel, keine Source Distribution und kein Operationsarchiv
aus diesem Lauf.

Es gibt daher keine neuen Artefakthashes oder Releaseprovenance.

## Statisch bestätigter Sollpfad

Die Quality-Workflowdefinition bindet den vorgesehenen Wheel-Pfad an:

1. erfolgreichen normalen Testjob;
2. Python 3.12;
3. gelockte Buildwerkzeuge;
4. Installation mit Constraintdatei;
5. `SOURCE_DATE_EPOCH` aus dem reviewten Commit;
6. `python -m build --wheel --no-isolation`;
7. fail-closed Wheel-Verifikation;
8. Upload erst nach erfolgreicher Verifikation.

Dieser statische Sollpfad ist vorhanden, wurde lokal aber nicht ausgeführt.

Der bestehende Workflow baut derzeit nur das Wheel; ein aktueller expliziter
Source-Distribution- und Operationsbundle-Job bleibt separat nachzuweisen.

## Sicherheitsentscheidung

Ein Build mit Python 3.9, unterschrittenem Backend und altem Wheel wäre keine
zulässige Annäherung an das Releasegate.

Ein Build aus dem uncommitted Arbeitsbaum könnte zudem nicht die vom
Bundle-Builder verlangte saubere Commitbindung erfüllen.

Ein synthetisches Evidence-Dokument darf fehlende Tests, PostgreSQL-Läufe oder
Artefaktprüfungen nicht als bestanden markieren.

Der korrekte Ausgang ist deshalb `blocked before build` ohne Artefakt.

## Statischer Nachweis

`tests/test_lq414_local_packaging_bundle_preflight.py` sichert:

- die deklarierten Python- und Backend-Mindestgrenzen;
- die gelockten CI-Werkzeugversionen;
- den Python-3.12- und No-Isolation-Wheelpfad;
- die dokumentierte Trennung zwischen statisch vorhanden und lokal ausgeführt;
- das Verbot eines falschen Packaging-Erfolgsclaims;
- den additiven Roadmap-Handoff an LQ-415.

Der Test baut kein Paket und benötigt keine externe Abhängigkeit.

## Offene Pflichtgates

Weiterhin offen sind:

- geeignete Python-Laufzeit;
- gelocktes Build-Frontend und Backend;
- vollständige normale Testsuite;
- aktuelle PostgreSQL-Pflichtsuite;
- sauberer, reviewter Source-Commit;
- Wheel und Source Distribution;
- Entry-Point-Importcheck;
- echter Wheel-Inventarscan;
- neue atomare Verification Evidence;
- Operationsbundle-Build und -Verifikation;
- Secret-, Konfliktmarker- und finaler Diffscan am Releaseumfang.

## Nichtziele

LQ-414 ändert keine Produktlogik, Packagingkonfiguration, CI-Definition,
Migration, Entry Points oder Bundlepolicy.

Der Slice installiert keine Dependency, verwendet kein Netzwerk und führt
keine Datenbank-, Provider-, Publication-, Signatur-, Promotion-, Staging- oder
Deploymentaktion aus.

Er erzeugt keinen Branch und staged, committed oder pusht nichts.

## Nächster Slice

LQ-415 sollte einen kontrollierten grünen Build-Runner spezifizieren und
implementieren, der in einer geeigneten Laufzeit alle lokalen Packaginggates
in fester Reihenfolge ausführt.

Seine Evidenz darf nur atomar grün entstehen und muss bei fehlendem oder
fehlgeschlagenem Pflichtgate detailfrei ohne Erfolgsartefakt enden.
