# LQ-290 — Persistent Research Job, Claim and Lease Foundation Contract

## Ergebnis

LQ-290 entscheidet die persistente Foundation für Research-Jobannahme,
atomaren Worker-Claim und begrenzte Lease.

Der Slice implementiert noch keinen Typ, Port, Adapter, Schema, SQL, Migration,
Command, Heartbeatloop, Runner oder Compose-Wiring.

## Getrennte stabile Identitäten

Die Foundation benötigt getrennte, nicht wiederverwendbare interne Fakten:

- `ResearchJobAcceptanceId` als stabiler Retry-Anker der Annahme;
- `JobId` als intern erzeugte Identität der Arbeitseinheit;
- `ResearchJobRevisionId` für jede persistente Zustandsrevision;
- `ResearchWorkerId` für den technischen claimenden Prozess;
- `ResearchJobClaimId` für genau eine Lease-/Ausführungsperiode.

Keine dieser Identitäten ist eine Membership, Permission, Session oder
Allow-Entscheidung.

IDs werden nicht neu zugeordnet, recycelt oder nach terminalem Abschluss für
einen anderen Job verwendet.

## Warum Acceptance-ID und Job-ID getrennt sind

Die Control Plane benötigt vor dem ersten Persistenzaufruf einen stabilen
Requestanker, damit ein verlorenes Ergebnis exakt wiederholt werden kann.

Die Job-ID entsteht dagegen innerhalb der atomaren Persistenzgrenze durch einen
kryptografisch sicheren Generator.

Ein exakter Retry derselben Acceptance-ID und desselben vollständigen Inputs
liefert dieselbe Job-ID und aktuelle Annahmerevision ohne zweite Mutation oder
neuen Generatorzug.

Abweichende Wiederverwendung derselben Acceptance-ID ist ein detailfreier
Konflikt.

## Geschlossene autorisierte Annahme

Die spätere Annahmegrenze erhält ausschließlich:

- stabile Acceptance-ID;
- identifizierende Actor-User-ID aus dem authentifizierten Principal;
- vollständig validierten `ExperimentSnapshot`;
- erwartete kontrollierte Ergebnis-/Artifactklasse.

Workspace-ID stammt aus dem Snapshot und muss mit allen persistierten
Workspacebindungen übereinstimmen.

Die Grenze akzeptiert keine Session-ID, CSRF-Behauptung, Rolle, Membership,
Permissionliste, `allow`, Jobstatus, Job-ID, Revision, Claim, Lease, Worker-ID,
Runnerimport oder Dateipfad.

## Aktuelle Annahmeauthority

Vor Commit werden User, Workspace und Membership aktuell aus dem System of
Record aufgelöst.

Nur aktive Fakten mit `research:write` für exakt Actor und Snapshot-Workspace
erlauben die Annahme.

SessionPrincipal identifiziert den Actor auf Application-Ebene, gewährt aber
keine Queueauthority und wird nicht persistiert.

Fehlende, inaktive, fremde oder entzogene Authority endet neutral ohne Job.
Der Adapter akzeptiert niemals ein caller-geliefertes Autorisierungsergebnis.

## Atomare Erstannahme

Ein erfolgreicher neuer Request persistiert in einer Transaktion:

- unveränderliche Acceptance-/Jobbindung;
- intern erzeugte Job-ID und initiale Revision-ID;
- Actor- und Workspacebindung;
- kanonischen validierten Experiment-Snapshot;
- Ergebnis-/Artifactklasse;
- serverseitige Annahmezeit;
- initialen ausführbaren Queuezustand.

Ohne Commit wird keine Job-ID ausgegeben.

Die Annahme führt keinen Runner aus, erzeugt kein Resultat und schreibt kein
Artifact.

## Snapshotpersistenz

Persistiert werden alle aktuellen `ExperimentSnapshot`-Felder bytegetreu in
einer kanonischen, versionsgebundenen Darstellung:

- Experiment- und Workspace-ID;
- Titel;
- Datasetreferenz und Fingerprint;
- Strategy-Version-ID;
- sortierte Strategy-, Risk- und Cost-Parameter.

Die Rekonstruktion durchläuft erneut die Domainvalidierung. Beschädigte,
unvollständige, doppelte oder nichtkanonische Persistenz ist technische
Nichtverfügbarkeit und kein ausführbarer Job.

Freie Pythonobjekte, Pickles und Importpfade werden nicht gespeichert.

## Sichtbarer Mindestzustand

Die persistente Foundation unterscheidet mindestens:

