# LQ-518 — Owner-Controlled Single Supervisor Control-Directory Cleanup Operator Contract

## Ergebnis

LQ-518 friert den Prozessvertrag für einen owner-kontrollierten Offline-Operator
auf Basis der expliziten LQ-517-Composition ein.

Der Slice implementiert noch keinen CLI-Befehl oder Console Entry Point.

## Prozessgrenze

Der spätere Operator ist ein ausdrücklich gestarteter, kurzlebiger lokaler
Prozess.

Jeder Aufruf wählt genau einen der Befehle `execute` oder `reconcile`, behandelt
genau ein persistentes Control Directory und endet danach.

Er ist keine HTTP-, Browser-, Appstartup-, Lifespan- oder Daemongrenze.

## Owner

Nur der kontrollierte lokale Betriebssystem-Owner darf den Prozess und seine
privaten Eingabedateien besitzen.

OS-Ownership erteilt keine fachliche Cleanup-Authority.

Die aktuelle persistente Managementauthority und alle Clearancequellen bleiben
alleinige fachliche Wahrheit.

## Getrennte Befehle

`execute` darf einen neuen Attempt vorbereiten, atomar clearen und höchstens
einmal physisch ausführen.

`reconcile` darf ausschließlich einen bereits Unknown beziehungsweise nach
Crash write-claimed Attempt read-only inspizieren und terminal klassifizieren.

Kein Aufruf darf beide Befehle nacheinander ausführen.

## CLI-Eingänge

Der spätere Command akzeptiert nur Pfade zu vier vorab bereitgestellten
lokalen Dateien:

- Datenbank-URL-Datei;
- Backendinstanz-ID-Datei;
- Control-Root-Datei;
- befehlsspezifische Requestdatei.

Database-URL, Backend-ID, Root, Actor-, Attempt- oder Directory-ID sind keine
direkten Kommandozeilenwerte.

Es gibt keinen Environment-, Current-Directory- oder Defaultwertfallback.

## Private Dateigrenze

Alle vier Eingabedateien müssen regulär, owner-kontrolliert, einfach verlinkt,
nicht symbolisch und Modus `0400` oder `0600` sein.

Sie werden begrenzt mit No-follow-Semantik geöffnet und nach dem Open erneut
über ihren Descriptor validiert.

Unsichere Datei-, Owner-, Link- oder Modusfakten sind technische
Nichtverfügbarkeit.

## Datenbank

Die URL-Datei enthält genau eine unterstützte Datenbank-URL mit optional genau
einem finalen LF.

Der Prozess baut genau eine Engine und übergibt sie an genau eine
LQ-517-Composition.

Vor jeder fachlichen Aktion muss Readiness einschließlich exaktem
Migration-Head `20260826_0040` bestätigt sein.

Der Operator migriert, erstellt, repariert oder seedet kein Schema.

## Engine-Lifecycle

Die kurzlebige Operatorgrenze besitzt die von ihr erzeugte Engine.

Sie disposed die Engine in jedem Erfolgs-, Ablehnungs- und Fehlerpfad genau
einmal nach Abschluss der Aktion.

LQ-517 selbst übernimmt diesen Lifecycle weiterhin nicht.

## Backendinstanz

Die separate Backend-ID-Datei enthält genau eine nicht leere stabile interne
ID mit optional genau einem finalen LF.

Der Operator konstruiert daraus den geschlossenen
`ManifestHandoffSupervisorBackendInstanceId`-Wert.

Requestdateien können diese ID weder wählen noch überschreiben.

## Control Root

Die Root-Datei enthält genau einen absoluten Pfad mit optional genau einem
finalen LF.

Der Pfad muss auf ein bereits bestehendes privates `0700`-Verzeichnis des
Prozessowners zeigen und in allen Komponenten symlinkfrei gebunden sein.

Der Operator erstellt, repariert, chmodded oder ersetzt den Root nicht.

## Execute-Request

Die kanonische Execute-Requestdatei enthält exakt:

- `actor_user_id`;
- `directory_id`.

Beide Werte sind nicht leere stabile interne Strings.

Unbekannte, fehlende, doppelte oder falsch typisierte Felder werden vollständig
abgelehnt.

## Interne Attempt-ID

Die Execute-Requestdatei enthält keine Attempt-ID.

Der spätere Operator erzeugt für jeden ausdrücklich begonnenen Execute-Aufruf
genau eine kryptografisch starke neue Attempt-ID innerhalb der kontrollierten
Prozessgrenze.

Nach möglicher persistenter Wirkung wird sie niemals im selben Aufruf ersetzt
oder neu erzeugt.

## Principal ist keine Authority

Der Operator konstruiert `SessionPrincipal` ausschließlich als Identität des
angegebenen Actors.

Er behandelt Actor- oder Principalbesitz nicht als Allowentscheidung.

LQ-508 bindet Principal und Requestactor und löst aktive Foundations,
Scope-Management, Hold, Recovery, References, Terminalbeobachtung und
Cleanupentscheidung aktuell aus dem System of Record auf.

## Keine caller-gelieferte Freigabe

Der Execute-Request enthält keine Rolle, Permission, Capability,
Managementrevision, Clearance-ID, Decision-ID, Policyrevision oder
Allow-/Force-/Override-Boolean.

Er enthält weder Leafnamen noch Root, Handle, Artefaktpfade, Dateinamen,
Inventar, Hashes oder erwartete Bytes.

Diese Fakten werden ausschließlich persistent und lokal durch LQ-508 bis
LQ-515 gebunden.

