# LQ-370 — Direct Generation-two Runtime Cleanup Continuation Contract
## Zweck
LQ-370 definiert Generation zwei als direkten Cleanup-Versuch nach einer
nichtterminalen LQ-369-Finalization-Evidence der Generation eins.
Der Slice erweitert den LQ-365-Operatorvertrag auf den ersten wiederholten
Vorgängertyp, implementiert aber keinen Command, Claim oder Dockeraufruf.
## Exakte Generation
Die neue Generation ist zwingend die positive Ganzzahl zwei.
Ihre Vorgängerart ist exakt `repeatable_generation` und ihre
Vorgängergeneration exakt eins.
Generation, Vorgängerart und Vorgängergeneration werden aus der kanonischen
LQ-369-Evidence abgeleitet, nicht vom Caller gewählt.
Null, eins, größere Werte, Sprünge oder alternative Vorgänger bleiben technisch
unavailable.
## Zulässige LQ-369-Ausgänge
Nur `generation_continuation_attempt_finalized` und `later_prefix_finalized`
dürfen Generation zwei begründen.
`generation_continuation_evidence_confirmed` und
`runtime_removal_ready_for_cleanup_finalization` sind terminal und führen
ausschließlich zu LQ-343.
`not_found`, `investigation_required`, malformed oder technisch nicht
verfügbare Ergebnisse erteilen keine Folgeautorität.
Kein Ausgang startet Generation zwei automatisch.
## Direkte Vorgängerbindung
Die neue Autorisierung bindet Generation-1-Continuation-, Reconciliation- und
Finalization-ID sowie SHA-256 der vollständigen LQ-369-Autorisierung.
Sie bindet SHA-256 der exakten kanonischen LQ-369-Finalization-Evidence und
deren Ausgang.
Vorgänger-ID, Generation, Root-Kette, beide historischen Präfixe und
Finalization-Evidence müssen eine einzige unveränderte Kette bilden.
Eine ältere Evidence, LQ-362 als direkter Anker oder mehrere alternative
Vorgänger sind ausgeschlossen.
## Neue owner-only Autorisierung
Generation zwei benötigt eine neue stabile, nicht wiederverwendbare
Generation-Continuation-ID.
Die Autorisierung bindet außerdem Run-, Dispositions-, Cleanup-, LQ-349-,
LQ-355-, LQ-358- und Generation-1-Kette vollständig.
Sie enthält Phase `disposable_postgres`, Source-Commit, Image-Digest,
Compose-Hash, Root-Evidencehashes und sämtliche direkten Autorisierungshashes.
Scope ist exakt `runtime_only`; Operation exakt
`continue_disposable_postgres_cleanup_from_generation`.

Executor und Autorisierer sind neu und getrennt; das aktuelle UTC-Fenster ist
positiv und höchstens eine Stunde lang.

Caller liefern keinen Allow-Bool, Zustand, Generation, Vorgänger, Präfix,
Ressourcennamen, Restbudget oder Dockerargumente.

## Historischer und effektiver Präfix

`predecessor_resume_from` bleibt exakt der effektive Startpräfix der
Generation-1-Autorisierung.

Bei `generation_continuation_attempt_finalized` ist der neue `resume_from`
exakt gleich diesem Vorgängerpräfix.

Bei `later_prefix_finalized` ist der neue `resume_from` zwingend
`application_network_removed`.

Zulässig sind nur `container_removed` und `application_network_removed`.

Die beiden Felder bleiben getrennt gebunden, damit Fortschritt nicht als
historischer Startzustand umgedeutet wird.

## Vollständige historische Validierung

Der spätere Operator validiert Root-, LQ-362-, LQ-365-, LQ-367- und
LQ-369-Kette erneut.

Historische Autorisierungen werden ausschließlich an ihrem ursprünglich
gültigen Fenstermittelpunkt ausgewertet.

Die neue Autorisierung verlängert keine frühere Mutation, Reconciliation oder
Finalisierung.

IDs, Hashes, Präfixe, Run, Projektname und Ressourcen müssen dieselbe
unveränderte Kette beschreiben.

## Claim-Voraussetzungen

Der ursprüngliche LQ-339-Cleanup-Claim muss offen, owner-only, kanonisch und
exakt gebunden bleiben.

