# LQ-098 — Optional Authorized Evidence Route

## Ergebnis

Status- und Evidence-Route laden einen sichtbaren Job nun über denselben kleinen
Helfer. Bei vollständig injiziertem Principal und Membership-Lookup delegiert
dieser Helfer an den autorisierten Leseanwendungsfall aus LQ-096.

Die Evidence wird erst nach erfolgreicher Job-Sichtbarkeitsprüfung gelesen.
Eine zweite Membership- oder Permission-Entscheidung wurde nicht eingeführt.

## Neutrale Ressourcensichtbarkeit

Unbekannte, fremde und mangels `research:read` nicht sichtbare Jobs liefern auf
der Evidence-Route ein identisches `404 research_job_not_found`. Erst für einen
sichtbaren, aber noch unfertigen Job bleibt `research_evidence_not_found`
erhalten.

## Bewusst nicht enthalten

- keine Start-Routenautorisierung,
- keine Principal- oder Sessionprüfung,
- keine konkrete Membership-Speicherung,
- keine Cookies, CSRF-Prüfung oder Providerintegration,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-099 kann die Research-Start-Autorisierung als separaten Anwendungsfall mit
`research:write` definieren. Die HTTP-POST-Route bleibt bis zu einem eigenen
Integrationsslice unverändert.
