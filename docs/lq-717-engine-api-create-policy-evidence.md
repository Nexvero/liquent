# LQ-717 — Engine API Create Policy Evidence

## Ergebnis

Ausführbare Evidenz belegt exakt ein Writer- und ein Recoveryprofil.

Writer rekonstruiert Control, Source und Target; Recovery besitzt keinen
Sourcefakt und bindet Target ausschließlich read-only.

## Negative Matrix

Detailfrei abgelehnt werden Rootuser, Tagimage, Zusatzlabel, Hostnetwork,
privilegierter Modus, Zusatzmount, fremdes Entrypointprogramm und ein Target
außerhalb der kontrollierten Wurzel.

Nichtkanonisches und Duplicate-Key-JSON scheitern ebenfalls.

## Inertheit

Die Policy liest keine Datei, löst keinen Symlink auf, öffnet keinen Socket und
besitzt keine Forwardingoberfläche.

Hostfakten bleiben deshalb ein expliziter späterer Preflight und werden nicht
aus Requestbehauptungen abgeleitet.
