# LQ-719 — Engine API Host Preflight Contract

## Ziel

Vor Listener- oder Forwardingaktivierung müssen aktuelle Hostfakten für beide
Sockets und alle drei kontrollierten Wurzeln detailfrei geprüft werden.

## Proxy-Socket

Der private Eingang ist ein echter Unix-Socket, gehört der festen Proxy-UID und
der getrennten Client-GID und hat exakt Modus 0660.

Reguläre Datei, Symlink, FIFO, breiterer Modus oder abweichende Identität ist
not-ready.

## Daemon-Socket

Der Upstream ist ebenfalls ein echter Unix-Socket mit exakt konfigurierter
Daemon-UID/GID und Modus 0660.

Daemon-UID darf systembedingt 0 sein; Proxy-, Client-, Host- und Datenidentitäten
bleiben positiv und explizit.

## Wurzeln

Control ist ein dediziertes Verzeichnis mit Host-Owner-UID/GID und Modus 0700.

Source und Target sind getrennte Verzeichnisse mit Daten-Owner-UID/GID und
Modus 0750.

Alle fünf Pfade sind absolut, geschlossen, Nicht-Root und voneinander verschieden.

## Racebegrenzung

Verzeichnisse werden per `lstat`, `O_NOFOLLOW`, `fstat` und erneutem `lstat`
gegen Device/Inode-Austausch geprüft.

Sockets werden vor und nach der Faktenprüfung erneut per `lstat` verglichen.

Dies ist ein Readiness-Snapshot, keine dauerhafte Autorisierung: Listener und
Upstreamtransport müssen gebundene Deskriptoren und Peercredentials selbst
erneut prüfen.

## Keine Mutation

Der Preflight erstellt, repariert, chmoddet, chownt, verbindet oder löscht
nichts.

Jede Abweichung ergibt ausschließlich `manifest_handoff_supervisor_host_unavailable`.
