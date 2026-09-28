# LQ-843 — Peer-verified Engine API Health Exchange Contract

## Ziel

Ein bereits akzeptierter und extern besessener Unix-Stream darf genau einen
Healthaustausch erst nach aktueller Kernel-Peerprüfung ausführen.

## Reihenfolge

Die feste Reihenfolge ist Peerauthorize, Requestread, Protocolhandle,
Responsewrite. Jede Stufe muss vollständig erfolgreich sein, bevor die nächste
beginnt.

Der Autorisierungsnachweis muss der exakte bestehende Peer-Nachweistyp sein,
dieselbe Streaminstanz binden und dessen aktuellen Deskriptor enthalten.

Vor dem Write wird der Deskriptor erneut mit dem Nachweis verglichen. Ein
geschlossener oder ausgetauschter Stream scheitert vor Antwortwirkung.

## Fehler

Jeder Peer-, Read-, Protocol-, Response- oder Writefehler stoppt spätere Stufen
und wird detailfrei vereinheitlicht.

## Ownership und Grenzen

Die Operation erwirbt, konfiguriert oder schließt den Stream nicht. Kein
Listener, Accept, Loop, Thread oder Deployment wird ergänzt.
