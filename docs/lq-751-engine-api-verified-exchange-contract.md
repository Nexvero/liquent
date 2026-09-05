# LQ-751 — Engine API Verified Exchange Contract

## Ziel

Ein Single Exchange darf erst beginnen, nachdem Client- und Daemonstream im
selben Aufruf aus aktuellen Kernelinformationen autorisiert wurden.

## Reihenfolge

Zuerst wird der Clientstream über die feste Client-Peerpolicy geprüft. Danach
wird der davon verschiedene Daemonstream über die feste Daemon-Peerpolicy
geprüft.

Erst wenn beide Nachweise vorliegen und weiterhin exakt ihre Eingabestreams und
verschiedene Deskriptoren binden, darf der bestehende geschlossene Exchange
aufgerufen werden.

## Keine Caller-Nachweise

Der Aufrufer liefert ausschließlich die beiden Streams. Er liefert weder
Nachweise noch PID, UID, GID, Endpoint, Rolle oder Allow-Entscheidung.

Damit kann ein öffentlich konstruierter Nachweis keine Kernelauflösung
überspringen.

## Wirkungsgrenze

Eine abgelehnte Clientprüfung verhindert auch die Daemonprüfung und jedes
Stream-I/O. Eine abgelehnte Daemonprüfung erfolgt nach Clientprüfung, aber vor
jeglichem Streamread oder Write.

Descriptorgleichheit oder Änderung zwischen Nachweis und Exchange scheitert
ebenfalls vor Stream-I/O.

## Ownership

Die Komposition übernimmt weder Timeout noch Close. Kernel- oder Exchangefehler
werden nicht automatisch wiederholt.

## Grenzen

Kein Listener, Accept, Connect, Socketbau, Timeoutsetzen, Close oder Loop wird
ergänzt.
