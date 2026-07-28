# LQ-113 — Session Lifecycle Ports

## Status

- Ein speicherneutraler `BrowserSessionLifecycle`-Port enthält ausschließlich
  Erzeugen, Rotieren und Widerrufen.
- Erzeugung und erfolgreiche Rotation liefern opake Session-ID, CSRF-Nachweis
  und Ablaufzeitpunkt als unveränderliches `IssuedBrowserSession`.
- Eine nicht mögliche Rotation liefert neutral keinen neuen Eintrag.
- Widerruf hat keinen Rückgabewert und verrät damit keinen Bestand.

## Fehlergrenze

Atomare Konflikte verwenden ausschließlich `session_lifecycle_conflict`. Der
Fehler akzeptiert keine IDs, Ursachen oder Speicherdetails. Session-ID und
CSRF-Nachweis erscheinen nicht in der Darstellung des Ausgabeobjekts.

## Bewusst nicht enthalten

- keine Lifecycle-Implementierung oder Schreiblogik,
- keine Zufalls-, Uhr- oder Lebensdauer-Policy,
- keine Datenbank, Locks oder Transaktionen,
- keine HTTP-, Cookie- oder Login-/Logout-Integration,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

## Nächster Schritt

LQ-114 kann die Erzeugung als isolierten Anwendungsfall über einen atomaren
Store-Port spezifizieren. Rotation und Widerruf bleiben separate Slices.
