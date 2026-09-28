# LQ-812 — Signal-bound Engine API Process Status

## Umsetzung

Der Owned Process Run akzeptiert den expliziten booleschen
`defer_terminal_status`. Nur die vollständige Proxycomposition setzt ihn true.

In diesem Modus bleibt erfolgreicher innerer Abschluss in `stopping`.
`finalize_outer_run` akzeptiert ausschließlich einen booleschen Ausgang und
setzt danach genau einen passenden Terminalzustand.

Der Signal-owned Run erkennt ausschließlich diese konkrete interne
Deferred-Bindung. Nach dem Restore finalisiert er Erfolg oder Fehler; ein Fehler
der Finalisierung selbst macht den gesamten Run detailfrei unavailable.

## Nicht umgesetzt

Keine öffentliche Statusmutation, kein caller-gelieferter Allow-Wert, keine
Healthroute, Paketscript- oder Deploymentänderung.
