# LQ-378 — Bounded Generation Lineage Continuation

## Ergebnis

LQ-378 erweitert den bestehenden
`liquent-disposable-postgres-cleanup-generation-continue` um Generation drei
und eine gemeinsame begrenzte historische Lineage-Auflösung.

Generation eins und zwei behalten ihre bisherigen geschlossenen Resolver und
Eingaben unverändert.

## Begrenzte Lineage

Ab Generation drei verlangt der Operator zwei gleich lange geordnete Folgen
privater Continuation- und Finalisierungsautorisierungen.

Die Folgen enthalten exakt Generation eins bis `n - 1`. Ihre Länge wird vor
historischen Reads gegen die aktuelle Generation und die feste Obergrenze 16
geprüft.

Leere, unterschiedlich lange, unvollständige, vertauschte, überzählige oder
oberhalb der Grenze liegende Folgen bleiben detailfrei technisch unavailable.

Der Grenzwert ist nicht caller-konfigurierbar und erweitert kein
Mutationsbudget.

## Genesis-Validierung

Der erste Eintrag muss Generation eins mit Vorgängerart `lq362` und
Vorgängergeneration null sein.

Die vollständige LQ-362-Finalisierungsautorisierung wird an ihrem historischen
Fenstermittelpunkt erneut validiert.

Root-Kette, historischer Präfix sowie Autorisierungs- und Evidencehash müssen
exakt übereinstimmen.

Nur `chained_continuation_attempt_finalized` oder `later_prefix_finalized`
bilden einen zulässigen Genesis-Ausgang.

## Direkte Paarverkettung

Jede historische Continuation- und Finalisierungsautorisierung wird vollständig
an ihrem eigenen Fenstermittelpunkt validiert.

Beide Dateien eines Paars müssen dieselbe Generation und dieselben gebundenen
Continuation-Fakten tragen. Die Finalisierung muss den SHA-256 der exakten
Continuation-Autorisierung binden.

Ab Generation zwei müssen Vorgängergeneration, Vorgängerart, Root-Kette,
historischer Präfix sowie Hashes der unmittelbar vorherigen
Finalisierungsautorisierung und Evidence exakt übereinstimmen.

Eine ältere, übersprungene, doppelte oder alternativ ausgewählte Generation
bleibt unavailable.

## Präfixfortschreibung

Der Resolver berechnet jeden historischen effektiven Präfix erneut aus dem
direkten Finalisierungsausgang.

Bei `generation_continuation_attempt_finalized` bleibt der Präfix des
Vorgängers erhalten; bei `later_prefix_finalized` wird er exakt
`application_network_removed`.

Die gespeicherte Continuation muss diesem Ergebnis entsprechen. Ein korrekter
Hash allein kann eine falsche Präfixfortschreibung nicht legitimieren.

Dieselbe Regel wird anschließend zwischen dem letzten Lineage-Eintrag und der
aktuellen Generation angewendet.

## Evidence und Ausgänge

Jede historische Finalization-Evidence wird aus ihrer nicht
wiederverwendbaren Finalization-ID abgeleitet und owner-only, kanonisch sowie
hashgenau geprüft.

Nur `generation_continuation_attempt_finalized` und
`later_prefix_finalized` sind innerhalb der Lineage zulässig.

Terminale, neutrale, konfliktbehaftete, unbekannte oder malformed Evidence
erteilt keine Folgeautorität.

## Historische Claims

Für jeden Lineage-Eintrag wird der Claimname ausschließlich aus SHA-256 seiner
Continuation-ID abgeleitet.

Jeder historische Claim muss exakt fehlen. Ein vorhandener Claim wird
vollständig validiert, aber niemals durch die aktuelle Generation entfernt.

Malformed oder fremde Claims bleiben unavailable. Der ursprüngliche
LQ-339-Cleanup-Claim muss weiterhin exakt offen sein.

## Generation drei

Generation drei verwendet eine Lineage aus genau zwei Paaren: Generation eins
und Generation zwei.

Ihre aktuelle Autorisierung bindet Generation zwei als direkten Vorgänger,
die exakte Generation-2-Finalisierungsautorisierung und deren Evidence.

Nach vollständiger Lineage-Auflösung gelten unverändert die bestehende frische
LQ-341-Zustandsprüfung, Claimanlage und minimale Restmutation.

Ein caller-gelieferter Zustand, Ausgang oder wirksamer Präfix wird nicht
akzeptiert.

## Unveränderte Mutationsgrenze

Nur exakte frische Übereinstimmung mit dem autoritativ abgeleiteten Startpräfix
erreicht den aktuellen Claim und Docker.

Ab `container_removed` dürfen nur Application- und Data-Network entfernt und
jeweils als abwesend bestätigt werden. Ab `application_network_removed`
entfällt der erste Schritt.

Danach wird ausschließlich das erhaltene rungebundene Volume read-only auf
Identität geprüft.

Containeroperationen, Compose-Down, Force, Prune, Disconnect, SQL,
Volumezugriff und Volume-Löschung bleiben ausgeschlossen.

## Unknown Outcome und Evidence-first

Die bestehende Unknown-Outcome-Grenze bleibt unverändert: Ab dem ersten Remove
bleiben Cleanup- und aktueller Generation-Claim bei technischem Mehrdeutigkeit
offen.

Nach bestätigter Entfernung schreibt der Operator aktuelle private Evidence
atomar vor Freigabe ausschließlich des aktuellen Claims.

Ein Evidence-Retry wiederholt nur diese Claimfreigabe und keinen Dockeraufruf.

Historische Lineage-Artefakte und Claims werden niemals geschrieben,
überschrieben oder entfernt.

## CLI

Die bestehende CLI erhält je eine wiederholbare Option für historische
Continuation- und Finalisierungsdateien.

Positionen gleicher Reihenfolge bilden ein Paar; Anzahl und kanonische
Generationen werden intern vollständig validiert.

Generation eins und zwei weisen Lineage-Optionen zurück. Ab Generation drei
werden die bisherigen einzelnen Vorgängeroptionen zurückgewiesen.

Technische Nichtverfügbarkeit bleibt detailfrei bei Exitcode 2.

## Tests

Sechs neue Fake-basierte Tests decken beide nichtterminalen Generation-2-
Ausgänge als Generation-3-Basis ab.

Sie prüfen beide minimalen Mutationsbudgets, unvollständige und vertauschte
Lineages, einen wieder aufgetauchten historischen Claim und die Obergrenze vor
historischen Reads.

Zusammen mit Generation eins und zwei bestehen 46 fokussierte Prüfungen der
vollständigen Generation-Kette.

## Bundle und Nichtziele

LQ-378 erweitert nur das bestehende Continuation-Modul und dessen bestehenden
Entry Point. Bundle-Gates bleiben bei 49 Entry Points, 53 Operatormodulen, 27
Migrationen und Head `20260819_0027`.

Keine Inspector- oder Finalizer-Lineage, automatische Schleife, neue
Persistenz, Migration, Port-, Modell-, Compose- oder Production-Wiring-
Entscheidung wird ergänzt.

## Nächster Slice

LQ-379 sollte den bestehenden read-only Generation-Inspector auf denselben
begrenzten Lineage-Resolver erweitern.

Er muss Generation drei reconciliieren, ohne Claims, Evidence, Lineage oder
Ressourcen zu verändern.