## Execute-Reihenfolge

Die feste Reihenfolge lautet:

1. private Eingaben vollständig lesen und validieren;
2. eine Engine aufbauen und Readiness prüfen;
3. genau eine LQ-517-Composition aufbauen;
4. genau eine interne Attempt-ID erzeugen;
5. den gebundenen Cleanuprequest und Principal konstruieren;
6. Clearance genau einmal erzeugen;
7. nur bei exakt gebundener positiver Clearance Execution genau einmal aufrufen;
8. den geschlossenen Ausgang ausgeben;
9. Engine immer disposen und Prozess beenden.

Neutrale oder konfliktbehaftete Clearance startet keine Execution.

## Keine Wirkungsschleife

`cleanup_control_directory` wird an höchstens einer Stelle und ohne Schleife,
Fallback oder Resume im Execute-Prozess aufgerufen.

Nach Write Claim gibt es keinen zweiten Preflight, Claim oder Remove.

Timeout, Signal oder technische Unverfügbarkeit autorisieren keinen
automatischen Wiederholungsversuch.

## Execute-Ausgänge

Ein bestätigter terminaler Erfolg gibt nur aus:

- `outcome=removed` oder `outcome=already_absent`;
- die intern erzeugte `attempt_id`;
- die angeforderte `directory_id`.

Ein persistierter unbekannter Effekt gibt nur
`outcome=reconciliation_required` mit Attempt- und Directory-ID aus.

Diese Antwort startet Reconciliation nicht automatisch.

## Neutrale Ablehnung

Fehlendes Ziel oder fehlende aktuelle positive Authority-/Clearancefakten
enden ohne physische Wirkung als `outcome=not_available`.

Bekannte abweichende, stale, cross-gebundene oder unsichere fachliche Fakten
enden detailfrei als `outcome=rejected`.

Beide Ausgänge enthalten keine Authority-, Journal-, Policy-, Hold-, Recovery-,
Reference-, Pfad- oder Artefaktdetails.

## Reconcile-Request

Die kanonische Reconcile-Requestdatei enthält exakt:

- `attempt_id`;
- `directory_id`.

Sie enthält keinen Actor, Principal, neuen Attempt, Claim, erwarteten
Dateisystemausgang oder gewünschtes Reconciliationresultat.

Unbekannte oder zusätzliche Felder werden abgelehnt.

## Reconcile-Reihenfolge

Nach denselben privaten Konfigurations- und Readinessprüfungen baut der Prozess
genau eine LQ-517-Composition auf.

Er konstruiert genau einen gebundenen Reconciliationrequest und ruft
`reconcile_control_directory_cleanup` genau einmal auf.

Clearance-Erzeugung und Execution werden in diesem Befehlszweig niemals
aufgerufen.

## Reconciliationausgänge

Terminale Reconciliation gibt nur `outcome=absent`, `outcome=present` oder
`outcome=conflict` mit Attempt- und Directory-ID aus.

Unbekannter Attempt bleibt neutral `outcome=not_available`.

Bekannter unzulässiger oder cross-gebundener Zustand bleibt detailfrei
`outcome=rejected`.

Keiner dieser Ausgänge autorisiert einen neuen Cleanupattempt.

## Technische Unverfügbarkeit

Input-I/O nach syntaktischer Annahme, Rootprüfung, Engineaufbau, Readiness,
Lookup, Clock, Codec, Descriptor, SQL und unerwartete Compositionfehler enden
detailfrei als `operator_unavailable`.

Database-URL, Backend-ID, absolute Pfade, OS-Fehler und persistente Details
werden weder auf stdout noch stderr ausgegeben.

LQ-518 benennt keinen neuen domänenweiten Exceptiontyp.

## Exitcodes

Der spätere Prozess verwendet eine kleine feste Exitcode-Menge:

- `0` für einen gültig klassifizierten fachlichen Ausgang einschließlich
  neutral und rejected;
- `2` für syntaktisch oder strukturell abgelehnte Operatorinputs;
- `4` für detailfreie technische Nichtverfügbarkeit.

Signale und unbekannte Effekte werden nicht in Erfolg normalisiert.

## Keine Discovery

Der Operator besitzt keinen Lookup zum Auflisten oder Suchen von Directories.

Er wählt weder oldest, retired, eligible noch irgendein anderes Ziel
automatisch.

Die exakte Directory-ID muss in der jeweiligen privaten Requestdatei stehen.

## Kein Batch oder Scheduler

Es gibt keine Listenrequestform, Schleife über IDs, Queue, Cron-, Timer-,
Watcher-, Worker- oder Daemonfunktion.

Ein Prozessaufruf behandelt genau ein Directory und genau einen Befehl.

Der Operator wird weder von Appfactory noch Supervisorservice automatisch
gestartet.

## Keine neue Persistenz

LQ-518 ergänzt keine Tabelle, Migration, Spalte, SQL-Anweisung, Domainklasse,
Portsignatur oder Statusausprägung.

Head bleibt `20260826_0040` mit 40 linearen Migrationen.

## Tests

Statische Vertragsprüfungen belegen private Eingänge, interne Attempt-ID,
aktuelle Clearance vor einmaliger Wirkung, getrennte Reconciliation,
geschlossene Ausgänge und fehlende Discovery-, Batch- und Autostartgrenzen.

## Nächster Slice

LQ-519 sollte den owner-kontrollierten Einzel-Operator und seinen separaten
Console Entry Point exakt nach diesem Vertrag implementieren.

Automatische Planung, Directorysuche und Batchcleanup bleiben geschlossen.
