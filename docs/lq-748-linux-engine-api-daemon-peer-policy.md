# LQ-748 — Linux Engine API Daemon Peer Policy

## Umsetzung

`LinuxManifestHandoffSupervisorEngineApiDaemonPeerPolicy` kombiniert Family,
Type, Timeout, Fileno, `fstat`, Inheritability, `SO_ACCEPTCONN`, beide Endpoints
und `SO_PEERCRED`.

Der lokale Endpoint muss exakt leer und der Peerendpoint exakt der konfigurierte
Daemonpfad sein. Root- und explizit konfigurierte Nicht-Root-Daemons werden mit
derselben exakten UID-/GID-Regel behandelt.

## Nachprüfung

Nach dem Lesen der Kernelcredentials werden Fileno, beide Endpoints und
Inodeidentität erneut geprüft. Erst danach entsteht ein unveränderlicher,
streamgebundener Nachweis.

## Detailfreiheit

System-, Socket-, Endpoint-, Struktur- und Identitätsfehler werden auf die
bestehende technische Nichtverfügbarkeit reduziert.

## Nicht umgesetzt

Kein Socketbau, Connect, Timeoutsetzen, Inheritability-Mutation, Shutdown,
Close, Retry oder Exchange-Aufruf wird ergänzt.
