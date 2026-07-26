# LQ-063 — OCI Image and Container Smoke Gate

## Status

- Mehrstufiges Application-Image mit digest-gepinntem Python-Basisimage definiert.
- Runtime läuft als feste unprivilegierte Identität `10001:10001`.
- Image enthält einen Liveness-Healthcheck und nur das verifizierbare Wheel.
- CI prüft Image-Metadaten und startet einen gehärteten Smoke-Container.
- Kein Registry-Push, Deployment oder VPS-Zugriff eingerichtet.

## 1. Vertrauenskette

```text
reviewed source + exact CI constraints + commit timestamp
                    ↓
        wheel in isolated builder stage
                    ↓
 digest-pinned Python runtime + locked dependencies
                    ↓
 non-root / healthcheck / OCI revision verification
                    ↓
 read-only smoke container with all capabilities dropped
```

Das Basisimage ist sowohl auf Python `3.12.13` und Debian Bookworm als auch auf
den vollständigen Multi-Architecture-Digest festgelegt. Ein Basisimage-Update
ist damit eine sichtbare, reviewpflichtige Quellcodeänderung.

## 2. Laufzeitgrenzen

- feste numerische UID/GID statt Host-abhängiger Namensauflösung,
- keine Login-Shell und kein Home-Verzeichnis,
- `read_only`, `no-new-privileges` und `cap_drop: ALL` im Smoke-Test und Compose,
- nur `/tmp` als temporäres Dateisystem; persistente Artefakte bleiben ein
  explizites Compose-Volume,
- Healthcheck verwendet `/health/live`; Datenbankbereitschaft bleibt separat
  über `/health/ready` und das Migration-Gate abgesichert,
- keine Trading-, Broker- oder Exchange-Verbindung im Image aktiviert.

## 3. CI-Gate

Der Container-Job läuft erst nach Test- und Wheel-Gate. Er baut lokal auf dem
GitHub-Runner, prüft Benutzer, Healthcheck und Commit-Label und startet danach
den Container mit gehärteten Optionen. Das Image wird weder exportiert noch in
eine Registry übertragen. Der lokale Entwicklungsrechner besitzt derzeit keine
Docker-Laufzeit; deshalb ist der echte Build-/Smoke-Nachweis bis zum ersten
GitHub-Lauf offen und wird nicht als bestanden behauptet.

## 4. Offene Gates

- Workflow auf GitHub ausführen und Container-Check als Pflichtstatus setzen,
- Image-Inhalt und Betriebssystempakete scannen,
- SBOM sowie Provenance/Attestation erzeugen,
- GHCR-Publish mit minimalem `packages: write` in separatem Release-Workflow,
- Digest nach Freigabe in `operations/compose/images.env` übernehmen,
- Staging-Deployment und externen HTTPS-Readiness-Test durchführen.

## 5. Definition of Done

- Dockerfile nutzt keine veränderliche Basisreferenz.
- Build- und Runtime-Stufe sind getrennt.
- Runtime ist non-root, besitzt Healthcheck und enthält die Alembic-Migrationen.
- Smoke-Test läuft read-only und ohne Linux-Capabilities.
- CI besitzt weiterhin keine Registry- oder Deployment-Schreibrechte.
- Statische Vertragsprüfungen und die vollständige lokale Testsuite sind grün.
- Nächster Schritt ist LQ-064: SBOM-, Vulnerability- und Provenance-Gate.
