# LQ-415 — Controlled Green Build Runner and Atomic Evidence

## Zweck

LQ-415 implementiert die fail-closed Koordinationsgrenze für einen lokalen
grünen Release-Preflight.

Der Runner entscheidet weder konkrete Buildbefehle noch Releasefreigaben.

Er stellt sicher, dass nur ein vollständiger, commitgebundener Lauf sichtbare
Erfolgsevidenz erzeugen kann.

## Feste Phasen

Der Runner akzeptiert exakt zehn Phasen in unveränderlicher Reihenfolge:

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

Eine fehlende oder zusätzliche Phase lehnt bereits die Composition ab.

Es gibt keinen Skip-, Warn-, Optional- oder caller-supplied Allow-Pfad.

## Vertrauensgrenze

Konkrete Phasenadapter werden später an der kontrollierten Composition
bereitgestellt.

Jeder Adapter darf nur unterhalb des privaten temporären Workspaces arbeiten
und muss ein kanonisches Receipt zurückgeben.

Der Runner akzeptiert keine boolesche Erfolgsaussage und keinen freien
Rollen- oder Statusstring.

## Phasenreceipt

Ein Receipt enthält exakt:

- `schema_version=1`;
- den erwarteten Phasennamen;
- `status=passed`;
- einen 40-stelligen kleingeschriebenen Commit-SHA;
- den SHA-256-Digest der phaseneigenen Fakten.

Das JSON muss kanonisch, ASCII-kodiert und newline-terminiert sein.

Fremde Felder, andere Phasen, nicht kanonische Bytes oder ungültige Digests
werden detailfrei abgelehnt.

## Commitbindung

Das erste gültige Receipt bindet den Source-Commit des gesamten Laufs.

Jedes spätere Receipt muss denselben Commit nennen.

Damit können Test-, Build-, Wheel- oder Bundlenachweise unterschiedlicher
Quellstände nicht zu einem grünen Gesamtergebnis kombiniert werden.

## Atomare Sichtbarkeit

Alle Phasen laufen in einem privaten Verzeichnis mit Modus `0700`.

Vor dem letzten erfolgreichen Receipt existiert kein finales
Ergebnisverzeichnis.

Nach zehn Erfolgen erzeugt der Runner `controlled-preflight.json` mit Modus
`0600` und verschiebt den gesamten Workspace atomar an das Ziel.

Ein vorhandenes Ziel wird niemals überschrieben.

## Fehlerverhalten

Bei Ablehnung, technischem Fehler, malformed Receipt oder Commitkonflikt:

- stoppt die Sequenz sofort;
- wird keine spätere Phase aufgerufen;
- wird der private Workspace entfernt;
- entsteht keine Erfolgsevidenz;
- bleibt ein vorhandenes fremdes Ziel unverändert;
- wird nur `controlled release preflight rejected` sichtbar.

Interne Fehlerdetails werden nicht in Evidenz oder Exceptiontext übernommen.

## Gesamtevidenz

Die finale Evidenz enthält:

- Schema und `outcome=passed`;
- den gemeinsamen Source-Commit;
- alle zehn Phasen in Reihenfolge;
- je Phase Digest des Receipts und Digest der Fakten;
- `publishing_authorized=false`;
- `deployment_authorized=false`.

Die Evidenz ist kein Signatur-, Promotion-, Publication- oder Deploymenttoken.

## Getrennte Bundle-Evidenz

`controlled-preflight.json` ist bewusst nicht die bestehende
`verification.json` des Operationsbundles.

Die spätere Adaptercomposition muss reale Testzahlen, Werkzeugversionen,
Wheel-Import-, Migrations-, Secret- und Diffchecks aus den gebundenen
Phasenfakten ableiten.

Sie darf keine Werte erfinden oder fehlende Fakten als bestanden übersetzen.

## Implementierungsumfang

LQ-415 ergänzt:

- `tools/controlled_release_preflight.py`;
- `tests/test_lq415_controlled_release_preflight.py`;
- diesen Vertrag und den additiven Roadmapeintrag.

Es wird kein Console Entry Point und kein automatisches CI-Wiring ergänzt.

## Verifikation

Die Tests decken ab:

- feste Phasenreihenfolge;
- atomare Erfolgsevidenz;
- Abbruch und vollständiges temporäres Cleanup;
- falsche Phase und divergierenden Commit;
- fehlende und zusätzliche Gates;
- nicht kanonische Receipts;
- Schutz vorhandener Zielverzeichnisse;
- unveränderte Nichtautorisierung externer Aktionen.

## Lokale Ausführungsgrenze

Der echte Build-Runner wird in LQ-415 nicht gegen die aktuelle Maschine
ausgeführt.

Die in LQ-414 belegten Blocker bestehen fort: Python 3.9.6, fehlende Build- und
Pytestmodule, veraltete Buildwerkzeuge, fehlendes PostgreSQL-Test-DSN und ein
uncommitted Quellbaum.

Eine synthetische Unit-Test-Gatecomposition ist kein Packagingnachweis.

## Nichtziele

LQ-415 installiert keine Dependency, startet kein PostgreSQL und baut kein
Wheel, keine Source Distribution und kein Bundle.

Der Slice verändert keine Produktlogik, Migration, Entry Points,
Packagingkonfiguration, CI-Definition oder Runtimecomposition.

Er erzeugt keinen Branch und staged, committed, pusht, signiert, promotet,
publiziert oder deployed nichts.

## Nächster Slice

LQ-416 sollte die kontrollierten lokalen Adapter für Runtime-, Source-, Test-,
Distribution-, Wheel-, Entry-Point-, sdist-, Bundle- und Diffphasen
implementieren.

Die Adapter müssen Fakten selbst aus dem Systemzustand ermitteln, dürfen keine
caller-supplied Erfolgsbooleschen akzeptieren und bleiben ohne automatische
CLI- oder CI-Aktivierung.
