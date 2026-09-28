# LQ-412 — Consolidated Roadmap Status and Gate Consistency

## Zweck

LQ-412 konsolidiert den Kopf der technischen Status- und Roadmapdatei mit dem
belegten kumulierten Endstand.

Der Slice ergänzt einen statischen Nachweis gegen erneute Status-, Inventar-,
Migrations- und Releasegrenzendrift.

Er verändert keine Produktlogik und führt keine Releaseaktion aus.

## Verifizierte Ausgangslage

Der Arbeitsbaum steht detached auf Commit `83699b1`.

Der letzte vollständige normale Testlauf aus LQ-410 bestand mit:

- 3945 bestandenen Tests;
- 99 Skips;
- 615 bestehenden Warnungen.

Diese Zahlen beschreiben den normalen lokalen Lauf.

Sie behaupten keinen aktuellen Lauf gegen ein reales PostgreSQL-Testsystem.

## PostgreSQL-Nachweis

Der letzte ausdrücklich belegte vollständige Pflicht-DSN-Lauf stammt aus
LQ-231 und umfasst 74 PostgreSQL-Integrationen.

Dieser historische Nachweis bleibt gültig für seinen damaligen Scope.

Er ist kein Ersatz für die erneute PostgreSQL-Pflichtsuite gegen den
kumulierten Endstand vor Release.

Fehlt das freigegebene Test-DSN, lautet der Status nicht bestanden, sondern
nicht erneut ausgeführt.

## Aktuelles Paketinventar

Die aktuelle Paketkonfiguration registriert 58 Console Entry Points.

Unter `src/liquent_platform/operators` liegen 64 gepackte Pythonmodule ohne
das Paketmodul `__init__.py`.

Nicht jedes Operatormodul hat einen eigenen Console Entry Point.

Interne Composition-, Configuration-, Loop-, Probe- und Process-Adapter sind
ebenfalls gepackte Operatormodule.

Die Persistenzhistorie enthält 27 lineare Migrationen.

Der eindeutige erwartete Head lautet `20260819_0027`.

## Korrektur der bisherigen Modulaussage

LQ-406 bis LQ-411 nannten 62 Operatormodule.

Die direkte Dateiinventur ergibt 64.

Die Differenz entsteht nicht durch zwei zusätzliche Console Commands, sondern
durch interne Module ohne eigene Scriptregistrierung.

LQ-412 korrigiert nur den konsolidierten Roadmap-Kopf und seinen eigenen
Statusblock.

Historische additive Sliceeinträge bleiben unverändert und damit als
zeitgebundene Aussagen nachvollziehbar.

## Erkannte Bundle-Drift

`tools/operational_release_bundle.py` erzwingt noch:

- 34 Console Entry Points;
- 38 Operatormodule;
- 27 Migrationen.

Die Migrationsgrenze ist aktuell.

Die Entry-Point- und Operatorgrenzen sind gegenüber dem Paketbestand veraltet.

Damit darf der finale Packaging- und Bundle-Preflight noch nicht als bestanden
ausgegeben werden.

LQ-412 ändert den Bundle-Prüfer bewusst nicht.

Die Synchronisierung gehört in einen separaten, reviewbaren Implementierungsslice.

## Statischer Konsistenznachweis

`tests/test_lq412_roadmap_status_gate_consistency.py` liest den Bestand direkt
aus den Repositorydateien.

Der Test weist nach:

- der konsolidierte Kopf nennt den normalen Teststand vollständig;
- der PostgreSQL-Nachweis bleibt davon getrennt;
- die Roadmap nennt 58 Entry Points und 64 Operatormodule;
- diese Zahlen stimmen mit `pyproject.toml` und dem Operatorverzeichnis überein;
- es existieren 27 Migrationen;
- der erwartete Migrationshead bleibt `20260819_0027`;
- der Kopf behauptet weder Staging noch Deployment;
- die Bundle-Drift ist im LQ-412-Vertrag sichtbar.

Der Test führt keine Anwendung, Migration oder externe Verbindung aus.

Er ist rein statisch und deterministisch.

## Aussagegrenzen

Der konsolidierte Kopf unterscheidet vier Ebenen:

1. normaler lokaler Teststand;
2. historischer und noch zu wiederholender PostgreSQL-Pflichtstand;
3. statisch gezähltes Paket- und Migrationsinventar;
4. externe Staging-, Deployment- und Providerfreigabe.

Keine Ebene impliziert automatisch die nächste.

Insbesondere bedeuten grüne normale Tests nicht, dass PostgreSQL, Packaging,
Bundle, Staging oder Deployment freigegeben sind.

Lokale Volume-Finalisierung bedeutet weiterhin keine vollständige
Datenentsorgung außerhalb ihres exakt belegten Scopes.

## Pflichtgates vor Staging

Vor Staging bleiben erforderlich:

1. vollständige normale Suite;
2. vollständige PostgreSQL-Pflichtsuite mit freigegebenem Test-DSN;
3. Upgrade einer leeren PostgreSQL-Datenbank bis Head;
4. synchronisierter Bundle-Prüfer;
5. Entry-Point-Import- und Paketmetadatenprüfung;
6. Wheel- und Source-Distribution-Build;
7. Prüfung aller erforderlichen Runbooks und Betriebsartefakte;
8. Konfliktmarker- und Secretscan;
9. `git diff --check`;
10. erneute Dateiinventur.

Nicht ausgeführte Gates bleiben offen.

## Nichtziele

LQ-412:

- ändert keine Anwendung oder Domainlogik;
- ändert keine Ports, Modelle oder Signaturen;
- ergänzt keine Migration und keinen Entry Point;
- ändert kein Bundle- oder Releasewerkzeug;
- erzeugt kein Releaseartefakt;
- startet kein PostgreSQL, Staging oder Deployment;
- erstellt keinen Branch und staged, committed oder pusht nichts.

## Entscheidung

Der Roadmap-Kopf ist mit dem belegten Stand konsolidiert.

Der statische Test verhindert stille Rückkehr zu den alten Kopfzahlen.

Der Gesamtbestand ist dennoch nicht packaging- oder releasebereit, solange die
erkannte Bundle-Drift und die noch offenen Pflichtgates bestehen.

## Nächster Slice

LQ-413 sollte den Bundle-Prüfer auf das aktuelle Inventar synchronisieren und
prüfen, ob alle seit LQ-235 hinzugekommenen zwingenden Betriebsartefakte im
Bundle enthalten sind.

Dieser Folgeslice darf keine Produktfunktion, Migration, externe Ausführung,
Branch-, Commit-, Push- oder Deploymentaktion enthalten.
