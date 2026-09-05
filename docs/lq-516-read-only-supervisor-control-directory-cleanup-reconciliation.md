# LQ-516 — Read-Only Supervisor Control-Directory Cleanup Reconciliation

## Ergebnis

LQ-516 implementiert die sichere Reconciliation für nach Crash verbliebene
`write_claimed`- und bestehende `outcome_unknown`-Cleanup-Attempts.

Sie führt keine physische Mutation und keinen zweiten Cleanupversuch aus.

## Historischer Claimlookup

Ein neuer minimaler
`ManifestHandoffSupervisorControlDirectoryCleanupWriteClaimLookup` löst
ausschließlich nach interner Attempt-ID auf.

Er liefert den vollständigen historischen Claimed-Wert oder neutral `None`.

Der Lookup besitzt keine Claim-, Outcome-, Reconciliation- oder Dateimutation.

## Persistente Rekonstruktion

Der LQ-511-Adapter verbindet Claimzeile und Attempt über Attempt- und
Directory-ID.

Er akzeptiert historische Claims nur für `write_claimed`, `outcome_unknown`,
claimgebundenes `completed` oder `reconciled`.

Preflight-, Clearance-, Claim-, Attempt- und Directory-ID sowie Prepared-,
Claim- und Attemptzeiten werden vollständig rekonstruiert und validiert.

## Kein historisches Authoritygrant

Der Claimlookup beweist nur, welcher irreversible Versuch persistent gebunden
wurde.

Er reaktiviert keine Managementauthority und öffnet keine neue Wirkung.

SessionPrincipal, Membership, Rolle und caller-gelieferte Allowentscheidung
werden nicht akzeptiert.

## Lokaler read-only Inspector

`SafeLocalManifestHandoffSupervisorControlDirectoryCleanupReconciliation`
implementiert ausschließlich den bestehenden physischen Reconciliation-Port.

Er akzeptiert nur den Attempt-/Directory-gebundenen bestehenden
Reconciliationrequest.

Root, Leaf, Handle, Pfade, Namen und erwarteter Ausgang werden intern
aufgelöst.

## Zulässige Attemptzustände

Nur ein aktuell `write_claimed` rekonstruierter Claimed-Wert oder ein
vollständiger Reconciliation-required-Wert darf inspiziert werden.

Completed, reconciled, started, unbekannte oder cross-gebundene Attempts
liefern neutral beziehungsweise detailfreien Konflikt.

Der historische Claim muss zusätzlich exakt dieselbe Attempt- und Directory-ID
binden.

## Wiederverwendete Sicherheitsprüfung

Der Inspector verwendet die read-only Root-, Leaf-, Inventar-, Datei- und
Codec-Prüfhelfer der LQ-513-Grenze.

Dadurch gelten identische `0700`-Root-/Leaf-, No-follow-, Owner-, Device- und
Inodeanforderungen.

Artefakte müssen weiterhin reguläre private `0600`-Single-Link-Dateien sein
und kanonisch dem persistenten Record entsprechen.

## Keine Wiederverwendung der Mutation

Der Inspector ruft niemals `remove_control_directory` auf.

Er verwendet weder `unlink`, `rmdir`, `mkdir`, `rename`, `replace`, `chmod`,
`chown`, `truncate` noch `fsync`.

Geöffnete Descriptoren werden ausschließlich gelesen und geschlossen.

## Absent

Fehlt das exakte persistierte Leaf unter einem erneut sicher gebundenen Root,
ist die physische Klassifikation `absent`.

Absent behauptet nicht, ob die Entfernung vollständig durch LQ-513, teilweise
durch einen Crash oder bereits vorher geschah.

Es erlaubt nur den terminalen Reconciliationausgang für denselben Attempt.

## Present

Ein vorhandenes Leaf ist nur `present`, wenn es vollständig und unverändert
dem gesamten aktuellen persistenten Artefaktset entspricht.

Alle Namen, Dateien, Bytes und Records müssen wie vor dem ursprünglichen
Cleanup gebunden sein.

Present autorisiert keinen Retry desselben Claims oder Attempts.

## Conflict

Unsicheres Leaf, unbekannter oder partieller Bestand, fehlende belegte Datei,
zusätzlicher Name, Symlink, Hardlink, Spezialdatei oder nichtkanonische Bytes
werden physisch als `conflict` klassifiziert.

