# LQ-755 — Engine API Daemon Connect Contract

## Ziel

Der Proxy darf pro Aufruf höchstens einen neuen Unix-Stream ausschließlich zum
fest konfigurierten lokalen Engine-Daemon erzeugen und verbinden.

## Aufbaufolge

Der Stream wird als AF_UNIX/SOCK_STREAM mit Close-on-exec angefordert. Unmittelbar
danach wird Inheritability explizit auf false und der feste positive Timeout
gesetzt.

Erst anschließend erfolgt genau ein Connect zum absoluten Nicht-Root-
Daemon-Socketpfad. Alternative oder caller-gelieferte Ziele existieren nicht.

## Nachprüfung

Nach erfolgreichem Connect müssen Family, Type, Fileno, echter Socketdeskriptor,
Nichtvererbbarkeit, Timeout, leerer lokaler Endpoint und exakter Peerendpoint
erneut stimmen.

Die separate Daemon-Peerpolicy prüft danach zusätzlich die Kernelcredentials;
ein Connect allein erteilt keine Exchangeautorität.

## Ownership und Fehler

Bei Erfolg wird der offene Stream an den Aufrufer übertragen und nicht vom
Connector gehalten.

Jeder Fehler nach Erzeugung schließt den partiellen Stream genau einmal. Auch ein
Closefehler bleibt detailfrei und ersetzt nicht den ursprünglichen Fehlschlag.

## Grenzen

Der Connector besitzt keinen Listener, Bind, Accept, Shutdown, Retry, Pool oder
dauerhaften Close-Lifecycle.
