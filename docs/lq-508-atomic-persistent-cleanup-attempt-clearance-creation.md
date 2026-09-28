# LQ-508 — Atomic Persistent Cleanup Attempt and Clearance Creation

## Ergebnis

LQ-508 implementiert den LQ-500-Clearance-Creation-Port als atomare persistente
Erzeugung eines neuen Started-Attempts und seiner positiven revisionsgebundenen
Clearance.

Der Slice führt noch keine physische Cleanupoperation aus.

## Principal und Request

Die Grenze akzeptiert ausschließlich `SessionPrincipal` und den geschlossenen
Cleanuprequest aus Attempt-ID, Actor-ID und Directory-ID.

`principal.user_id` muss exakt `request.actor_user_id` entsprechen.

Der Principal erteilt selbst keine Cleanupauthority.

## Keine Caller-Evidence

Caller liefern weder Clearance-ID, Scope, Handle, Journal, Retentiondecision
noch Management-, Hold-, Recovery- oder Referenzrevision.

Alle Fakten werden innerhalb der Schreibtransaktion aus ihren Systemen of
Record gelesen.

Es gibt kein Allowboolean oder Evidence-Dict.

## Retry- und Adoptionprüfung zuerst

Attempt und Clearance werden zu Beginn anhand der Request-Attempt-ID gelesen.

Sind beide abwesend, kann eine neue Creationentscheidung beginnen.

Sind beide vorhanden, wird ein möglicher exakter Retry vollständig geprüft.

## Keine Adoption einzelner Attempts

Ist nur ein Attempt ohne Clearance vorhanden, liefert die Grenze einen
detailfreien Cleanupkonflikt.

Eine Clearance ohne Attempt ist ebenfalls Divergenz.

LQ-494-Einzelattempts werden nicht nachträglich productionfähig gemacht.

## Retry bleibt aktuell gebunden

Ein vorhandenes Attempt-/Clearancepaar wird nicht blind zurückgegeben.

Actor, Directory, Started-Zustand, Decision, Scope, Terminal-Observation und
alle vier aktuellen Revisionen müssen weiterhin exakt der gespeicherten
Clearance entsprechen.

Späterer Entzug oder Blockierung macht den Retry unwirksam.

## Aktuelles Retired-Directory

Die Creation liest das Directory anhand der internen Request-ID.

Nur ein vollständig rekonstruierter aktueller Retired-Wert öffnet weitere
Prüfungen.

Reserved, Active oder beschädigte Lifecyclefacts bleiben fail-closed.

## Transaktionaler Journalview

Journaljob und gesamte geordnete Transitionhistory werden über das Handle des
Retired-Werts innerhalb derselben Transaktion gelesen.

Der bestehende Journaladapter stellt dafür eine reine klassenbasierte
`reconstruct_view`-Funktion bereit.

Sie verwendet dieselben History- und Domainvalidierungen wie normale Inspect-
Aufrufe und führt keine zusätzlichen Datenbankzugriffe aus.

## Terminalitätsanforderung

Der rekonstruierte View muss `TERMINAL_OBSERVED`, Terminal-Observation-ID und
geschlossenes Ergebnis tragen.

Journalregistration und Ergebnis müssen über die bestehenden Domainwerte zum
Retired-Handle passen.

Unvollständige oder divergente Journalhistory ist technische Unverfügbarkeit.

## Serverseitiger Scope

Der Handoffscope stammt ausschließlich aus
`journal.registration.process_request.binding.scope_id`.

Actor-User und dieser Scope müssen aktuell persistent aktiv sein.

Ein Caller-Scope oder Workspace wird nicht akzeptiert.

## Aktuelle Retentionentscheidung

Die höchste Retentionentscheidung für das Directory wird erneut gelesen und als
vollständiger Domainwert rekonstruiert.

Nur `eligible` ist positiv.

Eine neuere Retain-Decision sperrt Creation und Retry.

## Aktuelle Managementrevision

Die höchste Managementrevision für Request-Actor und abgeleiteten Scope wird
erneut gelesen.

Nur Active ist positiv.

Inactive oder fehlender Bestand liefert keine Clearance.

## Aktuelle Holdrevision

Die höchste Holdrevision für das Directory wird erneut gelesen.

Sie muss Clear sein und wird mit dem vollständigen aktuellen Retired-Wert
rekonstruiert.

Blocked oder fehlender Bestand sperrt die Creation.

## Aktuelle Recoveryrevision

Recovery wird unabhängig aus seiner eigenen höchsten Revision gelesen.

Nur Clear ist positiv.

Terminalität ersetzt diese Prüfung nicht.

