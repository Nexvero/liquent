# LQ-449 — Persistent Manifest Handoff Supervisor Correlation Foundation

## Ergebnis

LQ-449 schafft die additive relationale Plattformfoundation für die in
LQ-448 entschiedene Supervisor-Korrelation.

Revision `20260824_0030` folgt linear auf `20260824_0029`.

Die Migration erzeugt sechs leere Tabellen und weder Seed noch Backfill.

## Persistenzgrenze

Die Plattform persistiert fachliche Korrelationen zum externen
Supervisorjournal.

Sie persistiert keinen erfundenen aktuellen OS-, PID-, Container- oder
Prozessstatus.

Das Supervisorjournal bleibt autoritative Quelle für Gatewirkung, laufenden
Prozess und direktes terminales Ergebnis.

## Backendinstanzen

`manifest_handoff_supervisor_backends` hält eine stabile nicht leere
Backendinstanz-ID, `active` oder `inactive` und die Provisionierungszeit.

Die ID ist weder Hostname noch Socket-, Container- oder Deploymentname.

Inaktive Backendinstanzen müssen spätere Entscheidungen fail-closed sperren.

Die Tabelle erzeugt keine initiale Instanz.

## Prepare-Reservierungen

`manifest_handoff_supervisor_preparations` reserviert eine stabile Prepare-ID
vor jedem Backendaufruf.

Sie bindet genau eine Backendinstanz, genau eine Capability, genau einen Claim,
genau einen Owner und die Reservierungszeit.

Die Capability ist ausschließlich `writer` oder `recovery`.

## Exakte Claimform

Writer bindet genau einen Execution-Claim und keinen Recovery-Claim.

Recovery bindet genau einen Recovery-Claim und keinen Execution-Claim.

Eine Checkbedingung erzwingt Capability und Claimform gemeinsam.

Beide Claimspalten besitzen ihre bestehenden Fremdschlüssel.

## Ein Prepare je Claim

Execution- und Recovery-Claim sind jeweils eindeutig.

Ein unklarer Backendaufruf kann daher nicht durch eine zweite
Prepare-Reservierung für denselben Claim ersetzt werden.

Retry und Reconciliation müssen dieselbe Prepare-ID verwenden.

Leaseablauf öffnet keine neue Reservierung.

## Ownerbindung

Jede Prepare-Reservierung speichert die nicht leere Owner-ID.

Der spätere Adapter muss sie gegen den aktuellen Claimbestand prüfen.

Die Migration interpretiert Owner nicht als Actor, Session oder Authority.

Ein Ownerwert erteilt keine Prozessfähigkeit.

## Handlebindungen

`manifest_handoff_supervisor_handle_bindings` bindet einen nicht leeren
opaken Handle genau einmal an Prepare und Backendinstanz.

Prepare ist in der Handletabelle eindeutig.

Auch Backendinstanz und Handle sind als Paar eindeutig.

Es gibt kein Rebind und kein Handle-Reassignment.

## Getrennte Reservierung und Bindung

Prepare-Reservierung und Handlebindung sind getrennte append-orientierte
Fakten.

Damit kann eine vor dem Backendaufruf durable Prepare-ID ohne erfundenen
Handle existieren.

Ein späterer bestätigter Handle wird additiv gebunden.

Ein fehlender Handle beweist weder Nichtwirkung noch Prozessende.

## Releaseanforderungen

`manifest_handoff_supervisor_releases` bindet eine stabile nicht leere
Release-ID an genau einen vorhandenen Handle.

Der Handle ist eindeutig und kann höchstens eine Plattform-Releaseanforderung
besitzen.

Die Tabelle hält die Anforderungszeit, aber keinen caller-gelieferten
Gateerfolg.

Das Supervisorjournal bleibt Quelle der physischen Gatewirkung.

## Terminierungsanforderungen

`manifest_handoff_supervisor_terminations` bindet eine stabile nicht leere
Terminate-ID an genau einen vorhandenen Handle.

Auch hier ist der Handle eindeutig.

Die persistierte Anfrage bedeutet weder Signalzustellung noch Prozessende.

Ein Timeout erzeugt keinen terminalen Fakt.

## Terminale Korrelationen

`manifest_handoff_supervisor_terminal_observations` bindet eine stabile
terminale Observation-ID an genau einen Handle.

Ein Handle kann höchstens eine solche Korrelation besitzen.

`observed_at` ist die Plattform-Korrelationszeit, kein Callerzeitbeweis.

Das geschlossene direkte Ergebnis bleibt Sache des Supervisoradapters und
seines Journals.

## Keine Statusspaltenfiktion

Prepare, Handle, Release, Terminate und Terminal sind getrennte Tabellen.

Es gibt kein frei überschreibbares `current_state`, `gate_released`,
`running`, `terminal` oder `allowed`.

Spätere Adapter müssen die Faktenfolge validieren.

Tabellenanwesenheit allein erzeugt keine Wirkung.

## Fremdschlüssel

Prepare referenziert Backendinstanz und den passenden vorhandenen
Execution- oder Recovery-Claim.

