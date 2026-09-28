# LQ-418 — Controlled Release Preflight Chain Reaudit

## Zweck

LQ-418 reauditiert die vollständige lokale Kette aus Runner, Gateadaptern und
expliziter Kommandooberfläche.

Der Audit konzentriert sich auf die Übersetzung gemessener Fakten in
Bundle-Evidenz und die Reihenfolge von finalem Diff und Bundle.

## Befund zur bisherigen Reihenfolge

LQ-415 definierte ursprünglich `bundle` als Phase neun und `final_diff` als
Phase zehn.

Das LQ-416-Bundlegate schrieb dabei bereits `diff_check=passed` in
`verification.json`, obwohl der ausdrückliche `git diff --check` erst danach
ausgeführt wurde.

Der vor jeder Phase erneut geprüfte saubere Gitstatus begrenzte das Risiko,
ersetzte aber nicht den behaupteten konkreten Diffnachweis.

Die Evidenzreihenfolge war deshalb semantisch zu weit.

## Korrektur

Die verbindliche Reihenfolge endet nun mit:

9. `final_diff`;
10. `bundle`.

Das Final-Diff-Gate setzt seinen internen Nachweis erst nach erfolgreichem
`git diff --check`.

Das Bundlegate verlangt diesen gespeicherten Nachweis vor dem Schreiben von
`verification.json`.

Damit entsteht keine Bundle-Evidenz mehr vor dem behaupteten Diffcheck.

## PostgreSQL-Versionsbefund

Die erste LQ-416-Fassung setzte im Versionsfeld lediglich den Text
`verified by postgres integration gate`.

Das bestehende Bundleschema verlangt zwar nur einen nicht leeren String, doch
dieser Text war keine gemessene PostgreSQL-Version.

Nach erfolgreicher PostgreSQL-Suite liest das Gate nun über dieselbe
Umgebungs-DSN `SHOW server_version`.

Nur eine begrenzte numerische Versionsform wird akzeptiert und in den
Phasenfakten gespeichert.

Das Bundlegate übernimmt ausschließlich diese gemessene Version.

## Testevidenz

Das normale Testgate misst bestandene Tests und Warnungen aus dem tatsächlichen
Pytestprozess.

Das PostgreSQL-Gate misst seinen eigenen Passed-Wert und erzwingt weiterhin
`LIQUENT_REQUIRE_POSTGRES_TESTS=1`.

Fehlende oder nicht eindeutig parsebare Summaries werden nicht in grüne
Evidenz übersetzt.

## Wheel- und Migrationsevidenz

Wheel-Digest, Entry-Point-Anzahl, Operatordateien, Migrationsanzahl und Head
werden aus dem erzeugten Wheel gelesen.

Entry-Point-Erfolg entsteht erst nach privater Installation und Laden aller 58
Objekte.

Migration- und Importstatus in `verification.json` beruhen damit auf
vorangegangenen erfolgreichen Phasen.

## Secret-Scan-Grenze

Der Operationsbundle-Builder scannt den vollständigen Payload einschließlich
Wheel, Runbooks, Verträge, Beispiel und Evidence vor Archivveröffentlichung.

Ein Treffer verhindert Bundle und Receipt atomar.

Der `secret_scan=passed`-Status ist deshalb nur zusammen mit einem erfolgreich
gebauten und anschließend verifizierten Bundle sichtbar.

Er ist kein allgemeiner Secret-Scan jedes Repositorypfads außerhalb des
gebündelten Payloads.

## Terminales Bundlegate

Das Bundle ist nun die letzte Phase.

Es verlangt vor Ausführung:

- beide gespeicherten Testzählungen;
- gemessene PostgreSQL-Version;
- erzeugtes und geprüftes Wheel;
- privaten `SOURCE_DATE_EPOCH` aus Git;
- erfolgreichen finalen Diffnachweis;
- weiterhin sauberen Sourcebaum am gleichen Commit.

Danach erzeugt und verifiziert es das Operationsbundle.

Nur `integrity=verified` und `promotable=false` führen zum letzten Receipt.

## Atomare Gesamtaussage

Der LQ-415-Runner veröffentlicht `controlled-preflight.json` erst nach dem
terminalen Bundlereceipt.

Damit bindet die Gesamtevidenz alle vorgelagerten Messungen und den
verifizierten Bundle-Digest an denselben Commit.

Publication und Deployment bleiben in der Gesamtevidenz ausdrücklich nicht
autorisiert.

## Verbleibende Grenzen

Die Adapterkette besitzt weiterhin keinen installierten Entry Point und kein
automatisches CI-Wiring.

Der manuelle Modulaufruf erfordert eine geeignete, bereits vorbereitete
Laufzeit und einen sauberen Source-Commit.

Die aktuelle isolierte Umgebung erfüllt diese Voraussetzungen nicht.

LQ-418 ist daher kein echter Packaginglauf und erzeugt kein Releaseartefakt.

## Statischer Regressionsnachweis

`tests/test_lq418_release_preflight_chain_reaudit.py` sichert:

- finaler Diff vor terminalem Bundle;
- harte Bundlevoraussetzung des gemessenen Diffstatus;
- echte PostgreSQL-Versionsmessung statt Platzhaltertext;
- Builder vor Verifier im terminalen Gate;
- unveränderte Nichtpromotierbarkeit;
- begrenzte Roadmap- und Releaseaussagen.

## Nichtziele

LQ-418 installiert keine Dependency und startet keinen PostgreSQL-Server.

Es führt keinen echten Build, Bundlelauf, Signatur- oder Providerzugriff aus.

Es erteilt keine Publication-, Promotion- oder Deploymentfreigabe.

Es ändert keine Produktlogik, Migration, Entry Points oder externe
Runtimeverdrahtung.

Es erstellt keinen Branch und staged, committed oder pusht nichts.

## Nächster Slice

LQ-419 sollte die lokale Preflightkette gegen Abbruch, unbekannten
Prozessausgang und Artefaktretention härten.

Insbesondere sind Prozesszeitlimits, maximale Outputgrößen und die
Retentiongrenze fehlgeschlagener privater Buildartefakte separat festzulegen,
ohne externe Releaseaktionen zu öffnen.
