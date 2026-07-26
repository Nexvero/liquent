# LQ-070 — Release Readiness Evidence

## Status

- Read-only Release-Readiness-Nachweis implementiert.
- Kandidat, Version und erfolgreicher `main`-Push-Quality-Lauf werden geprüft.
- Der Nachweis erteilt ausdrücklich keine Veröffentlichungsfreigabe.
- Registry-Publikation und Deployment bleiben als nicht autorisiert und nicht
  ausgeführt markiert.
- Kein GHCR-Login, Image-Push oder VPS-Zugriff erfolgt durch diesen Schritt.

## 1. Zweck

Zwischen einem grünen `main`-Commit und einem tatsächlichen Registry-Release
liegt eine bewusste Freigabegrenze. LQ-070 macht den technischen Kandidaten
prüfbar, ohne den Bestätigungstext `PUBLISH` zu verwenden oder den manuellen
Releaseworkflow zu starten.

```text
vollständiger Commit-SHA + geplante Version + GitHub-Quality-Evidenz
                              ↓ read only
                Release-Readiness-Manifest
                              ↓
       publication.authorized=false / performed=false
       deployment.authorized=false  / performed=false
```

## 2. Vertrag

`tools/write_release_readiness.py` akzeptiert:

- einen vollständigen kleingeschriebenen Commit-SHA,
- eine strikt semantische Version `X.Y.Z`,
- die unveränderte GitHub-Antwort der Quality-Workflow-Läufe,
- einen lokalen Ausgabepfad.

Akzeptiert wird nur ein abgeschlossener erfolgreicher `push`-Lauf auf `main`
für exakt den Kandidaten-Commit und den Workflow
`.github/workflows/quality.yml`. Pull-Request-Läufe, Feature-Branches,
unvollständige und fehlgeschlagene Läufe werden abgewiesen.

## 3. Abgrenzung zur Veröffentlichung

Der Readiness-Nachweis enthält absichtlich kein positives
Autorisierungsmerkmal. Die Veröffentlichung erfordert weiterhin einen separat
gestarteten `.github/workflows/release.yml`-Lauf mit:

- vollständigem Commit-SHA,
- freigegebener Releaseversion,
- exakter Bestätigung `PUBLISH`,
- dem GitHub Environment `registry-release`,
- erneut erfolgreichen Build-, Smoke-, SBOM- und Vulnerability-Gates.

Der Readiness-Report ist deshalb ein Entscheidungsartefakt, kein Releasebeleg
und kein Ersatz für das spätere `release-manifest.json`.

## 4. Vorgeschlagener erster Kandidat

Nach einem erfolgreichen `main`-Quality-Lauf kann der aktuelle Commit als
technischer Kandidat für `0.1.0` geprüft werden. Die Versionswahl ist damit
nicht automatisch genehmigt. Ein konkreter Release darf erst nach separater
Freigabe gestartet werden.

## 5. Definition of Done

- Metadaten- und Quality-Prüfung sind wiederverwendbar getrennt,
- Readiness kann ohne `PUBLISH` und ohne schreibende GitHub-Berechtigung erzeugt
  werden,
- maschinenlesbare Evidenz markiert Veröffentlichung und Deployment negativ,
- ungültige oder nicht erfolgreiche Quality-Evidenz wird fail-closed abgewiesen,
- vollständige lokale Testsuite ist grün,
- kein Release, Registry-Push oder VPS-Deployment wurde ausgelöst.
