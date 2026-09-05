# LQ-387 — Runtime Cleanup Runbook and Static Audit

## Ergebnis

LQ-387 implementiert das in LQ-386 definierte Betreiberartefakt als
`operations/runbooks/disposable-postgres-runtime-cleanup.md`.

Ein statischer Audit prüft Command-Inventar, Authority-Reihenfolge,
Ausgangsrouting, Incidentgrenzen, Retention und Volume-Ausschluss.

## Beaufsichtigter Offline-Prozess

Das Runbook definiert Runtime-Cleanup ausdrücklich als kurzlebigen,
owner-kontrollierten Offline-Prozess.

Es ist kein ausführbares Gesamtskript und keine Scheduler-, Service-, CI-,
Deployment- oder HTTP-Grenze.

Nach jedem Command ist eine neue bewusste Betreiberentscheidung erforderlich.

Die nummerierte Commandliste ist Authority-Inventar und kein linearer Blindlauf.

## Gebundener Run und Rollen

Das Runbook verlangt einen einzelnen gebundenen Run mit immutable Image-Digest,
Source-Commit, Compose-Hash, Projektname, Host und privatem Evidenceverzeichnis.

Environment Owner, Authorizer, Executor, Retention Owner und Incident Owner
bleiben getrennte Verantwortungen.

Das dedizierte Prozesskonto gewährt selbst keine Cleanup-Authority.

Private Eingaben werden unter `umask 077` ohne Environment-, Log-, Ticket- oder
Chatweitergabe behandelt.

## Autorisierungsmaterial-Handoff

Vor jedem mutierenden, inspizierenden oder finalisierenden Schritt verlangt das
Runbook eine neue owner-only Autorisierungsdatei.

Quelle, bytegenauer SHA-256, neue ID, getrennte Identitäten, Operation, Scope,
Zeitfenster und Review werden privat inventarisiert.

Der Executor darf keine eigene Autorisierung erzeugen, verlängern oder aus
Tests kopieren.

Stale, malformed oder widersprüchliches Material stoppt fail-closed.

## Vollständiges Command-Inventar

Alle 16 installierten Cleanup-Entry-Points stehen in ihrer Authority-Reihenfolge
im Runbook.

Der Ablauf umfasst Preflight, initialen Cleanup, Inspector und LQ-343-
Finalisierung sowie erste Continuation, Recontinuation, Chained Continuation und
begrenzte Generationen mit jeweils Inspector und Finalizer.

Disposition und vorgelagerte PostgreSQL-Reconciliation bleiben separat
referenzierte Voraussetzungen.

Kein neuer Entry Point entsteht.

## Ausgangsrouting

Für jede Stufe beschreibt das Runbook positive, nichtterminale, terminale,
neutrale, abgelehnte, konfliktbehaftete und technische Ausgänge getrennt.

Unknown Outcome nach möglicher Mutation routet ausschließlich zum passenden
read-only Inspector.

Finalizer schreiben Evidence vor Claimfreigabe. Ein Evidence-Retry verwendet
dieselben Dateien und wiederholt nur die Claimfreigabe.

Exitcode 2 wird ausdrücklich weder als `not_found` noch als Erfolg behandelt.

## Generation-Lineage

Generation eins verwendet den direkten LQ-362-Anker ohne Lineage-Optionen.

Generation zwei verwendet genau die beiden direkten Vorgängerdateien.

Ab Generation drei werden gleich lange geordnete Continuation-/Finalization-
Optionsfolgen dokumentiert.

Generation 17 ist mit 16 historischen Paaren die positive Obergrenze;
Generation 18 bleibt fail-closed ohne Paging oder Abschneiden.

## Terminaler LQ-343-Handoff

Nur terminale Generation-Finalisierung routet zum Cleanup-Abschluss.

Das Runbook verlangt eine neue aktuelle LQ-343-Autorisierung und eine frische
LQ-341-Beobachtung.

Generation-Dateien werden nicht an LQ-343 übergeben und bleiben bytegenau
erhalten.

Cleanup-Evidence entsteht vor Freigabe ausschließlich des ursprünglichen
LQ-339-Claims.

## Incident und Retention

Conflict, malformed Evidence, fremder Claim, Hashabweichung, Hostverlust und
technische Nichtverfügbarkeit stoppen alle Cleanup-Commands.

Manuelle Dockermutation, Claimlöschung, Evidence-Reparatur, ID-Ersatz,
Berechtigungsverbreiterung und automatische Retries sind verboten.

Der Retention Owner führt ein privates Inventar aus Pfad, Hash, Eigentum,
Modus, Linkzahl, ID, Generation, Ausgang und UTC-Zeit.

Retention endet weder bei Claimfreigabe noch Runtimeabschluss.

## Separate Volume-Disposition

Das Runbook endet mit erhaltenem rungebundenem PostgreSQL-Datenvolume.

Mount, Inhaltszugriff, Export, Backupentscheidung, Legal Hold, Retentionfreigabe
und Löschung sind ausdrücklich ausgeschlossen.

Runtime-Cleanup darf nicht als vollständige Umgebungsentsorgung kommuniziert
werden.

Ein späterer Volume-Prozess benötigt einen eigenen Vertrag.

## Statischer Audit

Drei neue Tests prüfen:

- alle 16 Commands in Authority-Reihenfolge und ihre Installation in
  `pyproject.toml`;
- Autorisierungshandoff, Unknown Outcome, Evidence-Retry, Generationen,
  LQ-343-Handoff, Exitcode- und Retentiongrenzen;
- Ausschluss von Automatisierung, manuellen Abkürzungen und
  Volume-Disposition.

Die Tests führen keinen Cleanup- oder Dockercommand aus.

## Readiness-Entscheidung

Die in LQ-385 festgestellte interne Runbooklücke ist geschlossen.

Das Repository enthält jetzt eine zusammenhängende beaufsichtigte
Betreiberprozedur für die implementierte Runtime-Cleanup-Kette.

Ein konkreter Environmentlauf benötigt weiterhin eigene Host-, Account-,
Pfad-, Image-, Evidence- und Incidentfreigabe.

Vollständige Entsorgung bleibt bis separater Volume-Disposition ausgeschlossen.

## Bundle und Nichtziele

LQ-387 ergänzt nur Runbook, statischen Test und Dokumentation.

Produktionsmodule, Funktionssignaturen, Claims, Evidenceformate, CLI,
Entry Points, Compose und Migrationen bleiben unverändert.

Bundle-Gates bleiben bei 49 Entry Points, 53 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-388 sollte die separate PostgreSQL-Volume-Disposition als Vertrag
definieren.

Der Vertrag muss Retention, Backup-/Restore-Nachweis, Legal Hold,
Löschautorität, Unknown Outcome und evidence-first Entfernung schließen, ohne
den Runtime-Cleanup-Vertrag rückwirkend zu erweitern.
