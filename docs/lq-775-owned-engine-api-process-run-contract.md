# LQ-775 — Owned Engine API Process Run Contract

## Ziel

Ein vollständiger endlicher Proxylauf besitzt Hostprüfung, Listenerpublikation,
Serve-Loop und Listener-Retire in einer festen fail-closed Folge.

## Zweiphasiger Preflight

Vor Listenerpublikation werden der Daemon-Socket sowie Control-, Source- und
Targetwurzeln aktuell geprüft. Der zu diesem Zeitpunkt zwingend abwesende
Proxy-Socket ist nicht Teil dieser Vorprüfung.

Nach erfolgreichem Listener-Open wird der vollständige bestehende Preflight
erneut ausgeführt. Er bindet nun zusätzlich den tatsächlich publizierten
Proxy-Socket mit Ownership, Modus und Inodefakten.

Nur beide erfolgreichen, exakt benannten Readinessergebnisse erlauben den Loop.

## Lauf und Ownership

Der Listener wird genau einmal geöffnet und ausschließlich an den begrenzten
Serve-Loop übergeben. Dessen Stopquelle bleibt explizit extern geliefert.

Ab erfolgreichem Open gehört der Listener bis zum Operationsende dem Prozesslauf
und wird nach Erfolg oder jedem späteren Fehler genau einmal retired.

## Fehlersemantik

Fehler vor Open besitzen kein Retireziel. Vollpreflight-, Loop- und
Retirefehler bleiben detailfreie technische Nichtverfügbarkeit.

Ein Retirefehler nach erfolgreichem Loop verhindert einen erfolgreichen
Prozessabschluss.

## Grenzen

Kein Signalhandler, Thread, Entry Point, Deployment-Wiring oder unendlicher Lauf
wird ergänzt.
