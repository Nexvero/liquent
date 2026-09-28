# LQ-721 — Engine API Host Preflight Evidence

## Ergebnis

Dateibasierte Evidenz erzeugt zwei lokale Unix-Sockets sowie private Control-,
Source- und Targetverzeichnisse mit aktuellen Prozessidentitäten.

Die vollständige Matrix ist ready und bleibt über die Prüfung inode-, mode-,
uid- und gid-identisch.

## Driftmatrix

Für Proxy-Socket, Daemon-Socket, Control, Source und Target wird jeweils eine
Modeabweichung separat als derselbe detailfreie not-ready-Grund belegt.

Ein reguläres File statt Proxy-Socket und ein Symlink statt Sourcewurzel werden
ebenfalls abgelehnt.

## Geschlossene Oberfläche

Ungültige oder überlappende Konfiguration scheitert vor Check.

Die Klasse besitzt keine Create-, Chmod-, Chown-, Connect-, Bind-, Remove- oder
Cleanupoperation.

## Restgrenze

Der Preflight öffnet keinen Listener und prüft keine Peercredentials.

Sein positives Ergebnis erlaubt daher allein noch kein Forwarding.
