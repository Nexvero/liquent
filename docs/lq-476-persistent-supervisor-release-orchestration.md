# LQ-476 — Persistent Supervisor Release Orchestration

## Ergebnis

LQ-476 implementiert die restart-sichere Releasefolge des persistenten
Manifest-Handoff-Supervisorservice für Writer und Recovery.

Der Slice beginnt ausschließlich bei einem persistent vorbereiteten Job und
endet mit Journal-Running sowie genau einer Capabilityübergabe.

## Servicegrenze

`PersistentManifestHandoffSupervisorReleaseService` bietet getrennte
`release_writer`- und `release_recovery`-Methoden.

Beide akzeptieren nur den geschlossenen LQ-472-Releasecommand.

Prepare, Inspect, Terminate und Terminalisierung bleiben getrennt.

## Keine Caller-Authority

Der Command enthält ausschließlich Handle, Release-ID, Token-Artefakt-ID und
Running-Observation-ID.

Session, Nutzer, Workspace, Rolle, Permission und Allowentscheidung werden
nicht akzeptiert.

Claim, Owner, Scope und Capabilityrequest stammen aus dem Journal.

## Neutrale Abwesenheit

Ein autoritativ unbekannter Handle liefert vor neuer Wirkung neutral `None`.

Nach vorhandenem Journaljob ist fehlender erwarteter Runtime-, Gate-, Ready-,
Token- oder Consumed-Bestand nicht neutral.

Unklare Wirkung wird nie als Nichtwirkung normalisiert.

## Zulässige Zustände

Release verarbeitet nur `prepared_gated`, `release_committed` und `running`.

Prepare-Zwischenzustände, Termination und Terminalität werden nicht released.

Eine andere persistierte Release-ID ist ein Servicekonflikt.

Der Caller kann keinen Zustand überspringen.

## Persistente Voraussetzungen

Runtimebinding, Gatebinding und persistierter Readyrecord werden vor dem
Release-Commit aktuell aufgelöst.

Handle, Control-Directory und Writer-/Recoveryprofil müssen vollständig
übereinstimmen.

Ready-ID, Rolle und Gated-Observation-ID müssen der Gatebinding entsprechen.

Divergenz wird weder adoptiert noch repariert.

## Release-Commit zuerst

Nur `prepared_gated` wird mit derselben stabilen Release-ID nach
`release_committed` überführt.

Kein Token wird vor bestätigtem durablem Commit publiziert.

Ein Commitretry verwendet dieselbe ID.

Eine neue Release-ID ist kein Reconciliationmechanismus.

## Kanonisches Token

Der Service konstruiert genau ein geschlossenes
`ManifestHandoffSupervisorReleaseTokenDocument`.

Artefakt-ID, Handle und Release-ID stammen ausschließlich aus Command und
persistentem Job.

Der bestehende Codec erzeugt kanonische Bytes und Fakten.

Der bestehende Publisher veröffentlicht atomar und ohne Overwrite.

## Tokenfakten

Nach dauerhafter Publikation werden Token-ID, Handle, Release-ID, Digest und
Bytezahl über den bestehenden Artefaktstore persistiert.

Exakter Retry akzeptiert ausschließlich denselben Record.

Tokenkonflikt verhindert Consumed und Journal-Running.

Tokenpublikation allein erteilt noch keine Capability.

## Wrapper liest Token

Der Gatewrapper liest das Token aus der festen Release-Token-Rolle des
gebundenen Control-Directory.

Gelesene Token-ID und Release-ID müssen exakt dem Command entsprechen.

Fehlendes Token nach erfolgreicher Publikation ist technische
Unverfügbarkeit.

Fremder oder beschädigter Bestand wird nicht ignoriert.

## Consumed-Ack

Nur der typisierte akzeptierte Tokenzustand darf an `publish_consumed` gehen.

Consumed-ID stammt aus der vorab persistenten Gatebinding.

Ack und Token tragen dieselbe Release-ID.

Wrapperkonflikt erzeugt kein Ersatzartefakt.

## Persistierte Consumed-Fakten

Consumed-ID, Handle, Release-ID, Digest und Bytezahl werden nach dauerhafter
Publikation separat persistiert.

Token und Ack bleiben zwei unveränderliche Records.

Ein Ack ohne passenden Tokenrecord ist keine Freigabe.

Erst der vollständige Released-Marker darf weitergegeben werden.

## Direkte Enginebeobachtung

Nach Token und Consumed wird ausschließlich die persistierte Container-ID
direkt inspiziert.

Container-ID, Creation-ID, Image-Digest und Profil müssen Runtime und Journal
entsprechen.

Nur direkt beobachtetes `running` erlaubt Journal-Running.

Ready, Token oder Ack ersetzen diese Beobachtung nicht.

