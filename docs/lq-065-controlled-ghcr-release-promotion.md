# LQ-065 — Controlled GHCR Release and Promotion Contract

## Status

- Separater, ausschließlich manuell startbarer GHCR-Release-Workflow definiert.
- Nur vollständige Commit-SHAs mit erfolgreichem `main`-Push-Quality-Lauf sind
  zulässige Releasekandidaten.
- Container-Smoke, SBOM-Prüfung und High/Critical-Scan laufen erneut unmittelbar
  vor der Registry-Anmeldung.
- Veröffentlichung verwendet einen versions- und commitqualifizierten Tag;
  Digest bleibt die kanonische Deploymentidentität.
- Der publizierte Digest wird attestiert und in einem Release-Evidenzmanifest
  mit Commit und SBOM-Digest verbunden.
- Kein VPS-Deployment und keine automatische Production-Promotion enthalten.

## 1. Freigabekette

```text
manual workflow dispatch (revision + version + PUBLISH)
                         ↓
 successful completed quality.yml push run on main
                         ↓
 candidate must be an ancestor of origin/main
                         ↓
 rebuild → hardened smoke → SBOM verify → High/Critical scan
                         ↓ all green
 GHCR login → push version-SHA tag → capture registry digest
                         ↓
 registry provenance attestation + release evidence manifest
```

Der Workflow verwendet das GitHub Environment `registry-release`. Die
Environment-Erstellung allein erzwingt noch keine Freigabe: Required Reviewers
und Schutzregeln müssen einmalig in den Repositoryeinstellungen aktiviert und
danach nachgewiesen werden.

## 2. Identitäten und Unveränderlichkeit

- Eingabe `revision`: exakt 40 kleingeschriebene Hexzeichen,
- Eingabe `version`: strikt `X.Y.Z`,
- Bestätigung: exakt `PUBLISH`,
- Workflow-Ref: ausschließlich `refs/heads/main`,
- Registry: `ghcr.io/nexvero/liquent`,
- Tag: `<version>-<full-commit-sha>`,
- Deploymentreferenz: ausschließlich
  `ghcr.io/nexvero/liquent@sha256:<64 hex>`.

Der Tag ist auffindbare Metadatenidentität, nicht Vertrauensanker. Compose darf
nur den nach dem Push ermittelten Registry-Digest erhalten. Ein separates
bewegliches `latest`-Tag wird nicht erzeugt.

## 3. Berechtigungsgrenze

Nur der Releasejob erhält `packages: write`, `id-token: write` und
`attestations: write`; global bleibt `contents: read`. Das eingebaute
`GITHUB_TOKEN` wird erst nach erfolgreichem Rebuild, Smoke-Test, SBOM-Check und
Vulnerability-Gate bei GHCR angemeldet. Externe Registry-Secrets sind nicht
erforderlich.

Der Workflow besitzt keine SSH-Schlüssel, VPS-Adresse, Deploymentumgebung oder
Möglichkeit, Compose neu zu starten. Registry Release und Server Promotion sind
zwei getrennte Kontrollpunkte.

## 4. Release-Evidenz

`release-manifest.json` bindet:

- Releaseversion,
- vollständigen Git-Commit,
- Image-Repository,
- Registry-Digest,
- SHA-256 der SPDX-SBOM.

SBOM, Grype-Ergebnis und Manifest werden 30 Tage als Workflow-Artefakt
aufbewahrt. Zusätzlich wird die Provenance direkt für den publizierten
Image-Digest erzeugt und an GHCR übertragen.

## 5. Noch offene externe Gates

- `registry-release` mit Required Reviewers konfigurieren,
- Packagesichtbarkeit und Zugriffsrechte für `Nexvero/liquent` festlegen,
- ersten kontrollierten Release-Workflow ausführen,
- Registry-Digest, SBOM, Scan und Attestation unabhängig verifizieren,
- optional GHCR-Regeln gegen Tagüberschreibung prüfen,
- separaten LQ-066-Staging-Promotionprozess entwickeln,
- erst danach den digestgepinnten Compose-Wert auf dem VPS ändern.

## 6. Definition of Done

- kein ungetesteter oder nicht auf `main` befindlicher Commit kann releast werden,
- Registry-Authentifizierung erfolgt erst nach sämtlichen Sicherheitsgates,
- kein bewegliches Tag dient als Deploymentreferenz,
- der publizierte Digest besitzt Provenance und nachvollziehbare Evidenz,
- Releaseworkflow enthält keine Server- oder Deploymentberechtigung,
- lokale Vertrags- und Regressionstests sind grün,
- nächster Schritt ist LQ-066: kontrollierte Staging-Promotion und Rollback.
