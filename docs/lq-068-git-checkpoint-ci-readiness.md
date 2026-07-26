# LQ-068 — Git Checkpoint and First CI Readiness

## Status

- Gesamter Plattform-Checkpoint LQ-053 bis LQ-067 lokal auditiert.
- Vollständige Testsuite, Dependency-Check, Bash-/Python-Syntax und
  Whitespace-Prüfung sind grün.
- Branch basiert auf `origin/main`; der Plattformstand ist in einem Foundation-
  Commit plus eng begrenzten CI-/Security-Korrekturen versioniert.
- Secretmuster-, Symlink-, Großdatei- und sensitive-Dateinamen-Prüfung ergab
  keine unerwarteten Artefakte.
- Dokumentierte Test-, Branch- und Working-Tree-Angaben wurden konsolidiert.
- Branch und Pull Request `#1` sind auf GitHub veröffentlicht. Der reale
  Quality-Lauf mit Test, Wheel, Container-Smoke, SBOM und Vulnerability-Gate
  ist grün; Provenance bleibt bis zu einem `main`-Push erwartungsgemäß aus.

## 1. Empfohlener Checkpoint

Der aktuelle Stand bildet einen zusammenhängenden vertikalen Slice-0:

```text
architecture and quality contracts (LQ-053–055)
                    ↓
runtime / compose / persistence / operations (LQ-056–061)
                    ↓
CI / container / supply chain / release (LQ-062–065)
                    ↓
staging promotion / edge bootstrap (LQ-066–067)
```

Obwohl mehrere Themen enthalten sind, hängen die späteren Gates direkt von den
früheren Dateien ab. Für den ersten remote sichtbaren Plattformstand wird daher
ein einzelner, reviewbarer Foundation-Checkpoint empfohlen. Nach dessen Merge
sollen zukünftige LQ-Slices wieder klein und einzeln committed werden.

Empfohlene Commit-Nachricht:

```text
feat: establish Liquent platform slice-0 foundation
```

## 2. Commit-Ausschlüsse

- `.venv`, Build- und Testcaches,
- echte `.env`-Dateien, Schlüssel und Zertifikate,
- Markt-/Reportdaten,
- VPS-spezifische Runtimekonfiguration,
- Backupinhalte oder Restic-Credentials,
- generierte Wheels, Images, SBOMs und Scanresultate.

Die eingecheckten `*.example`-Dateien enthalten ausschließlich Platzhalter und
öffentliche Konfigurationsstruktur.

## 3. Durchgeführter Commit- und Push-Nachweis

1. Foundation-Commit erstellt und Inhalt geprüft.
2. Vollständige Testsuite aus dem committed Zustand erneut ausgeführt.
3. Leeren Working Tree bestätigt.
4. Branch gepusht und Pull Request `#1` eröffnet.
5. Reale CI-Fehler ohne Umgehung der Gates korrigiert und erneut geprüft.

## 4. Erster GitHub-Lauf

`test`, `wheel`, `container` und Supply-Chain-Gates wurden im Pull Request
beobachtet und sind erfolgreich. Der GitHub-Runner bestätigte Image-Build,
Image-Vertrag, gehärteten Smoke-Test, SPDX-SBOM sowie das reparierbare
High/Critical-Gate. Die vollständige lokale Suite umfasst nun `861` Tests.

Release, GHCR-Push, DNS, TLS und VPS-Staging bleiben auch nach erfolgreicher CI
separate manuell freizugebende Schritte.

## 5. Definition of Done

- Checkpoint ist konsistent, secretfrei, committed und vollständig getestet,
- Pull Request `#1` enthält einen grünen realen Quality-Lauf,
- Working Tree ist leer und Branch mit GitHub synchron,
- weder Merge noch Release, DNS/TLS-Änderung oder VPS-Deployment erfolgte,
- nächster externer Schritt bleibt die ausdrücklich freizugebende Merge-
  Entscheidung einschließlich Branch-Protection-Prüfung.
