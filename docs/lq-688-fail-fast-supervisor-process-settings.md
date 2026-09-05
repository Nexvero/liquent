# LQ-688 — Fail-fast Supervisor Process Settings

## Umsetzung

`PlatformSettings` enthält die acht optionalen Werte des LQ-687-Vertrags.

Die bestehende Settingsvalidierung behandelt sie als atomare Gruppe und lehnt
unvollständige oder widersprüchliche Konfiguration vor jedem App-Aufbau ab.

## Modus

Nur der Literalwert `candidate` ist darstellbar.

Es gibt keinen Legacy-, Compatibility-, Auto- oder Fallbackmodus.

## Validierung

Die Validierung erzwingt:

- vollständige Gruppe oder vollständige Abwesenheit
- eine 1 bis 64 Zeichen lange kleingeschriebene Backend-ID aus Buchstaben,
  Ziffern und Bindestrichen
- konfigurierte gemeinsame Datenbankquelle
- absolute Nicht-Root-Pfade ohne Parent-Traversierung
- verschiedene Socket- und Controlpfade
- positive begrenzte numerische IDs
- gleiche Reader-/Wrapper-GID
- verschiedene Host-Owner-/Wrapper-UID

## Öffentliche Zusammenfassung

`manifest_handoff_supervisor_enabled` ist ausschließlich ein abgeleitetes
Boolean und keine caller-gelieferte Freigabe.

Die Zusammenfassung serialisiert nur `true` oder `false`.

## Deploymentbeispiel

Das Runtime-Environment-Beispiel dokumentiert alle Namen ausschließlich
auskommentiert.

Dadurch bleibt das reale Deployment bis zu den späteren Composition- und
Deploymentsträngen unverändert inaktiv.
