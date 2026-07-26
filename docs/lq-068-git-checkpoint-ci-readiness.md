# LQ-068 — Git Checkpoint and First CI Readiness

## Status

- Gesamter Plattform-Checkpoint LQ-053 bis LQ-067 lokal auditiert.
- Vollständige Testsuite, Dependency-Check, Bash-/Python-Syntax und
  Whitespace-Prüfung sind grün.
- Branch basiert exakt auf `origin/main`; alle Plattformänderungen sind noch
  uncommitted und damit vollständig lokal reversibel.
- Secretmuster-, Symlink-, Großdatei- und sensitive-Dateinamen-Prüfung ergab
  keine unerwarteten Artefakte.
- Dokumentierte Test-, Branch- und Working-Tree-Angaben wurden konsolidiert.
- Noch kein Commit, Push, GitHub-Workflow oder externer Schreibvorgang erfolgt.

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

## 3. Nach Commit, vor Push

1. Commit-Inhalt per `git show --stat --oneline HEAD` prüfen.
2. Vollständige Testsuite aus dem committed Zustand erneut ausführen.
3. Sicherstellen, dass `git status --short` leer ist.
4. Erst dann mit expliziter Freigabe den Branch zu GitHub pushen.

## 4. Erster GitHub-Lauf

Nach dem Push müssen `test`, `wheel`, `container` und Supply-Chain-Gates
beobachtet werden. Der lokale Rechner besitzt keine Docker-Runtime; Container,
SBOM und Vulnerability-Scan gelten daher erst nach einem erfolgreichen
GitHub-Lauf als praktisch bestätigt. Ein Fehlschlag führt zu einem neuen
Korrekturcommit, niemals zu einer Umgehung des Gates.

Release, GHCR-Push, DNS, TLS und VPS-Staging bleiben auch nach erfolgreicher CI
separate manuell freizugebende Schritte.

## 5. Definition of Done

- lokaler Checkpoint ist konsistent, secretfrei und vollständig getestet,
- Commitumfang und Nachricht sind vorab dokumentiert,
- kein Commit oder Push erfolgt ohne ausdrückliche Freigabe,
- erster Remote-Schritt ist Branch-Push plus Beobachtung der Quality-Pipeline,
- nächster Schritt nach Freigabe: Commit erstellen, erneut prüfen und pushen.
