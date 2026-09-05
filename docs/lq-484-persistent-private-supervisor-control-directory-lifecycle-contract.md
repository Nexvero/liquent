# LQ-484 — Persistent Private Supervisor Control-Directory Lifecycle Contract

## Ergebnis

LQ-484 definiert den persistenten Lifecycle privater Supervisor-Control-
Directories als Voraussetzung des späteren Production-Wirings.

Der Slice implementiert noch keine Domainwerte, Ports, Tabelle oder
Dateisystemwirkung.

## System-of-Record

Die persistente Registry ist System of Record für Directory-ID, gebundenen
Supervisorhandle, internes Leaf und Lifecyclezustand.

Das Dateisystem ist System of Record für die physische Directoryexistenz und
deren Sicherheitsfakten.

Keines der beiden Systeme darf Fakten des anderen erfinden.

## Stabile Directory-ID

`ManifestHandoffSupervisorControlDirectoryId` bleibt eine stabile interne,
nicht wiederverwendbare Identität.

Sie wird genau einem Supervisorhandle zugeordnet.

Retirement, Terminalität oder spätere physische Entfernung erlauben keine
Neuzuordnung.

## Kein Pfadinput

Caller liefern keinen Rootpfad, relativen Pfad, Leafnamen oder Dateinamen.

Die Directory-ID wird niemals direkt als Hostpfad oder Pfadkomponente
interpretiert.

Slash-, Traversal-, Unicode- oder Normalisierungslogik gehört nicht in einen
Request.

## Privates Root

Das Root wird konstruktiv als absoluter process-eigener Pfad injiziert.

Es muss ein reales, nicht verlinktes Directory mit erwartetem Eigentümer und
Modus `0700` sein.

Rootanlage, Mount und Deploymentbesitz liegen außerhalb eines Jobrequests.

## Opaques internes Leaf

Für jede neue Reservation erzeugt die Registrygrenze ein kryptographisch
starkes opaques Leafmaterial.

Das Leaf ist nicht aus Handle, Directory-ID, Claim, Owner oder Handoffname
ableitbar.

Es wird persistent gebunden und niemals rotiert oder wiederverwendet.

## Geschlossene Zustände

Der Lifecycle besitzt genau `reserved`, `active` und `retired`.

Es gibt keinen freien Statusstring und kein Zurücksetzen.

Die einzige reguläre Folge ist Reserved zu Active zu Retired.

## Reserved

Reservation bindet Directory-ID, Handle und opaques Leaf dauerhaft, bevor eine
physische Directoryanlage erlaubt ist.

Exakter Retry liefert dieselbe Reservation.

Cross-Handle-, Cross-ID- oder Cross-Leaf-Wiederverwendung ist Konflikt.

## Keine Datei vor Reserved

Ohne bestätigten durablem Reserved-Fakt darf kein Leaf angelegt werden.

Ein unklarer Registrycommit wird zuerst mit denselben Identitäten aufgelöst.

Eine neue ID oder ein neues Leaf ist kein Reconciliationmechanismus.

## Physische Anlage

Nach Reserved darf ausschließlich das persistierte Leaf relativ zum bereits
geprüften Root angelegt werden.

Die Anlage verwendet Directorydescriptor, No-follow-Semantik, `0700` und
Directory-fsync.

Absolute Verkettung, chdir und tolerantes Symlink-Following sind unzulässig.

## Exakte Create-Retry

Existiert das Leaf bereits, werden Typ, Eigentümer, Modus, Link-/Symlinkfakten
und Rootzugehörigkeit vollständig geprüft.

Exakter sicherer Bestand ist idempotenter Erfolg.

Fremder, mehrdeutiger oder unsicherer Bestand ist Konflikt beziehungsweise
technische Unverfügbarkeit und wird nicht adoptiert.

## Active

Active darf erst nach erfolgreicher physischer Anlage und Root-Directory-fsync
persistiert werden.

Nur Active darf durch den späteren Control-Artefaktresolver als Directory
ausgegeben werden.

Reserved allein ist keine publizierbare Control-Grenze.

## Aktivierungsretry

Ein unklarer Active-Commit wird mit derselben Reservation und erneuter sicherer
Filesystemprüfung reconciliert.

Active ohne gültiges physisches Directory ist technische Divergenz.

Der Lifecycle erstellt in diesem Zustand kein Ersatzleaf.

## Read-only Auflösung

