# LQ-479 — Persistent Supervisor Terminate Orchestration

## Ergebnis

LQ-479 implementiert durable-before-signal Termination für persistente Writer-
und Recoveryjobs.

Ein Engine-Signal ist niemals vor dem persistenten `termination_requested`-
Fakt zulässig.

## Eingang und Zustände

Writer und Recovery akzeptieren nur den geschlossenen Terminatecommand mit
Handle und stabiler Terminate-ID.

Unbekannte profilspezifische Handles bleiben vor Wirkung neutral `None`.

Prepared, Release-Committed, Running und exakter Termination-Requested-Retry
sind zulässig; Terminal wird read-only rekonstruiert.

## Launch-Committed-Sperre

Ein bloßer Launch-Committed-Job ohne dauerhaft korreliertes Ready wird vor
Signalwirkung abgelehnt.

Ohne Ready kann der bestehende Gatevertrag kein Terminal-Envelope tragen.

Der Service erzeugt kein Ready nach einer Terminateentscheidung und erfindet
keinen terminalen Ersatzpfad.

## Persistente Voraussetzungen

Runtime, Gate und Ready müssen Handle, Control-Directory, Profil, Ready-ID und
Gated-Observation-ID vollständig verbinden.

Ein freier Containername, PID oder Pfad wird nicht akzeptiert.

Persistente Divergenz wird nicht repariert oder überschrieben.

## Durable vor Signal

Vor dem ersten Stop-/Kill-Aufruf wird dieselbe Terminate-ID profilspezifisch
als `termination_requested` appendiert.

Ein unklarer Append wird mit derselben ID reconciliert.

Eine abweichende Terminate-ID ist kein Retry und liefert Konflikt.

## Enginewirkung

Erst nach bestätigtem Termination-Requested wird ausschließlich die persistente
Container-ID an die geschlossene Engine übergeben.

Signal und Graceperiod bleiben konstruktive Enginepolicy und sind keine
Callerparameter.

Annahme behauptet noch kein Ende.

## Direkte Terminalbeobachtung

Nach Annahme wartet der Service auf denselben Container.

Container-ID, Creation-ID, Image-Digest und Profil werden vollständig mit der
Runtimebinding verglichen.

Nur `exited` oder `dead` erlaubt die weitere Terminalkorrelation.

## Vor Release

Besitzt der Job keine persistierte Release-ID, bildet Termination nach
Engineende den geschlossenen profilspezifischen `outcome_unknown`-Ausgang.

Der Outcome trägt Handle, Claim, Owner und eine serverseitige aware UTC-Zeit.

Er erteilt weder Writer- noch Cleanupfähigkeit.

## Nach Release

Eine vorhandene Release-ID verlangt vollständige persistente Token- und
Consumedrecords sowie das kanonisch gelesene Token.

Fehlender oder partieller Released-Bestand ist technische Unverfügbarkeit und
wird nicht als Vor-Release normalisiert.

Aus Released, Prepared und Processrequest wird dieselbe Execution rekonstruiert.

## Outcome nach Signal

Für eine freigegebene Execution verwendet der Service ausschließlich den
bestehenden begrenzten profilspezifischen Outcome-Wait.

Er released oder executes die Capability nicht erneut.

Nur ein geschlossener Executed-Outcome darf fortgesetzt werden.

## Terminal-Envelope

Nach Engineende und geschlossenem Outcome publiziert der Gatewrapper das
kanonische Terminal-Envelope auf Basis von Ready oder Released.

Artefakt-ID und Terminal-Observation-ID stammen aus der persistenten
Gatebinding.

Envelopekonflikt erzeugt keinen Ersatzrecord.

## Persistenz und Wiederprüfung

Envelope-Digest und Bytezahl werden über den bestehenden Artefaktstore
persistiert.

Danach wird dasselbe Envelope über Reader und Codec kanonisch erneut geprüft.

Handle, Fakten, Observation-ID und Outcome müssen exakt übereinstimmen.

## Terminaljournal zuletzt

Die profilspezifische Terminaltransition folgt erst nach durablem
Termination-Requested, Engineende, geschlossenem Outcome, Envelope-Publikation,
persistierten Fakten und kanonischer Wiederprüfung.

Sie verwendet die stabile Gate-Terminal-ID.

Erst der Terminalview bildet den ServiceResult.

## Retry

Termination-Requested-Retry verwendet dieselbe Terminate-ID und Container-ID.

Die Enginegrenze behandelt bereits terminale Container idempotent.

Envelope und Journal verwenden dieselben IDs und kanonischen Bytes.

Terminal-Observed-Retry bleibt vollständig read-only.

## Fehler und Konflikte

Journal-, Runtime-, Engine-, Wrapper- und Artefaktkonflikte werden detailfrei
als Servicekonflikt vereinheitlicht.

Fehlender erwarteter Bestand und technische Fehler bleiben an der bestehenden
`ManifestHandoffRegistryUnavailable`-Grenze.

LQ-479 benennt keinen neuen Exceptiontyp.

## Keine Authority oder freien Signale

Der Command akzeptiert keine Session, Nutzer-, Workspace-, Rollen-, Permission-
oder Allowentscheidung.

Caller liefern weder Signal, Timeout, Graceperiod noch Container-ID.

Claim und Owner stammen ausschließlich aus dem Journal.

## Keine Wiederaufnahme oder Cleanup

Terminate startet, released oder executes keine Capability.

Es löscht keinen Container, kein Control-Artefakt und keine Persistenz.

Retention und Cleanup bleiben getrennt.

## Kein Schema oder Wiring

LQ-479 ergänzt keine Migration, Tabelle, SQL- oder Portsignatur.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

Es gibt keinen CLI-, Route-, Compose- oder Production-Wiring-Entscheid.

## Tests

Fokussierte Prüfungen belegen Ready-Voraussetzung, Journal-vor-Signal,
Engineannahme-vor-Wait, Vor-Release-Unknown, Released-Outcome-Wait,
Envelope-/Faktenkorrelation, Terminaljournal zuletzt und terminalen Retry.

## Nächster Slice

LQ-480 sollte die vier Teilservices für Prepare, Release, Inspect, Terminate und
interne Completion zu den bestehenden Writer-/Recovery-Serviceports
komponieren, ohne Production-Wiring vorwegzunehmen.
