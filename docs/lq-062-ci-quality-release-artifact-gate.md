# LQ-062 — CI Quality and Release Artifact Gate

## Status

- GitHub-Actions-Qualitätsworkflow für Pull Requests und `main` angelegt.
- Vollständige Testsuite und Bash-Syntax laufen vor jedem Artefaktbuild.
- Python-/Build-Abhängigkeiten sind für CI exakt versioniert.
- Verifiziertes Wheel wird mit Commitbezug und kurzer Retention hochgeladen.
- Workflow besitzt ausschließlich lesenden Repositoryzugriff und keine Secrets.
- Noch kein Containerimage gebaut, veröffentlicht oder deployed.

## 1. Vertrauenskette

```text
reviewed commit
   ↓ read-only checkout
locked Python 3.12 environment
   ↓
dependency check + Bash syntax + complete pytest suite + whitespace gate
   ↓ success only
wheel build with fixed SOURCE_DATE_EPOCH
   ↓
contents / entry points / migrations / forbidden-path check
   ↓
short-lived GitHub workflow artifact named by commit SHA
```

Der Workflow deployt nicht. Er besitzt kein Package-, Container-, Environment-
oder Production-Schreibrecht. Production-Promotion bleibt ein separater,
manuell freigegebener Prozess.

## 2. Supply-Chain-Regeln

- Externe GitHub Actions sind auf vollständige 40-stellige Commit-SHAs gepinnt.
- Python wird explizit als 3.12 gewählt, nicht aus dem Runner geerbt.
- `requirements/ci.lock` begrenzt alle CI-/Buildversionen exakt.
- Der Wheel-Build verwendet die installierte, gelockte Buildumgebung statt einer
  unkontrolliert neu aufgelösten Isolation Environment.
- Dependabot öffnet getrennte, überprüfbare Python- und Actions-Updates.
- Ein Dependency-Update benötigt aktualisierten Lock, vollständige Tests,
  Artefaktprüfung und Review.

Die aktuelle Lockdatei fixiert Versionen, aber noch keine Download-Hashes. Vor
einer externen Release-Signierung wird ein hash-gesperrter Lock-/SBOM-Prozess
ergänzt. Das Wheel selbst erhält bereits einen ausgegebenen SHA-256.

## 3. Artefaktprüfung

`tools/verify_release_wheel.py` verweigert das Artefakt, wenn:

- Control-Plane-, Migration- oder Health-Entrypoint fehlt,
- Alembic-Umgebung oder Baseline nicht paketiert ist,
- `.env`, Schlüssel, lokale Markt-/Reportdaten oder Secretpfade enthalten sind,
- keine eindeutige Entrypoint-Metadatei existiert.

Der Check gibt Dateiname und SHA-256 aus. Das hochgeladene Workflow-Artefakt
wird 14 Tage aufbewahrt und ist kein Production-Release.

## 4. Noch offene Gates

- Workflow erstmals auf GitHub ausführen und Branch Protection auf den
  erforderlichen `test`- und `wheel`-Checks konfigurieren,
- Dependency Review beziehungsweise Vulnerability Scan ergänzen,
- SBOM und Provenance/Attestation erzeugen,
- Application- und Backup-OCI-Images reproduzierbar bauen und scannen,
- GHCR-Push und manuelle Production-Environment-Freigabe separat umsetzen.

Diese externen Repositoryeinstellungen werden nicht durch das Einchecken einer
Workflowdatei als aktiv behauptet.

## 5. Definition of Done dieser Phase

- CI ist minimal berechtigt, zeitlich begrenzt und concurrency-geschützt.
- Tests müssen vor dem Build erfolgreich sein.
- Build verwendet den eingecheckten Versionsstand.
- Wheel-Inhalt wird fail-closed geprüft.
- Keine Deployment-Credentials oder automatische Promotion existieren.
- Lokaler Referenzbuild und vollständige Testsuite sind erfolgreich.
- Nächster Schritt ist LQ-063: OCI-Image- und Container-Smoke-Gate.
