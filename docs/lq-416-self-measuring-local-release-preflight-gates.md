# LQ-416 — Self-Measuring Local Release Preflight Gates

## Zweck

LQ-416 implementiert die zehn konkreten lokalen Gateadapter für den
kontrollierten LQ-415-Runner.

Die Adapter messen den lokalen Systemzustand selbst und erzeugen ihre
phasengebundenen Receipts nur nach erfolgreicher Prüfung.

Es gibt weiterhin keine automatische CLI- oder CI-Aktivierung.

## Gemeinsame Quellbindung

Vor jeder einzelnen Phasenmessung liest der Adapter frisch:

- `git rev-parse HEAD`;
- `git status --porcelain=v1 --untracked-files=all`.

Nur ein sauberer Baum und ein vollständiger 40-stelliger Commit-SHA werden
akzeptiert.

Damit sperrt eine nachträgliche Quelländerung jede spätere Phase.

## Receiptbildung

Adapter akzeptieren keinen Allow-Boolean und keinen caller-supplied Status.

Jeder Adapter erzeugt Fakten aus seiner eigenen Messung, serialisiert sie
kanonisch und bindet deren SHA-256-Digest in das Receipt.

Nur nach einer vollständigen Messung wird `status=passed` erzeugt.

Fehler werden als `local release preflight gate rejected` detailfrei
vereinheitlicht.

## Runtime

Das Runtimegate verlangt exakt Python 3.12 und die gelockten Versionen:

- Build 1.5.0;
- Pytest 9.1.1;
- Setuptools 80.10.2;
- Wheel 0.47.0.

Fehlende oder abweichende Distributionen sperren den Lauf.

## Source

Das Sourcegate liest den Commitzeitstempel aus Git und setzt daraus den
privaten `SOURCE_DATE_EPOCH` des Laufkontexts.

Freie Zeitstempel vom Aufrufer sind nicht erforderlich.

## Tests

Das normale Testgate führt die vollständige Suite aus und parst bestandene
Tests sowie Warnungen aus dem Prozessresultat.

Das PostgreSQL-Gate verlangt ein vorhandenes
`LIQUENT_TEST_DATABASE_URL`, setzt `LIQUENT_REQUIRE_POSTGRES_TESTS=1` und
führt ausschließlich den Marker `postgres_integration` aus.

Nach erfolgreicher Suite liest es `SHOW server_version` über dieselbe
Umgebungs-DSN und bindet die gemessene Versionsnummer in seine Fakten.

Ein fehlendes DSN, ein Skip-only-Lauf oder ein Prozessfehler sperrt den Lauf.

## Distributionen

Der Buildadapter ruft fest `python -m build --no-isolation` auf und schreibt
in den privaten LQ-415-Workspace.

Er verlangt exakt ein Liquent-Wheel und eine Liquent-Source-Distribution.

Beide Artefaktdigests werden aus den erzeugten Bytes berechnet.

## Wheel

Das Wheelgate verwendet beide bestehenden fail-closed Prüfer.

Es verlangt:

- 58 Console Entry Points;
- 65 Operator-Pythondateien;
- 27 lineare Migrationen;
- Head `20260819_0027`.

## Entry Points

Das Entry-Point-Gate installiert das private Wheel mit `--no-deps` in einen
privaten Targetpfad.

Es lädt alle 58 im Wheel registrierten Entry-Point-Objekte über
`importlib.metadata`.

Ein fehlender Import oder zusätzlicher beziehungsweise fehlender Entry Point
sperrt die Phase.

## Source Distribution

Das sdist-Gate liest das Archiv ohne Extraktion.

Es lehnt symbolische und harte Links ab und verlangt mindestens
`pyproject.toml` sowie den `liquent_platform`-Quellbaum.

Dateizahl und Digest werden aus dem tatsächlichen Archiv ermittelt.

## Finaler Diff

Die vorletzte Phase führt erneut `git diff --check` aus und setzt erst nach
erfolgreichem Prozess den internen Diffnachweis.

Da jede Phase zusätzlich den sauberen Gitstatus prüft, dürfen private
Artefakte den Sourcebaum nicht verändern.

## Operationsbundle

Das abschließende Bundlegate erzeugt die bestehende `verification.json`
ausschließlich aus den zuvor gespeicherten Test-, Werkzeug-, Wheel-,
Migrations-, PostgreSQL-Versions- und Diffakten.

Danach ruft es den synchronisierten Builder und Verifier aus LQ-413 auf.

Ohne gespeicherten finalen Diffnachweis und gemessene PostgreSQL-Version wird
das Bundle vor Erzeugung abgelehnt.

Nur ein integritätsgeprüftes und weiterhin nicht promotables Bundle erhält das
letzte Phasenreceipt.

## Sicherheitsgrenzen

Es existiert kein Adapter für Publication, Promotion oder Deployment.

Der Runner erhält keine Providercredentials, Signaturauthority oder
Deploymentfreigabe.

Prozessausgaben werden nur gehasht oder auf eng begrenzte Summaries geparst und
nicht in die kontrollierten Receipts kopiert.

## Lokaler Status

Die echte Adapterkette wird in diesem Slice nicht ausgeführt.

Der aktuelle uncommitted Baum und die in LQ-414 belegte ungeeignete Laufzeit
werden bereits vom Runtime- beziehungsweise Sourcegate fail-closed abgelehnt.

Statische und synthetische Tests sind kein Packagingnachweis.

## Nichtziele

LQ-416 ergänzt keinen Console Entry Point, kein CI-Wiring und keine
Produktfunktion.

Es installiert keine Dependency, startet kein PostgreSQL und publiziert,
signiert, promotet oder deployed nichts.

Es erstellt keinen Branch und staged, committed oder pusht nichts.

## Nächster Slice

LQ-417 sollte die Adapter mit dem LQ-415-Runner in einer expliziten lokalen
Composition verbinden und eine detailfreie manuelle Kommandooberfläche
definieren.

Diese Oberfläche darf weder Dependencies installieren noch externe Aktionen
autorisieren und muss vor Ausführung weiterhin alle Runtime- und Sourcegates
durchlaufen.
