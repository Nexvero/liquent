# LQ-474 — Persistent Immutable Supervisor Gate Binding Adapter

## Ergebnis

LQ-474 implementiert die LQ-473-Store-/Lookupports gegen Revision 0033.

`DatabaseManifestHandoffSupervisorGateBindings` persistiert ausschließlich
Gateidentitäten und reservierte Artefaktrollen.

## Voraussetzung

Neue Binding verlangt einen bestehenden Journaljob und eine bestehende
Runtimebinding desselben Handles.

Runtime-Control-Directory muss exakt der Gatebindung entsprechen.

Journal-Capability muss exakt dem Writer-/Recoveryprofil entsprechen.

Fehlende oder nicht passende Voraussetzung liefert neutral `None` vor jeder
Insertwirkung.

## Atomare Binding

Gatebinding und drei Artefaktreservierungen werden in derselben
Datenbanktransaktion geschrieben.

Es gibt keinen erfolgreichen Zwischenzustand mit weniger als drei Rollen.

Ready, Consumed und Terminal werden immer gemeinsam reserviert.

Die serverseitige aware UTC Bindungszeit entsteht genau einmal.

## Exakter Handle-Retry

Ein vorhandener Handle wird vollständig read-only rekonstruiert.

Verglichen werden Handle, Control-Directory, Profil, Ready-ID,
Gated-Observation-ID, Consumed-ID, Terminal-ID und
Terminal-Observation-ID.

Vollständige Gleichheit liefert die ursprüngliche Bindingform zurück.

Jede Abweichung liefert den feldlosen Gatebinding-Konflikt.

## Occupied Observation

Vor neuer Binding werden Gated- und Terminal-Observation-ID gegen bestehenden
Bestand geprüft.

Belegte IDs führen zu Konflikt und nicht zu Rebind.

Die Datenbank-Uniqueconstraints bleiben letzte Race-Sperre.

Ein Integritätsrace wird detailfrei technisch vereinheitlicht.

## Occupied Artifact

Ready-, Consumed- und Terminal-Artefakt-ID werden gemeinsam gegen die globale
Reservierungstabelle geprüft.

Jede belegte ID führt zum detailfreien Konflikt.

Cross-Role- und Cross-Job-Wiederverwendung erzeugt keine zweite Binding.

Es gibt kein Last-write-wins.

## Drei Inserts

Nach der Gatebinding-Zeile werden exakt die Rollen `wrapper_ready`,
`release_consumed` und `terminal_envelope` geschrieben.

Rolle und passende ID stammen ausschließlich aus dem geschlossenen
Startbindingtyp.

Ein Caller liefert keinen freien Rollenstring.

Release-token wird weiterhin nicht vorreserviert.

## Transaktionsrollback

Fehler bei einer Reservierung rollt Binding und alle vorherigen
Reservierungen zurück.

Ein technisch unklarer Commit wird durch Retry desselben Handles vollständig
reconciliert.

Der Adapter erzeugt keine neuen IDs.

Partielle beschädigte Persistenz wird nicht automatisch repariert.

## Lookup nach Handle

`resolve_gate` liest Gatebinding, Runtime-Control-Directory und
Journal-Capability über denselben Handle.

Fehlender autoritativer Bestand liefert `None`.

Genau eine vollständige Binding wird rekonstruiert.

Mehrdeutigkeit oder beschädigte Struktur bleibt technische Unverfügbarkeit.

## Lookup nach Artefakt-ID

`resolve_gate_artifact` startet bei genau einer reservierten Artefakt-ID und
joint dieselbe Binding, Runtime und Journalregistrierung.

Er rekonstruiert immer die vollständige Startbindung mit allen drei Rollen.

Unbekannte ID liefert neutral `None`.

Lookup adoptiert oder publiziert kein Artefakt.

## Vollständige Rollenmatrix

Rekonstruktion verlangt exakt drei Reservierungszeilen.

Die Rollenmenge muss exakt Ready, Consumed und Terminal sein.

Doppelte oder unbekannte Rolle ist technische Unverfügbarkeit.

Eine partielle Binding wird niemals als vorhandener Retry zurückgegeben.

