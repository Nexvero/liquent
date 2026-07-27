# LQ-100 — Optional Authorized Research Start Route

## Status

- Die vorhandene Research-POST-Route verwendet bei vollständig injizierter
  Identität den bestehenden autorisierten Startpfad.
- `research:write` wird geprüft, bevor Resolver, Registrierung oder Ausführung
  erreicht werden.
- Der bestehende explizite Local-/CI-Pfad bleibt ohne Auth-Injection unverändert.

## Verhalten

- Erlaubte Starts liefern weiterhin `202` und das bestehende Job-Format.
- Fehlendes Schreibrecht liefert neutral `403 permission_denied`.
- Abgelehnte Starts erzeugen keinen Job und führen keine Research-Ausführung aus.
- Principal und Membership-Lookup bleiben eine gemeinsame Konfigurationseinheit.

## Bewusst nicht enthalten

- keine Session-Verifikation oder Session-Ablage,
- kein CSRF-Nachweis,
- kein persistenter Membership-Adapter,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

Das Environment-Gate aus LQ-084 bleibt geschlossen, bis Session, CSRF und
Membership-Auflösung Ende-zu-Ende nachgewiesen sind.

