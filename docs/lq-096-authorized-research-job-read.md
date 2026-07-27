# LQ-096 — Authorized Research Job Read

## Ergebnis

`get_authorized_research_job` bildet den ersten geschützten
Research-Leseanwendungsfall:

1. Job über seine `JobId` laden.
2. Die `workspace_id` ausschließlich aus dem gespeicherten Snapshot lesen.
3. Den bestehenden Guard mit `research:read` ausführen.
4. Nur bei Erfolg den Job zurückgeben.

Der Aufrufer übergibt keine Workspace-ID für die Ressource und kann deren
Zugehörigkeit daher nicht überschreiben.

## Fehlerverhalten

- Ein unbekannter Job bleibt ein unbekannter Job.
- Eine fehlende oder unzureichende Membership erzeugt weiterhin ausschließlich
  `permission_denied`.
- Der Membership-Lookup läuft nicht, wenn der Job nicht existiert.

## Bewusst nicht enthalten

- keine HTTP-Routenänderung oder Statusabbildung,
- keine Session- oder Principal-Ermittlung,
- keine konkrete Membership-Speicherung,
- noch keine Evidence- oder Start-Autorisierung,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-097 kann die bestehende Jobstatus-Route optional über diesen
Anwendungsfall führen, sobald Principal und Membership-Lookup ausdrücklich in
die App injiziert sind. Ohne diese Abhängigkeiten bleibt das aktuelle Local-/CI-
Verhalten unverändert und Shared Environments bleiben gesperrt.