Handle referenziert Prepare und dieselbe Backendinstanz über einen
zusammengesetzten Fremdschlüssel.

Release, Terminate und Terminal referenzieren ausschließlich eine vorhandene
Handlebindung.

Es gibt keine kaskadierende Löschung.

## Nichtwiederverwendung

Primär- und Eindeutigkeitsbedingungen bilden die untere Grenze gegen
Wiederverwendung.

Backendinstanz-, Prepare-, Handle-, Release-, Terminate- und Terminal-ID dürfen
nicht für andere Fakten reassigned werden.

Löschen und späteres Wiederverwenden ist durch den Vertrag verboten.

Eine konkrete Retentionfrist bleibt separat.

## Active und inactive

Der Backendstatus ist geschlossen auf `active` und `inactive`.

Die Migration definiert noch keinen Mutationsoperator.

Spätere Auflösung muss den aktuellen Status frisch lesen.

Fehlend, unbekannt oder inaktiv ist keine Start- oder Releasefreigabe.

## Neutrale Abwesenheit

Eine fehlende nicht erwartete Prepare-ID kann neutral sein und gibt keine
Backenddetails aus.

Eine reservierte Prepare-ID ohne Handle ist nicht automatisch neutral
erledigt.

Ein erwarteter unauflösbarer Handle ist keine terminale Abwesenheit.

Neutralität autorisiert keinen neuen Prozess.

## Detailfreie technische Unverfügbarkeit

Beschädigte Capability-/Claimform, divergente Ownerbindung, widersprüchliche
Backend-/Handlebindung und unauflösbare erwartete Supervisorfakten bleiben
detailfreie technische Unverfügbarkeit.

Die Migration benennt keinen neuen Exceptiontyp.

PID-, Host-, Socket-, Container- und Pfaddetails werden nicht gespeichert.

## Keine Authority

Die Tabellen enthalten weder Actorentscheidung noch SessionPrincipal, Rolle,
Allowboolean oder Authoritysnapshot.

Execution- und Recoveryauthority bleiben in LQ-443 und LQ-444.

Ein aktives Backend autorisiert keinen fachlichen Claim.

Revocation muss spätere fachliche Entscheidungen weiterhin sperren.

## Kein Supervisorjournal

Revision 0030 implementiert nicht das interne Journal des dedizierten
Supervisorservices.

Sie speichert weder Kindprozesspayload noch IPC-Nachricht, Exitcode, stdout
oder stderr.

Sie ersetzt keine direkte Gate- oder Terminalbeobachtung.

Die Servicefoundation folgt separat.

## Kein Backfill

Alle sechs Tabellen bleiben nach Upgrade leer.

Bestehende Attempts, Claims, Dateien, PIDs und Logs erzeugen keine
Backendinstanz, Prepare-ID oder Handlebindung.

Altattempts werden nicht als terminal oder recoverbar markiert.

Bestandsverankerung bleibt owner-kontrolliert und separat.

## Downgrade

Der Downgrade entfernt ausschließlich die sechs neuen Tabellen in umgekehrter
Abhängigkeitsreihenfolge.

Bestehende Tabellen aus Revision 0029 werden nicht verändert.

Es gibt keine Datenkonvertierung oder kompensierende Mutation.

## Keine Adapterentscheidung

LQ-449 ergänzt keine Domainklasse, Portsignatur oder Persistenzadaptermethode.

Es implementiert keinen Supervisorservice, Prozess, Start-Gate oder
IPC-Transport.

Es gibt kein CLI-, Compose-, Operator-, Route- oder Production-Wiring.

LQ-439 bleibt unverändert.

## Migration-Gates

Der erwartete Head ist `20260824_0030`.

Das Release-Bundle erwartet nun 30 lineare Migrationen.

Die technische Roadmap nennt denselben Head und dieselbe Anzahl.

Die Migrationshistorie bleibt linear und eindeutig.

## Tests

Fokussierte statische Tests belegen:

- lineare leere Revision 0030 nach 0029;
- genau sechs neue Korrelationstabellen;
- aktive/inaktive Backendinstanzen ohne Seed;
- exakte Writer-/Recovery-Claimform;
- höchstens ein Prepare je Claim und ein Handle je Prepare;
- höchstens eine Release-, Terminate- und Terminalkorrelation je Handle;
- Fremdschlüssel ohne Kaskadenlöschung;
- keine PID-, Prozessstatus-, Authority- oder Backfillspalten;
- synchronisierte Head-, Bundle- und Roadmap-Gates;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-449 implementiert keine Backendprovisionierung oder -deaktivierung.

Es persistiert keine Supervisorjournalzustände und führt keine
Backendoperation aus.

Typen, Ports, Adapter, Serviceprozess, Composition, Bestand, Cleanup und
Retention bleiben separate Slices.

## Nächster Slice

LQ-450 sollte geschlossene Plattformwerte und Ports für Backendinstanz-,
Prepare-, Handle-, Release-, Terminate- und Terminalkorrelation definieren.

Supervisorjournal und Prozessservice folgen danach separat.
