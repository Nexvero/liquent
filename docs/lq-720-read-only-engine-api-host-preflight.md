# LQ-720 — Read-only Engine API Host Preflight

## Umsetzung

`ManifestHandoffSupervisorEngineApiHostPreflight` ist ein synchroner
Readinessprobe ohne Netzwerkverbindung oder Mutation.

## Konstruktion

Der Konstruktor bindet fünf eindeutige absolute Pfade und die erwarteten
Proxy-, Client-, Daemon-, Host- und Datenidentitäten.

Relative, Root-, Traversal- oder überlappende Pfade sowie ungültige IDs scheitern
vor jeder Prüfung detailfrei.

## Prüfung

Beide Sockets werden als Sockettyp, UID, GID, Modus und stabile Inode geprüft.

Jede Wurzel wird no-follow geöffnet und Path-/Descriptoridentität, Verzeichnistyp,
UID, GID und exakter Modus werden verglichen.

Alle Deskriptoren werden in jedem Pfad geschlossen.

## Ergebnis

Nur die vollständige Matrix liefert
`manifest_handoff_supervisor_host_ready`.

Jeder technische oder semantische Fehler liefert denselben detailfreien
not-ready-Grund.
