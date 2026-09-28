# LQ-807 — Engine API Real Run Status Instrumentation Contract

## Ziel

Der reale Owned Process Run muss genau eine Statusinstanz an seine belastbaren
Listener- und Serve-Lebenszykluspunkte binden.

## Übergänge

`starting` wird vor dem Dependency-Preflight gesetzt. `serving` darf erst nach
Listenerpublikation und erfolgreichem vollständigem Hostpreflight entstehen.

Nach einem typisierten Serve-Ergebnis folgt `stopping`. `stopped` darf erst nach
erfolgreichem Listener-Close und sicherem Retire entstehen.

Jeder Preflight-, Open-, Verify-, Loop-, Ergebnis-, Close-, Retire- oder
Statusfehler führt detailfrei zu `failed`, soweit der Status noch nicht terminal
ist.

## Ownership

Die Dependencycomposition erzeugt genau eine Statusinstanz und übergibt sie an
den realen Process Run. Kein globaler Status oder caller-gelieferter Snapshot
wird akzeptiert.

## Grenzen

Keine HTTP-Healthroute, Nebenläufigkeit des Serve Loops, Logging-, Deployment-
oder Restartentscheidung wird ergänzt.
