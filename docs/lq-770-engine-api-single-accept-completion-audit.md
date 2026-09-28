# LQ-770 — Engine API Single-Accept Completion Audit

## Ergebnis

LQ-767 bis LQ-770 schließen Accept-Setup-Exchange-Finally-Close für genau einen
Client eines bereits aktiven privaten Listeners.

## Geschlossene Eigenschaften

- aktuelle Listenerprüfung vor Accept
- genau ein Accept
- Client-Close-on-exec und fester Timeout
- vollständige Clientdescriptor- und Endpointprüfung
- bestehende Connect-/Peer-/Gate-/Exchange-Kette
- genau ein Client-Close auf jedem Post-Accept-Pfad
- kein Listener-Close
- detailfreie Fehler und kein Retry

## Offene Blocker

Listener-Lifecycle und Single Accept müssen noch in eine begrenzte Serve-
Operation mit Startup-/Shutdownownership gebunden werden.

Hostpreflight-Reihenfolge, Stop-Signal, Acceptunterbrechung, Loopbegrenzung,
Fehlerbudget und Prozessentrypoint fehlen weiterhin.

## Productionstatus

Es gibt noch keinen Serve-Loop oder Prozessstart; `production_ready=false` bleibt
korrekt.

## Verifikation

- 261 fokussierte Accept-, Listener-, Connected-Exchange-, Connector-, Peer-, Stream-, Gate-, Policy-, Host- und Migrationsprüfungen bestehen.
- 5.616 vollständige Nicht-PostgreSQL-Tests bestehen; 108 werden erwartungsgemäß übersprungen.
- Deprecation-Warnungen werden in der vollständigen Suite als Fehler behandelt.
- Die abschließende Diffprüfung bleibt die Whitespace- und Scopegrenze.

## Nächster Strang

Als Nächstes ist ein explizit begrenzter synchroner Serve-Loop mit Stopprüfung
zwischen den Einzelaustauschen umzusetzen.
