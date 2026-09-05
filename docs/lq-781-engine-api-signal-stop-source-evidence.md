# LQ-781 — Engine API Signal Stop Source Evidence

## Wirkungsfreiheit

Konstruktion und Stopread erzeugen keinen Signalzugriff. Installation außerhalb
des Main Threads scheitert bereits vor dem Lesen globaler Handler.

## Signalwirkung

SIGTERM und SIGINT setzen jeweils ausschließlich den lokalen Stopzustand. Ein
unbekanntes Signal und ein gespeicherter Handleraufruf nach Restore haben keine
Wirkung.

Restore setzt beide Originalhandler in umgekehrter Reihenfolge zurück. Eine
erneute Installation setzt den vorherigen Stopzustand zurück.

## Fehlerpfade

Eine partielle Installation mit Fehler bei SIGINT rollt den bereits gesetzten
SIGTERM-Handler zurück.

Bei Restorefehler für SIGINT wird SIGTERM trotzdem versucht und wiederhergestellt.
Zweite Installation und zweites Restore scheitern fail-closed.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Kill, Raise-signal, Thread, Run oder Close. Die
Tests ersetzen ausschließlich das Signalmodul und senden kein Prozesssignal.
