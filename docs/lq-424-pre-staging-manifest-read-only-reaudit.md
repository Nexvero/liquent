# LQ-424 — Pre-Staging Manifest Read-Only Reaudit

## Zweck

LQ-424 reauditiert das dateigenaue LQ-423-Manifest gegen Gitstatus,
Dateisystem, Reviewabdeckung und bekannte Secret-Pattern-Ausnahmen.

Der Audit härtet den Generator gegen Zwischenverzeichnis-Symlinks und
Quellzustandsdrift während der Berechnung.

## Zwischenverzeichnisbefund

LQ-423 lehnte eine symbolische Zieldatei ab.

Ein regulärer Dateiname unter einem symbolischen Zwischenverzeichnis konnte
jedoch außerhalb der Sourcewurzel aufgelöst werden.

Beispielsweise durfte `docs/file.md` nicht akzeptiert werden, wenn `docs`
selbst ein Symlink war.

## Gehärtete Pfadauflösung

LQ-424 prüft jede Pfadkomponente zwischen Sourcewurzel und Datei mit `lstat`.

Jede Zwischenkomponente muss ein echtes Verzeichnis und darf kein Symlink
sein.

Die finale Datei wird mit `O_NOFOLLOW` geöffnet, sofern das Betriebssystem
diese Grenze bereitstellt.

Nach dem Öffnen wird der Dateityp mit `fstat` erneut als regulär bestätigt.

Die Bytes werden aus demselben geöffneten Descriptor gelesen, aus dem Modus
und Größe stammen.

## Zustandsdriftbefund

Ein einzelner Gitstatus vor dem Hashen konnte Änderungen während eines langen
Manifestlaufs nicht erkennen.

Dadurch konnten HEAD, Branch, Status oder Datei-Bytes aus unterschiedlichen
Zeitpunkten in einer Aussage landen.

## Doppelte Snapshotmessung

Der Generator misst nun zweimal:

1. vollständigen HEAD-SHA, Branch und Null-delimited Dateistatus;
2. alle geordneten Dateieinträge mit Modus, Größe und SHA-256;
3. denselben Git-Snapshot erneut;
4. dieselben Dateieinträge erneut.

Nur byte- und strukturidentische Ergebnisse werden ausgegeben.

Commit-, Branch-, Status-, Modus-, Größen- oder Inhaltsdrift lehnt den Lauf
detailfrei ab.

Die doppelte Messung ist kein Betriebssystem-Dateisystemsnapshot, schließt
aber stabile und zwischen den Durchläufen sichtbare Drift fail-closed.

## Reviewabdeckung

Der reale Manifestlauf verlangt für jede Datei mindestens eine bekannte
Reviewsektion.

Alle Zuordnungen müssen Teil der sieben kanonischen Sektionen sein.

Der Gesamtbestand deckt alle sieben Sektionen ab.

Nicht eindeutig klassifizierbare gemeinsame Dateien bleiben allen Sektionen
zugeordnet und können nicht still aus einem Review verschwinden.

## Secret-Pattern-Ausnahmen

Der read-only Scan des realen Manifestumfangs findet für den privaten
Schlüssel-Header weiterhin exakt:

- `tests/test_lq304_research_worker_staging_evidence.py`;
- `tests/test_operational_release_bundle.py`.

Beide Treffer sind erwartete Negativtests für fail-closed Scanner.

LQ-424 findet keinen dritten Treffer im manifestierten Scope.

Diese eng begrenzte Prüfung ersetzt weiterhin keinen vollständigen dedizierten
Secret-Scanner vor Staging.

## Determinismus

Die zweite Messung verändert das Manifestformat nicht.

Bei stabilem Zustand bleiben Sortierung, JSON-Kanonisierung und Digest
deterministisch.

Es wird weiterhin kein Zeitstempel, Host, Benutzer oder absoluter Pfad
aufgenommen.

## Nichtautorisierung

Der Reaudit verändert keine der vier Grenzen:

- Staging bleibt nicht autorisiert;
- Commit bleibt nicht autorisiert;
- Publication bleibt nicht autorisiert;
- Deployment bleibt nicht autorisiert.

Das Manifest ist Reviewevidenz, keine Mutationserlaubnis.

## Tests

Die LQ-424-Tests belegen:

- Ablehnung von Gitstatusdrift;
- Ablehnung von Commitdrift;
- Ablehnung von Datei-Byte-Drift;
- vollständige reale Reviewabdeckung;
- exakt zwei bekannte Negativtest-Fixtures;
- additive Roadmapverlinkung.

Der ergänzte LQ-423-Test belegt außerdem die Ablehnung eines symbolischen
Zwischenverzeichnisses.

## Lokale Ausführungsgrenze

Der reale Manifestlauf liest den kumulierten Arbeitsbaum zweimal.

Er staged, sperrt, verschiebt oder schreibt keine Source-Datei.

Er erzeugt kein persistentes Manifestartefakt.

Die ungeeignete Buildlaufzeit aus LQ-414 bleibt davon unberührt.

## Nichtziele

LQ-424 implementiert keinen Dateisystem-Snapshotdienst und keine persistente
Manifestregistry.

Der Slice installiert keine Dependency, erzeugt keinen Branch und ändert
weder Gitindex noch Historie.

Er baut, signiert, promotet, publiziert oder deployed nichts.

## Entscheidung

Der read-only Pre-Staging-Manifestpfad ist gegen die im Reaudit gefundenen
Pfad- und Driftgrenzen gehärtet.

Ein persistentes Handoffartefakt ist weiterhin nicht autorisiert.

## Nächster Slice

LQ-425 sollte einen privaten, owner-kontrollierten Manifest-Handoffvertrag
definieren, ohne bereits eine Datei zu schreiben.

Er muss Zielbesitz, Modus, atomare Erzeugung, Retention und Nichtwiederverwendung
festlegen und darf weder Staging noch Commit autorisieren.
