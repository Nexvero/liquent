# LQ-094 — Research Authorization Guard

## Ergebnis

`require_research_authorization` ist ein dünner Guard über der bestehenden
booleschen Entscheidung aus LQ-092:

- erlaubter Zugriff: Rückkehr ohne Ergebnis,
- verweigerter Zugriff: `ResearchAuthorizationDenied` aus LQ-093.

Der Guard dupliziert keine Membership- oder Permission-Regel. Er delegiert die
vollständige Entscheidung an `authorize_research`.

## Neutrale Ablehnung

Fehlende Membership, inaktiver Status, fehlendes Recht und inkonsistente
User-/Workspace-Zuordnung erzeugen denselben Fehler `permission_denied`. Der
Aufrufer erhält keinen internen Ablehnungsgrund.

## Bewusst nicht enthalten

- keine HTTP-Status- oder Response-Abbildung,
- keine Unterscheidung sichtbarer und fremder Ressourcen,
- kein Logging, Audit oder Telemetrie,
- keine Sessionprüfung, Cookies, CSRF oder Provider,
- keine konkrete Membership-Speicherung,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-095 kann den Guard zunächst an genau einen bestehenden Research-Lesepfad
binden. Der Startpfad und die Sessionprüfung bleiben bis zu ihren eigenen
Slices unverändert gesperrt.
