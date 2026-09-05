# LQ-514 — Claim-Bound Persistent Physical Cleanup Outcomes

## Ergebnis

LQ-514 implementiert die persistente claimgebundene Abschlussgrenze für die
physischen LQ-513-Ausgänge Removed und Unknown.

Der Slice führt selbst keine Dateisystemoperation aus.

## Eigener Outcome-Port

`ManifestHandoffSupervisorControlDirectoryCleanupPhysicalOutcomeStore`
besitzt ausschließlich
`persist_control_directory_cleanup_physical_outcome`.

Der Port akzeptiert nur
`RemovedManifestHandoffSupervisorControlDirectory` oder
`UnknownManifestHandoffSupervisorControlDirectoryCleanupEffect`.

Freie Statusstrings, Allowbooleans, Pfade und ungebundene IDs sind
ausgeschlossen.

## Ein persistenter Adapter

Der bestehende
`DatabaseManifestHandoffSupervisorControlDirectoryCleanup` implementiert den
neuen Port zusätzlich zu seinen bisherigen Decision- und Attemptgrenzen.

Dadurch verwendet Outcome-Persistenz denselben geschlossenen
Attemptzustandsautomaten und dieselbe technische Fehlergrenze.

Es entsteht keine zweite Outcome-Tabelle oder parallele Wahrheit.

## Autoritative Unbekanntheit

Eine unbekannte Attempt-ID liefert neutral `None`.

Sobald ein Attempt vorhanden ist, werden Directory, Zustand und Claimbindung
vollständig geprüft.

Cross-Directory-, Cross-Claim- und falsche Zustandsbindungen liefern den
detailfreien Cleanupkonflikt.

## Nur write_claimed

Ein neuer physischer Outcome darf ausschließlich einen Attempt im Zustand
`write_claimed` abschließen.

Started besitzt noch keine physische Wirkung; Outcome-unknown, Completed und
Reconciled werden nicht als neue Wirkungseingänge adoptiert.

Die Claimzeile muss vollständig rekonstruierbar sein.

## Exakte Claimbindung

Claim-ID, Attempt-ID und Directory-ID des physischen Outcomes müssen dem
persistenten Claimed-Wert exakt entsprechen.

Die bedingte SQL-Mutation verlangt zusätzlich eine existierende Claimzeile mit
derselben zusammengesetzten Bindung.

Eine bekannte Attempt-ID allein reicht nicht für Removed.

## Removed-Transition

Ein bestätigtes physisches Removed überführt `write_claimed` atomar nach
`completed` mit geschlossenem Outcome `removed`.

`completed_at` ist exakt die aware UTC `removed_at`-Zeit des physischen
Ergebnisses.

Sie darf nicht vor der persistenten Claimzeit liegen.

Der persistierte Completed-Wert bindet dieselbe Attempt- und Directory-ID und
enthält keine Pfad- oder Artefaktdetails.

## Unknown-Transition

Ein physischer Unknown-Effekt überführt `write_claimed` atomar nach
`outcome_unknown`.

`unknown_at` wird intern aus der serverseitigen aware UTC Uhr erzeugt und darf
nicht vor `claimed_at` liegen.

Das Ergebnis ist ausschließlich der bestehende gebundene
Reconciliation-required-Wert.

Es behauptet weder Wirkung noch Nichtwirkung.

## Kein direktes Removed mehr

Die ältere generische `complete_cleanup_attempt`-Methode akzeptiert nun
ausschließlich `already_absent` aus `started`.

Ein `removed` ohne vollständigen physischen Claim-Outcome-Wert wird als
technisch ungültiger Aufruf abgelehnt.

Damit kann kein Caller den LQ-513-Nachweis durch Attempt-ID, Directory-ID und
freien Outcomeenum umgehen.

## Already-absent bleibt getrennt

`already_absent` beschreibt weiterhin den wirkungsfreien LQ-512-Absentpfad.

Er benötigt keinen Claim und darf ausschließlich `started` nach `completed`
überführen.

LQ-514 ändert diese neutrale physische Abwesenheitssemantik nicht.

