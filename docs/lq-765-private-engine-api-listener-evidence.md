# LQ-765 — Private Engine API Listener Evidence

## Erfolgsnachweis

Die Tests belegen die feste Reihenfolge Close-on-exec, Bind, Ownership/Mode,
Listen und Verify sowie sichere spätere Schließung und Pfadentfernung.

Der publizierte Pfad besitzt exakt UID/GID und Modus 0660. Ein zweites Open wird
ohne Wirkung abgelehnt.

## Fremdpfad- und Fehlernachweis

Ein vorbestehender Zielname verhindert bereits Socketerzeugung. Bind- und
Listenfehler schließen den partiellen Listener; nur ein weiterhin identischer
selbst publizierter Socket wird entfernt.

Wird der Pfad vor Cleanup oder Retire ausgetauscht, bleibt er unangetastet.
Falsche Elternfakten stoppen vor Socketerzeugung.

Ein falsches Closeobjekt hat keine Wirkung. Ein Closefehler hält den aktiven
Zustand für einen späteren expliziten Retry.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Accept, Connect, Serve, Run oder Loop. Die Tests
simulieren Dateisystem und Socketfactory ohne Hostpublikation.
