# LQ-421 — Local Release Preflight Final Drift Audit

## Zweck

LQ-421 auditiert den lokalen Preflightpfad aus LQ-414 bis LQ-420 abschließend
auf Code-, Test-, Vertrags-, Inventar- und Roadmapdrift.

Der Audit führt keinen echten Packaginglauf aus.

## Geprüfter Pfad

Der geschlossene lokale Pfad besteht aus:

- LQ-414 fail-closed Umgebungs-Preflight;
- LQ-415 atomarem Zehnphasen-Runner;
- LQ-416 selbst messenden Gateadaptern;
- LQ-417 expliziter lokaler Moduloberfläche;
- LQ-418 Evidenz- und Reihenfolgekorrektur;
- LQ-419 Prozess- und Retentiongrenzen;
- LQ-420 Signal- und Cleanuphärtung;
- diesem abschließenden Drift-Audit.

## Phaseninventar

Code und Adaptercomposition enthalten exakt:

1. `runtime`;
2. `source`;
3. `normal_tests`;
4. `postgres_tests`;
5. `distributions`;
6. `wheel`;
7. `entrypoints`;
8. `sdist`;
9. `final_diff`;
10. `bundle`.

Es existiert keine zusätzliche Publish-, Promote-, Deploy-, Skip- oder
Installationsphase.

## Atomare Signalrandlücke

Der LQ-420-Reaudit schützte das atomare `replace()` selbst vor einer
widersprüchlichen Signalablehnung.

LQ-421 findet ein noch kleineres Fenster unmittelbar nach erfolgreichem
`replace()` und vor Wiederherstellung der ursprünglichen Signalhandler.

Der bisherige `finally`-Block setzte den Signal-Latch in diesem Fenster bereits
zurück.

Ein SIGINT oder SIGTERM konnte dadurch Ablehnung auslösen, obwohl das
vollständige Ergebnisverzeichnis sichtbar war.

## Korrektur der Erfolgsgrenze

Der Commit-Boundary-Latch wird nun unmittelbar vor `replace()` gesetzt.

Bei einem technischen Replacefehler wird er zurückgesetzt und der Lauf
detailfrei abgelehnt.

Nach erfolgreichem Replace bleibt er gesetzt, bis der Kontext die vorherigen
Signalhandler wiederhergestellt hat.

Ein Signal in diesem Zeitraum wird konsumiert, weil der Lauf bereits atomar
und vollständig committed ist.

Damit gibt es nur zwei beobachtbare Zustände:

- vor Commit: Ablehnung, Cleanup, kein finales Ziel;
- ab Commit: vollständiger Erfolg, erhaltenes owner-kontrolliertes Ziel.

## Regressionsnachweis des Commitmoments

Der LQ-421-Test ersetzt den atomaren Verzeichniswechsel kontrolliert durch
eine Variante, die direkt nach erfolgreichem Betriebssystem-Replace SIGTERM an
den laufenden Prozess sendet.

Der Runner beendet den Lauf als Erfolg, die Evidenz ist vollständig und die
ursprünglichen Handler werden anschließend wiederhergestellt.

Ein sichtbares Erfolgsziel kann dadurch nicht mehr mit einer Fehlerantwort
kombiniert werden.

## Paket- und Migrationsinventar

Der statische Audit zählt weiterhin:

- 58 installierte Console Entry Points;
- 65 gepackte Operator-Pythondateien einschließlich `__init__.py`;
- 27 lineare Migrationen;
- erwarteten Head `20260819_0027` über die bestehenden Gates.

LQ-421 fügt keinen Entry Point, kein Operatormodul und keine Migration hinzu.

## Dokumentations- und Testtopologie

Für jeden Slice LQ-414 bis LQ-421 existieren:

- genau ein Slicevertrag unter `docs`;
- genau eine fokussierte Testdatei unter `tests`;
- ein additiver Roadmapeintrag in chronologischer Reihenfolge.

Historische Aussagen bleiben erhalten.

Der konsolidierte Roadmap-Kopf bleibt die aktuelle Bestandsaussage.

## Installations- und Wiringgrenze

`controlled-release-preflight` ist weiterhin nicht in `pyproject.toml`
registriert.

Die lokale Oberfläche ist nicht in Quality-CI oder Compose verdrahtet.

Erfolgsevidenz setzt weiterhin:

- `publishing_authorized=false`;
- `deployment_authorized=false`.

## Verifizierter synthetischer Stand

Vor LQ-421 bestanden 30 fokussierte Prüfungen der Kette LQ-415 bis LQ-420.

LQ-421 ergänzt fünf Drift- und Commit-Boundary-Prüfungen.

Diese 35 fokussierten Prüfungen sind synthetische und statische Nachweise.

Sie ersetzen weder die vollständige Pytest-Suite noch PostgreSQL-, Wheel-,
sdist- oder Bundle-Pflichtgates.

## Offener realer Status

Die in LQ-414 festgestellten Blocker bestehen fort:

- ungeeignete lokale Python- und Buildwerkzeugversionen;
- fehlender Pytest-Runner;
- fehlendes PostgreSQL-Test-DSN;
- detached und kumuliert uncommitted Sourcebaum.

Deshalb wurde kein echter Preflight als grün ausgegeben.

## Nichtziele

LQ-421 installiert keine Dependency und verändert weder Packaging noch CI.

Der Slice startet keinen Build, PostgreSQL-Server oder externen Provider.

Er signiert, promotet, publiziert oder deployed nichts.

Er erstellt keinen Branch und staged, committed oder pusht nichts.

## Entscheidung

Der lokale Preflightpfad ist auf Code-, Test-, Dokumentations-, Inventar- und
Roadmapebene geschlossen.

Weitere lokale Preflightfunktion ist vor einem realen grünen Lauf nicht
empfohlen.

Der nächste Schritt ist Integrationsvorbereitung, nicht ein weiterer
Funktionsslice.

## Nächster Slice

LQ-422 sollte den kumulierten Arbeitsbaum erneut inventarisieren und einen
konkreten sauberen Build- und Review-Handoff vorbereiten.

Ohne ausdrückliche Freigabe darf dieser Slice weiterhin keinen Branch, kein
Staging, keinen Commit, Push, Dependencydownload oder externen Lauf ausführen.
