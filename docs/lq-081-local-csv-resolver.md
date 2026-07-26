# LQ-081 — Lokaler CSV-Resolver

## Status

- Genau eine lokale Kombination ist auflösbar: CSV-Datei unter einem
  konfigurierten Daten-Root, MidBreakout v0 und absolutes Risk-Sizing.
- Dataset-Pfad und SHA-256-Fingerprint werden vor dem Runner-Aufbau geprüft.
- Strategie-, Risiko- und Kostenparameter müssen exakt vollständig sein.
- Der vorhandene `HistoricalFileSource`, `MidBreakoutStrategy`, `RiskEngine`,
  `CostModel` und `BacktestRunner` werden direkt wiederverwendet.

## Sicherheitsgrenzen

- `dataset_ref` muss auf eine Datei innerhalb des konfigurierten Roots zeigen.
- Ein abweichender Fingerprint stoppt die Auflösung.
- Nur `mid-breakout-v0` und `sizing_mode=absolute` sind zugelassen.
- Unbekannte oder fehlende Parameterschlüssel scheitern fail-closed.
- Keine Netzwerk-, Broker-, Paper- oder Live-Ausführung wird aktiviert.

## Bewusst nicht gebaut

- kein Resolver-Register, Plugin-System oder dynamischer Import,
- keine Strategie v1, Optimierung oder Parameterauswahl,
- keine externe Datenquelle und kein Datei-Upload,
- kein HTTP-POST, keine Authentifizierung, Datenbank oder Queue,
- kein Release oder Deployment.

## Definition of Done

- eine lokale CSV kann reproduzierbar in den bestehenden Runner aufgelöst werden,
- Pfadflucht und Inhaltsabweichung werden abgelehnt,
- nur die explizit unterstützten vollständigen Parameter werden akzeptiert,
- Architektur- und vollständige Testsuite bleiben grün,
- nächster Schritt kann diesen Resolver optional in einen kleinen POST-Adapter injizieren.
