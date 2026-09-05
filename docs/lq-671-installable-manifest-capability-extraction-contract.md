# LQ-671 — Installable Manifest Capability Extraction Contract

## Ergebnis

Renderer, atomarer Writer und read-only Reconciler werden aus dem
Repository-`tools`-Namespace in ein installierbares Liquent-Paket verschoben.

Es darf danach weiterhin nur je eine maßgebliche Implementierung geben.

## Zielnamespace

Die Primitiven liegen unter `liquent_platform.capabilities` und werden durch die
bestehende Setuptools-Suche unter `src` in das Wheel aufgenommen.

Packagecode importiert ausschließlich diesen Namespace.

## Semantische Identität

Algorithmen, Ergebniswerte, Exceptions, Detailgrenzen, Dateimodi,
Atomizitätsregeln und read-only Eigenschaften bleiben unverändert.

Die Extraktion fügt keine Normalisierung, neue Outcomeart oder zusätzliche
Dateiwirkung hinzu.

## Toolkompatibilität

Die bisherigen drei `tools.*`-Modulnamen bleiben als dünne CLI- und
Importkompatibilitätsgrenze bestehen.

Beim Import müssen sie auf exakt dasselbe package-lokale Modulobjekt zeigen.

Damit treffen bestehende Monkeypatches und Imports dieselben Funktionsglobals;
es entsteht keine Wrapperkopie mit abweichendem Zustand.

## Abhängigkeitsrichtung

Renderer ist die unterste Primitive.

Writer importiert ausschließlich Renderer; Reconciler importiert ausschließlich
die gemeinsamen sicheren Writerhilfen.

Kein Modul unter `src` importiert zurück aus `tools`.

## Unveränderte Grenzen

Keine Wrappercommands, Settings, Appfactory, Compose-, Control-Adapter-, Engine-,
Schema-, SQL-, Migrations- oder Productionaktivierung wird ergänzt.
