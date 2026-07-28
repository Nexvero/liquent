# LQ-116 — Secure Session Material Generator

## Status

- Ein konkreter Standardgenerator erfüllt den vorhandenen Material-Port.
- Session-ID und CSRF-Nachweis entstehen durch zwei unabhängige Aufrufe einer
  kryptographisch geeigneten Betriebssystem-Zufallsquelle.
- Jeder Wert verwendet standardmäßig 32 Zufallsbytes beziehungsweise 256 Bit
  Entropie und wird URL-sicher kodiert.
- Schwächere oder ungültige Entropiekonfigurationen werden abgewiesen.

## Sicherheitsgrenze

Der Generator speichert und protokolliert keine erzeugten Werte. Eine höhere
Entropie kann explizit gewählt werden; das Minimum kann nicht unterschritten
werden.

## Bewusst nicht enthalten

- keine globale Konfiguration oder Dependency-Injection,
- keine Lebensdauer- oder Cookie-Policy,
- kein konkreter Session-Store oder Datenbankschema,
- keine Rotation, Widerrufs-, HTTP- oder Login-Integration,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-117 kann die Cookie-Ausgabe als eigenständige Transportentscheidung mit
Secure-, HttpOnly- und SameSite-Regeln festlegen. Production bleibt gesperrt.
