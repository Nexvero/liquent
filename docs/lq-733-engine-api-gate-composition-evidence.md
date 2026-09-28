# LQ-733 — Engine API Gate Composition Evidence

## Requestevidenz

Ein Inspectrequest erzeugt Route und Containerbindung, aber keine
Createautorität. Ein gültiger Create erzeugt sowohl Routen- als auch vollständige
semantische Profilbindung.

Semantisch erweitertes Create, DELETE, Imageszugriff und ein Startrequest mit
Body scheitern vor Ausgabe eines Nachweises.

## Responseevidenz

Inspect 200 und neutrale 404 werden nur mit einem zuvor autorisierten
Inspectnachweis angenommen. Ein Create-201 unter demselben Inspectnachweis wird
abgelehnt.

Nachweise können nicht zwischen zwei Gateinstanzen übertragen werden. Ein vom
Caller aus öffentlichen Werteklassen zusammengesetzter Nachweis ist ebenfalls
keine Responseautorität.

## Fähigkeitsgrenze

Konstruktion und Policyaufrufe erzeugen kein I/O. Die Oberfläche bietet weder
Listen, Bind, Connect, Recv, Send, Forward noch Close.

Die Tests laufen gemeinsam mit Framing-, Response-, Host-, Create-, Route-,
Client- und Migrationsprüfungen.
