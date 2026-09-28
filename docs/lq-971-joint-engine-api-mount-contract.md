# LQ-971 — Joint Engine API Mount Contract

## Ergebnis

Definiert vier private Settingsdateien, Docker-Socket sowie Control-, Source- und Target-Root als acht Bindungen.

## Grenze

Nur Source ist read-only; Runtime-Sockets liegen im privaten tmpfs.
