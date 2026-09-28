# LQ-767 — Engine API Single-Accept Contract

## Ziel

Ein extern besessener privater Listener darf pro Aufruf höchstens einen Client
annehmen, sicher konfigurieren, durch die Connected-Exchange-Kette führen und
deterministisch schließen.

## Listenerprüfung

Vor Accept muss der Listener AF_UNIX/SOCK_STREAM, ein echter nicht vererbbarer
Socketdeskriptor, aktiv lauschend und exakt an den festen privaten Socketpfad
gebunden sein.

Eine Abweichung stoppt vor Accept. Der Listener wird weder verändert noch
geschlossen.

## Accept und Clientsetup

Genau ein Accept ist erlaubt. Der akzeptierte Client muss einen leeren lokalen
Peeradresswert liefern.

Close-on-exec false und der feste positive Clienttimeout werden unmittelbar
gesetzt. Danach werden Family, Type, Socketdeskriptor, Inheritability, Timeout,
lokaler Endpoint, leerer Peerendpoint und Nicht-Listenerstatus geprüft.

## Exchange und Ownership

Nur der vollständig konfigurierte Client geht in die bestehende
Connect-Verify-Exchange-Finally-Close-Kette.

Der Client gehört ab Accept bis Operationsende dieser Einmaloperation und wird
auf jedem Pfad genau einmal geschlossen. Der Listener bleibt extern besessen.

## Fehlersemantik

Acceptfehler hat kein Client-Closeziel. Jeder Post-Accept-Fehler schließt den
Client best-effort und bleibt detailfrei. Es gibt keinen Retry.

## Grenzen

Kein Listener-Open/Retire, Loop, Parallelismus, Shutdown oder Prozesslifecycle
wird ergänzt.
