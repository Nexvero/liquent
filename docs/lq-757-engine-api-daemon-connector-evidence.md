# LQ-757 — Engine API Daemon Connector Evidence

## Positive Evidenz

Die Factory wird genau einmal mit AF_UNIX und SOCK_STREAM/Close-on-exec
aufgerufen. Inheritability false und Timeout werden vor genau einem Connect zum
festen Daemonpfad gesetzt.

Ein vollständig passender Stream wird offen und unverändert an den Aufrufer
übertragen.

## Fehler- und Cleanup-Evidenz

Fehler beim Inheritabilitysetup, Timeoutsetup oder Connect schließen den
partiellen Stream genau einmal.

Family-, Type-, Fileno-, Timeout-, lokaler Endpoint-, Peerendpoint-, Dateityp-
und Inheritabilitydrift nach Connect werden ebenfalls mit genau einem Close
abgelehnt.

Factoryfehler, None und selbst ein Fehler im Cleanup-Close bleiben detailfrei.

## Fähigkeitsgrenze

Die Oberfläche enthält kein Listen, Bind, Accept, Shutdown oder dauerhaftes
Close. Es gibt keinen Retry und keinen zweiten Connect.

Die Tests verwenden ausschließlich eine kontrollierte Socketfactory und öffnen
keine reale Hostverbindung.
