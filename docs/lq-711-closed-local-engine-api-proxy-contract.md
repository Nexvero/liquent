# LQ-711 — Closed Local Engine API Proxy Contract

## Ziel

Eine spätere lokale Proxygrenze darf dem Control-Plane-Prozess nur den exakt
benötigten Supervisorausschnitt der Docker Engine API vermitteln.

## Exakte Operationen

Erlaubt sind ausschließlich API-Version 1.45 und sieben Operationen:

- Find nach genau einem Creationlabel
- Create eines noch separat vollständig zu validierenden Profils
- Inspect einer exakten 64-stelligen Container-ID
- Start
- Wait mit `condition=not-running`
- Stop mit festem Timeout 10
- Kill ausschließlich mit Signal KILL

Remove, Exec, Attach, Logs, Pull, Build, Images, Volumes, Networks, Events und
jede freie Daemonoperation bleiben verboten.

## Requestgrenzen

Methode, Pfad, Query, Bodyanwesenheit und kanonische Querykodierung werden vor
jeder Weiterleitung geprüft.

Requesttarget ist auf 4096 ASCII-Bytes, Requestbody auf 65.536 Bytes begrenzt.

Unbekannte API-Versionen, doppelte JSON-/Queryschlüssel, zusätzliche Parameter,
alternative Signale und Timeoutwerte scheitern detailfrei.

## Create bleibt zweistufig

Die Routenpolicy klassifiziert Create, autorisiert aber noch keine
Daemonweiterleitung.

Vor Forwarding muss ein eigener semantischer Filter Image-Digest, Labels,
Entrypointanker, numerischen User, Securityprofil und jede Bindquelle gegen
kontrollierte Proxykonfiguration validieren.

## Responsegrenzen

Der spätere Proxy akzeptiert nur die je Operation erwarteten Statuscodes,
Content-Type und höchstens 1.048.576 Responsebytes.

Er puffert keine unbegrenzten Antworten und gibt keine Daemonfehlerdetails an
den Client weiter.

## Hostownership

Der Proxy allein besitzt den realen Daemon-Socket.

Sein privater Eingangssocket gehört einer getrennten nichtprivilegierten Gruppe,
ist nicht öffentlich und wird weder an Wrapper noch andere Dienste gemountet.

## Grenzen

Kein Listener, Forwarder, Socket, Daemonzugriff, Compose- oder
Productionaktivierung wird in diesem Slice erzeugt.
