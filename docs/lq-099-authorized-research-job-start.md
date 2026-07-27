# LQ-099 — Authorized Research Job Start

## Ergebnis

`authorize_resolve_and_start_research_job` schützt den bestehenden
Research-Startpfad als separater Anwendungsfall:

1. `research:write` für die im Snapshot gespeicherte `workspace_id` verlangen.
2. Erst nach erfolgreicher Autorisierung den bestehenden Resolver aufrufen.
3. Danach unverändert den vorhandenen registrierten Startpfad verwenden.

## Fail-closed-Verhalten

Fehlende Rechte oder eine reine `research:read`-Membership erzeugen den
neutralen Fehler `permission_denied`. In diesem Fall wird weder aufgelöst noch
registriert oder ausgeführt.

## Bewusst nicht enthalten

- noch keine POST-Routenverdrahtung,
- keine Principal- oder Sessionprüfung,
- keine konkrete Membership-Speicherung,
- keine CSRF-Prüfung oder Providerintegration,
- keine Freischaltung von Preview oder Produktion,
- kein Release oder Deployment.

## Nächster Schritt

LQ-100 kann die vorhandene POST-Route bei vollständiger Injection über diesen
autorisierten Startpfad führen. Ohne diese Abhängigkeiten bleibt der lokale/CI-
Entwicklungsweg unverändert.
