# LQ-087 — Research Authorization Decision

## Ergebnis

Eine kleine, reine Domänenfunktion beantwortet genau eine Frage: Darf eine
Workspace-Mitgliedschaft die verlangte Research-Aktion ausführen?

Die Entscheidung verwendet ausschließlich:

- den bestehenden `MembershipStatus`,
- die vorhandenen `Permission`-Werte,
- das für die Aktion erforderliche Recht.

## Entscheidungsregeln

| Mitgliedschaft | vorhandenes Recht | verlangtes Recht | Ergebnis |
|---|---|---|---|
| inactive | beliebig | beliebig | verweigert |
| active | keines | beliebig | verweigert |
| active | research:read | research:read | erlaubt |
| active | research:read | research:write | verweigert |
| active | research:write | research:read | erlaubt |
| active | research:write | research:write | erlaubt |

Die Funktion ist fail-closed und verändert keinen Zustand.

## Bewusst nicht enthalten

- keine Ermittlung von User, Workspace oder Mitgliedschaft,
- keine Session-, Cookie- oder CSRF-Prüfung,
- keine HTTP-Fehlerabbildung oder Middleware,
- keine Datenbank, Rollenmatrix oder Policy Engine,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-088 kann die minimale, unveränderliche Workspace-Mitgliedschaft als Eingabe
für diese Entscheidung definieren. Session- und Transportintegration bleiben
separate spätere Slices.