Der Inspector repariert, vervollständigt oder entfernt nichts.

Der geschlossene Inspection-Wert enthält keine internen Details.

## Abschlussrevalidierung

Nach der physischen Klassifikation werden aktueller Attempt, historischer
Claim, Retired-Ziel und vollständige Artefaktrecordmenge erneut aufgelöst.

Jede Drift beendet als detailfreier Cleanupkonflikt statt eine veraltete
Inspection auszugeben.

Inspectionzeit ist intern erzeugte aware UTC und nicht vor `claimed_at`.

## Controlled Reconciliation

`ControlledManifestHandoffSupervisorControlDirectoryCleanupReconciliation`
implementiert den bestehenden High-Level-Reconciliation-Port.

Sie verbindet Crashsicherung, genau eine read-only Inspection und den
persistenten terminalen Reconciliationübergang.

Es gibt keinen physischen Cleanupaufruf.

## Crashzustand write_claimed

Findet die Composition einen vollständigen `write_claimed`-Wert, behandelt sie
ihn konservativ als möglicherweise bereits wirksam.

Sie persistiert zuerst über LQ-514 denselben claimgebundenen Unknown-Effekt.

Erst nach erfolgreichem `outcome_unknown`-Commit beginnt die read-only
Dateisysteminspection.

## Warum zuerst Unknown

Ein Prozessabbruch kann zwischen physischem Systemcall und LQ-514-Commit
geschehen sein.

`write_claimed` beweist daher weder Wirkung noch Nichtwirkung.

Ein erneuter Remove wäre unsicher; die dauerhafte Unknown-Transition schließt
diesen Retrypfad vor jeder weiteren Beobachtung.

## Bestehendes outcome_unknown

Ein bereits vollständiger Reconciliation-required-Wert wird ohne erneute
Unknown-Mutation direkt inspiziert.

Attempt und Directory müssen dem Reconciliationrequest exakt entsprechen.

Andere Zustände werden nicht adoptiert.

## Genau eine Inspection

Die Composition ruft `inspect_control_directory_cleanup` an genau einer Stelle
und ohne Schleife auf.

Neutraler oder fachlich abweichender Ausgang eines bekannten Attempts wird
nicht als Abwesenheit normalisiert.

Ein fremder Inspectiontyp ist technische Unverfügbarkeit.

## Terminale Persistenz

Die geschlossene Inspectionklassifikation wird über den bestehenden
`record_cleanup_reconciliation`-Pfad atomar von `outcome_unknown` nach
`reconciled` persistiert.

Persistierter Attempt, Directory und Outcome müssen exakt der Inspection
entsprechen.

`absent`, `present` und `conflict` bleiben terminale historische Fakten für
diesen Attempt.

## Retry

Ein bereits reconciled Attempt wird von der High-Level-Composition nicht neu
inspiziert.

Die persistente Attemptauflösung kann seinen terminalen Wert separat
rekonstruieren.

Ein neuer physischer Cleanup benötigt einen neuen Attempt und eine neue
aktuelle Clearance; LQ-516 erzeugt beides nicht.

## Fehlergrenze

Unbekannter Attempt bleibt neutral vor erwarteter Bindung.

Cross-Bindings und unzulässige bekannte Zustände bleiben detailfreier
Cleanupkonflikt.

Lookup-, Descriptor-, Clock-, Codec-, SQL- und Infrastrukturfehler bleiben
detailfreie technische Unverfügbarkeit.

LQ-516 benennt keinen neuen Exceptiontyp.

## Keine Schema- oder Productionwirkung

LQ-516 ergänzt keine Tabelle, Migration, Spalte, Seedzeile oder neue
Zustandsausprägung.

Es gibt keine Route, CLI, Worker-, Timer-, Startup-, Shutdown-, Appfactory-,
Compose- oder Productionverdrahtung.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Fokussierte Prüfungen belegen historische Claimrekonstruktion, ausschließlich
read-only absent/present/conflict-Inspection, Unknown vor Crashinspection,
genau einen Inspect-Aufruf, terminale Persistenz und fehlenden Remove-/Retrypfad.

## Nächster Slice

LQ-517 sollte Cleanup-Execution und Reconciliation explizit opt-in mit den
persistenten und lokalen Adaptern verdrahten.

Automatische Planung, Batchcleanup und Productionaktivierung bleiben dabei
geschlossen.
