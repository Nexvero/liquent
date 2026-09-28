# LQ-364 — Generation-bound Repeatable Runtime Cleanup Continuation Contract
## Zweck
LQ-364 definiert einen dauerhaft wiederholbaren Runtime-Cleanup-Versuch nach
einer nichtterminal finalisierten LQ-362- oder späteren Generation.

Der Slice schließt die in LQ-363 belegte Wiederholungslücke, implementiert aber
keinen Operator, Claim, Writer oder Dockeraufruf.
## Generationsmodell
Jeder Versuch besitzt eine positive kanonische Generation und eine stabile,
nicht wiederverwendbare Generation-Continuation-ID.

Generation eins folgt unmittelbar auf LQ-362-Finalization-Evidence. Jede
spätere Generation folgt unmittelbar auf die Finalization-Evidence der
vorherigen wiederholbaren Generation.

Die Generationsnummer ist kein caller-gelieferter Offset. Sie muss exakt eins
größer als die kanonisch belegte Vorgängergeneration sein.

Übersprungene, doppelte, rückläufige oder anders verankerte Generationen sind
technisch unavailable.
## Zulässige Vorgängerausgänge
Nur `chained_continuation_attempt_finalized` oder `later_prefix_finalized` aus
exakter LQ-362-Evidence dürfen Generation eins eröffnen.

Für spätere Generationen sind ausschließlich die semantisch gleichen
nichtterminalen Ausgänge der direkten Vorgänger-Finalization-Evidence zulässig.

Evidence-confirmed und runtime-removal-ready sind terminal und führen nur zu
LQ-343. `not_found`, `investigation_required` und technische
Nichtverfügbarkeit erteilen keine Folgeautorität.
## Direkte Vorgängerbindung
Die Autorisierung bindet Vorgängerart, Vorgängergeneration,
Vorgänger-Continuation-ID, Vorgänger-Finalization-ID und SHA-256 der exakten
Vorgänger-Finalization-Evidence.

Für Generation eins ist die Vorgängerart exakt `lq362`. Danach ist sie exakt
`repeatable_generation`.

Eine Autorisierung darf nie eine ältere Evidencegeneration auswählen, eine
neuere auslassen oder mehrere Vorgänger alternativ zulassen.

Die direkte Evidence bleibt owner-only, kanonisch und bytegenauer jüngster
Autoritätsanker.
## Geschlossene Root-Kette
Jede Generation bindet weiterhin unverändert Run-, Dispositions-, Cleanup-,
Continuation-, Recontinuation- und LQ-358-Kette.

Sie bindet Phase `disposable_postgres`, Source-Commit, Image-Digest,
Compose-Hash, ursprüngliche Reconciliation-, Claim-Reconciliation- und
Disposition-ID sowie sämtliche Root-Evidencehashes.

Die neue Generation ersetzt keine historische Evidence und verlängert keine
frühere Autorisierung.

Abweichende Root- oder Vorgängerbindung bleibt detailfrei unavailable.
## Neue owner-only Autorisierung
Die Autorisierung muss mindestens Generation-Continuation-ID, Generation,
direkte Vorgängerbindung, vollständige Root-Kette und autoritativen
Startpräfix enthalten.

Scope ist exakt `runtime_only`; Operation exakt
`continue_disposable_postgres_cleanup_from_generation`.

Executor und Autorisierer sind neu und getrennt. Das aktuelle UTC-Fenster ist
positiv und auf höchstens eine Stunde begrenzt.

Caller liefern weder Allow-Bool, Zustand, Generation, Vorgänger, Ressourcen,
Restbudget noch Dockerargumente.
## Autoritativer Startpräfix

Bei `attempt_finalized` bleibt `resume_from` exakt der in der direkten
Vorgängerevidence gebundene Startpräfix.

Bei `later_prefix_finalized` ist `resume_from` zwingend
`application_network_removed`.

Zulässig sind nur `container_removed` und `application_network_removed`.
Der Präfix wird aus dem System of Record abgeleitet und nie aus einer freien
Callerangabe übernommen.

## Claim-Voraussetzungen

Der LQ-339-Cleanup-Claim muss offen, owner-only, kanonisch und exakt gebunden
sein.