Resolution akzeptiert ausschließlich eine interne Directory-ID.

Unbekannte ID liefert neutral `None`.

Reserved, Retired, partielle Registry oder unsicherer physischer Bestand sind
nicht als aktives Directory auflösbar.

## Handlebindung

Ein zusätzlicher Lookup nach Supervisorhandle darf höchstens die eine
vollständige Lifecyclebindung liefern.

Runtime- und Gatecomposition müssen dieselbe Directory-ID vergleichen.

Ein Handle kann kein Directory eines anderen Jobs adoptieren.

## Retired

Retirement ist eine dauerhafte Registrytransition nach bestätigter terminaler
Korrelation und separater Lifecycleentscheidung.

Retired sperrt neue Artefaktpublikation und spätere Reaktivierung.

Es löscht das physische Directory nicht.

## Retirement vor Cleanup

Physische Entfernung darf niemals vor durablem Retired-Fakt stattfinden.

Retirement allein autorisiert noch keinen Cleanup; Retention, Beweisgrenzen und
separate Cleanupauthority müssen zusätzlich erfüllt sein.

LQ-484 definiert keinen Deletepfad.

## Restart RESERVED

Die Registry liefert dasselbe Leaf und dieselbe Bindung.

Fehlt das Leaf autoritativ, darf dieselbe sichere Anlage fortgesetzt werden.

Vorhandener exakter Bestand darf aktiviert werden; Divergenz bleibt gesperrt.

## Restart ACTIVE

Active wird read-only gegen dasselbe Root und Leaf geprüft.

Fehlender oder unsicherer Bestand ist technische Unverfügbarkeit und erzeugt
keine Neuanlage unter anderem Namen.

Es findet keine implizite Rotation statt.

## Restart RETIRED

Retired bleibt endgültig und nicht auflösbar für neue Control-Artefaktwirkung.

Vorhandener physischer Bestand bleibt bis separater Retention-/Cleanup-
Entscheidung erhalten.

ID, Handle und Leaf werden dauerhaft gegen Wiederverwendung aufbewahrt.

## Parallelität

Reservation, Aktivierung und Retirement müssen pro Directory-ID und Handle
serialisiert werden.

Globale Leaf-Eindeutigkeit bleibt eine persistente Invariante.

Filesystem-Races werden durch No-replace-Anlage und erneute Faktenprüfung
geschlossen.

## Neutrale Abwesenheit und Konflikt

Nur eine autoritativ unbekannte Directory-ID vor erwarteter Bindung ist
neutral.

Belegte Identitäten, Cross-Bindings und unsicherer physischer Bestand sind
detailfreie Konflikte.

Erwarteter fehlender oder technisch unklarer Bestand bleibt detailfreie
technische Unverfügbarkeit.

## Keine Authority

Directory-ID, Handle, Activezustand und physischer Besitz erteilen keine
Supervisor-, Writer-, Recovery- oder Cleanupauthority.

Requests akzeptieren keine Session, User-ID, Workspace-ID, Rolle, Permission
oder Allowentscheidung.

Aktuelle Plattformauthority bleibt vor Lifecyclemutation.

## Retention und Nichtwiederverwendung

Registryfakten zu Directory-ID, Handle und Leaf bleiben mindestens so lange
erhalten wie Journal, Runtimebinding, Gatebinding und korrelierte
Control-Artefakte.

Tombstones müssen darüber hinaus jede spätere Wiederverwendung verhindern.

Der Vertrag nennt keine konkrete Aufbewahrungsdauer oder Tabellenform.

## Keine Implementation

LQ-484 ergänzt keine Klasse, Portsignatur, Tabelle, SQL, Migration,
Filesystemadapter, Operatorgrenze oder Productioncomposition.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

Es gibt keinen Seed, Backfill, Adoption, CLI-, Route-, Compose- oder
Environment-Wiring.

## Tests

Fokussierte Vertragsprüfungen belegen stabile nicht wiederverwendbare IDs,
opaque Leafs, Reserved-vor-Create, fsync-vor-Active, active-only Resolution,
Retired-vor-Cleanup, Restartzustände, Retention und fehlende Authority.

## Nächster Slice

LQ-485 sollte geschlossene Reservation-, Aktivierungs-, Retirement- und
Lookupwerte sowie minimale Store-/Lookupports definieren.

Persistenzschema und Filesystemadapter folgen danach getrennt.
