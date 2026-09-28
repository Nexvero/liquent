# LQ-674 — Installable Capability Extraction Completion Audit

## Ergebnis

LQ-671 bis LQ-674 beseitigen die ersten beiden LQ-668-Entrypointblocker.

Renderer, Writer und Reconciler sind jetzt Teil des installierbaren
`liquent_platform`-Pakets und besitzen weiterhin jeweils genau eine
Implementierung.

## Geschlossene Eigenschaften

- keine Algorithmuskopie zwischen `src` und `tools`
- keine Productionimports aus `tools`
- objektidentische Toolkompatibilitätsmodule
- unveränderte Writer-Atomizität und Unknown-Grenze
- unveränderte read-only Recoveryfähigkeit
- keine neue Authority oder Dateifähigkeit

## Unveränderte Readiness

Der Kandidat bleibt `production_ready=false`.

Es fehlen weiterhin der direkte atomare Child-Control-Artifact-Adapter und die
feste Writer-/Recovery-Processcomposition samt Commands.

## Unveränderte Grenzen

Keine Settings-, Appfactory-, Compose-, Engine-, Mount-, Schema-, SQL-, Port-,
Modell-, Signatur-, Migrations- oder Productionaktivierung wurde ergänzt.

## Verifikation

55 fokussierte Tests bestehen für ursprüngliche Capabilitysemantik,
Toolkompatibilität, Modulidentität, Paketgrenze und den LQ-429-Abschlussaudit.

Ein lokaler Wheel-Build ohne Netzwerkisolation enthält alle drei Module unter
`liquent_platform/capabilities`.

Der vollständige Lauf besteht mit 5311 Tests; 108 umgebungsabhängige Fälle
bleiben erwartungsgemäß übersprungen.

## Nächster Strang

Als Nächstes ist der direkte atomare Adapter für die bereits gemountete
`/run/liquent/control`-Directory zu implementieren und gegen die bestehende
Control-Artifact-Semantik zu belegen.
