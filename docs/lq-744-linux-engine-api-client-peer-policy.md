# LQ-744 — Linux Engine API Client Peer Policy

## Umsetzung

`LinuxManifestHandoffSupervisorEngineApiClientPeerPolicy` prüft einen bereits
akzeptierten Stream ausschließlich aus aktuellen Objekt- und Kernelinformationen.

Sie kombiniert Family, Type, Timeout, Fileno, `fstat`, Inheritability,
`SO_ACCEPTCONN`, lokalen und entfernten Endpoint sowie `SO_PEERCRED`.

Die Peerstruktur wird als exakt drei native Integer für PID, UID und GID
dekodiert. Fehlende oder abweichende Fakten sind technische Nichtverfügbarkeit.

## Nachprüfung

Nach Credentialauflösung werden Descriptor, lokaler Endpoint und Inodeidentität
erneut geprüft. Der resultierende Nachweis hält die geprüfte Streaminstanz, ohne
ihren Lebenszyklus zu übernehmen.

## Detailfreiheit

System-, Socket-, Struktur- und Konfigurationsfehler werden auf die bestehende
detailfreie technische Nichtverfügbarkeit reduziert.

## Nicht umgesetzt

Kein Listener, Accept, Timeoutsetzen, Inheritability-Mutation, Connect, Shutdown,
Close oder Exchange-Aufruf wird ergänzt.
