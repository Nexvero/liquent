# LQ-423 — Deterministic File-Level Pre-Staging Manifest

## Zweck

LQ-423 implementiert ein deterministisches, dateigenaues und read-only
Pre-Staging-Manifest für den kumulierten Review-Scope.

Der Generator staged, committed, pusht oder verändert keine Datei.

## Aufruf

Der explizite lokale Aufruf lautet:

```text
python -m tools.pre_staging_manifest --source-root REPOSITORY
```

Das kanonische JSON wird ausschließlich auf Standardausgabe geschrieben.

Der Generator nimmt keinen Ausgabepfad entgegen und erzeugt selbst keine
Manifestdatei.

## Git-Quelle

Die Dateiliste stammt aus genau:

```text
git status --porcelain=v1 -z --untracked-files=all
```

Das Nullformat verhindert Mehrdeutigkeit durch Leerzeichen oder Zeilenumbrüche
in Dateinamen.

Der Generator liest zusätzlich den vollständigen HEAD-SHA und den aktuellen
Branchnamen.

Detached HEAD wird als `branch=null` dargestellt.

## Zugelassene Statuswerte

Zugelassen sind ausschließlich:

- ungestagte veränderte getrackte Dateien;
- ungetrackte Dateien.

Staged, gelöschte, umbenannte, kopierte, konfliktbehaftete oder unbekannte
Statuswerte werden detailfrei abgelehnt.

Damit kann das Manifest nicht versehentlich einen bereits mutierten Index oder
eine unvollständige Dateientfernung als Pre-Staging-Scope bestätigen.

## Erlaubter Scope

Dateien dürfen nur liegen unter:

- `docs/`;
- `operations/`;
- `src/`;
- `tests/`;
- `tools/`;
- oder exakt `pyproject.toml` sein.

Absolute Pfade, `..`, nicht kanonische Pfade und alle anderen Top-Level-Ziele
werden abgelehnt.

## Dateigrenze

Jeder Eintrag muss beim Manifestlauf eine reguläre Datei sein.

Symlinks, Verzeichnisse, Sockets, Devices und fehlende Dateien werden
abgelehnt.

Der Generator folgt keinem symbolischen Dateiziel.

## Dateieintrag

Jede Datei erhält exakt:

- relativen POSIX-Pfad;
- Status `modified` oder `untracked`;
- Bytegröße;
- vierstelligen POSIX-Modus;
- SHA-256 der tatsächlichen Bytes;
- eine oder mehrere Reviewsektionen.

Ein absoluter Sourcepfad erscheint nicht im Manifest.

## Reviewsektionen

Die sieben Sektionen entsprechen LQ-422:

1. `identity_authority`;
2. `release_control_plane`;
3. `research_jobs_worker`;
4. `staging_recovery`;
5. `runtime_cleanup_lineage`;
6. `volume_disposition_deletion`;
7. `integration_preflight`.

LQ-Dokumente und LQ-Tests werden primär über ihre Slicenummer zugeordnet.

Eindeutige Modul- und Betriebsnamen werden über begrenzte Pfadregeln
zugeordnet.

Gemeinsame oder nicht eindeutig ableitbare Dateien erhalten alle sieben
Reviewsektionen und können dadurch nicht aus einem Review herausfallen.

Die Zuordnung ist Reviewrouting, keine Ownership- oder Commitauthority.

## Determinismus

Das Manifest enthält keinen Zeitstempel, Hostnamen, Benutzernamen, absoluten
Pfad oder zufällige ID.

Dateien werden lexikografisch nach relativem Pfad sortiert.

JSON-Schlüssel sind sortiert, kompakt serialisiert und mit genau einem Newline
abgeschlossen.

Gleicher Commit, Status und gleiche Datei-Bytes erzeugen dieselben
Manifestbytes.

## Gesamtaussage

Das Manifest enthält:

- `schema_version=1`;
- `base_commit`;
- Branch oder `null`;
- exakte Dateizahl;
- die geordnete Dateiliste;
- die sieben Reviewsektionen;
- vier explizite Nichtautorisierungen.

Folgende Felder sind immer `false`:

- `staging_authorized`;
- `commit_authorized`;
- `publishing_authorized`;
- `deployment_authorized`.

## Fehlerausgang

Jede technische, Status-, Pfad- oder Dateiablehnung ergibt Exitcode 2 und:

```json
{"error": "pre_staging_manifest_rejected"}
```

Interne Pfade und Fehlerdetails werden nicht ausgegeben.

Argparse-Aufruffehler bleiben vor dieser Grenze normale lokale Nutzungsfehler.

## Retention und Nichtwiederverwendung

Der Generator speichert kein Manifest.

Wenn ein Operator die Standardausgabe später bewusst in eine private Datei
umleitet, gehören Retention, Modus, Name und Nichtwiederverwendung zu einem
separaten kontrollierten Handoff.

LQ-423 autorisiert keine solche persistente Ablage.

## Tests

Die Tests belegen:

- deterministische Sortierung und Bytebindung;
- detached und benannten Branch;
- gemeinsame Reviewzuordnung;
- unveränderte Nichtautorisierung;
- Ablehnung von staged, deleted, renamed und scopefremd;
- Ablehnung von Symlink, Duplikat, fehlender Datei und nicht kanonischem Pfad;
- additive Roadmapverlinkung.

## Lokaler Snapshot

Vor LQ-423 umfasste der LQ-422-Endstand 665 tatsächliche uncommitted Dateien.

LQ-423 ergänzt Tool, Test und Vertrag; die Roadmap bleibt eine bereits
veränderte getrackte Datei.

Der Generator kann den neuen Gesamtstand read-only im Speicher erfassen, doch
LQ-423 committed kein konkretes Manifestartefakt.

## Nichtziele

LQ-423 fügt keinen Console Entry Point und kein CI- oder Compose-Wiring hinzu.

Der Slice installiert keine Dependency, baut kein Paket und startet keine
Datenbank oder externe Aktion.

Er staged, committed, pusht, signiert, promotet, publiziert oder deployed
nichts.

## Nächster Slice

LQ-424 sollte das generierte Manifest read-only gegen die tatsächliche
Dateiinventur, Reviewabdeckung und bekannte Secret-Pattern-Ausnahmen
reauditieren.

Auch dieser Audit darf ohne ausdrückliche Freigabe weder Index noch Git-Historie
oder externe Systeme verändern.
