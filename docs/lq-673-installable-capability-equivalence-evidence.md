# LQ-673 — Installable Capability Equivalence Evidence

## Ergebnis

Ausführbare Evidenz belegt Installierbarkeit, Identität und unveränderte
Capabilitysemantik.

## Paketbeleg

Alle drei Modulpfade liegen unter `src/liquent_platform/capabilities` und damit
unter dem konfigurierten Paketroot.

Keines der Paketmodule importiert `tools`.

## Identitätsbeleg

Jeder `tools.*`-Kompatibilitätsimport ist mit dem entsprechenden
`liquent_platform.capabilities.*`-Modul per Objektidentität gleich.

Die Tooldateien enthalten keine Renderer-, Writer- oder Reconciliationlogik.

## Regressionsbeleg

Die ursprünglichen Tests für deterministischen Renderer, Reaudit, atomaren
Writer, Unknown-Grenze, read-only Reconciliation, Cleanup und persistente
Anwendungscomposition laufen gegen dieselben extrahierten Funktionen weiter.

Bestehende Patches auf `tools.private_manifest_handoff.render_manifest` treffen
weiterhin die tatsächliche Writerglobalvariable.

## Sicherheitsbeleg

Die Anwendung besitzt keine Productionabhängigkeit mehr auf einen
nicht ausgelieferten Repositorynamespace.

Es wurde kein subprocess- oder dynamischer Importfallback ergänzt.
