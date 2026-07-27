# LQ-093 — Neutral Authorization Error

## Ergebnis

`ResearchAuthorizationDenied` ist der minimale Anwendungsfehler für einen
verweigerten Research-Zugriff. Sein einziger öffentlicher Code lautet:

- `permission_denied`

Der Fehler akzeptiert keine Ursache, User-ID, Workspace-ID, Membership-Angabe
oder Ressourcendetails. Dadurch können interne Ablehnungsgründe nicht
versehentlich über die Fehlernachricht veröffentlicht werden.

## Regeln

- Alle fachlichen Permission-Ablehnungen teilen denselben neutralen Code.
- Der Fehler enthält keine Information darüber, ob eine Membership existiert.
- Interne Diagnose und Auditierung werden später separat behandelt.
- Die HTTP-Schicht entscheidet später ausdrücklich über 403 oder neutrales 404
  für nicht sichtbare Ressourcen.

## Bewusst nicht enthalten

- keine Änderung der booleschen Autorisierungsentscheidung,
- keine HTTP-Status- oder Response-Abbildung,
- kein Logging, Audit oder Telemetrie,
- keine Session-, Cookie-, CSRF- oder Provider-Implementierung,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-094 kann eine kleine Guard-Funktion ergänzen, die die bestehende boolesche
Entscheidung in Erfolg oder diesen neutralen Fehler übersetzt. HTTP und
Ressourcen-Sichtbarkeit bleiben weiterhin separate Slices.
