# LQ-089 — Workspace Membership Lookup Port

## Ergebnis

`WorkspaceMembershipLookup` trennt die spätere Autorisierungsanwendung von der
Herkunft einer Membership. Der Port besitzt genau eine Operation:

- Eingabe: `UserId` und `WorkspaceId`,
- Ausgabe: die zugehörige unveränderliche `WorkspaceMembership` oder `None`.

`None` bedeutet ausschließlich, dass für diese Kombination keine Membership
sichtbar ist. Der Port verrät keine weiteren Informationen und trifft selbst
keine Autorisierungsentscheidung.

## Regeln

- Beide Identitäten sind für jeden Lookup erforderlich.
- Es gibt keine Abfrage nur über User oder nur über Workspace.
- Ein fehlender Treffer bleibt neutral und fail-closed auswertbar.
- Die Schnittstelle enthält keine Speicher- oder Transportdetails.

## Bewusst nicht enthalten

- keine In-Memory- oder Datenbankimplementierung,
- keine Listen-, Such-, Einladungs- oder Mutationsoperation,
- kein Cache und kein generisches Repository,
- keine Session-, HTTP- oder Middleware-Integration,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-090 kann eine kleine Anwendungsfunktion ergänzen, die den Port aufruft und
die reine Entscheidung aus LQ-087 verwendet. HTTP-Fehlerabbildung,
Sessionprüfung und Speicherung bleiben getrennte spätere Slices.
