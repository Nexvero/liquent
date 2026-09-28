# LQ-829 — Engine API Health Socket Authority Evidence

## Positive Evidenz

Die vollständige Authority bewahrt alle neun expliziten Fakten, ist
unveränderlich und repräsentiert keine privaten Werte.

Die erzeugte Kernel-Peerpolicy besitzt objektidentischen Socketpfad und exakt die
konfigurierte Peer-UID/GID sowie den Timeout.

## Ablehnungsevidenz

Relative, Root-, direkt unter Root liegende und Parentsegmentpfade scheitern.
Null, boolesche oder falsche Identitätsformen sowie Timeout und Backlog außerhalb
der geschlossenen Bereiche werden abgelehnt.

## Trennung

Socket-, Eltern- und Peeridentitäten bleiben sechs unabhängige Werte. Die
Oberfläche enthält keinen Listener, Requestauthorize, Rolle, Allow oder
Environmentzugriff.

Ein interner Policykonstruktionsfehler verliert seine privaten Details.
