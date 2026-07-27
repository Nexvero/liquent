# LQ-105 — Optional Session-Bound CSRF HTTP Path

## Status

- Die optionale HTTP-Autorisierung akzeptiert den gebundenen
  `ResolvedBrowserSession`-Kontext statt eines losen Principals.
- Status und Evidence verwenden dessen verifizierten Principal.
- Der Research-POST-Pfad verlangt in diesem Modus einen passenden
  `X-CSRF-Token`-Header vor Autorisierung und Ausführung.
- Fehlende und falsche Nachweise liefern identisch
  `403 csrf_validation_failed` und erzeugen keinen Job.

## Kompatibilitätsgrenze

Ohne injizierten Session-Kontext bleibt der explizite Local-/CI-Pfad
unverändert. Session-Kontext und Membership-Lookup müssen weiterhin gemeinsam
konfiguriert sein. Das Environment-Gate aus LQ-084 bleibt geschlossen.

## Bewusst nicht enthalten

- keine Cookie- oder Session-ID-Auswertung,
- keine Session-Auflösung, Ablaufprüfung, Rotation oder Widerrufslogik,
- kein Session- oder Membership-Speicher,
- keine allgemeine Middleware,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

