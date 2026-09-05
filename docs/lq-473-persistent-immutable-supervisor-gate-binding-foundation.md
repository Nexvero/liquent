# LQ-473 — Persistent Immutable Supervisor Gate Binding Foundation

## Ergebnis

LQ-473 schließt den LQ-472-Restartblocker mit einer leeren persistenten
Gatebinding-Foundation, einem Storeport und read-only Lookupport.

Der Slice implementiert noch keinen Persistenzadapter oder Supervisorservice.

## Revision 0033

Revision `20260825_0033` folgt linear auf `20260824_0032`.

Sie ergänzt genau zwei leere Tabellen.

Es gibt keinen Seed, Backfill oder Adoption bestehenden Dateibestands.

Head und Releasebundle werden auf 33 Migrationen synchronisiert.

## Gatebinding-Tabelle

`manifest_handoff_supervisor_gate_bindings` besitzt genau eine Zeile je
Supervisorhandle.

Der Handle ist Primärschlüssel und Fremdschlüssel auf eine bestehende
Runtimebinding.

Damit kann keine Gatebinding vor Journaljob und Runtimebinding entstehen.

Eine zweite Binding desselben Handles ist ausgeschlossen.

## Keine doppelte Control-Directory-Spalte

Control-Directory-ID bleibt unveränderlicher Bestandteil der bestehenden
Runtimebinding.

Die Gatebinding referenziert denselben Runtimehandle und dupliziert den Wert
nicht.

Der spätere Adapter rekonstruiert die Startbindung aus Gate- und Runtimezeile.

Cross-Directory-Rebinding ist dadurch ausgeschlossen.

## Profil

Profil ist ausschließlich `writer` oder `recovery`.

Ein freier Profilstring wird durch Checkconstraint abgelehnt.

Der Adapter muss das Profil zusätzlich gegen die Journalregistrierungsart
prüfen.

Schema allein behauptet keine Cross-Table-Profilkonsistenz.

## Gated-Observation-ID

Die vorab reservierte Gated-Observation-ID ist nicht leer und global eindeutig
in ihrer Spalte.

Sie wird vor Ready-Publikation dauerhaft gebunden.

Sie ersetzt noch keinen `prepared_gated`-Journalfakt.

Ein Retry muss exakt dieselbe ID verwenden.

## Terminal-Observation-ID

Die Terminal-Observation-ID ist ebenfalls nicht leer und eindeutig.

Sie bleibt bereits vor Prozessstart für spätere Envelope- und
Journalkorrelation auflösbar.

Gated- und Terminal-Observation-ID müssen innerhalb einer Binding verschieden
sein.

Reservierung behauptet keine Terminalität.

## Normalisierte Artefaktreservierungen

Ready-, Consumed- und Terminal-Artefakt-ID werden in einer getrennten
normalisierten Tabelle gespeichert.

Jede Artefakt-ID ist globaler Primärschlüssel.

Dadurch kann dieselbe ID weder in einer anderen Rolle noch in einem anderen Job
wiederverwendet werden.

Eine breite Bindingzeile könnte diese globale Cross-Role-Eindeutigkeit nicht
gleichwertig erzwingen.

## Geschlossene Reservierungsrollen

Die Tabelle erlaubt ausschließlich `wrapper_ready`, `release_consumed` und
`terminal_envelope`.

Je Handle und Rolle existiert höchstens eine Reservierung.

Alle drei Rollen sind für eine vollständig rekonstruierbare Startbindung
erforderlich.

Der spätere Store muss sie atomar gemeinsam schreiben.

## Warum Release-Token nicht vorab reserviert ist

Token-Artefakt-ID entsteht mit dem stabilen Releasecommand und gehört zur
konkreten Release-ID.

Sie ist nicht Teil der ursprünglichen Startbindung.

Nach Release-Commit wird ihre Publikation bereits in der bestehenden
Control-Artefakttabelle dauerhaft korreliert.

Release-Unknown verwendet dieselbe Release- und Token-ID.

## Fremdschlüssel

Gatebinding verlangt eine bestehende Runtimebinding desselben Handles.

Jede Artefaktreservierung verlangt die bestehende Gatebinding.

Es gibt kein Cascade-Delete.

Retention und Cleanup bleiben separate owner-kontrollierte Entscheidungen.