- `queued`: committet, aktuell ungeclaimt und grundsätzlich auswählbar;
- `running`: genau einem aktuellen Claim zugeordnet;
- `succeeded`: späterer terminaler vollständiger Resultabschluss;
- `failed`: späterer detailarmer terminaler Fehlerabschluss;
- `invalidated`: aktuelle Authority erlaubt keine neue Ausführung mehr;
- `cancelled`: für einen späteren expliziten Cancellationvertrag reserviert.

Das heutige In-Memory-`ready` bleibt eine lokale Vorstufe vor persistenter
Annahme und wird nicht als zweiter persistenter Queuezustand benötigt.

## Erneute Authorityprüfung beim Claim

Ein früher erfolgreich angenommener Job besitzt kein dauerhaftes Grace-Ticket.

Vor jedem neuen Claim werden gespeicherter Actor und Workspace erneut gegen
aktiven User, aktiven Workspace, aktive Membership und `research:write`
geprüft.

Ist die Authority entzogen, wird der Job in derselben atomaren Entscheidung
nach `invalidated` überführt und nicht ausgegeben.

Der Worker erhält weder den Grund noch Membershipdetails. Er sucht anschließend
nach dem nächsten auswählbaren Job.

Bereits RUNNING befindliche Jobs werden durch diese Claimentscheidung nicht
rückwirkend verändert; laufender Entzug und Cancellation benötigen einen
späteren expliziten Vertrag.

## Deterministische Auswahl

Claiming betrachtet ausschließlich committete `queued` Jobs.

Auswahl erfolgt in stabiler FIFO-Reihenfolge nach serverseitiger Annahmezeit und
Job-ID als vollständigem Tie-Breaker.

Es existieren noch keine Priorität, Workspacequote, Schedulezeit, mehrere
Queues oder caller-gesteuerte Sortierung.

Ein nicht autorisierter älterer Job darf jüngere autorisierte Arbeit nicht
dauerhaft blockieren; seine atomare Invalidierung setzt die Auswahl fort.

## Atomarer Claim

Die Claimgrenze erhält nur eine stabile technische Worker-ID.

Claim-ID, neue Jobrevision, Claimzeit und Leaseablauf werden innerhalb der
Persistenzgrenze erzeugt beziehungsweise serverseitig bestimmt.

Der erfolgreiche Claim ändert genau einen `queued` Job nach `running` und gibt
denselben gebundenen Snapshot gemeinsam mit Job-, Revision-, Worker-, Claim-
und Leasefakten aus.

Kein Job darf zwei gleichzeitig aktuelle Claims besitzen. Auswahl ohne
committierte Claimmutation erteilt keine Ausführungsauthority.

Eine leere Queue oder ausschließlich nicht auswählbare Jobs ergeben neutrales
`None`, nicht technische Nichtverfügbarkeit.

## PostgreSQL-Konkurrenzsemantik

Zwei unabhängige Verbindungen und Prozesse dürfen konkurrierend claimen.

Unter PostgreSQL muss genau einer denselben Job erhalten. Der andere erhält
einen anderen zulässigen Job oder neutral keine Arbeit.

Der Claim hält keine Transaktion während der Research-Ausführung offen.

Die spätere Implementierung darf Row Locks, `SKIP LOCKED` oder äquivalente
serverseitige Serialisierung verwenden, muss aber Fairness und atomare
Authorityprüfung gemeinsam belegen.

SQLite darf denselben funktionalen Einzelprozessvertrag tragen. Der
verpflichtende Mehrverbindungsnachweis läuft gegen PostgreSQL 16.

## Leasezeit

Lease-Dauer ist validierte Processkonfiguration und kein Job- oder Claiminput.

Claimzeit und `lease_expires_at` stammen aus einer gemeinsamen serverseitigen
UTC-Zeitbasis. Caller liefert weder `now` noch Ablaufzeit.

Der Ablauf liegt strikt nach Claimzeit und innerhalb eines später festgelegten
begrenzten Minimums und Maximums.

Worker-Wall-Clock entscheidet nicht über Leaseauthority. Monotone Zeit steuert
nur lokales Warten und Heartbeatplanung.

## Heartbeat

Heartbeat bindet exakt Job-ID, erwartete aktuelle Jobrevision, Worker-ID und
Claim-ID.

Nur ein nicht abgelaufener aktueller Claim im Zustand `running` darf seine Lease
um die konfigurierte Dauer verlängern und eine neue Revision erzeugen.

Caller liefert keine neue Ablaufzeit und keinen Status.

Stale Revision, falscher Worker, fremder Claim, terminaler Job oder bereits
abgelaufene Lease endet neutral ohne Mutation. Technische Persistenzfehler
bleiben separat detailfrei nicht verfügbar.

