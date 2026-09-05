# LQ-417 — Explicit Local Controlled Release Preflight Command

## Zweck

LQ-417 verbindet den atomaren LQ-415-Runner mit den selbst messenden
LQ-416-Adaptern in einer ausdrücklich aufzurufenden lokalen
Kommandooberfläche.

Die Oberfläche installiert nichts, autorisiert keine externe Aktion und ist
weder als Console Entry Point noch in CI oder Runtime verdrahtet.

## Aufruf

Der lokale Aufruf lautet:

```text
python -m tools.run_controlled_release_preflight \
  --source-root REPOSITORY \
  --output-directory NEW_PRIVATE_DIRECTORY
```

Das Zielverzeichnis muss neu sein.

Ein vorhandenes oder symbolisches Ziel wird vom Runner abgelehnt.

## Eingaben

Die Kommandooberfläche akzeptiert exakt:

- `--source-root`;
- `--output-directory`.

Sie akzeptiert keine freien Befehle, Pythonpfade, Erfolgsbooleschen, Skipflags,
Dependencyinstallationen, DSN-Werte oder Releaseauthorities.

Das PostgreSQL-Test-DSN wird ausschließlich von LQ-416 aus der bestehenden
Prozessumgebung gelesen und niemals als CLI-Argument gerendert.

## Composition

`compose_local_preflight` erzeugt einen `LocalGateContext` und bindet exakt die
zehn LQ-416-Gates an `ControlledReleasePreflight`.

Die Composition führt beim Aufbau kein Gate aus.

Erst `run_local_preflight` startet die feste Sequenz.

Es gibt keinen alternativen Produktionsfallback und keine Teilcomposition.

## Erfolgsantwort

Nur nach atomar veröffentlichter LQ-415-Evidenz gibt das Kommando JSON aus:

```json
{"deployment_authorized": false, "evidence": "controlled-preflight.json", "outcome": "passed", "publishing_authorized": false}
```

Die Ausgabe enthält keinen absoluten Pfad, Commit, Test-DSN, Werkzeugpfad oder
internen Phaseninhalt.

Auch Erfolg autorisiert weder Publication noch Deployment.

## Ablehnungsantwort

Jede vom Runner vereinheitlichte Ablehnung ergibt Exitcode 2 und exakt:

```json
{"error": "controlled_release_preflight_rejected"}
```

Interne Exceptions, Prozessausgaben, Pfade, DSN-Inhalte und Gatebezeichnungen
werden nicht nach außen kopiert.

Argparse-Fehler für fehlende oder unbekannte Optionen bleiben normale lokale
Aufruffehler vor der Composition.

## Nicht installierte Oberfläche

LQ-417 ergänzt bewusst keinen Eintrag unter `[project.scripts]`.

Dadurch bleibt die Zahl installierter Produkt- und Operationsbefehle bei 58.

Das Kommando ist nur aus einem explizit vorhandenen Repositorycheckout als
Pythonmodul aufrufbar.

## Keine automatische Aktivierung

Die neue Moduloberfläche erscheint nicht in:

- `.github/workflows/quality.yml`;
- `operations/compose/compose.yaml`;
- HTTP-App oder Application-Wiring;
- Release-, Publication- oder Deploymentworkflows.

Ein lokaler Aufruf bleibt eine bewusste separate Operatorhandlung.

## Laufzeitgrenzen

Die Oberfläche umgeht kein LQ-416-Gate.

Insbesondere bleiben verbindlich:

- Python 3.12 und gelockte Werkzeuge;
- sauberer Gitbaum am exakten Commit;
- vollständige normale Suite;
- erzwungene PostgreSQL-Integrationen mit vorhandenem DSN;
- Wheel-, sdist-, Entry-Point- und Bundleprüfungen;
- finaler Quellbaum- und Diffnachweis.

Der aktuelle kumulierte Worktree wird daher detailfrei abgelehnt.

## Tests

Die LQ-417-Tests belegen:

- exakte Composition aller zehn Phasen ohne Ausführung beim Aufbau;
- begrenzte Erfolgsantwort ohne Pfadleck;
- konstante Ablehnung ohne internes Detail;
- fehlende freie Befehls-, Dependency-, DSN-, Skip- und Authorityoptionen;
- fehlende Installation und automatische Verdrahtung.

Synthetischer CLI-Erfolg ersetzt keinen echten Packaginglauf.

## Nichtziele

LQ-417 führt den echten Build in der aktuellen Umgebung nicht aus.

Der Slice installiert keine Dependency, startet kein PostgreSQL, baut kein
Releaseartefakt und signiert, promotet, publiziert oder deployed nichts.

Er ändert keine Produktlogik, Migration, Packagingkonfiguration oder CI.

Er erstellt keinen Branch und staged, committed oder pusht nichts.

## Nächster Slice

LQ-418 sollte die gesamte LQ-415-bis-LQ-417-Kette statisch und synthetisch
reauditieren, insbesondere die Evidenzübersetzung des Bundlegates und die
Reihenfolge zwischen Bundle- und finalem Diffnachweis.

Dabei darf kein echter Build oder externer Releaseclaim simuliert werden.
