# LQ-108 — Optional Session Cookie HTTP Boundary

## Status

- Die optionale HTTP-Sicherheitsgrenze liest eine opake Session-ID aus dem
  Cookie `liquent_session`.
- Der bestehende `BrowserSessionLookup` und Session-Guard lösen daraus den
  gebundenen Request-Kontext auf.
- Fehlende und unbekannte Sessions liefern identisch
  `401 authentication_required`.
- Status, Evidence und Research-Start verwenden denselben aufgelösten Kontext.

## Kompatibilitätsgrenze

Die Grenze ist nur aktiv, wenn Session- und Membership-Lookups gemeinsam
injiziert sind. Ohne diese Abhängigkeiten bleibt der explizite Local-/CI-Pfad
unverändert. Der POST-Pfad benötigt im Session-Modus weiterhin zusätzlich den
passenden `X-CSRF-Token`.

## Bewusst nicht enthalten

- keine Session-Erzeugung oder Cookie-Ausgabe,
- keine Festlegung von Ablaufzeit, Rotation oder Widerrufsablauf,
- kein konkreter Session- oder Membership-Speicher,
- keine Login-, Logout- oder Providerintegration,
- keine Freigabe von Preview oder Production,
- kein Release und kein Deployment.

