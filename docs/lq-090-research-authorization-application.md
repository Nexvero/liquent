# LQ-090 — Research Authorization Application

## Ergebnis

`authorize_research` verbindet den Membership-Lookup aus LQ-089 mit der reinen
Research-Entscheidung aus LQ-087. Die Anwendungsfunktion benötigt:

- den Membership-Lookup-Port,
- `UserId` und `WorkspaceId`,
- das erforderliche Research-Recht.

Sie liefert ausschließlich `True` oder `False` und verändert keinen Zustand.

## Ablauf

1. Membership exakt für User und Workspace laden.
2. Fehlenden Treffer verweigern.
3. Einen inkonsistenten Treffer mit abweichendem User oder Workspace verweigern.
4. Status und Rechte durch die vorhandene reine Entscheidung auswerten.

Damit bleibt die Zuordnung der Ressource serverseitig prüfbar und die
Entscheidung fail-closed.

## Bewusst nicht enthalten

- keine Session- oder Identitätsermittlung,
- keine HTTP-Fehlerabbildung oder Middleware,
- keine konkrete Membership-Speicherung,
- keine Audit-Ereignisse oder Telemetrie,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-091 kann einen minimalen, unveränderlichen Session-Principal-Vertrag
definieren, der ausschließlich eine verifizierte `UserId` transportiert.
Cookie-, Provider-, Speicher- und HTTP-Details bleiben getrennte Slices.