## Aktuelle Referenzrevision

Referenzen werden ebenfalls aus ihrer eigenen höchsten Revision gelesen.

Nur Clear kann Teil der aggregierten Clearance sein.

Tabellenabwesenheit wird nicht zu Clear normalisiert.

## Geschlossene Aggregation

Die positiven Fakten werden vor dem Write als vollständige Retired-, Journal-,
Decision-, Management-, Hold-, Recovery- und Referenzwerte konstruiert.

Damit gelten Actor-, Scope-, Directory-, Handle-, Disposition- und
Zeitinvarianten bereits an der Domaingrenze.

Teilaggregation ist unzulässig.

## Interne Clearance-ID

Die Clearance-ID wird innerhalb der kontrollierten Grenze erzeugt.

Sie ist nicht aus Attempt, Actor, Directory oder Zeit abgeleitet.

Tests können einen deterministischen Generator injizieren.

## Monotone Creationzeit

`cleared_at` und `started_at` verwenden denselben serverseitigen aware-UTC-
Zeitpunkt.

Er darf nicht vor Retirement, Terminalobservation oder einer gebundenen
Entscheidungs-/Authorityzeit liegen.

Rückläufige Uhren scheitern technisch fail-closed.

## Atomarer Doppelinsert

Nach vollständiger positiver Revalidierung schreibt dieselbe Transaktion:

1. den neuen Started-Attempt mit aktueller Retentiondecision;
2. die immutable Clearance mit Scope, Terminal-ID und allen Revisionen.

Entweder beide Inserts committen oder keiner.

## Attemptzustand

Der neue Attempt startet exakt in `started`.

Unknown-, Outcome-, Completion- und Reconciliationfelder bleiben NULL.

Die Creation behauptet keine bereits ausgeführte Dateiwirkung.

## Immutable Clearance

Die Clearance bindet Attempt, Actor, Directory, Scope, Terminalobservation,
Retentiondecision, Management-, Hold-, Recovery- und Referenzrevision sowie
Creationzeit.

Sie besitzt keinen Status und wird nicht nachträglich aktualisiert.

Spätere Revocation bleibt eine neue höhere Quellrevision.

## PostgreSQL-Sperrordnung

Die Schreibtransaktion sperrt User, Scope, Directory, Journal, Retention,
Management, Hold, Recovery, Referenzen, Attempts und Clearances in fester
Reihenfolge.

Damit werden konkurrierende Source-Appends und Clearancecreation sichtbar
geordnet.

SQLite bleibt für lokale fokussierte Tests unterstützt.

## Detailfreie Ergebnisse

Unbekannte Foundations oder fehlende positive Fakten liefern neutral None.

Principalabweichung, Einzelattempt-Adoption, gespeicherte Bindungsabweichung
oder stale Retry liefern den bestehenden feldlosen Cleanupkonflikt.

Struktur-, Journal-, Generator-, Uhr- und Datenbankfehler bleiben technische
Unverfügbarkeit.

## Keine Quellmutation

LQ-508 schreibt keine Retention-, Management-, Hold-, Recovery- oder
Referenzrevision.

Es liest ausschließlich deren aktuellen höchsten Bestand.

Authority-Set- und Change-Historien bleiben unverändert.

## Keine Dateioperation

Der Adapter öffnet, inspiziert, verändert oder entfernt keine Datei und kein
Verzeichnis.

Positive Clearance ist nur persistente Voraussetzung eines späteren physischen
Execution-Slices.

Unlink, Rmdir und rekursiver Cleanup bleiben geschlossen.

## Keine Productionverdrahtung

Settings, Appfactory, Route, CLI, Operator, Compose und Deployment bleiben
unverändert.

Der Adapter wird nicht automatisch aktiviert.

Head und Migrationsanzahl bleiben `20260826_0039` und 39.

## Tests

Fokussierte Prüfungen belegen Principalbindung, Retry-/Adoptionprüfung vor neuen
Writes, vollständige transaktionale Journalrekonstruktion, aktuelle positive
Retention-/Management-/Hold-/Recovery-/Referenzfakten, interne Clearance-ID,
monotone Zeit und Attempt-vor-Clearance-Doppelinsert.

Sie belegen außerdem aktuelle Retry-Revalidierung sowie fehlende Quellmutation,
Datei- und Wiringwirkung.

## Nächster Slice

LQ-509 sollte den physischen Cleanup-Execution-Vertrag nach positiver aktueller
Clearance und unmittelbar erneuter read-only Bestandsprüfung definieren.

Production-Wiring bleibt weiterhin getrennt.
