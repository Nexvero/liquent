# LQ-700 — Supervisor Control-plane Entrypoint Composition

## Umsetzung

`build_app` erkennt ausschließlich die vollständig validierte Supervisorgruppe.

Bei Aktivität erzeugt es eine Engine, typisiert die stabile Backend-ID,
komponiert den exklusiven Kandidatenprozess und bindet dessen Probe.

## Gemeinsame Engine

Processcomposition, Datenbankreadiness, persistente Browsergrenzen und optional
OIDC verwenden dieselbe Engineinstanz.

Es entsteht keine zweite automatische Appfactory-Engine.

## Explizite Engineownership

`create_app` akzeptiert `database_engine_owned=true` nur zusammen mit einer
expliziten Engine.

Damit kann der Entrypoint die gemeinsam erzeugte Engine an den bestehenden
Lifespan übertragen, ohne externe Engineaufrufe allgemein zu übernehmen.

## Geschlossener Pfad

Ohne Supervisorgruppe baut `build_app` weiterhin exakt den bisherigen
Control-Plane-Pfad.

Es gibt keinen Legacyfallback und keine automatische Backend-ID.

## Deploymentgrenze

Die Composition ist erreichbar, kann im aktuellen Compose aber keine
Hostfähigkeiten erhalten und meldet weiterhin not-ready.
