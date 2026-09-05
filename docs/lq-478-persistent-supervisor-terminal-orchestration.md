# LQ-478 — Persistent Supervisor Terminal Orchestration

## Ergebnis

LQ-478 implementiert die restart-sichere reguläre Terminalorchestrierung für
bereits laufende Writer- und Recoveryjobs.

Die interne Composition ergänzt keine öffentliche Portsignatur.

## Eingang

`complete_writer` und `complete_recovery` akzeptieren ausschließlich den
geschlossenen Handle-Inspectcommand.

Ein unbekannter profilspezifischer Handle bleibt neutral `None`.

Nur `running` und der idempotente Retry von `terminal_observed` sind zulässig.

## Terminal-Retry

Ein bereits terminaler Job wird ausschließlich über den read-only
LQ-477-Inspectservice rekonstruiert.

Er erzeugt keine Outcome-, Datei-, Engine- oder Journalwirkung.

Ein anderer nichtterminaler Journalzustand liefert Servicekonflikt.

## Released-Rekonstruktion

Der Runningjob verlangt Runtime-, Gate-, Ready-, Token- und Consumedrecords
desselben Handles und derselben Release-ID.

Der Wrapper liest das kanonische Token erneut read-only.

Aus persistenten Publikationsfakten wird derselbe Released-Marker
rekonstruiert; Token oder Ack werden nicht erneut publiziert.

## Executionbindung

Prepared, Released und der persistente Processrequest bilden exakt denselben
profilspezifischen Executionrequest wie LQ-476.

Handle, Claim, Owner und Profil werden durch die bestehenden Typen erneut
geprüft.

Es gibt keinen zweiten Capability-Release oder Execute-Aufruf.

## Outcome-Inspection

Der Service ruft genau einmal die profilspezifische read-only
Outcome-Inspection auf.

Ein Running-Outcome liefert den bestehenden Running-ServiceResult ohne weitere
Wirkung zurück.

Nur ein geschlossener Executed-Outcome darf Terminalisierung fortsetzen.

## Envelope vor Engineende

Der geschlossene Outcome wird über den bestehenden Gatewrapper als
kanonisches Terminal-Envelope publiziert.

Terminal-Artefakt-ID und Observation-ID stammen ausschließlich aus der
persistenten Gatebinding.

Wrapperkonflikt wird detailfrei zum Servicekonflikt.

## Persistierte Envelope-Fakten

Digest und Bytezahl des dauerhaft publizierten Envelopes werden vor jeder
Terminaltransition über den bestehenden Artefaktstore persistiert.

Exakter Retry akzeptiert denselben Record.

Divergenz wird nicht überschrieben oder repariert.

## Direkte Engine-Terminalität

Erst danach wartet der Service über die geschlossene Enginegrenze auf denselben
persistierten Container.

Container-ID, Creation-ID, Image-Digest und Profil werden vollständig
verglichen.

Nur `exited` oder `dead` ist terminal; Envelope allein genügt nicht.

## Kanonische Wiederprüfung

Nach Engineende wird das Terminal-Envelope erneut über Reader und Codec
kanonisch gelesen.

Artefakt-ID, Handle, Fakten, Terminal-Observation-ID und Outcome müssen dem
persistenten und beobachteten Bestand exakt entsprechen.

Beschädigter oder fehlender Bestand sperrt das Terminaljournal.

## Terminaljournal zuletzt

Die profilspezifische Terminaltransition wird erst nach geschlossenem Outcome,
persistiertem Envelope, direktem Engineende und kanonischer Wiederprüfung
appendiert.

Sie verwendet dieselbe stabile Terminal-Observation-ID.

Erst der bestätigte Terminalview bildet den ServiceResult.

## Restartpunkte

Crash nach Envelope-Publikation reconciliiert dieselben kanonischen Bytes.

Crash nach Envelope-Record verwendet denselben persistenten Record.

Crash nach Engineende liest denselben Container und dasselbe Envelope erneut.

Crash nach Journalterminal führt ausschließlich read-only Inspect aus.

## Konflikte und Fehler

Journal-, Runtime-, Engine-, Wrapper- und Artefaktkonflikte werden detailfrei
als Servicekonflikt sichtbar, soweit der Servicevertrag dies vorsieht.

Fehlender erwarteter Bestand und technische Fehler verwenden weiterhin
`ManifestHandoffRegistryUnavailable`.

LQ-478 benennt keinen neuen Exceptiontyp.

## Keine Authority oder Termination

Der Service akzeptiert keine Session, Nutzer-, Workspace-, Rollen-, Permission-
oder Allowentscheidung.

Er sendet kein Stop-/Kill-Signal und erzeugt keinen Terminate-Request.

Claim und Owner stammen ausschließlich aus dem Journal.

## Keine Wiederholung oder Cleanup

Terminalisierung released, startet oder executes die Capability nicht erneut.

Sie löscht weder Container noch Control-Artefakte oder Persistenz.

Retention und Cleanup bleiben getrennt.

## Kein Schema oder Wiring

LQ-478 ergänzt keine Migration, Tabelle, SQL- oder Portsignatur.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

Es gibt keinen CLI-, Route-, Compose- oder Production-Wiring-Entscheid.

## Tests

Fokussierte Prüfungen belegen Released-Rekonstruktion, read-only Outcome,
Running-Rückgabe, Envelope-vor-Engine, persistierte Fakten,
Envelope-Wiederprüfung, Terminaljournal zuletzt und terminalen read-only Retry.

## Nächster Slice

LQ-479 sollte die restart-sichere Terminate-Orchestrierung mit durablem
Termination-Requested vor Engine-Signal und anschließender konservativer
Terminalkorrelation implementieren.
