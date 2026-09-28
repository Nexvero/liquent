# LQ-477 — Read-only Persistent Supervisor Inspect Orchestration

## Ergebnis

LQ-477 implementiert die read-only Rekonstruktion sichtbarer persistenter
Supervisorzustände für Writer und Recovery.

Inspect erzeugt keine Journal-, Datei-, Engine- oder Capabilitywirkung.

## Sichtbare Zustände

Der Service rekonstruiert ausschließlich `prepared_gated`, `running` und
`terminal_observed`.

Prepare-Registered, Launch-Committed und Release-Committed bleiben interne
Orchestrierungszustände und sind technisch unverfügbar.

Termination-Requested wird nicht in eine erfundene Releasezeit normalisiert.

## Neutrale Abwesenheit

Nur ein im profilspezifischen Journal autoritativ unbekannter Handle liefert
neutral `None`.

Fehlender erwarteter Runtime-, Gate-, Artefakt-, Datei- oder Enginebestand nach
gefundenem Journaljob ist technische Unverfügbarkeit.

Cross-Profile-Abwesenheit erteilt keine Sichtbarkeit.

## Persistente Bindungen

Jeder sichtbare Result verlangt ein Runtimebinding und eine vollständige
Gatebinding desselben Handles.

Control-Directory und Writer-/Recoveryprofil müssen vollständig
übereinstimmen.

Inspect adoptiert keinen Container und erzeugt keine neue ID.

## Ready-Grundlage

Alle drei sichtbaren Zustände verlangen den persistenten Readyrecord.

Ready-ID und Gated-Observation-ID müssen der Gatebinding entsprechen.

Der physische kanonische Readyrecord wird über Reader und Codec erneut geprüft.

Persistenz allein ersetzt keine vorhandenen unveränderten Bytes.

## Prepared

`prepared_gated` verlangt direkte Enginebeobachtung `running` für die
persistierte Container-ID.

Prepared wird aus Handle, Claim, Owner und persistierter Gated-Beobachtungszeit
rekonstruiert.

Ready erteilt weiterhin keine Capability.

## Running

`running` verlangt persistente Token- und Consumedrecords derselben
Journal-Release-ID.

Beide physischen Dokumente werden kanonisch gelesen und vollständig mit ihren
persistierten Fakten verglichen.

Zusätzlich muss dieselbe Engine-Container-ID direkt `running` sein.

## Terminal

`terminal_observed` verlangt den profilspezifischen geschlossenen
Journaloutcome, die gebundene Terminal-Observation-ID und den persistenten
Terminal-Envelope-Record.

Das physische kanonische Envelope muss exakt denselben Outcome tragen.

Die Engine muss denselben Container direkt als `exited` oder `dead` melden.

Trägt das Terminaljournal eine Release-ID, bleiben Token und Consumed ebenfalls
zwingende korrelierte Belege.

## Enginevergleich

Container-ID, Creation-ID, Image-Digest und Profil werden bei jeder Inspection
mit der Runtimebinding verglichen.

Engine-Running ersetzt kein Ready, Token oder Consumed.

Engine-Terminal ersetzt kein Envelope oder Journalterminal.

## Physische Artefakte

Readerzugriffe verwenden ausschließlich Control-Directory-ID und geschlossene
Rollen.

Artefakt-ID, Handle, Rolle, Digest, Bytezahl und Korrelations-ID müssen mit dem
persistenten Record übereinstimmen.

Inspect publiziert oder überschreibt keine Datei.

## Writer-/Recoverytrennung

`inspect_writer` akzeptiert nur den geschlossenen Inspectcommand und liest nur
das Writerjournal.

`inspect_recovery` verwendet entsprechend ausschließlich Recoverytypen.

Cross-Profile-Journal, Prozess oder Envelope wird nicht konvertiert.

## Keine Reconciliationwirkung

Inspect ruft keine Register-, Commit-, Record-, Bind-, Create-, Start-,
Release-, Execute-, Wait-, Terminate- oder Publishmethode auf.

Inkonsistenz wird gemeldet und nicht repariert.

Ein späterer Wirkungsslice muss seine Voraussetzungen erneut prüfen.

## Technische Unverfügbarkeit

Unvollständige Persistenz, beschädigte Dokumente, falsche Rückgabetypen und
Engine-/Codec-/Readerfehler werden über die bestehende detailfreie
`ManifestHandoffRegistryUnavailable`-Grenze vereinheitlicht.

LQ-477 benennt keinen neuen technischen Exceptiontyp.

## Keine Authority

Inspect akzeptiert keine Session, User-ID, Workspace-ID, Rolle, Permission
oder Allowentscheidung.

Persistente IDs und Artefakte erteilen keine allgemeine Authority.

Claim und Owner werden ausschließlich aus dem Journal rekonstruiert.

## Keine Retention oder Details

Inspect löscht keine Runtime-, Journal-, Gate- oder Artefaktfakten.

Resultate enthalten keine Container-ID, Control-Datei, Bytes oder Pfade.

Infrastrukturdetails verlassen die technische Grenze nicht.

## Kein Schema oder Wiring

LQ-477 ergänzt keine Migration, Tabelle, SQL- oder Portsignatur.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

Es gibt keinen CLI-, Route-, Compose- oder Production-Wiring-Entscheid.

## Tests

Fokussierte Prüfungen belegen die drei sichtbaren Zustände, neutrale unbekannte
Handles, vollständige Runtime-/Gatebindung, kanonische Artefaktprüfung,
direkte Enginebeobachtung, Terminalkorrelation und fehlende Wirkung.

## Nächster Slice

LQ-478 sollte die restart-sichere Terminalorchestrierung über Outcome,
Terminal-Envelope, persistierte Envelope-Fakten, Engineende und
Terminaljournal implementieren.

Terminate folgt danach separat.
