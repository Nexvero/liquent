# LQ-777 — Owned Engine API Process Run Evidence

## Reihenfolgeevidenz

Die Tests belegen exakt Dependency-Preflight, Open, vollständigen Preflight,
Run und Retire. Listenerobjekt und Loopresultat bleiben dabei identisch.

Ein zusätzlicher Hostpreflighttest entfernt nur den Proxy-Socket: Die
Dependency-Prüfung bleibt ready, während der vollständige Preflight fail-closed
not-ready ist.

## Fehlerpfade

Fehlgeschlagene Dependency-Prüfung erzeugt keine Listenerwirkung. Openfehler hat
kein Retireziel.

Fehler im vollständigen Preflight oder Loop retiren den Listener genau einmal.
Ein Retirefehler nach erfolgreichem Loop verhindert Erfolg und bleibt detailfrei.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Signal, Thread, Main, Entry Point oder separates
Close. Die Tests patchen konkrete Komponenten und öffnen keinen Hostlistener.

Der Prozesslauf bleibt explizit endlich durch den bereits geschlossenen Loop.
