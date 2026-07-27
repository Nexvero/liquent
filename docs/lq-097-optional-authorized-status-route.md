# LQ-097 — Optional Authorized Status Route

## Ergebnis

Die bestehende Jobstatus-Route verwendet den autorisierten Leseanwendungsfall
aus LQ-096, wenn zwei Abhängigkeiten gemeinsam in die App injiziert werden:

- ein bereits verifizierter `SessionPrincipal`,
- ein `WorkspaceMembershipLookup`.

Fehlt eine der beiden Abhängigkeiten, scheitert die App-Erzeugung. Sind beide
nicht gesetzt, bleibt das bisherige ausdrücklich lokale/CI-Verhalten erhalten.

## Neutrale Ressourcensichtbarkeit

Ein unbekannter Job und ein für den Principal nicht sichtbarer Job liefern an
dieser Ressourcenroute dieselbe Antwort: `404 research_job_not_found`. Dadurch
wird die Existenz fremder Job-IDs nicht bestätigt.

## Bewusst nicht enthalten

- keine Erzeugung oder Prüfung des Principals,
- keine konkrete Membership-Speicherung,
- noch keine Evidence- oder Start-Routenautorisierung,
- keine Cookies, CSRF-Prüfung oder Providerintegration,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-098 kann denselben gespeicherten Workspace-Bezug für den Evidence-Lesepfad
wiederverwenden. Eine echte Sessionauflösung bleibt Voraussetzung für eine
spätere Freigabe von Shared Environments.
