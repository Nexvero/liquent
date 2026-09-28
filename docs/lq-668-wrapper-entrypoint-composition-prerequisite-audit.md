# LQ-668 — Wrapper Entrypoint Composition Prerequisite Audit

## Ergebnis

Der LQ-667-Entrypoint kann mit dem aktuellen installierbaren Paket noch nicht
vollständig und ehrlich konstruiert werden.

Vier konkrete Voraussetzungen fehlen.

## Blocker 1: package-lokale Writerprimitive

Der konkrete atomare Writer liegt unter `tools/private_manifest_handoff.py` und
hängt zusätzlich vom Renderer unter `tools/pre_staging_manifest.py` ab.

Die Setuptools-Paketsuche umfasst ausschließlich `src`; `tools/` ist kein
Bestandteil des installierten Liquent-Wheels.

Ein Entrypointimport aus `tools` würde lokal Tests bestehen können, im
Produktionsimage jedoch fehlen.

## Blocker 2: package-lokale Recoveryprimitive

Die konkrete read-only Reconciliation liegt ebenfalls ausschließlich unter
`tools/private_manifest_handoff_reconcile.py`.

Im installierbaren Paket existiert kein gleichwertiger process-eigener Adapter.

## Blocker 3: direkte Child-Control-Dateiansicht

Der vorhandene atomare Control-Artifact-Adapter erwartet ein Hostroot plus eine
jobbezogene Resolver-Childdirectory.

Der Container sieht dagegen bereits die einzelne Artifactdirectory direkt als
`/run/liquent/control`.

Ein erfundener Parentpfad oder ein Mapping auf dieselbe Directory würde die
bestehende Root-/Childprüfung umgehen.

## Blocker 4: feste Process-Composition

Es existiert noch keine process-eigene Composition aus Ankercodec, Loader,
direktem Child-Control-Adapter, konkretem Capabilityexecutor, UTC-/Monotonic-
Clocks und fester Waitpolicy.

Nur die One-shot-Ablaufklasse oder ein injizierbarer Testexecutor genügt nicht.

## Entscheidung

LQ-668 ergänzt keine `[project.scripts]`-Einträge und keinen `main()`-Pfad.

Ein registrierter Command, der erst nach Containerstart an fehlenden Modulen
oder Adaptern scheitert, wäre eine falsche Productionfähigkeit.