## Bestehender Unknown-Helfer

Der ältere `record_cleanup_outcome_unknown`-Pfad kann nur einen bereits
`write_claimed` Attempt konservativ sperren.

Er kann keine Wirkung oder Removed behaupten und rekonstruiert intern den
vorhandenen Claim.

Der neue physische Outcome-Port ist die präzise Grenze für LQ-513-Ergebnisse.

## Bedingte atomare Mutation

Die persistente Transition und ihre Claim-Existenzprüfung erfolgen in einer
Datenbanktransaktion.

Die Mutation muss exakt eine `write_claimed`-Zeile treffen.

Null oder mehrere betroffene Zeilen sind technische Unverfügbarkeit und
werden nicht als Erfolg ausgegeben.

## Retry zuerst

Completed und Outcome-unknown werden vor jeder neuen Mutation erkannt.

Ein exakter Removed-Retry mit derselben Claimbindung und derselben
`removed_at`-Zeit rekonstruiert denselben Completed-Wert.

Ein exakter Unknown-Retry rekonstruiert denselben
Reconciliation-required-Wert.

Retry schreibt keine neue Zeit und startet keine physische Operation.

## Abweichender Retry

Andere Claim-ID, anderes Directory, andere Removed-Zeit, anderer Outcome-Typ
oder ein bereits `already_absent` abgeschlossener Attempt ist kein Retry.

Diese Fälle liefern detailfreien Konflikt.

Ein Unknown kann nicht nachträglich als Removed umgeschrieben werden und
Removed nicht zu Unknown zurückgesetzt werden.

## Keine Authority-Neuentscheidung

LQ-514 bewertet Management-, Retention-, Hold-, Recovery- oder
Referenzauthority nicht erneut.

Diese Entscheidung wurde vor Wirkung atomar im LQ-511-Claim getroffen.

Outcome-Persistenz zeichnet nur den bestimmten oder unklaren physischen
Ausgang dieses Claims auf.

Ein späterer Widerruf darf historische Wirkung nicht zu Nichtwirkung
umschreiben.

## Fehler nach physischer Wirkung

Kann der LQ-513-Ausgang wegen Datenbank- oder Prozessfehler nicht bestätigt
persistiert werden, darf die Composition den physischen Remove niemals erneut
aufrufen.

Der Attempt bleibt persistent `write_claimed` und muss wie ein möglicher
Unknown-Ausgang behandelt werden.

Die sichere Crash-/Compositiongrenze folgt im nächsten Slice.

## Fehlergrenze

Unbekannter Attempt bleibt neutral vor erwarteter Bindung.

Zustands- und Cross-Binding-Abweichungen bleiben detailfreier Cleanupkonflikt.

Defekte Claimhistorie, Clockfehler, SQL- und Infrastrukturfehler bleiben
detailfreie technische Unverfügbarkeit.

LQ-514 benennt keinen neuen Exceptiontyp.

## Keine neue Persistenzstruktur

LQ-514 verwendet ausschließlich die bestehenden LQ-493-/LQ-511-Tabellen und
Constraints.

Es ergänzt keine Tabelle, Migration, Spalte, Seedzeile oder SQL-Datenklasse.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Keine physische oder operative Wirkung

Der Adapter importiert weder `Path` noch `os` und ruft kein Preflight, Unlink,
Rmdir oder Reconciliationverfahren auf.

Es gibt keine Route, CLI, Worker-, Timer-, Startup-, Shutdown-, Service- oder
Productionverdrahtung.

## Tests

Fokussierte Prüfungen belegen den minimalen Outcome-Port, exakte Claimbindung,
Removed-/Unknown-Transitionen, serverseitige monotone Unknown-Zeit,
wirkungsfreies Already-absent, Retry-first und fehlende Datei-/Schemawirkung.

## Nächster Slice

LQ-515 sollte Preflight, Absent-Abschluss, Write-Claim, einmalige physische
Wirkung und sofortige LQ-514-Persistenz kontrolliert komponieren.

Read-only Reconciliation und Production-Wiring bleiben danach getrennte
Slices.
