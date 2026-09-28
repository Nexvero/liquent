# LQ-769 — Engine API Single-Accept Evidence

## Erfolgsreihenfolge

Die Tests belegen Listenerprüfung, genau ein Accept, Client-Close-on-exec und
Timeoutsetup, Connected Exchange und genau ein Client-Close.

Der Listener wird nicht geschlossen; die konkrete Clientobjektidentität bleibt
bis zum Exchange erhalten.

## Fehlerpfade

Ein falscher Listener stoppt vor Accept. Ein Acceptfehler besitzt kein
Client-Closeziel.

Family-, Type-, Fileno-, Endpoint-, Peer-, Listenerstatus- und Timeoutabweichung
des Clients schließen ihn genau einmal vor dem Exchange.

Nichtleere Acceptadresse, Exchangefehler und Client-Closefehler bleiben
detailfrei. Ein Post-Accept-Fehler löst keinen Retry aus.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Open, Listen, Bind, Connect, Run, Loop oder Close.
Die Tests verwenden ausschließlich bereits aktive kontrollierte Doubles.
