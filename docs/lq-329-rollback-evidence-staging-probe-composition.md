# LQ-329 — Rollback Evidence Staging Probe Composition

## Ergebnis

LQ-329 komponiert den LQ-328-Inspector kontrolliert in
`liquent-staging-phase-probe` für die bestehende LQ-303-Phase `rollback`.

Die Phase bindet aktuelle Rollback-Evidence an dieselbe validierte
Staging-Run-Autorisierung wie alle anderen Probephasen und reduziert das
Ergebnis über die bestehende LQ-308-Grenze.

Sie startet keinen Prozess und führt insbesondere keinen Docker-, Restore-,
SQL- oder Rollbackeffekt aus.

## Zusätzliche Phaseneingaben

Für `--phase rollback` verlangt der Probe-Command zusätzlich genau:

- `--rollback-expectation-file`;
- `--rollback-evidence-file`.

Beide Pfade werden als `Path` übergeben und anschließend durch die owner-only
Dateigrenze des LQ-328-Inspectors gelesen.

Fehlt eine der beiden Dateien, endet die Probe vor jedem Prozesszugriff
technisch unavailable.

Die zwei Argumente sind bei jeder anderen Phase unzulässig. Dadurch können
private Rollbackinputs nicht unbeachtet an eine Image-, Compose-, Runtime-
oder Artifactprüfung angehängt werden.

## Gemeinsame Staging-Bindung

Vor der Rollbackentscheidung validiert die bestehende Probe weiterhin:

- die aktuelle owner-only Staging-Run-Autorisierung;
- den daraus abgeleiteten Projektnamen;
- den exakten SHA-256 des Composefiles;
- die private Runtime-Environmentdatei;
- die geschlossene Image-Environmentdatei;
- alle fünf unveränderlichen Image-Digestreferenzen;
- den autorisierten Application-Kandidatendigest.

Damit bleibt `rollback` Teil desselben geschlossenen Staginglaufs. Die Phase
besitzt keinen verkürzten alternativen Aufruf mit frei gewählten Source-,
Image- oder Projektwerten.

## Exakte Autorisierungsrelation

Die LQ-328-Erwartung muss zusätzlich exakt mit der geladenen
`StagingRunAuthorization` übereinstimmen:

- Run-ID;
- Source-Commit;
- Kandidaten-Application-Digest;
- Executoridentität;
- Autorisiereridentität;
- Beginn und Ende des UTC-Gültigkeitsfensters.

Diese Werte werden aus beiden Systeminputs abgeleitet und verglichen. Der
Caller liefert kein Allow-Boolean und keine frei interpretierte Rolle.

Ein strukturell gültiger, aber anders gebundener Erwartungsbestand ergibt das
neutrale Faktum `rollback_current=false`. Malformed oder technisch nicht
lesbare Inputs bleiben detailfrei unavailable.

## Inspector-Aufruf

Nach erfolgreicher gemeinsamer Bindung ruft die Composition ausschließlich
den reinen LQ-328-Inspector mit Erwartungsdatei, Evidencedatei, geladener
Staging-Autorisierung und derselben injizierten Uhr auf.

Der Inspector prüft Hash, geschlossene JSON-Struktur, Evidencebindung,
Rollbackziel, getrennte Identitäten, Status und Frische erneut.

Es gibt keinen zweiten Parser mit schwächeren Regeln, keinen Environment-
Fallback, stdin-Payload, Pfad aus JSON oder übersprungenen Hashvergleich.

## Kein Prozess- oder Dockereffekt

Die `rollback`-Verzweigung wird vor Erzeugung des lokalen Prozessrunners
abgeschlossen.

Weder das gebundene Docker-Executable noch Compose wird ausgeführt. Es gibt
kein `docker inspect`, `docker compose`, `docker run`, Shellprogramm oder
externes Inspector-Executable in dieser Composition.

Die bestehenden Docker- und Composepfade werden nur als Teil der gemeinsamen
Runbindung validiert. Daraus entsteht kein Besitz- oder Mutationsrecht.

## Neutrale LQ-308-Reduktion

Der kanonische LQ-328-Output wird als erfolgreiche begrenzte lokale
Beobachtung modelliert und durch `reduce_phase_output("rollback", ...)`
geführt.

Damit gelten unverändert die geschlossenen Regeln:

- exakt Schema-Version eins;
- exakt Phase `rollback`;
- exakt Boolean-Fakt `rollback_current`;
- `true` wird `passed`;
- `false` wird `failed`;
- malformed Output wird unavailable.

Raw Evidence, Pfade, IDs, Digests, Zeitwerte und technische Fehlerdetails
werden nicht in das reduzierte Evidenceobjekt übernommen.

## Fehlersemantik

Eindeutige fachliche Nichtaktualität bleibt neutral `failed`. Dazu gehören
unter anderem stale Evidence, Hashabweichung, Bindungsmismatch und ein
unbrauchbares Rollbackziel.

Dateirechtefehler, Duplikatschlüssel, beschädigtes JSON, ungültige Typen oder
interne Reduktionsfehler werden detailfrei zu
`staging_read_only_probe_cli_unavailable`.

Die CLI schreibt bei technischer Nichtverfügbarkeit weder stdout noch stderr
und endet mit Exitcode zwei.

## Tests

Die LQ-329-Tests beweisen einen aktuellen gebundenen Pass ohne Prozessaufruf,
neutralen Fail bei Evidence- und Runbindungsmismatch sowie die Pflicht beider
Rollbackdateien.

Sie beweisen außerdem, dass andere Phasen Rollbackinputs vor Prozesszugriff
zurückweisen.

Die angrenzenden LQ-312-, LQ-315- und LQ-328-Tests bleiben unverändert grün.

## Bundle und Nichtziele

LQ-329 ergänzt weder Entry Point noch Operatormodul. Die Bundle-Gates bleiben
bei 30 Entry Points, 33 Operatormodulen, 27 Migrationen und Head
`20260819_0027`.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

Der Slice führt keinen Application- oder Datenbankrollback aus, prüft keine
Registry und erzeugt keine Backup- oder Restore-Evidence.

## Nächster Slice

LQ-330 sollte die mutierende `disposable_postgres`-Composition separat
implementieren. Sie muss die LQ-327-Isolationsvorbedingungen vor dem ersten
Docker-Effekt schließen und Unknown Outcomes ohne Retry oder Blind-Cleanup
erhalten.
