# LQ-419 — Release Preflight Process Bounds and Retention

## Zweck

LQ-419 härtet die lokale Preflightkette gegen hängende Prozesse,
unbegrenzte Prozessausgaben, unbekannte Ausgänge und unsichere
Artefaktretention.

Der Slice erweitert keine Releaseauthority und aktiviert die Kette nicht
automatisch.

## Feste Prozessgrenzen

Jeder von LQ-416 gestartete Prozess erhält dieselben festen Obergrenzen:

- maximal 900 Sekunden Laufzeit;
- maximal 1.048.576 Bytes kombinierte Standardausgabe und Fehlerausgabe;
- zugleich maximal 1.048.576 Bytes je einzelner Ausgabestrom;
- geschlossenes `stdin`;
- eigene Prozesssession.

Diese Werte sind Implementierungskonstanten.

Der lokale CLI-Aufrufer kann sie nicht überschreiben.

## Private Ausgabepuffer

Standardausgabe und Fehlerausgabe werden nicht mit unbeschränkten
Speicherpipes gesammelt.

Beide Ströme laufen in private anonyme temporäre Dateien.

Erst nach eindeutig erfolgreichem Prozessende werden ihre Größen bestimmt.

Nur vollständige Ausgaben innerhalb der gemeinsamen Obergrenze werden in den
internen `CommandResult` gelesen.

Teiloutput wird niemals als erfolgreiche Messung akzeptiert.

## Timeout und Prozessgruppe

Jeder Prozess startet in einer neuen Session.

Bei Timeout sendet der Adapter `SIGKILL` an die gesamte Prozessgruppe.

Falls der Gruppenkill technisch fehlschlägt, wird zusätzlich der direkte
Prozesskill versucht.

Danach wird begrenzt auf Prozessende gewartet.

Timeout, Killfehler oder weiterhin unklarer Ausgang enden immer detailfrei als
Gateablehnung.

Es gibt keinen automatischen Retry.

LQ-420 ergänzt darauf aufbauend die gleiche Prozessgruppenbeendigung für
asynchrone Operatorunterbrechungen des übergeordneten Preflights.

## Nicht erfolgreiche Prozessausgänge

Ein von null verschiedener Exitcode wird abgelehnt.

Ein durch Signal beendeter Prozess wird ebenfalls als nicht erfolgreicher
Exitcode abgelehnt.

Übergroße Einzel- oder Gesamtausgabe wird erst nach Prozessende erkannt und
detailfrei abgelehnt, ohne die Ausgabe in Evidenz zu kopieren.

Interne stderr-Inhalte, DSNs, Pfade und Prozessargumentdetails werden nicht im
Exceptiontext sichtbar.

## Unbekannter Ausgang

Ein Timeout oder Fehler während Start, Wait, Kill oder Ergebnislesung ist kein
neutraler Skip und kein Erfolg.

Der LQ-415-Runner stoppt bei dieser Ablehnung sofort.

Spätere Gates werden nicht ausgeführt und es entsteht kein
`controlled-preflight.json`.

Ein erneuter Lauf ist eine neue bewusste Operatorhandlung mit neuem, noch
nicht existierendem Zielverzeichnis.

## Fehlgeschlagene private Artefakte

Alle Build-, Installations-, Test- und Bundlezwischenstände liegen unter dem
privaten temporären LQ-415-Workspace.

Bei jeder Ablehnung entfernt der Runner diesen gesamten Workspace.

Fehlgeschlagene oder in ihrem Ausgang unbekannte Artefakte werden nicht als
Evidenz aufbewahrt, nicht publiziert und nicht in einen späteren Lauf
übernommen.

Die untere Retentionsgrenze für solche nicht autoritativen Zwischenstände ist
nur die Dauer des laufenden Preflights.

## Erfolgreiche Evidenzretention

Nach vollständigem Erfolg wird der private Workspace atomar an das explizite
Ziel verschoben.

Der Runner löscht oder rotiert dieses Ergebnis nicht automatisch.

Das Ziel bleibt owner-kontrollierte Evidenz, bis eine separate
Retentionentscheidung seine Entfernung autorisiert.

Ein vorhandenes, leeres, nicht leeres oder symbolisches Ziel wird nicht
wiederverwendet und nicht überschrieben.

Zielnamen und Evidenzpfade dürfen nicht als implizite Authority oder
Releasefreigabe interpretiert werden.

## Nichtwiederverwendung

Ein Zielverzeichnis gehört genau einem Preflightversuch.

Nach Erfolg bleibt es belegt.

Nach Fehler existiert das finale Ziel nicht; ein neuer Versuch muss dennoch
bewusst neu gestartet werden und erhält keine Fakten aus dem alten Versuch.

LQ-419 führt keine dauerhafte Attempt-ID-Persistenz ein.

Eine stärkere globale Namens-Nichtwiederverwendung benötigt eine separate
persistente Registry und liegt außerhalb dieses Slices.

## Tests

Die LQ-419-Tests belegen:

- vollständige kleine stdout-/stderr-Ausgabe;
- begrenzten Timeoutabbruch;
- Ablehnung von Exitfehlern;
- Ablehnung je Stream und kombiniert übergroßer Ausgabe;
- vollständiges Cleanup nach unbekanntem Gateausgang;
- unveränderte owner-kontrollierte Evidenz bei vorhandenem Ziel.

## Lokale Ausführungsgrenze

Die Tests verwenden nur kleine synthetische Kindprozesse.

Sie führen keinen Build, keine Testsuite, keine PostgreSQL-Verbindung und
keinen Bundlelauf aus.

Die LQ-414-Blocker für einen echten Preflight bestehen fort.

## Nichtziele

LQ-419 installiert keine Dependency und ändert weder Packaging noch CI.

Der Slice ergänzt keinen Entry Point, keine automatische Wiederholung, keinen
Scheduler und keine externe Retentionmutation.

Er signiert, promotet, publiziert oder deployed nichts.

Er erstellt keinen Branch und staged, committed oder pusht nichts.

## Nächster Slice

LQ-420 sollte die Prozessgrenzen und Cleanupsemantik end-to-end mit der
detailfreien LQ-417-Oberfläche reauditieren.

Dabei sind insbesondere Signalweitergabe, Operatorabbruch und die Aussage
`kein Erfolgsartefakt nach unbekanntem Ausgang` statisch und synthetisch zu
schließen, ohne den echten Packaginglauf zu behaupten.
