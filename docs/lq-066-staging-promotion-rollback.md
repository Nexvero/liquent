# LQ-066 — Controlled Staging Promotion and Rollback

## Status

- Digestgebundener, operatorgesteuerter Staging-Promotionspfad implementiert.
- Preflight arbeitet ohne Mutation und bindet Image, Release-Manifest und
  frische Backup-Evidenz zusammen.
- Promotion verwendet einen exklusiven Host-Lock und ein persistentes
  Zustandsjournal je Lauf.
- PostgreSQL-Health, Migration-Gate, Control-Plane-Health und externe
  HTTPS-Liveness bilden die Freigabesequenz.
- Fehler stellen die vorherige Imagekonfiguration wieder her und versuchen
  einen Application-Rollback.
- Datenbankmigrationen werden niemals automatisch zurückgedreht.
- Kein Lauf wurde auf dem VPS oder gegen eine Staging-Domain ausgeführt.

## 1. Kontrollfluss

```text
release digest + release manifest + verified backup evidence
                           ↓ check only
 previous healthy digest + HTTPS URL + Compose contract
                           ↓ host lock / journal
 pull candidate → compose validate → postgres healthy
                           ↓
 one-shot migration gate → control plane replacement
                           ↓
 container healthy → external HTTPS liveness exact payload
             ┌─────────────┴─────────────┐
          success                     failure
       journal complete       restore previous config/image
```

## 2. Fail-closed-Grenzen

- akzeptiert ausschließlich `ghcr.io/nexvero/liquent@sha256:<64 hex>`,
- Release-Manifest muss exakt denselben Repositorynamen und Digest enthalten,
- Backup-Evidenz benötigt Snapshot-ID und UTC-Verifikationszeitpunkt,
- Konfiguration muss regulär, nicht verlinkt und Modus `0600` sein,
- Staging-Health-URL muss HTTPS verwenden und auf `/health/live` enden,
- ein bekannter vorheriger Digest ist Pflicht,
- parallele Promotionen werden über `flock` verhindert,
- ein ungültiger oder unbekannter Rollback-Lauf wird abgewiesen.

Der bewusste Zwang zu einem vorherigen gesunden Digest bedeutet, dass das
erstmalige Staging-Bootstrap nicht stillschweigend als normale Promotion
behandelt wird. Dafür ist ein eigener, explizit freizugebender Initiallauf nötig.

## 3. Migration und Rollback

Das Migration-Gate läuft vor der neuen Control Plane. Automatischer Rollback
betrifft ausschließlich das Application-Image. Migrationen werden nicht per
`alembic downgrade` zurückgedreht, da ein halb ausgeführter oder datenlöschender
Schema-Rollback riskanter wäre. Bis ein expand/contract-Migrationsprozess
implementiert ist, müssen alle Staging-Migrationen mit der vorherigen
Application-Version kompatibel bleiben.

## 4. Betriebsnachweis

Jeder Lauf speichert unter dem root-only State-Verzeichnis:

- vorherigen Digest,
- Kandidatendigest,
- unveränderte vorherige Imagekonfiguration,
- SHA-256 von Release-Manifest und Backup-Evidenz,
- Status `preparing`, `complete`, `failed` oder `rolled_back`.

Das Journal enthält keine Registry- oder Datenbankcredentials.

## 5. Noch offene externe Gates

- echte Staging-Domain und TLS-Routing konfigurieren,
- initialen gesunden Staging-Digest separat bootstrappen,
- root-owned Deploykonfiguration installieren,
- frischen Backup-/Restore-Nachweis erzeugen,
- ersten Preflight und anschließend eine beaufsichtigte Promotion ausführen,
- Fehlerfall und Application-Rollback kontrolliert testen,
- erst danach einen Production-Promotionvertrag erstellen.

## 6. Definition of Done

- Promotion ist digestgebunden, serialisiert und journaliert,
- keine Migration läuft ohne geprüfte Backup-Evidenz,
- interner und externer Health-Nachweis sind verpflichtend,
- Fehlerpfad besitzt einen vorher bekannten Application-Digest,
- Datenbankrollback wird nicht gefährlich automatisiert,
- vollständige lokale Vertrags- und Regressionstests sind grün,
- nächster Schritt ist LQ-067: Initial-Staging-Bootstrap und Edge-Routing-Plan.
