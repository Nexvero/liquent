# LQ-069 — Release Environment Governance

## Status

- GitHub Environment `registry-release` im Repository `Nexvero/liquent` angelegt.
- Deploymentzugriff explizit auf den Branch `main` begrenzt.
- Das Environment enthält keine Secrets und keine Konfigurationsvariablen.
- Der Releaseworkflow referenziert ausschließlich dieses Environment.
- Kein GHCR-Release, Registry-Login, Image-Push oder VPS-Deployment ausgeführt.

## 1. Governance-Grenze

```text
geschützter main-Commit
        ↓
manueller workflow_dispatch mit revision + version + PUBLISH
        ↓
registry-release (Branchregel: main)
        ↓
erneuter Build / Smoke / SBOM / Vulnerability-Gate
        ↓
erst danach GHCR-Authentifizierung und digestgebundener Push
```

Das Environment ist eine zusätzliche GitHub-seitige Grenze und ersetzt weder
die Workflowvalidierung noch die Branch-Ruleset-Prüfungen. Die Branchregel wird
als explizites Muster `main` geführt. Die GitHub-Option „Protected branches
only“ wurde bewusst nicht verwendet, weil GitHub das Repository-Ruleset in der
Environment-Ansicht nicht als klassische Branch-Protection-Regel erkannte und
dadurch fälschlich alle Branches zugelassen hätte.

## 2. Reviewer-Entscheidung

Required Reviewers sind derzeit nicht aktiviert. Aktuell existiert kein
unabhängiger zweiter Maintainer; eine Fremdfreigabe würde den Releasepfad daher
dauerhaft blockieren oder nur eine Scheintrennung erzeugen. Sobald ein zweiter
verantwortlicher Maintainer vorhanden ist, wird diese Entscheidung erneut
geprüft und als eigener Governance-PR dokumentiert.

Der Release bleibt dennoch mehrstufig geschützt durch:

- ausschließlich manuellen Workflowstart,
- exakten vollständigen Commit-SHA auf `main`,
- semantische Version `X.Y.Z`,
- Bestätigungstext `PUBLISH`,
- erneute technische Gates vor dem Registry-Login,
- digestgebundene Evidenz und Attestation.

## 3. Verifizierter externer Zustand

| Einstellung | Verifizierter Wert |
|---|---|
| Environment | `registry-release` |
| Deployment policy | Selected branches and tags |
| Branch pattern | `main` |
| Angewandte Branches | 1 |
| Environment secrets | 0 |
| Environment variables | 0 |
| Required reviewers | deaktiviert (Solo-Maintainer-Grenze) |

## 4. Offene Gates

- erster GHCR-Release benötigt weiterhin ausdrückliche Freigabe,
- Packagesichtbarkeit und Repositoryzugriff nach dem ersten Push prüfen,
- publizierten Digest, SBOM, Scan und Attestation unabhängig verifizieren,
- Required Reviewer ergänzen, sobald eine zweite verantwortliche Person besteht,
- erst nach separat freigegebenem Release eine Staging-Promotion erwägen.

## 5. Definition of Done

- Release-Environment existiert und ist ausschließlich an `main` gebunden,
- keine Secrets oder VPS-Berechtigungen wurden ergänzt,
- Workflow- und Environmentname sind vertraglich durch Tests gekoppelt,
- Solo-Maintainer-Grenze und Reviewer-Nachrüstpunkt sind dokumentiert,
- kein Release oder Deployment wurde ausgelöst.