## Zeit

Gatebinding speichert genau eine serverseitige aware UTC Bindungszeit.

Artefaktreservierungen benötigen keine eigenen unterschiedlichen Zeiten, weil
sie atomarer Bestandteil derselben Binding sind.

Die Clock wird später konstruktiv injiziert und ist kein Requestfeld.

Retry behält die ursprüngliche Bindungszeit.

## Atomare Storesemantik

`bind_gate` akzeptiert ausschließlich die bestehende geschlossene
`StartManifestHandoffSupervisorGateWrapper`.

Der spätere Adapter schreibt Binding und genau drei Reservierungen in einer
Transaktion.

Exakter Retry liefert dieselbe rekonstruierte Startbindung.

Partielle Binding ist niemals Erfolg.

## Konflikt

Wiederverwendung von Handle, Observation-ID oder Artefakt-ID mit abweichender
Bindung liefert den feldlosen
`ManifestHandoffSupervisorGateBindingConflict`.

Es gibt kein Rebind, Update oder Last-write-wins.

Konflikt enthält keine konkrete ID oder Datenbankdetails.

Er erzeugt keine Datei- oder Enginewirkung.

## Neutrale Abwesenheit

Store darf `None` liefern, wenn der vorausgesetzte Runtime-/Journalbestand
autoritativ fehlt oder nicht zur Registrierung passt.

Lookup liefert `None` nur für autoritativ unbekannten Handle beziehungsweise
unbekannte reservierte Artefakt-ID.

Partielle, beschädigte oder mehrdeutige Binding ist technische
Unverfügbarkeit.

`None` autorisiert keine neue ID.

## Read-only Lookup

`resolve_gate` adressiert exakt einen Supervisorhandle.

`resolve_gate_artifact` adressiert exakt eine reservierte Artefakt-ID.

Beide rekonstruieren dieselbe vollständige Startbindung einschließlich
Control-Directory aus Runtime.

Lookup mutiert, publiziert und adoptiert nichts.

## Keine Tokenauflösung

Der Gatebinding-Lookup löst keine Release-Token-ID auf.

Token gehört zur bestehenden Control-Artefaktkorrelation und Release-ID.

Die Trennung verhindert, dass eine Vorabbindung eine Releasewirkung behauptet.

Release-Commit bleibt zwingend vor Token.

## Keine Authority

Store und Lookup akzeptieren keine Session, User-ID, Permission, Rolle im
Autorisierungssinn oder Allowentscheidung.

Gatebinding erteilt keine Writer- oder Recoveryfähigkeit.

Claim-/Owner- und Lifecycleprüfung bleibt in der Plattformcomposition.

Persistenz ist kein Authoritycache.

## Keine Prozess- oder Dateiwirkung

Die Foundation erstellt kein Control-Directory und publiziert kein Artefakt.

Sie erstellt, startet oder terminiert keinen Container.

Sie enthält keinen Hostpfad, Socket, PID, Command oder Timeout.

IDs sind ausschließlich interne Korrelationen.

## Keine Mutation

Es gibt keinen Update-, Delete-, Rotate- oder Rebindport.

Terminalisierung verändert die Gatebinding nicht.

Reservierungen bleiben mindestens bis zur persistenten Terminalkorrelation und
späteren Retentionentscheidung erhalten.

IDs werden nicht wiederverwendet.

## Keine Implementation oder Wiring

LQ-473 ergänzt Migration, Domainkonflikt und Ports, aber keinen SQL-Adapter.

Es gibt keinen Servicecomposer, Thread, Entry Point, CLI-, Route-, Compose-
oder Production-Wiring.

Die Tabellen starten leer.

Bestehende Jobs werden nicht automatisch migriert oder adoptiert.

## Tests

Fokussierte Tests belegen linearen Head, zwei leere Tabellen, Runtime- und
Binding-Fremdschlüssel, geschlossene Profile/Rollen, globale Artefakt-ID,
einmalige Handle/Rolle, fehlende Cascades, minimale Store-/Lookupports und
synchronisierte Migrationsgates.

## Nächster Slice

LQ-474 sollte den atomaren persistenten Gatebinding-Adapter mit exaktem Retry,
Konflikt und vollständiger read-only Rekonstruktion implementieren.

Danach kann die LQ-471-Serviceimplementation beginnen.