## Keine automatische Wiederbeanspruchung

Ein `running` Job mit abgelaufener Lease wird nicht durch den normalen
Claimpfad erneut nach `queued` gesetzt und nicht automatisch ausgegeben.

Er bleibt mit letzter Revision, Worker-, Claim-, Claimzeit- und Ablaufevidence
sichtbar für eine spätere Recoveryentscheidung.

Damit kann Prozessverlust nicht zu blind paralleler oder doppelter Ausführung
führen.

LQ-290 entscheidet noch nicht, ob Recovery erneut ausführt, failed finalisiert
oder manuelle Prüfung verlangt.

## Claim-bezogene Mutation

Spätere Result-, Failure- und Artifactfinalisierung muss mindestens Job-ID,
erwartete Revision, Worker-ID und Claim-ID vergleichen.

Ein stale oder abgelaufener Claim darf kein Resultat, Failure, Artifactbinding
oder terminalen Status persistieren.

LQ-290 reserviert diese Bindung, entscheidet aber noch keine Resultsignatur,
Artifacttransaktion oder Finalizerports.

## Beobachtbarkeit

Die Control Plane benötigt später einen read-only Joblookup nach Job-ID.

Er rekonstruiert Workspace, Status, aktuelle Revision, serverseitige Zeiten und
detailarme Result-/Fehlerobservability, gibt aber niemals Claim-Interna,
Worker-ID, Leasewerte oder technische Fehler an unautorisierte Browser aus.

Jeder Read autorisiert den aktuellen Principal erneut mit `research:read` gegen
den gespeicherten Workspace. Job-ID allein gewährt keinen Zugriff.

Queue-Listen, Workerinventar und globale Jobzählungen sind nicht Teil dieser
Foundation.

## Retention und Nichtwiederverwendung

Acceptance-, Job-, Revisions- und Claimfakten bleiben mindestens für die
referenzierenden Result-, Artifact-, Incident- und Auditzeiträume erhalten.

Terminale oder invalidierte Jobs werden nicht gelöscht, um IDs neu zu nutzen.

Leasehistorie darf später verdichtet werden, aber normative Claim- und
Abschlussevidence muss erhalten bleiben. Konkrete Retentiondauer und
Archivschema bleiben environmentbezogene Folgeentscheidungen.

## Neutrale und technische Ergebnisse

Neutrale Ergebnisse umfassen:

- Annahme ohne aktuelle `research:write`-Authority;
- Claim ohne auswählbaren Job;
- Heartbeat mit stale, fremdem, terminalem oder abgelaufenem Claim;
- Read ohne aktuellen `research:read`-Zugriff oder unbekannter Job.

Sie verraten keine Existenz-, Authority-, Queue-, Worker- oder Leaseursache.

Beschädigte Persistenz, ungültige interne Generatorwerte, Clock-/Datenbankfehler
und nicht unterstützte Dialekte sind detailfreie technische
Nichtverfügbarkeit.

Konflikt gilt ausschließlich für abweichende Wiederverwendung derselben
Acceptance-ID. Es wird keine neue Exceptionbenennung in diesem Vertrag
entschieden.

## Keine Authority aus technischen Fakten

Worker-ID identifiziert einen technischen Prozess, erteilt aber keine
Membership oder Researchpermission.

Claim und Lease autorisieren nur die gebundene technische Mutation innerhalb
des bereits aktuell autorisierten Jobs.

Snapshot, Job-ID, Revision oder Status sind keine Berechtigung für Browser,
Worker oder Managementoperationen.

## Bewusst nicht entschieden

LQ-290 entscheidet keine konkrete Klasse, Python-Signatur, Tabelle, Spalte,
Constraint, Index, SQL, Isolation-Level, Migration, Locksyntax, Lease-Dauer,
Heartbeatintervall, Fehlerklasse, CLI, Queuebibliothek, Artifactformat oder
Wiringentscheidung.

Es erzeugt keinen User, Workspace, Membership, Session, Experiment, Job, Claim,
Lease, Result, Artifact, Prozess, Thread oder Netzwerkzugriff.

Head bleibt `20260819_0025`; Bundle und Compose bleiben unverändert.

## Implementierungsfolge

LQ-291 sollte zuerst stabile Research-Job-, Revision-, Worker- und Claimtypen
sowie geschlossene Acceptance-, Claim-, Heartbeat- und Lookupports einführen,
noch ohne Persistenz oder Runtime-Wiring.

LQ-292 kann danach Schema, Migration und PostgreSQL-/SQLite-Adapter atomar
implementieren.
