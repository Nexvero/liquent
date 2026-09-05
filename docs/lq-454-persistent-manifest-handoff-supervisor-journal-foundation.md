# LQ-454 — Persistent Manifest Handoff Supervisor Journal Foundation

## Ergebnis

LQ-454 schafft die additive persistente Foundation für das LQ-452-Journal.

Revision `20260824_0031` folgt linear auf `20260824_0030`.

Sie erzeugt zwei leere Tabellen ohne Seed oder Backfill.

## Journaljobs

`manifest_handoff_supervisor_journal_jobs` hält die unveränderliche
Registrierung eines Supervisorjobs.

Handle, Backendinstanz, Prepare-ID und Launch-Commit-ID sind nicht leer.

Prepare und Launch-Commit sind global eindeutig.

Ein Handle ist Primärschlüssel und wird nicht reassigned.

## Capability und Claim

Capability ist ausschließlich `writer` oder `recovery`.

Writer verlangt genau einen Execution-Claim und keinen Recovery-Claim.

Recovery verlangt genau einen Recovery-Claim und keinen Execution-Claim.

Die exakte Form wird durch eine Checkbedingung erzwungen.

## Owner- und Scopebinding

Jeder Job speichert nicht leere Owner- und Scopekorrelationen.

Diese Werte dokumentieren die unveränderliche Serviceanfrage, erteilen aber
keine Authority.

SessionPrincipal, Rolle, Permission und Allowboolean werden nicht gespeichert.

Der Journaladapter muss divergente Wiederverwendung ablehnen.

## Feste Prozessbindung

Source Root, Target Root und Handoffname werden als nicht leere feste
Prozessbindung gespeichert.

Der Service darf sie nach Registrierung nicht ersetzen.

Der spätere Adapter muss absolute, getrennte Roots und gültigen Namen über die
bestehenden Domaintypen rekonstruieren.

Die Tabellen enthalten kein freies Executable oder Command.

## Keine Plattform-Fremdauthorität

Die Journaltabellen bilden eine eigene autoritative Prozesshistorie.

Sie verwenden keine Fremdschlüssel, die Journalfortschritt von einer späteren
Plattformmutation abhängig machen.

Die Plattformkorrelation wird über stabile IDs verglichen.

Eine gemeinsame Datenbankplatzierung erzeugt keine gemeinsame Authority.

## Transitionstabelle

`manifest_handoff_supervisor_journal_transitions` hält ausschließlich
append-orientierte Übergänge.

Jede Transition besitzt stabile ID, Handle, Capability, positive Sequenz,
geschlossene Art und aware UTC Beobachtungszeit.

Handle und Capability referenzieren gemeinsam genau einen Journaljob.

## Geschlossene Übergangsarten

Die Tabelle erlaubt exakt:

- `launch_committed`;
- `prepared_gated`;
- `release_committed`;
- `running`;
- `termination_requested`;
- `terminal_observed`.

`prepare_registered` liegt als unveränderliche Jobzeile vor.

## Eindeutige Historie

Transition-ID ist Primärschlüssel.

Handle und Sequenz sind gemeinsam eindeutig.

Handle und Übergangsart sind gemeinsam eindeutig.

Damit kann kein Job dieselbe Wirkungsklasse zweimal journalisieren.

## Kein überschreibbarer Zustand

Es gibt keine `current_state`-, `gate_released`-, `running`- oder
`terminal`-Statusspalte.

Der aktuelle View wird später aus Job und gültiger Transitionfolge projiziert.

Die Migration erzeugt keine Update- oder Upsertlogik.

Reihenfolge und erlaubte Vorgänger erzwingt der spätere Adapter.

## Nichtterminale Payload

Alle nichtterminalen Transitionen müssen Outcome, Filename, Digest und
Dateizahl leer lassen.

Release- oder Terminierungsrequest kann daher keinen fachlichen Erfolg
behaupten.

PID, Signal, Exitcode, stdout und stderr sind keine Spalten.

Timeout erzeugt keinen terminalen Payload.

## Terminale Capabilitymatrix

Writerterminalität ist auf die fünf LQ-446-Arten begrenzt.

Recoveryterminalität ist auf fünf LQ-427-Arten plus unknown begrenzt.

