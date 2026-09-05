# LQ-809 — Engine API Real Run Status Evidence

## Erfolgsevidenz

Der reale Run durchläuft Dependency-Preflight, Open, Vollpreflight, Loop und
Close in fester Reihenfolge und erreicht erst danach `stopped`.

## Fehlerevidenz

Fehler bei Dependency-Preflight, Open, Vollpreflight, Loop und Close werden
detailfrei und terminal `failed`. Nach Open wird der Listener auf jedem späteren
Fehlerpfad weiterhin geschlossen.

Ein gestoppter Run kann nicht wiederverwendet werden und erzeugt keine weitere
Hostwirkung.

## Compositionevidenz

Die vollständige Composition enthält genau eine initiale Statusinstanz im realen
Process Run. Fremde injizierte Statusobjekte werden abgelehnt.

## Grenzen

Die Tests simulieren Hostgrenzen wirkungsfrei; keine echten Sockets, Signale oder
Dateisystemänderungen werden ausgelöst.
