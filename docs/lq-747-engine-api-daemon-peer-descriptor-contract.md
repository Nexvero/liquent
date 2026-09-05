# LQ-747 — Engine API Daemon Peer Descriptor Contract

## Ziel

Ein bereits verbundener Linux-Unix-Stream zum Engine-Daemon darf erst nach
aktueller Prüfung seiner Descriptor-, Endpoint- und Kernel-Peerfakten in einen
Exchange gelangen.

## Feste Konfiguration

Die Policy wird an einen absoluten Nicht-Root-Daemon-Socketpfad, eine explizite
nichtnegative Daemon-UID, eine positive Daemon-GID und einen positiven bereits
gesetzten Timeout gebunden.

UID null ist für einen root-besessenen lokalen Daemon ausdrücklich darstellbar,
aber niemals implizit angenommen.

## Descriptor und Endpoints

Der Stream ist AF_UNIX und SOCK_STREAM. Sein Deskriptor ist ein echter nicht
vererbbarer Socket und kein Listener.

Der lokale Clientendpoint ist ungebunden. Der Kernel-Peerendpoint entspricht
exakt dem konfigurierten Daemon-Socketpfad.

## Peercredentials

PID, UID und GID werden direkt über Linux `SO_PEERCRED` gelesen. PID muss positiv
sein; UID und GID müssen exakt der festen Daemonkonfiguration entsprechen.

Ein Dateisystempfad allein oder ein erfolgreicher Connect ist kein ausreichender
Identitätsnachweis.

## Racebegrenzung

Descriptor, lokaler und entfernter Endpoint sowie Device, Inode und Modus werden
nach der Credentialauflösung erneut verglichen.

## Grenzen

Die Policy verbindet, konfiguriert, beendet oder schließt keinen Stream. Ihr
Nachweis gilt ausschließlich für die unmittelbar geprüfte Streaminstanz.
