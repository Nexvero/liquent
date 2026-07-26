# LQ-067 — Initial Staging Bootstrap and Edge Routing

## Status

- Einmaliger, explizit bestätigter Initial-Staging-Bootstrap implementiert.
- Read-only Preflight bindet Release-Digest, Manifest, Backup-Evidenz, DNS-Ziel
  und TLS-Zertifikat zusammen.
- Zertifikatshostname und Übereinstimmung von Zertifikat und privatem Schlüssel
  werden vor jeder Mutation geprüft.
- Minimaler Nginx-Vertrag veröffentlicht ausschließlich `/health/live` über TLS.
- Erststart wird mit demselben Host-Lock und Journal wie spätere Promotionen
  serialisiert.
- Kein DNS-Eintrag, Zertifikat, Container oder VPS wurde tatsächlich verändert.

## 1. Systemgrenze

```text
public DNS: staging.liquent.ai
              ↓ 80/443 only
        existing Nginx edge
              ↓ liquent_public
 control-plane:8000 /health/live only
              ↓ liquent_application
          PostgreSQL internal
```

Der Edge bleibt der einzige Dienst mit veröffentlichten Hostports. Die Control
Plane besitzt weiterhin kein Port-Mapping. PostgreSQL, Migrationen, Readiness
und Prometheus-Metriken sind nicht öffentlich erreichbar.

## 2. TLS- und Routingvertrag

- HTTP wird mit Status 308 auf HTTPS umgeleitet,
- TLS 1.2 und TLS 1.3 sind zulässig,
- Zertifikat und Schlüssel werden ausschließlich vom Host read-only gemountet,
- HSTS beginnt für Staging bewusst mit 24 Stunden und ohne `includeSubDomains`,
- Security Header und ein Requestlimit von 1 MiB sind gesetzt,
- Proxy-Timeouts sind kurz und begrenzt,
- nur der exakte Pfad `/health/live` wird weitergereicht,
- alle übrigen HTTPS-Pfade antworten mit 404.

Die Plattform besitzt noch keine öffentliche Produkt-API oder UI. Das Routing
wird deshalb nicht vorsorglich geöffnet.

## 3. Initialisierungsgrenze

Anders als LQ-066 verlangt der Erststart keinen vorherigen Application-Digest.
Stattdessen benötigt er die wörtliche Bestätigung `INITIALIZE-STAGING` und eine
vollständige erfolgreiche Online-Vorprüfung. Bei Fehlern wird die Control Plane
gestoppt und die vorherige Edge-/Imagekonfiguration wiederhergestellt. Dieser
Pfad wird nach dem ersten gesunden Digest nicht erneut verwendet.

## 4. Noch offene externe Gates

- DNS-Eintrag für `staging.liquent.ai` anlegen und unabhängig verifizieren,
- TLS-Zertifikat sicher ausstellen und auf dem Host installieren,
- Edge-Container kontrolliert starten beziehungsweise aktualisieren,
- ersten GHCR-Release-Digest bereitstellen,
- Online-Preflight und beaufsichtigten Bootstrap durchführen,
- HTTPS-Verhalten von außerhalb des VPS prüfen,
- ersten gesunden Digest als Rollbackbasis dokumentieren.

## 5. Definition of Done

- Erststart ist von normalen Promotionen getrennt und explizit bestätigt,
- DNS, TLS, Release und Backup werden fail-closed geprüft,
- öffentliche Angriffsfläche ist auf einen Liveness-Pfad begrenzt,
- Fehlerpfad hinterlässt keinen unbeabsichtigt laufenden Control-Plane-Dienst,
- lokaler Offline-Preflight und vollständige Regression sind grün,
- nächster Schritt ist LQ-068: Git-Checkpoint und erster GitHub-CI-Lauf.
