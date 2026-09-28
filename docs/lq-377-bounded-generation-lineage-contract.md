# LQ-377 — Bounded Generation Lineage Contract

## Zweck

LQ-377 definiert den beobachtbaren Vertrag für Generation drei und spätere
Runtime-Cleanup-Generationen.

Der Slice ersetzt keine bestehende Generation-1/2-Regel und implementiert
keinen Resolver, Operator, Claim, Writer oder Dockeraufruf.

## Anwendungsbereich

Der Vertrag gilt ausschließlich für eine neue Generation nach nichtterminaler
Finalisierung der unmittelbar vorherigen wiederholbaren Generation.

Generation eins bleibt direkt an LQ-362 gebunden. Generation zwei bleibt
direkt an Generation eins gebunden.

Ab Generation drei muss dieselbe Vertrauenskette ohne weitere fest benannte
Vorgängerparameter vollständig auflösbar sein.

## Kanonische Generation

Die aktuelle Generation ist eine positive kanonische Ganzzahl und genau eins
größer als die belegte direkte Vorgängergeneration.

Die Vorgängerart ist ab Generation zwei exakt `repeatable_generation`.

Sprünge, Duplikate, Rückschritte, Null, negative Werte und alternative
Vorgängerarten bleiben detailfrei technisch unavailable.

Die Generationszahl allein beweist weder Existenz noch Autorität.

## Endliche geordnete Lineage

Für eine aktuelle Generation `n` enthält die historische Lineage exakt die
Generationen eins bis `n - 1` in aufsteigender Reihenfolge.

Jeder Eintrag besteht logisch aus der Continuation-Autorisierung und der
Finalisierungsautorisierung derselben Generation.

Fehlende, zusätzliche, doppelte, vertauschte oder übersprungene Einträge
werden nicht normalisiert und bleiben unavailable.

Dateinamen, Verzeichnisreihenfolge und lexikalische Sortierung dürfen keine
Lineage oder Generation ableiten.

## Implementierungseigene Obergrenze

Die Zahl historischer Generationen muss vor vollständiger Artefaktvalidierung
gegen eine endliche implementierungseigene Obergrenze geprüft werden.

Die Obergrenze ist nicht caller-konfigurierbar und kein Mutations- oder
Retrybudget.

Eine oberhalb dieser Grenze liegende Generation bleibt fail-closed technisch
unavailable und wird weder abgeschnitten noch teilweise ausgewertet.

Der konkrete Grenzwert und die Transportdarstellung bleiben einer späteren
Implementierung samt Tests vorbehalten.

## Vollständiger Genesis-Anker

Der erste Lineage-Eintrag muss Generation eins, Vorgängergeneration null und
Vorgängerart `lq362` belegen.

Er muss die exakte LQ-362-Finalisierungsautorisierung und deren kanonische
Finalization-Evidence über die bereits gebundenen Hashes referenzieren.

Nur `chained_continuation_attempt_finalized` oder `later_prefix_finalized`
dürfen diesen Genesis-Übergang begründen.

Eine Lineage ohne diesen Anker oder mit einer Generation-Autorisierung als
Genesis bleibt unavailable.

## Direkte Verkettung jedes Paars

Für jede Generation `g > 1` muss deren Continuation unmittelbar auf die
Finalisierung von Generation `g - 1` zeigen.

Vorgängergeneration, Vorgängerart, Continuation-ID, Finalization-ID,
Autorisierungshash, Evidencehash und historischer Präfix müssen gemeinsam
übereinstimmen.

Die Root-Kette von Run, Disposition, Cleanup, LQ-349, LQ-355 und LQ-362 muss in
jedem Eintrag unverändert bleiben.

Ein Eintrag darf keine ältere Generation direkt auswählen oder mehrere
alternative Vorgänger anbieten.

## Historische Autorisierungen

Jede historische Continuation- und Finalisierungsautorisierung wird mit ihrem
damaligen Schema vollständig am Mittelpunkt ihres eigenen Gültigkeitsfensters
validiert.

Ein späteres aktuelles Fenster verlängert, ersetzt oder repariert keine
historische Autorisierung.

Unbekannte Felder, malformed Zeiten, abweichende Operationen, Scopes,
Identitäten oder Root-Bindungen bleiben unavailable.

Executor und Autorisierer bleiben in jeder historischen Generation getrennt.

## Historische Finalization-Evidence

Zu jeder historischen Finalisierungsautorisierung muss genau die aus ihrer
nicht wiederverwendbaren Finalization-ID abgeleitete private Evidence bestehen.

Sie wird owner-only, regulär, single-link, kanonisch und hashgenau validiert.

Nur `generation_continuation_attempt_finalized` und `later_prefix_finalized`
dürfen innerhalb einer Lineage auf eine Folgegeneration zeigen.

`generation_continuation_evidence_confirmed` und
`runtime_removal_ready_for_cleanup_finalization` sind terminal und verweisen
ausschließlich auf LQ-343.

Neutrale, konfliktbehaftete, unbekannte oder technisch nicht verfügbare
Ausgänge erteilen keine Folgeautorität.

## Präfixfortschreibung

Bei `generation_continuation_attempt_finalized` bleibt der effektive Präfix der
Folgegeneration exakt der Startpräfix des direkten Vorgängers.

Bei `later_prefix_finalized` ist der effektive Präfix der Folgegeneration
exakt `application_network_removed`.

Zulässig bleiben nur `container_removed` und
`application_network_removed`.

