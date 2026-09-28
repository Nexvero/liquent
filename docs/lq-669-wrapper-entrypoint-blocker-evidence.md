# LQ-669 — Wrapper Entrypoint Blocker Evidence

## Ergebnis

Statische ausführbare Evidenz hält die LQ-668-Blocker reproduzierbar fest.

## Paketgrenze

`pyproject.toml` sucht Pythonpakete ausschließlich unter `src`.

Writer, Renderer und Reconciler liegen unter dem nicht ausgelieferten
Repositoryverzeichnis `tools` und besitzen keine package-lokalen Äquivalente.

## Entrypointgrenze

Die Projektskripte enthalten weder einen Writer- noch einen Recovery-
Supervisorwrapper.

Kindprozess und Kandidatencomposition besitzen keinen `main()`- oder
`__main__`-Pfad.

## Capabilitygrenze

Der einzige vorhandene Supervisor-Capabilityexecutor ist ein Adapter auf zwei
injizierte Supervisorports.

Er implementiert weder den Writer noch die read-only Recoveryprimitive selbst.

## Control-Artefaktgrenze

Der vorhandene lokale Adapter verlangt `path.parent == root` und öffnet danach
die Childdirectory unter dem Rootdescriptor.

Damit ist er nicht als direkter Adapter für die bereits gemountete
`/run/liquent/control`-Directory auszugeben.

## Sicherheitswirkung

Die Evidenz verhindert vorzeitige Commands, dynamische Imports, subprocess-
Fallbacks und eine irreführende `production_ready=true`-Behauptung.
