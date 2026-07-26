# LQ-088 — Workspace Membership

## Ergebnis

`WorkspaceMembership` bildet den kleinsten unveränderlichen Zusammenhang
zwischen einer menschlichen Identität und einem Workspace ab. Das Objekt bindet:

- `UserId`,
- den bereits vorhandenen `WorkspaceId`,
- `MembershipStatus`,
- eine unveränderliche Menge der vorhandenen Research-Rechte.

Es enthält keine Logik und keine abgeleiteten Rollen. Die reine Entscheidung aus
LQ-087 bleibt der einzige Ort für die Auswertung der Rechte.

## Invarianten

- Eine Mitgliedschaft gehört genau zu einem User und einem Workspace.
- Status und Rechte sind Teil desselben unveränderlichen Snapshots.
- Es existieren weiterhin nur die zwei Rechte aus LQ-086.
- Änderungen werden später als neuer Zustand modelliert, nicht als Mutation des
  bestehenden Objekts.

## Bewusst nicht enthalten

- keine Membership-ID, Zeitstempel oder Einladung,
- kein Repository und keine Datenbankmigration,
- keine Organisationen, Teams oder Rollen,
- keine Session-, HTTP- oder Middleware-Integration,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-089 kann einen schmalen Port zur Ermittlung einer Mitgliedschaft anhand von
`UserId` und `WorkspaceId` definieren. Eine konkrete Speicherung oder ein
Authentifizierungsprovider bleibt außerhalb dieses Slices.
