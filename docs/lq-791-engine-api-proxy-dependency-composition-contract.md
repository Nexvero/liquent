# LQ-791 — Engine API Proxy Dependency Composition Contract

## Ziel

Ein einziger vollständig validierter LQ-787-Settingswert muss den gesamten
privaten Proxygraphen deterministisch und ohne I/O erzeugen.

## Bindungen

Host-Owner-UID und Client-GID binden den zulässigen lokalen Clientpeer.
Proxy-UID und Client-GID binden den Socket. Host-Owner-UID/GID binden dessen
privates Elternverzeichnis.

Daemon-UID/GID und Daemontimeout binden Connector und Kernel-Peerprüfung an
denselben Daemonpfad. Wrapper-UID/GID binden ausschließlich Create-Requests.

Alle Pfade, Timeouts, Backlog und Laufgrenzen stammen unverändert aus derselben
Settingsinstanz. Es gibt keine Defaults oder zweite Konfigurationsquelle.

## Vollständiger Graph

Createpolicy, Gate, Stream-Exchange, beide Peerpolicies, Connector, Connected
Exchange, Accept, Serve Loop, Preflight, Listener, Process Run und Stopquelle
werden jeweils genau einmal in den signalbesessenen Lauf komponiert.

## Wirkungsgrenze

Composition liest weder Host noch Environment, öffnet keinen Socket, installiert
kein Signal und startet keinen Lauf. Fehler bleiben detailfrei.

Kein Settingsadapter, Entry Point, Deployment oder Readinessclaim gehört in
diesen Slice.
