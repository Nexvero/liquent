# LQ-293 — Controlled Persistent Research Job Composition

## Ergebnis

LQ-293 komponiert die persistente Research-Control-Plane und die technische
Worker-Control-Plane über exakt eine LQ-292-Storeinstanz.

Der Slice startet keinen Worker, Runner, Thread, Prozess oder Netzwerkzugriff
und verdrahtet noch keine HTTP-Route oder Productionkonfiguration.

## Browserseitige Control-Plane

`PersistentResearchControlPlane` besitzt ausschließlich Acceptance und
autorisierten Lookup.

Acceptance verlangt einen bereits aufgelösten `ResolvedBrowserSession`, prüft
den sessiongebundenen CSRF-Nachweis vor jedem Storezugriff und reicht nur die
Actor-User-ID weiter. Session, Cookie und CSRF-Wert werden nicht persistiert.

Der Store löst aktuelle `research:write`-Authority weiterhin selbst auf.
Principal und bestandene CSRF-Prüfung sind keine Authoritybehauptung.

Read reicht nur Actor-User-ID und Job-ID an den aktuell autorisierenden Lookup.
Fehlender Job und fehlende Leseberechtigung bleiben neutral identisch.

## Technische Worker-Control-Plane

`PersistentResearchWorkerControl` besitzt ausschließlich Claim und Heartbeat.

Claim erhält nur die stabile Worker-ID. Heartbeat bindet Job, erwartete
Revision, Worker und Claim ohne Callerzeit, Status oder Leasewert.

Die Workergrenze erhält keinen SessionPrincipal, CSRF-Wert, Userinput, Rolle,
Membership, Permissionliste oder Allow-Boolean.

## Eine gemeinsame Storeinstanz

`compose_persistent_research_jobs` erzeugt genau einen
`DatabaseResearchJobs` und reicht dieselbe Instanz an beide Control-Planes.

Damit sehen Browserreads, Acceptance, Claim und Heartbeat denselben
committierten Zustand und dieselbe aktuelle Authorityauflösung. Es gibt keinen
zweiten In-Memory-Fallback und keinen zwischen Prozessen geteilten Cache.

Engine und Generatoren bleiben extern besessen. Composition schließt oder
disposed sie nicht.

## Side-Effect-freier Aufbau

Composition validiert die Leasekonfiguration und baut nur Objekte.

Sie öffnet keine Datenbankverbindung, prüft keine Migration, liest keine Queue,
erzeugt keine ID, liest keine Clock und claimt keinen Job.

Ungültige Leasedauer scheitert vor jeder Datenbankaktivität.

## Bewusst keine Ausführung

Ein erfolgreicher Claim wird in LQ-293 nicht an einen Runner übergeben.

Ohne claim- und revisionsgebundene Result-/Failure-/Artifactfinalisierung wäre
eine ausführende Workercomposition unvollständig: Sie könnte Ergebnisse
berechnen, aber weder Erfolg noch Fehler atomar und stale-sicher abschließen.

Deshalb aktiviert dieser Slice weder den bestehenden synchronen In-Memory-Pfad
noch einen langlebigen Workercommand.

## Fehlergrenze

CSRF-Fehler bleiben die bestehende neutrale Application-Ablehnung.
Acceptance-, Claim-, Heartbeat- und Lookupfehler behalten die detailfreie
LQ-292-Persistenzgrenze; Composition führt keine neue Exception ein.

## Unveränderter Scope

Keine Migration, Tabelle, Spalte, SQL-, Port- oder Signaturänderung ist für
LQ-293 erforderlich. Head bleibt `20260819_0026`.

Bundle, Compose, HTTP-Routen, CLI, Workerloop, Signalhandling, Polling,
Heartbeatplanung, Runnerresolver, Resultate, Artifacts und Recovery bleiben
unverändert.

Die vollständige lokale Suite besteht mit 3333 Tests, 98 erwarteten
PostgreSQL-Skips und 595 bestehenden Warnungen.

## Implementierungsfolge

LQ-294 sollte zuerst die claim- und revisionsgebundene persistente
Result-/Failure-/Artifactfinalisierung entscheiden und implementieren.

Erst danach kann ein kontrollierter Worker einen Claim auflösen, ausführen,
heartbeaten und sicher terminal abschließen.
