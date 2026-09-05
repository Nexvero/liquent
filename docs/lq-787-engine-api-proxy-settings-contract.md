# LQ-787 — Engine API Proxy Settings Contract

## Ziel

Alle für die spätere Proxycomposition erforderlichen statischen Werte werden als
eine atomare, vollständige und unveränderliche Konfiguration gebunden.

## Eingabegrenze

Der Parser akzeptiert ausschließlich ein echtes Dictionary mit exakt dem
geschlossenen Schlüsselsatz und ausschließlich Stringschlüsseln und -werten.

Es gibt keine Defaults, partiellen Gruppen, zusätzlichen Schlüssel,
Environmentreads, Secretsauflösung, Normalisierung oder caller-gelieferte
Allow-Entscheidung.

## Pfade und Commands

Proxy-Socket, Daemon-Socket sowie Control-, Source- und Targetwurzel sind fünf
verschiedene absolute kanonische Nicht-Root-Pfade ohne Parentsegmente.

Writer- und Recoverycommand sind verschiedene absolute kanonische Pfade. Ein
freier Shellstring oder relatives Command ist verboten.

## Identitäten

Proxy-UID, Client-GID, Daemon-GID, Host-Owner-UID/GID, Daten-Owner-UID/GID und
Wrapper-UID/GID sind explizite positive Dezimalwerte.

Daemon-UID ist explizit nichtnegativ und darf für einen root-besessenen Daemon
null sein. Kein Wert wird aus einem anderen abgeleitet.

Alle Identitätswerte sind auf signed 32-bit positive beziehungsweise
nichtnegative Systemwerte begrenzt.

## Timeouts und Grenzen

Client- und Daemontimeout sind ganze Sekunden zwischen 1 und 300. Listenerbacklog
liegt zwischen 1 und 128. Die harte Laufgrenze liegt zwischen 1 und 1.000.000
Einzelaustauschen.

Dezimalwerte sind kanonisch ohne Vorzeichen, Whitespace, führende Null,
Fließkomma oder boolesche Schreibweise.

## Grenzen

Der Settingswert führt kein I/O aus, liest keine Umgebung und aktiviert keine
Composition oder Productionfähigkeit.
