# LQ-657 — Wrapper Entrypoint and Wiring Decision

## Ergebnis

Production-Wiring wird noch nicht geöffnet. Die notwendige Implementierungsfolge
wird verbindlich festgelegt.

## 1. Unveränderlicher Kindanker

Zuerst muss die Parent-erzeugte Soll-Erwartung über einen konstruktiv
kontrollierten, unveränderlichen Kindkanal gebunden werden.

Sie darf nicht vom Request, einer Rolle, einem Allowboolean, frei gesetztem
Environment oder dem zu prüfenden Dokument selbst stammen.

Die konkrete Transportform bleibt einem eigenen Slice vorbehalten.

## 2. Profilgetrennte Mountfähigkeiten

Danach muss die Engine aus den bereits gebundenen System-of-Record-Fakten eine
geschlossene Mountmenge ableiten.

Writer und Recovery erhalten nur ihre jeweils erforderlichen Quell-/Zielrechte;
Recovery erbt keine Writer- oder Cleanupfähigkeit.

Callerpfade und zusätzliche Mounts bleiben verboten.

## 3. Feste Entrypoints

Erst anschließend werden feste Writer- und Recovery-Entrypoints gebaut, die
Anker laden, den One-shot-Prozess genau einmal ausführen und Fehler detailfrei
beenden.

Sie führen keine Admission-, Authority-, Membership- oder Bootstrapentscheidung
aus.

## 4. Lebenszyklus

Start, bounded Wait, Crashbeobachtung und genau ein terminaler Abschluss müssen
als vollständiger Prozesslebenszyklus belegt sein.

Restart darf keine zweite Capabilitywirkung aus einer bereits konsumierten
Freigabe ableiten.

## 5. Exklusive Auswahl

Appfactory und Deployment dürfen anschließend genau einen vollständigen Graphen
auswählen.

Es gibt keinen Feld-für-Feld-Mix, keinen Kompatibilitätsfallback und keinen
Settings-only-Erfolg.

Der alte Parent-Executorpfad muss bei Kandidatenauswahl konstruktiv unerreichbar
sein.

## Unveränderte Grenzen

Dieser Slice ändert keine Settings, Ports, Modelle, Migrationen, SQL, CLI,
Compose-, Appfactory- oder Entrypointdatei.

Er aktiviert keinen Container und führt keine Capability aus.
