# LQ-095 — Research Workspace Binding

## Ergebnis

Jeder neue `ExperimentSnapshot` trägt nun verpflichtend eine unveränderliche
`WorkspaceId`. Da jeder Research-Job genau einen Snapshot besitzt, ist damit
auch jeder Job serverseitig eindeutig einem Workspace zugeordnet.

Der lokale Startvertrag nimmt die Workspace-ID als Teil des vollständigen
Snapshots entgegen. Eine leere Workspace-ID wird wie jede andere fehlende
Pflichtreferenz abgewiesen.

## Sicherheitswirkung

Der Autorisierungs-Guard kann künftig gegen die Workspace-ID der gespeicherten
Ressource prüfen. Eine frei aus Request-Kontext übernommene Workspace-Zuordnung
reicht dafür nicht aus.

## Bewusst nicht enthalten

- noch keine Guard-Anbindung an eine HTTP-Route,
- keine Session- oder Principal-Ermittlung,
- keine Membership-Speicherung,
- keine Änderung der öffentlichen Jobantwort,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-096 kann den autorisierten Research-Leseanwendungsfall gegen die
`workspace_id` des geladenen Jobs prüfen. Die HTTP- und Session-Abbildung bleibt
ein separater nachfolgender Slice.
