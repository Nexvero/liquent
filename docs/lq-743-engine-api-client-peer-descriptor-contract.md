# LQ-743 — Engine API Client Peer Descriptor Contract

## Ziel

Ein bereits akzeptierter Linux-Unix-Stream darf erst nach aktueller Prüfung
seiner Descriptor-, Endpoint- und Kernel-Peerfakten in einen Exchange gelangen.

## Feste Konfiguration

Die Policy wird an einen absoluten Nicht-Root-Pfad des privaten Proxy-Sockets,
eine positive Client-UID, eine positive Client-GID und einen positiven bereits
gesetzten Timeout gebunden.

Diese Werte stammen aus privater Prozesskonfiguration, nicht aus dem Request.

## Descriptorfakten

Der Stream ist AF_UNIX und SOCK_STREAM. Sein nichtnegativer Deskriptor ist ein
echter Socket, nicht vererbbar und kein Listener.

Der lokale Endpoint entspricht exakt dem konfigurierten Proxy-Socket. Der Stream
besitzt bereits exakt den konfigurierten Timeout; die Policy verändert ihn nicht.

## Peercredentials

PID, UID und GID werden direkt über Linux `SO_PEERCRED` aus dem Kernel gelesen.
PID muss positiv sein; UID und GID müssen den festen Clientfakten entsprechen.

Caller-gelieferte Rollen, Gruppenbehauptungen, Allow-Booleans oder Header sind
keine Eingabe dieser Entscheidung.

## Racebegrenzung

Deskriptornummer, lokaler Endpoint sowie Device, Inode und Modus werden nach der
Credentialauflösung erneut verglichen. Austausch oder Schließen während der
Prüfung scheitert fail-closed.

## Ergebnis und Grenzen

Der unveränderliche Nachweis bindet Deskriptor, PID, UID, GID, lokalen Pfad und
die geprüfte Streaminstanz.

Die Policy akzeptiert, konfiguriert, verbindet oder schließt keinen Socket und
ist ausdrücklich Linux-spezifisch.