## Profilprüfung bei Read

Persistiertes Gateprofil wird bei jeder Rekonstruktion erneut gegen die
Journal-Capability geprüft.

Cross-Profile-Bestand scheitert fail-closed.

Das Profil wird anschließend in die geschlossene Engine-Profilenum
rekonstruiert.

Unbekannte Werte bleiben technische Unverfügbarkeit.

## Control-Directory-Rekonstruktion

Control-Directory wird ausschließlich aus der persistenten Runtimebinding
gelesen.

Die Gatebinding-Tabelle dupliziert keinen Pfad oder Directorywert.

Der rekonstruierte Startbindingtyp validiert die ID erneut.

Es findet kein Dateisystemzugriff statt.

## Zeitprüfung

Die persistierte Bindungszeit wird bei jedem Read als aware UTC validiert.

Sie wird nicht im Startbindingresultat ausgegeben, bleibt aber
Strukturinvariante der Persistenz.

Ungültige Clock oder beschädigte Zeit ist technische Unverfügbarkeit.

Retry schreibt keine neue Zeit.

## PostgreSQL-Serialisierung

PostgreSQL-Writes sperren Journaljob-, Runtime-, Gatebinding- und
Reservierungstabellen in einer festen Reihenfolge.

Damit werden konkurrierende Handle-, Observation- und Artefaktreservierungen
serialisiert.

Der Lock ist Adapterpolicy und kein Requestparameter.

Read-only Lookups nehmen keinen Write-Lock.

## SQLite-Grenze

SQLite bleibt die lokale Testgrenze und nutzt seine Transaktionsserialisierung.

Andere SQL-Dialekte werden fail-closed abgelehnt.

Es gibt keinen dialektspezifischen Fallback.

Productionfreigabe bleibt PostgreSQL vorbehalten.

## Fehlergrenze

Decode-, Clock-, SQL-, Lock-, Rollen- und Strukturfehler werden über die
bestehende `ManifestHandoffRegistryUnavailable` detailfrei vereinheitlicht.

Konkrete IDs, SQL, Constraints und Datenbankdetails verlassen den Adapter
nicht.

Neutrales `None` und fachlicher Konflikt bleiben davon getrennt.

LQ-474 benennt keinen neuen technischen Exceptiontyp.

## Keine Mutation

Der Adapter besitzt kein Update, Delete, Rebind oder Rotate.

Bindings und Reservierungen werden niemals überschrieben.

Terminalisierung verändert die Gatebinding nicht.

Retention und Cleanup bleiben separat.

## Keine Authority

Der Adapter akzeptiert keine Session, User-ID, Permission, Managementrolle
oder Allowentscheidung.

Gatebinding erteilt keine Capability.

Journal-Capability ist eine Profilinvariante, keine Plattformrolle.

Claim-/Ownerprüfung bleibt im Supervisorservice.

## Keine Datei- oder Prozesswirkung

Der Adapter erstellt kein Directory und liest oder publiziert keine Datei.

Er erstellt, startet, inspiziert oder terminiert keinen Container.

Er importiert keine Docker-, subprocess-, Socket- oder Dateibibliothek.

Persistenzkorrelation ist keine physische Wirkung.

## Kein Schema oder Wiring

LQ-474 ändert Revision 0033 nicht und fügt keine weitere Migration hinzu.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

Es gibt keinen Seed, Backfill, Servicecomposer, Entry Point, CLI-, Route-,
Compose- oder Production-Wiring.

## Tests

Fokussierte Prüfungen belegen Runtime-/Journalvoraussetzung, vollständigen
Retryvergleich, occupied Observation-/Artefaktsperren, atomare Drei-Rollen-
Inserts, vollständige Lookup-Rekonstruktion, Profilprüfung, Locks und fehlende
Datei-/Prozess-/Authoritywirkung.

## Nächster Slice

LQ-475 sollte die LQ-471-Prepare-Orchestrierung über Journal, Engine,
Runtimebinding, Gatebinding und Ready implementieren.

Release, Terminal und Terminate folgen danach in getrennten Slices.
