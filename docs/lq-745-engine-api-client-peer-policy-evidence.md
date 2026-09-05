# LQ-745 — Engine API Client Peer Policy Evidence

## Positive Evidenz

Ein AF_UNIX/SOCK_STREAM mit echtem nicht vererbbarem Socketdeskriptor, festem
lokalem Endpoint, Nicht-Listenerstatus, exaktem Timeout und passenden
Kernelcredentials erzeugt den gebundenen Nachweis.

Der Stream wird dabei nicht geschlossen oder verändert.

## Negative Evidenz

Family, Type, Timeout, Fileno, lokaler Endpoint, Listenerstatus, PID, UID und GID
werden einzeln abweichend geprüft.

Reguläre oder vererbbare Deskriptoren, Inodeaustausch sowie malformed
Credentialbytes scheitern ebenfalls fail-closed und detailfrei.

Relative oder Rootpfade, nichtpositive Identitäten und nichtpositive Timeouts
werden bereits beim Policyaufbau abgelehnt.

## Fähigkeitsgrenze

Die Oberfläche bietet kein Accept, Settimeout, Set-inheritable, Connect oder
Close. Die Tests ersetzen nur Kernelfakten und öffnen keinen Socket.

Ein Nachweis autorisiert ausschließlich die spätere Nutzung genau des geprüften
bereits akzeptierten Streams.