LQ-345-, LQ-351-, LQ-358- und Generation-1-Claim müssen exakt abwesend sein.

Ein vorhandener historischer oder malformed Claim bleibt technisch unavailable
und wird weder ersetzt noch entfernt.

Der Generation-2-Claimname wird ausschließlich aus SHA-256 der neuen
Generation-Continuation-ID abgeleitet.

Ein vorhandener oder technisch unklarer aktueller Claim stoppt vor Docker.

## Frische Zustandsbestätigung

Unmittelbar vor Claimanlage muss LQ-341 mit historischer
Cleanup-Reconciliation-Autorisierung frisch und read-only ausgeführt werden.

Nur ein Ausgang exakt gleich dem autoritativ abgeleiteten `resume_from` darf
die Mutation erreichen.

Früherer oder späterer Präfix, vollständige Entfernung, Final-Evidence,
`runtime_intact`, `not_found` oder Conflict ergibt `rejected` ohne Claim oder
Ressourceneffekt.

Technische Nichtverfügbarkeit bleibt ohne Ergebnis und Mutation.

## Minimales Restbudget

Ab `container_removed` sind ausschließlich Application-Network-Remove,
Data-Network-Remove, jeweilige Abwesenheitsbestätigung und read-only
Volumeidentitätsprüfung zulässig.

Ab `application_network_removed` beginnt das Budget beim Data-Network.

Bestätigte Container- oder Netzwerkoperationen werden niemals wiederholt.

Es gibt keinen freien Start-, End-, Ressourcen- oder Befehlsumfang.

## Evidence-first Claim und Mutation

Der Claim wird erst nach exakter frischer Zustandsübereinstimmung owner-only
exklusiv angelegt und synchronisiert.

Er bindet Generation zwei, direkte LQ-369-Evidence, Root-Kette, beide Präfixe,
Restbudget, Ressourcen, Identitäten und UTC-Startzeit.

Jedes erlaubte Netzwerk wird einzeln intern abgeleitet entfernt und danach
exakt als abwesend bestätigt.

Anschließend wird ausschließlich die unveränderte rungebundene Volumeidentität
read-only geprüft.

Compose-Down, Stop, Start, Kill, Force, Disconnect, Prune, `--volumes`, SQL,
Wildcard-, Präfix-, Label- und Gruppencleanup sind verboten.

## Unknown Outcome

Ab dem ersten Remove beendet jeder mehrdeutige technische Ausgang den Ablauf.

Cleanup- und Generation-2-Claim bleiben offen; es gibt keinen Blind-Retry,
Ersatzbefehl, heuristischen Erfolg oder automatischen Folgeschritt.

Eine getrennte read-only Reconciliation des exakten Generation-2-Claims ist
erforderlich.

## Generation-2-Evidence

Nach bestätigter Runtimeentfernung und Volume-Erhalt entsteht getrennte private
Evidence mit `runtime_removed_pending_cleanup_finalization`.

Sie bindet Generation zwei, direkten Vorgänger, Root-Kette, Präfixe,
Restbudget, Ressourcen, Identitäten sowie UTC-Start und Abschluss.

Erst atomare Anlage, Synchronisation und vollständige Rücklesung erlauben die
Freigabe ausschließlich des aktuellen Generation-2-Claims.

Ein Evidence-Retry wiederholt nur diese Claimfreigabe und kein Docker.

## Neutrale Ausgabe und Retention

Der spätere Command liefert nur `runtime_removed_pending_cleanup_finalization`,
`rejected` oder technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Private Generation, IDs, Hashes, Pfade, Ressourcen und Zeiten bleiben verborgen.

Alle Generationen, IDs, Claims, Autorisierungen und Evidence bleiben mindestens
für Audit, Retry, Reconciliation, Finalisierung und LQ-343 unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden; eine
konkrete Retentionfrist wird nicht festgelegt.

## Nichtziele und Bundle

LQ-370 implementiert keinen Operator, Entry Point, Test, Claim, Evidencewriter,
Reconciliationoperator, Finalizer oder Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 49 Entry Points, 53 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-371 sollte den bestehenden generationengebundenen Continuation-Operator um
den direkten LQ-369-Vorgängerresolver für Generation zwei erweitern.

Reconciliation und Finalisierung der Generation zwei bleiben getrennte spätere
Slices.