## Journal-Running

Die stabile Running-Observation-ID wird erst nach persistiertem Token,
persistiertem Consumed und direktem Engine-Running appendiert.

Ein unklarer Append wird mit derselben ID reconciliert.

Eine abweichende bereits belegte Running-ID liefert Servicekonflikt.

Running wird niemals aus Dateibestand allein abgeleitet.

## Capabilityübergabe

Nach Journal-Running konstruiert der Service den profilspezifischen
Executionrequest aus Released, Prepared und dem persistenten Processrequest.

Der profilspezifische Executor wird genau einmal aufgerufen.

Ein unerwarteter Executorausgang bleibt technische Unverfügbarkeit und löst
keinen zweiten Aufruf aus.

Der terminale Outcome wird in diesem Slice noch nicht journalisiert.

## Running-Ergebnis

Release liefert einen profilspezifischen ServiceResult im Zustand `running`.

Handle, Claim und Owner stammen aus der persistenten Journalregistrierung.

`released_at` ist die persistierte Running-Beobachtungszeit.

Interne Token-, Datei- und Enginewerte werden nicht ausgegeben.

## Restart RELEASE_COMMITTED

Ein Restart verwendet dieselbe Release-ID und dieselbe Token-Artefakt-ID.

Kanonische Token- und Consumed-Publikation sind byteidentisch retrybar.

Persistente Artefaktrecords werden vollständig verglichen.

Es wird kein zweites Token und keine neue Ack-ID erzeugt.

## Restart RUNNING

Ein Running-Retry publiziert Token oder Consumed nicht erneut und ruft den
Capabilityexecutor nicht erneut auf.

Er rekonstruiert Ready und Released aus persistenten Records und liest das
kanonische Token über den Wrapper read-only.

Engine-Running wird erneut direkt geprüft.

Die Running-Observation-ID wird über den wirkungslosen idempotenten
Journalretry validiert; eine abweichende ID bleibt Konflikt.

## Kein zweiter Capabilitystart

Nur der Übergang dieses Aufrufs von Release-Committed zu Running führt zur
Executorübergabe.

Ein bereits Running beobachteter Job bleibt reine Reconciliation.

Technische Fehler nach Capabilityübergabe erlauben keine Wiederholung.

Spätere Outcomeprüfung verwendet die bestehenden LQ-469/LQ-470-Grenzen.

## Konfliktgrenze

Journal-, Runtime-, Engine-, Gatebinding-, Wrapper- und Filekonflikte werden
detailfrei als `ManifestHandoffSupervisorServiceConflict` vereinheitlicht.

Konflikte enthalten keine IDs, Pfade oder Infrastrukturdetails.

Es gibt kein Last-write-wins, Rebind oder automatisches Cleanup.

## Technische Unverfügbarkeit

Fehlender erwarteter Bestand, ungültige Rückgabetypen, Decode-, Publisher- und
Executorfehler verwenden die bestehende detailfreie
`ManifestHandoffRegistryUnavailable`-Grenze.

LQ-476 benennt keinen neuen technischen Exceptiontyp.

Ein technischer Fehler erzeugt keinen fachlichen Outcome.

## Keine Terminalisierung

Der Slice publiziert kein Terminal-Envelope und wartet nicht auf Engineende.

Er schreibt keine Terminaltransition.

Ein unmittelbar terminaler Executoroutcome wird nicht als vollständiger
Plattformabschluss ausgegeben.

Terminalkorrelation folgt separat.

## Keine Termination oder Cleanup

Der Service sendet kein Stop-, Kill- oder anderes Signal.

Er löscht keine Datei, Runtimebinding, Gatebinding oder Journalzeile.

Es gibt kein Timeout-, Polling-, Retention- oder Cleanupkommando.

Fehlerbehandlung erweitert keine Prozessfähigkeit.

## Kein Schema oder Wiring

LQ-476 ergänzt keine Migration, Tabelle, SQL- oder Portsignatur.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

Es gibt keinen Seed, Backfill, CLI-, Route-, Compose- oder Production-Wiring.

Die vollständige Servicecomposition bleibt separat.

## Tests

Fokussierte Prüfungen belegen Voraussetzung, Commit-vor-Token, Token-vor-
Consumed, persistierte Fakten, Engine-vor-Running, Running-vor-Executor,
Running-Retry ohne zweite Publikation/Execution, Konfliktgrenze und fehlende
Authority-, Terminal-, Terminate- und Wiringwirkung.

## Nächster Slice

LQ-477 sollte die read-only Inspect-Orchestrierung für Prepared, Running und
Terminal über Journal, Runtime, Gateartefakte, Engine und Outcomegrenzen
implementieren.

Terminalisierung und Terminate folgen danach getrennt.
