# LQ-086 — Access Domain Types

## Ergebnis

Die minimale Sprache für spätere Authentifizierungs- und
Autorisierungsschritte ist als kleine, stabile Domänengrenze vorhanden:

- `UserId` bezeichnet eine menschliche Identität.
- `MembershipStatus` unterscheidet ausschließlich `active` und `inactive`.
- `Permission` enthält ausschließlich `research:read` und `research:write`.

`WorkspaceId` bleibt der bereits vorhandene Typ aus der Research-Identität.
Damit entsteht kein zweites Workspace-Modell.

## Regeln

- Nur eine aktive Mitgliedschaft kann später Zugriff erlauben.
- Die Typen treffen selbst keine Autorisierungsentscheidung.
- Die in LQ-085 festgelegte Implikation von `research:write` zu
  `research:read` wird erst in einer expliziten Policy umgesetzt.
- Unbekannte Zustände und Rechte werden nicht dynamisch ergänzt.

## Bewusst nicht enthalten

- keine Session oder Session-Speicherung,
- keine Rollen, Teams oder Organisationshierarchie,
- keine Policy Engine oder HTTP-Middleware,
- kein Login, Provider, Token oder CSRF-Code,
- keine Datenbankmigration,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-087 kann eine kleine, reine Autorisierungsentscheidung für eine aktive
Workspace-Mitgliedschaft und die beiden Research-Rechte definieren. Transport,
Persistenz und Sessionprüfung bleiben davon getrennt.
