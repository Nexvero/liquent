# LQ-749 — Engine API Daemon Peer Policy Evidence

## Positive Evidenz

Ein verbundener AF_UNIX/SOCK_STREAM mit nicht vererbbarem Socketdeskriptor,
ungebundenem lokalen Endpoint, exaktem Daemonpeer, Timeout und passenden
Kernelcredentials erzeugt den Nachweis.

Sowohl explizite Root-UID null als auch eine konfigurierte positive Daemon-UID
werden belegt. Der Stream wird nicht verändert oder geschlossen.

## Negative Evidenz

Family, Type, Timeout, Fileno, lokaler Endpoint, Peerendpoint, Listenerstatus,
PID, UID und GID werden einzeln abweichend geprüft.

Reguläre und vererbbare Deskriptoren, Inodeaustausch sowie malformed
Credentialbytes scheitern fail-closed und detailfrei.

Relative oder Rootpfade, negative UID, nichtpositive GID und ungültige Timeouts
werden beim Aufbau abgelehnt.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Connect, Settimeout, Set-inheritable, Shutdown oder
Close. Die Tests öffnen keine Hostverbindung.