Capability und Outcome werden gemeinsam geprüft.

Ein Writeroutcome kann nicht als Recoveryresultat gespeichert werden.

## Faktenmatrix

`manifest_handed_off` verlangt Filename, 64-stelligen Digest und positive
Dateizahl.

`manifest_handed_off_pending_cleanup` verlangt dieselben Fakten.

`manifest_temporary_only` verlangt Fakten ohne Filename.

Alle übrigen terminalen Outcomes tragen weder Filename noch Manifestfakten.

## Terminal ist direkte Quelle

Eine terminale Zeile darf später nur aus direkter Supervisorbeobachtung
appendiert werden.

Das Schema selbst interpretiert Prozessabwesenheit nicht als Ende.

Terminal-ID ist die Transition-ID und bleibt stabil.

OS-Ressourcen dürfen erst nach gültigem terminalem Fakt entfallen.

## Nichtwiederverwendung

Primär-, Unique- und Fremdschlüsselbedingungen bilden die relationale
Untergrenze gegen ID- und Handlewiederverwendung.

Löschen und späteres Reassign bleibt vertraglich verboten.

Job- und Transitionfakten bleiben mindestens für Unknown-Auflösung,
Parallelitätsausschluss, Recovery und Audit erhalten.

Eine konkrete Frist bleibt separat.

## Neutrale Abwesenheit

Eine nie registrierte beliebige ID kann neutral fehlen.

Ein vorhandener Job ohne Folgetransition ist nicht terminal und nicht frei.

Eine Lücke oder widersprüchliche Historie ist keine neutrale Abwesenheit.

Neutralität autorisiert keinen zweiten Job.

## Detailfreie technische Unverfügbarkeit

Ungültige Capability-/Claimform, beschädigte UTF-8-IDs, unzulässige
Transitionfolge oder inkonsistente Terminalpayload bleiben detailfreie
technische Unverfügbarkeit.

LQ-454 benennt keinen neuen Exceptiontyp.

SQL-, Pfad-, PID-, Host- und Produktdetails verlassen die Grenze nicht.

## Kein Seed und Backfill

Beide Tabellen sind nach Upgrade leer.

Bestehende Plattformkorrelationen, Attempts, Claims, PIDs, Logs und Dateien
erzeugen keinen Journaljob.

Altbestand wird nicht adoptiert oder terminalisiert.

Bestandsverankerung bleibt separat owner-kontrolliert.

## Downgrade

Der Downgrade entfernt zuerst Transitionen und danach Jobs.

Revision-0030-Tabellen werden nicht verändert.

Es gibt keine Datenkonvertierung oder kompensierende Mutation.

Die Migration bleibt linear.

## Migration-Gates

Der erwartete Head ist `20260824_0031`.

Das Release-Bundle erwartet 31 lineare Migrationen.

Roadmap, Headtest und Inventarzähler nennen denselben Stand.

Die Historie besitzt weiterhin genau einen Head.

## Keine Implementation

LQ-454 implementiert keinen Journaladapter, Service, Prozesswrapper,
Gatekanal oder IPC-Transport.

Es ergänzt keine Domainklasse oder Portsignatur.

Es gibt kein CLI-, Compose-, CI-, Deployment- oder Production-Wiring.

LQ-439 und LQ-451 bleiben unverändert.

## Tests

Fokussierte statische Tests belegen lineare leere Revision, zwei Tabellen,
unveränderliche Jobbindung, geschlossene Capability-/Claimform, eindeutige
append-orientierte Transitionen, terminale Outcome-/Faktenmatrix und
synchronisierte Migration-Gates.

## Nichtziele

LQ-454 implementiert keine Journaltransaktion, Zustandsprojektion,
Serviceauthentisierung oder Prozessprimitive.

Adapter, Serviceprozess, Plattformcomposition, Bestand, Cleanup und Retention
bleiben separate Slices.

## Nächster Slice

LQ-455 sollte den persistenten Journaladapter mit exakten idempotenten Retries,
strikter Vorwärtszustandsmaschine und read-only Writer-/Recoveryinspection
implementieren.

Der tatsächliche Supervisorservice folgt danach separat.
