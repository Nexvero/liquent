# LQ-451 — Persistent Manifest Handoff Supervisor Correlations

## Ergebnis

LQ-451 implementiert die LQ-450-Ports gegen die sechs Tabellen aus LQ-449.

`DatabaseManifestHandoffSupervisorCorrelations` übernimmt aktuellen
Backendlookup, sechs idempotente Appends und fünf read-only Auflösungen.

Der Adapter führt keine Supervisor- oder Prozessoperation aus.

## Aktueller Backendlookup

`resolve()` liest bei jedem Aufruf den aktuellen persistenten Backendbestand.

Genau eine aktive Instanz wird als geschlossener Backendrecord geliefert.

Keine aktive Instanz ist neutrales `None`.

Mehr als eine aktive Instanz oder beschädigte Fakten sind detailfreie
technische Unverfügbarkeit.

## Kein Backendcache

Backendstatus wird nicht im Adapter gecacht.

Committed Deaktivierung wirkt auf spätere Prepare- und Releaseentscheidungen.

Der Caller kann keine Instanz-ID an den Lookup liefern.

Ein Backendstatus erteilt keine fachliche Authority.

## Writer-Prepare

`reserve_writer` akzeptiert ausschließlich den geschlossenen Writerrequest.

Ein neuer Append verlangt aktive Backendinstanz, vorhandenen offenen
Execution-Claim und exakt passenden Owner.

Ein beendeter, fehlender oder fremder Claim endet neutral.

Je Execution-Claim wird höchstens ein Prepare reserviert.

## Recovery-Prepare

`reserve_recovery` akzeptiert ausschließlich den geschlossenen
Recoveryrequest.

Backend muss aktiv und der Recovery-Claim offen und ownergleich sein.

Execution- und Recoveryclaims werden weder vertauscht noch konvertiert.

Je Recovery-Claim wird höchstens ein Prepare reserviert.

## Idempotente Prepare-ID

Exakte Wiederholung derselben Prepare-ID und Bindung liefert den vorhandenen
Record mit ursprünglicher Zeit.

Abweichende Backend-, Capability-, Claim- oder Ownerbindung liefert den
detailfreien Korrelationskonflikt.

Ein bereits anders reservierter Claim wird nicht übernommen.

Es gibt kein Last-write-wins.

## Handlebindung

`bind_handle` verlangt vorhandenes Prepare und dieselbe Backendinstanz.

Ein exakter Retry liefert die ursprüngliche Handlebindung.

Abweichender Handle für Prepare oder bereits belegter Handle ist Konflikt.

Der Adapter rekonstruiert keinen Handle aus PID oder Prozesslisting.

## Releasekorrelation

Ein Writer-Release wird nur nach durablem, ownergleichem
`manifest_handoff_execution_starts`-Fakt angelegt.

Ein Recovery-Release verlangt weiterhin den offenen ownergleichen
Recovery-Claim.

Das gebundene Backend muss für einen neuen Releaseappend aktuell aktiv sein.

Eine Releasezeile behauptet keine physische Gatewirkung.

## Terminierungs- und Terminalkorrelation

Terminate und Terminal verlangen eine vorhandene Handlebindung.

Jede Operations-ID ist idempotent an exakt denselben Handle gebunden.

Ein anderer Handle oder eine zweite Operations-ID für denselben Handle ist
Konflikt.

Terminate beweist kein Ende; Terminal speichert nur die Korrelation zu einer
extern direkt beobachteten Supervisorobservation.

## Read-only Auflösung

Prepare, Handle, Release, Terminate und Terminal werden ausschließlich über
ihre stabilen Lookupidentitäten gelesen.

Lookups mutieren keinen Bestand und erzeugen keine neue ID.

Fehlender Bestand liefert neutral `None`.

`None` wird nicht als Prozessende oder neue Startfreigabe interpretiert.

## Geschlossene Rekonstruktion

Persistente Bytes werden strikt als nicht leeres UTF-8 dekodiert.

Capability und nullable Claimform müssen exakt der LQ-449-Matrix entsprechen.

Gespeicherte Zeiten werden nur als UTC rekonstruiert.

Beschädigte Zeilen bleiben technische Unverfügbarkeit.

## Transaktionen

Jeder Append läuft in genau einer Datenbanktransaktion.

PostgreSQL serialisiert die beteiligten Korrelations- und Claimtabellen über
eine feste Lockgrenze.

SQLite bleibt als lokale Testgrenze unterstützt.

Andere Dialekte scheitern fail-closed.

## Konflikt und Neutralität

ID-Divergenz und belegte Einmaligkeitsgrenzen liefern ausschließlich
`ManifestHandoffSupervisorCorrelationConflict`.

Fehlendes, inaktives, beendetes oder ownerfremdes Ausgangsfaktum liefert bei
einer neuen Entscheidung neutral `None`.

Kein neutraler Ausgang legt eine Zeile an.

Technische Fehler bleiben davon getrennt.

## Detailfreie Unverfügbarkeit

Der Adapter verwendet die bestehende
`ManifestHandoffRegistryUnavailable`-Grenze.

SQL-, Constraint-, Treiber-, Host-, PID-, Handle- und Pfaddetails verlassen
die Grenze nicht.

Es wird kein neuer Exceptiontyp benannt.

## Keine Authorityausweitung

Der Adapter nimmt keine Session, Rolle, Permission oder Allowentscheidung an.

Execution- und Recoveryclaim bleiben die fachlichen Quellen.

Release prüft die bereits persistierte claimed-Start-Reihenfolge, erteilt aber
keine neue Writerauthority.

Revocation und Backenddeaktivierung wirken auf spätere Entscheidungen.

## Kein Supervisorjournal

Die Implementierung schreibt ausschließlich die Plattformkorrelationen.

Sie implementiert kein externes Supervisorjournal und keinen
Kindprozesszustand.

Sie kennt weder Gatebestätigung noch direktes Prozessoutcome.

Diese Quellen folgen in separaten Slices.

## Keine Prozesswirkung

Der Adapter importiert weder subprocess noch Docker-, Service-Manager- oder
Socketbibliotheken.

Er startet, released, inspiziert, signalisiert und beendet keinen Prozess.

Es gibt kein CLI-, Compose-, Operator-, Route- oder Production-Wiring.

LQ-439 bleibt unverändert.

## Migration und Bestand

LQ-451 ändert kein Schema und erzeugt keinen Seed oder Backfill.

Head bleibt `20260824_0030` mit 30 linearen Migrationen.

Altattempts ohne Korrelation bleiben unverändert fail-closed.

Backendprovisionierung bleibt separat.

## Tests

Fokussierte Prüfungen belegen:

- aktuellen uncached Backendlookup;
- strikte Writer-/Recovery-Claim- und Ownerprüfung;
- idempotente Prepare- und Handlebindung;
- Writer-Release nur nach claimed Start;
- ein Release, Terminate und Terminal je Handle;
- fünf rein read-only Auflösungen;
- detailfreie Konflikt-, Neutralitäts- und Unverfügbarkeitsgrenzen;
- keine Prozess-, Authority- oder Wiringfähigkeit;
- unveränderten Head 0030;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-451 provisioniert oder deaktiviert keine Backendinstanz.

Er implementiert keinen Supervisorservice, Journaltransport, Prozessadapter
oder Composer.

Bestandsverankerung, Cleanup und finale Retention bleiben separat.

## Nächster Slice

LQ-452 sollte den Vertrag für das interne durable Supervisorjournal und seine
idempotenten Prepare-, Release-, Inspect- und Terminatezustände definieren.

Serviceprozess und Plattformintegration folgen danach separat.