LQ-345-, LQ-351- und LQ-358-Claims sowie alle Claims abgeschlossener
wiederholbarer Generationen müssen exakt abwesend sein.

Ein vorhandener historischer oder malformed Claim bleibt unavailable und wird
nicht entfernt.

Der neue Claimname wird ausschließlich aus SHA-256 der neuen
Generation-Continuation-ID abgeleitet.

## Frische Zustandsbestätigung

Unmittelbar vor Claimanlage muss LQ-341 mit seiner historischen
Cleanup-Reconciliation-Autorisierung frisch und read-only ausgeführt werden.

Nur ein Ausgang exakt gleich dem autoritativ abgeleiteten `resume_from` darf
die Mutation erreichen.

Früherer oder späterer Präfix, vollständige Entfernung, Final-Evidence,
`runtime_intact`, `not_found` oder Conflict ergibt `rejected` ohne neuen Claim
und ohne Ressourceneffekt.

Technische Nichtverfügbarkeit bleibt ohne Ergebnis und Mutation.

## Minimales Restbudget

Ab `container_removed` sind nur Application-Network-Remove,
Data-Network-Remove, jeweilige exakte Abwesenheitsbestätigung und read-only
Volumeidentitätsprüfung zulässig.

Ab `application_network_removed` entfällt der bereits bestätigte erste Schritt.

Die Generation erweitert das Budget nicht und wiederholt keine bestätigte
Container- oder Netzwerkoperation.

Es gibt keinen freien Start-, End- oder Ressourcenoffset.

## Evidence-first Claim und Mutation

Der neue Claim wird erst nach frischer exakter Zustandsübereinstimmung
owner-only exklusiv angelegt und synchronisiert.

Er bindet Generation, direkte Vorgängerevidence, Root-Kette, Startpräfix,
Restbudget, Ressourcen, Identitäten und UTC-Startzeit.

Netze werden einzeln mit intern abgeleiteten Namen entfernt und jeweils exakt
als abwesend bestätigt. Danach wird nur die Volumeidentität read-only geprüft.

Compose-Down, Stop, Start, Kill, Force, Disconnect, Prune, `--volumes`,
Wildcard-, Präfix-, Label- und Gruppencleanup bleiben ausgeschlossen.

## Unknown Outcome

Ab dem ersten Remove beendet jeder mehrdeutige technische Ausgang den Ablauf.
Cleanup- und aktueller Generation-Claim bleiben offen.

Es gibt keinen Blind-Retry, Ersatzbefehl, heuristischen Erfolg oder
automatischen Folgeschritt.

Eine getrennte read-only Reconciliation muss den exakten Claim und die direkte
Generationsbindung auswerten.

## Generation-Evidence

Nach bestätigter Runtimeentfernung und Volume-Erhalt entsteht getrennte private
Evidence mit Ausgang `runtime_removed_pending_cleanup_finalization`.

Sie bindet Generation, Vorgänger, Root-Kette, Startpräfix, Restbudget,
Ressourcen, Identitäten sowie UTC-Start und Abschluss.

Erst atomare Anlage, Verzeichnissynchronisation und vollständige Rücklesung
erlauben die Freigabe nur des aktuellen Generation-Claims.

Ein Evidence-Retry wiederholt ausschließlich diese Claimfreigabe.

## Neutrale Ausgabe und Retention

Der spätere Command liefert nur `runtime_removed_pending_cleanup_finalization`,
`rejected` oder technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Private IDs, Generation, Hashes, Ressourcen, Pfade und Zeiten bleiben verborgen.

Alle IDs, Claims, Autorisierungen und Evidencegenerationen bleiben mindestens
für Audit, Retry, Reconciliation, Fortsetzung und LQ-343 unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden; eine
konkrete Retentionfrist wird nicht festgelegt.

## Nichtziele und Bundle

LQ-364 implementiert keine Reconciliation, Finalisierung, automatische
Schleife, LQ-343-Ausführung, Ressourcen- oder Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 46 Entry Points, 50 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-365 sollte den generationengebundenen Continuation-Operator mit geschlossenem
Vorgängerresolver und Fake-basierten Tests implementieren.

Reconciliation und Finalisierung jeder Generation bleiben getrennte spätere
Slices.
