# LQ-713 — Engine API Client Route Compatibility Evidence

## Ergebnis

Ausführbare Evidenz gleicht alle sieben vom bestehenden lokalen Docker-Client
erzeugten Routen mit der neuen Proxy-Routenpolicy ab.

## Positive Matrix

Find, Create, Inspect, Start, Wait, Stop und Kill werden jeweils exakt ihrer
typisierten Operation zugeordnet.

## Negative Matrix

Abgelehnt werden Delete, Exec, Logs, Image-Create, Build, falsche API-Version,
zusätzliche Findparameter, unsichere Creationwerte, nichtkanonische Container-ID,
anderer Stop-Timeout, anderes Signal und leerer Createbody.

Target- und Bodygrenzen werden separat belegt.

## Keine falsche Freigabe

Ein klassifizierter Create-Request kann nicht weitergeleitet werden, weil die
Policy weder Listener noch Transport oder Forwarding besitzt.

Damit ist Routekompatibilität belegt, ohne den noch fehlenden semantischen
Createfilter zu überspringen.
