# LQ-420 — Release Preflight Signal Cleanup Reaudit

## Zweck

LQ-420 schließt die lokale Preflightkette für SIGINT, SIGTERM und
asynchrone Unterbrechungen während eines Kindprozesses.

Der Slice stellt sicher, dass ein Operatorabbruch keine Erfolgsevidenz,
privaten Workspace oder weiterlaufende Gateprozessgruppe hinterlässt.

## Reauditbefund

LQ-419 beendete Kindprozessgruppen bei Timeout.

Ein Signal an den übergeordneten Python-Preflight verwendete jedoch noch das
normale Betriebssystemverhalten.

SIGTERM konnte den Prozess damit vor dem `TemporaryDirectory`-Cleanup beenden.

Ein Kindprozess lief in einer eigenen Session und erhielt das Elternsignal
nicht automatisch.

Damit bestand bei Operatorabbruch eine Restartefakt- und Prozesslücke.

## Temporäre Signalgrenze

Der LQ-415-Runner installiert nur für die Dauer eines Laufs eigene Handler für:

- SIGINT;
- SIGTERM.

Beide Handler erzeugen dieselbe detailfreie
`ControlledPreflightRejected`-Grenze.

Dadurch läuft die Unterbrechung durch den bestehenden kontrollierten
Cleanup-Pfad.

## Handlerretention

Vorhandene Prozesshandler werden vor dem Lauf gespeichert.

Nach Erfolg und nach jeder Ablehnung werden sie im `finally`-Pfad exakt
wiederhergestellt.

Kann die Signalgrenze nicht installiert werden, startet kein Gate.

Es gibt keine dauerhafte Signalmutation des aufrufenden Prozesses.

## Unterbrechung während eines Gates

SIGINT oder SIGTERM stoppt die aktuelle Gateausführung sofort.

Spätere Gates werden nicht aufgerufen.

Der private Runner-Workspace wird entfernt.

Das finale Ziel und `controlled-preflight.json` entstehen nicht.

Die LQ-417-Oberfläche vereinheitlicht den Ausgang weiterhin zu Exitcode 2 und
`controlled_release_preflight_rejected`.

## Unterbrechung während eines Kindprozesses

Der begrenzte Prozessadapter fängt jede asynchrone Exception während `wait`.

Vor der Weitergabe an den Runner beendet er:

1. die gesamte Kindprozessgruppe mit SIGKILL;
2. ersatzweise den direkten Kindprozess;
3. wartet anschließend höchstens fünf Sekunden auf die Beendigung.

Erst danach setzt sich die detailfreie Runnerablehnung fort.

Es gibt keinen Retry und keine Nutzung partieller Prozessausgabe.

## Atomarer Commitmoment

Ab unmittelbar vor dem einzelnen atomaren Verschieben des vollständig grünen
privaten Workspaces an das neue Ziel bleibt die eigene Unterbrechungsreaktion
bis zur Wiederherstellung der vorherigen Signalhandler unterdrückt.

Damit kann ein bereits erfolgreich verschobenes Ergebnis nicht nachträglich
als abgelehnt erscheinen.

Vor diesem Moment führt jedes Signal zum vollständigen Cleanup.

Nach diesem Moment ist das owner-kontrollierte Ergebnis vollständig sichtbar;
es kann nicht mehr im selben Lauf als abgelehnt gemeldet werden.

## Erfolgsevidenz nach unbekanntem Ausgang

Ein Signal, Timeout, Killfehler oder anderer unbekannter Prozessausgang kann
kein Phasenreceipt erzeugen.

Ohne alle zehn Receipts erzeugt der Runner keine Gesamtevidenz.

Ein bereits vorhandenes fremdes oder früheres Ziel wird nicht verändert.

Die Aussage `kein Erfolgsartefakt nach unbekanntem Ausgang` ist damit für den
lokalen Runner geschlossen.

## Tests

Die LQ-420-Tests senden echte SIGINT- und SIGTERM-Signale an den laufenden
Testprozess innerhalb eines kontrollierten Runnergates.

Ein weiterer Test startet einen echten Kindprozess, der den Elternprozess mit
SIGTERM unterbricht und danach schlafen würde.

Der Adapter beendet dessen Prozessgruppe, der Runner entfernt den Workspace
und es bleibt kein finales Ziel.

Zusätzlich wird die Wiederherstellung der ursprünglichen Signalhandler nach
Erfolg und Ablehnung geprüft.

## Aussagegrenzen

Die Tests sind synthetische Prozess- und Signalprüfungen.

Sie bauen kein Wheel, keine Source Distribution und kein Operationsbundle.

Sie starten keinen PostgreSQL-Server und liefern keinen Packagingnachweis.

Die Signalgrenze autorisiert keine externe Aktion.

## Nichtziele

LQ-420 ergänzt keinen Scheduler, Daemon, Retry oder persistenten
Attempt-Store.

Der Slice installiert keine Dependency und ändert weder CI noch Packaging.

Er signiert, promotet, publiziert oder deployed nichts.

Er erstellt keinen Branch und staged, committed oder pusht nichts.

## Nächster Slice

LQ-421 sollte den nun geschlossenen lokalen Preflightpfad als Ganzes auf
Code-, Test-, Doku- und Roadmapdrift auditieren.

Danach ist statt weiterer Funktion die Herstellung einer geeigneten sauberen
Buildlaufzeit und eines reviewten Commits erforderlich.