Jeder Eintrag bindet historischen Vorgängerpräfix und eigenen effektiven
Präfix getrennt; Fortschritt darf nicht als historischer Start umgedeutet
werden.

## Historische Claim-Abwesenheit

Zu jeder vollständig finalisierten historischen Generation muss der aus ihrer
Continuation-ID abgeleitete Claim exakt fehlen.

Ein vorhandener historischer Claim wird vollständig validiert, aber niemals
von einem späteren Resolver, Inspector oder Finalizer entfernt.

Malformed oder fremde historische Claims bleiben unavailable und werden nicht
als neutrale Abwesenheit behandelt.

Der ursprüngliche LQ-339-Cleanup-Claim muss dagegen weiterhin exakt offen
bleiben.

## Lineage ist keine Autorisierung

Die Lineage transportiert historische System-of-Record-Fakten, gewährt aber
allein keine aktuelle Mutation, Reconciliation oder Finalisierung.

Jeder aktuelle Schritt benötigt weiterhin seine eigene owner-only
Autorisierung mit neuer stabiler, nicht wiederverwendbarer ID und aktuellem
begrenztem UTC-Fenster.

Die aktuelle Autorisierung bindet Generation, direkten Vorgänger, dessen
Autorisierung und Evidence sowie die unveränderte Root-Kette.

Caller liefern keinen Allow-Bool, Zustand, Ausgang, Präfix, Restumfang oder
autoritativen Lineageabschluss.

## Continuation-Grenze

Vor Claimanlage validiert die Continuation die vollständige begrenzte Lineage
und führt LQ-341 frisch und read-only aus.

Nur exakte Übereinstimmung mit dem autoritativ fortgeschriebenen Präfix darf
den aktuellen Claim und das unveränderte minimale Restbudget erreichen.

Der Claim wird ausschließlich aus der aktuellen Continuation-ID abgeleitet und
erst nach der frischen Zustandsprüfung atomar angelegt.

Historische Claims, Evidence oder Autorisierungen werden nicht verändert.

## Reconciliation-Grenze

Der read-only Inspector validiert dieselbe vollständige Lineage und dieselbe
aktuelle direkte Vorgängerbindung.

Er prüft aktuelle Evidence vor Claim und führt nur bei offenem exakt gebundenem
Claim LQ-341 frisch aus.

Er schreibt oder entfernt keine Claims, Evidence oder Ressourcen.

Neutrale Abwesenheit und `conflict` bleiben von detailfreier technischer
Nichtverfügbarkeit getrennt.

## Finalisierungsgrenze

Der Finalizer validiert dieselbe Lineage, seine separate aktuelle
Autorisierung und ohne vorhandene eigene Evidence den Inspector frisch.

Er schreibt die aktuelle Finalization-Evidence atomar vor Freigabe nur des
aktuellen Claims.

Ein Evidence-Retry darf Inspector und Docker überspringen, aber keine
historische Claimfreigabe oder Folgemutation ausführen.

Terminale und nichtterminale Ausgänge behalten die geschlossene Matrix aus
LQ-375.

## Ressourcengrenze

Die Lineage erweitert weder Ressourcennamen noch Mutationsbudget.

Erlaubt bleiben höchstens die noch nicht bestätigten Network-Removes, deren
exakte Abwesenheitsprüfung und read-only Prüfung des erhaltenen Volumes.

Containeroperationen, Compose-Down, Force, Prune, Disconnect, SQL,
Volumezugriff und Volume-Löschung bleiben ausgeschlossen.

Keine Lineagegröße erlaubt Wiederholung eines bereits bestätigten Schritts.

## Retention und Nichtwiederverwendung

Alle Lineage-Autorisierungen, Claims und Evidence bleiben mindestens für Audit,
Retry, Reconciliation, Finalisierung, Folgegenerationen und LQ-343 eindeutig
unterscheidbar erhalten.

IDs, Generationen und Artefakte dürfen nicht unter anderer Root-, Run-,
Vorgänger-, Präfix- oder Ressourcenbindung wiederverwendet werden.

Claimfreigabe oder Erreichen der Implementierungsobergrenze verkürzt diese
Untergrenze nicht.

Eine konkrete Retentionfrist oder physische Ablagestruktur wird nicht
festgelegt.

## Keine automatische Schleife

Ein nichtterminal finalisierter Ausgang erlaubt nur die Beantragung einer
neuen separat autorisierten Generation.

Lineagevalidierung startet weder Continuation noch Inspector, Finalizer oder
LQ-343 automatisch.

Es gibt keinen rekursiven Selbstaufruf, Blind-Retry oder stilles Überspringen
einer nicht verfügbaren Generation.

## Nichtziele und Bundle

LQ-377 entscheidet keine Datei-, Manifest-, Listen-, Schema-, Tabellen-, SQL-,
Migration-, Port-, Modell-, Funktionssignatur-, CLI-, Compose- oder
Production-Wiring-Darstellung.

Es entsteht kein Operator, Entry Point, Test, Claim, Evidencewriter oder
Ressourcenmutator.

Bundle-Gates bleiben bei 49 Entry Points, 53 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-378 sollte die interne begrenzte Lineage-Auflösung implementieren und sie
zunächst in den bestehenden Continuation-Operator integrieren.

Inspector und Finalizer bleiben getrennte Folgeslices, müssen später denselben
Resolver ohne abweichende Historienlogik verwenden.
