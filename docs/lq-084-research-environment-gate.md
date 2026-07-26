# LQ-084 — Research-Environment-Gate

## Status

- Der lokale Research-Start ist ausschließlich in `local` und `ci` zulässig.
- `preview` und `production` lehnen einen konfigurierten Research-Data-Root
  bereits bei der Settings-Validierung ab.
- Das Gate bleibt bestehen, bis eine separate Authentifizierungs- und
  Mandantengrenze spezifiziert und umgesetzt ist.

## Begründung

Der aktuelle POST-Pfad führt ausschließlich Backtests auf lokalen, allowlisteten
CSV-Dateien aus. Trotzdem ist er eine mutierende Produktfunktion. Eine Bindung
an eine öffentlich erreichbare Preview- oder Produktionsinstanz wäre ohne
Identitätsprüfung und Berechtigungsmodell nicht verantwortbar.

Deshalb gilt fail-closed:

| Umgebung | Research-Data-Root |
|---|---|
| `local` | erlaubt |
| `ci` | erlaubt |
| `preview` | abgelehnt |
| `production` | abgelehnt |

## Bewusst nicht gebaut

- keine provisorischen API-Keys oder Shared Secrets,
- keine Benutzer-, Session-, Rollen- oder Mandantenmodelle,
- kein Reverse-Proxy-Workaround als vermeintliche Authentifizierung,
- kein Preview-/Produktions-Opt-out-Schalter,
- kein Release, VPS-Zugriff oder Deployment.

## Definition of Done

- unsichere Shared Environments scheitern vor dem Prozessstart,
- lokale Entwicklung und kontrollierte CI bleiben möglich,
- kein Konfigurationsschalter kann das Gate umgehen,
- vollständige Testsuite bleibt grün,
- Authentifizierung wird später als eigener Produktslice entworfen.
