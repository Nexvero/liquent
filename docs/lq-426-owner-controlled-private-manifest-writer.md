# LQ-426 — Owner-Controlled Private Manifest Writer

## Zweck

LQ-426 implementiert den expliziten lokalen Writer für den privaten
Pre-Staging-Manifest-Handoff aus LQ-425.

Der Writer erzeugt die Manifestbytes selbst über den gehärteten read-only
Generator und bindet sie atomar ohne Overwrite an ein owner-kontrolliertes
Ziel.

## Lokale Moduloberfläche

Der bewusste Aufruf lautet:

```text
python -m tools.private_manifest_handoff \
  --source-root REPOSITORY \
  --target-root PRIVATE_0700_DIRECTORY \
  --handoff-name NEW_NAME
```

Es wird kein Console Entry Point installiert und nichts automatisch in CI,
Compose oder Runtime verdrahtet.

## Zielvalidierung

Source- und Zielwurzel werden komponentenweise mit `lstat` geprüft.

Symlinks und nicht echte Verzeichnisse werden abgelehnt.

Beide Wurzeln müssen dem aktuellen Betriebssystemnutzer gehören.

Die Zielwurzel muss exakt Modus `0700` besitzen und außerhalb der Sourcewurzel
liegen.

## Name

Der Handoffname ist auf maximal 128 ASCII-Zeichen aus Buchstaben, Ziffern,
Punkt, Unterstrich und Bindestrich begrenzt.

Der Writer hängt fest `.json` an.

Pfadtrennzeichen, leere Namen und Traversal werden abgelehnt.

Ein existierender finaler Name endet neutral als `target_not_absent`, bevor
der Generator ausgeführt wird.

## Manifestquelle

`render_manifest(source)` erzeugt die Bytes direkt im selben Aufruf.

Ein vom Caller gelieferter JSON-Pfad, Digest, Filecount oder Allow-Wert wird
nicht akzeptiert.

Der Writer prüft erneut:

- kanonisches JSON;
- Schema 1;
- positive Dateizahl;
- alle vier Autorisierungsflags exakt `false`;
- Digest direkt aus den Bytes.

## Temporäre Datei

`mkstemp` erzeugt im Zielverzeichnis einen unvorhersagbaren neuen Namen.

Der Descriptor wird explizit auf `0600` gesetzt.

Alle Bytes werden in einer vollständigen Write-Schleife geschrieben und mit
`fsync` durable gemacht.

`fstat` und erneutes Lesen desselben Descriptors bestätigen Owner, Typ, Modus,
Größe und exakte Bytes.

## No-Overwrite-Bindung

Der Writer verwendet `os.link` statt ersetzendem Rename.

Der Hard-Link bindet denselben Inode atomar an den finalen Namen und schlägt
bei vorhandenem Ziel fehl, ohne dessen Inhalt zu lesen oder zu verändern.

Nach erfolgreichem Link wird das Zielverzeichnis synchronisiert.

Die finale Datei wird mit `O_NOFOLLOW` erneut vollständig verifiziert.

Erst danach wird der temporäre Name entfernt und das Verzeichnis erneut
synchronisiert.

## Erfolgsantwort

Erfolg liefert begrenztes JSON mit:

- `outcome=manifest_handed_off`;
- finalem Dateinamen ohne absoluten Pfad;
- Manifest-SHA-256;
- Dateizahl;
- `staging_authorized=false`;
- `commit_authorized=false`.

Der Zielpfad und temporäre Name werden nicht ausgegeben.

## Neutrale Ausgänge

Ein vorhandenes oder im Linkrennen entstandenes Ziel ergibt
`target_not_absent` und Exitcode 3.

Vom Generator explizit erkannte Drift zwischen seinen zwei Snapshots ergibt
`source_not_stable` und Exitcode 3.

Ein neutrales Ergebnis enthält weder Digest noch Dateizahl oder Pfad.

## Technische Unverfügbarkeit

Fehler vor möglicher finaler Bindung ergeben Exitcode 2 und:

```json
{"error": "manifest_handoff_unavailable"}
```

Eine temporäre Datei wird in diesem Fall best-effort entfernt.

## Unbekannter Ausgang

Jeder Fehler nach erfolgreichem Hard-Link ergibt Exitcode 4 und:

```json
{"error": "manifest_handoff_outcome_unknown"}
```

Finaler und gegebenenfalls temporärer Name bleiben für read-only
Reconciliation erhalten.

Der Writer versucht weder Retry noch Rebind oder Löschung.

## Tests

Die Tests belegen:

- private exakte Erfolgserzeugung;
- neutralen No-Overwrite-Ausgang vor Generatoraufruf;
- Ablehnung ungültiger Namen, Wurzeln und Modi;
- Cleanup bei Fehler vor Link;
- Unknown-Outcome und Erhalt beider Namen nach Link;
- fehlende Installation als Console Entry Point.

## Ausführungsgrenze

LQ-426 führt keinen Writer gegen den echten kumulierten Worktree aus.

Tests verwenden ausschließlich private temporäre Verzeichnisse und ein
synthetisches kanonisches Manifest.

Es wird kein dauerhaftes Manifestartefakt erzeugt.

## Nichtziele

LQ-426 implementiert keinen Reconciler, persistenten Attempt-Store oder
Retentiondeleter.

Der Slice staged, committed, pusht, baut, signiert, promotet, publiziert oder
deployed nichts.

## Nächster Slice

LQ-427 sollte den read-only Reconciler für erfolgreichen, abwesenden,
konfliktbehafteten und technisch unverfügbaren Manifest-Handoffzustand
definieren und implementieren.

Er darf keinen Dateinamen wiederverwenden und keine Datei verändern.
