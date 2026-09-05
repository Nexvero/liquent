# LQ-761 — Engine API Connected Exchange Evidence

## Erfolgsreihenfolge

Die Tests belegen Connect vor Verified Exchange und exakt ein Daemon-Close
danach. Der Clientstream wird nicht geschlossen.

Die konkrete Objektidentität von Client- und Daemonstream bleibt beim Übergang
an den Verified Exchange erhalten.

## Fehlerpfade

Ein Connectfehler ruft keinen Exchange auf und besitzt kein Closeziel.

Ein Exchangefehler schließt den Daemonstream genau einmal. Ein Closefehler nach
erfolgreichem Exchange wird technische Nichtverfügbarkeit. Gleichzeitiger
Exchange- und Closefehler bleibt ein einziges detailfreies Ergebnis.

## Kompositionsgrenze

Duck-typed Connector- oder Exchangeersatz wird beim Aufbau abgelehnt. Die
öffentliche Oberfläche besitzt kein Listen, Bind, Accept, Connect, Retry oder
Close.

Die Tests öffnen keine reale Hostverbindung und übernehmen keinen Clientstream.
