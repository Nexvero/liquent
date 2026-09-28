# LQ-380 — Evidence-first Bounded Generation Lineage Finalizer

## Ergebnis

LQ-380 erweitert
`liquent-disposable-postgres-cleanup-generation-finalize` um die
evidence-first Finalisierung ab Generation drei.

Generation eins und zwei behalten ihre bisherigen direkten Resolver und
Eingaben.

## Gemeinsamer Lineage-Resolver

Ab Generation drei verwendet der Finalizer denselben begrenzten Resolver wie
LQ-378 und LQ-379.

Die geordneten Folgen enthalten exakt die Continuation- und
Finalisierungsautorisierungen der Generationen eins bis `n - 1`.

Ihre Länge muss vor historischen Reads zur aktuellen Generation passen und
darf die feste Obergrenze 16 nicht überschreiten.

Unvollständige, unterschiedlich lange, vertauschte, doppelte oder zu lange
Lineages bleiben detailfrei technisch unavailable.

## Vollständige Vertrauenskette

Der erste Eintrag muss Generation eins direkt an LQ-362 binden.

Jedes weitere Paar muss dieselbe Generation, Root-Kette und gebundene
Continuation-Fakten tragen.

Autorisierung und Evidence der unmittelbar vorherigen Finalisierung werden
hashgenau gebunden. Alle historischen Autorisierungen werden an ihrem eigenen
Fenstermittelpunkt erneut vollständig validiert.

Eine ältere, übersprungene oder caller-selektierte Generation begründet keine
Finalisierungsautorität.

## Historische Präfixe und Ausgänge

Jeder effektive Präfix wird erneut aus der direkten
Vorgänger-Finalization-Evidence berechnet.

`generation_continuation_attempt_finalized` erhält den Vorgängerpräfix;
`later_prefix_finalized` ergibt exakt `application_network_removed`.

Nur diese beiden nichtterminalen Ausgänge dürfen innerhalb einer Lineage
stehen.

Terminale, neutrale, konfliktbehaftete, unbekannte oder malformed Evidence
stoppt fail-closed.

## Separate aktuelle Autorisierung

Die aktuelle owner-only Finalisierungsautorisierung bindet Finalization-,
Reconciliation- und Continuation-ID, Generation, direkten Vorgänger,
vollständige Root-Kette und SHA-256 der LQ-379-Autorisierung.

Operation bleibt exakt
`finalize_disposable_postgres_cleanup_generation_continuation`, Scope
`runtime_only` und das aktuelle UTC-Fenster höchstens eine Stunde.

Executor und Autorisierer sind getrennt. Caller liefern keinen Zustand,
Ausgang, Claimstatus, Präfix oder Freigabebool.

## Historische Claim-Gates

Alle Claims der Lineage müssen exakt fehlen. Ein vorhandener historischer Claim
wird vollständig validiert und anschließend abgewiesen.

Der Finalizer entfernt oder repariert keinen historischen Claim.

LQ-345-, LQ-351- und LQ-358-Claims müssen ebenfalls fehlen; der ursprüngliche
LQ-339-Cleanup-Claim bleibt exakt offen.

Nur der aktuelle Generation-Claim darf nach eigener atomarer Evidence
freigegeben werden.

## Frische LQ-379-Reconciliation

Fehlt passende aktuelle Finalization-Evidence, führt der Finalizer den
LQ-379-Inspector frisch am historischen Fenstermittelpunkt der gebundenen
Reconciliation aus.

Dabei reicht er dieselben geordneten Lineage-Folgen unverändert weiter.

Ein gespeicherter oder caller-gelieferter Zustand oder Ausgang wird nicht
akzeptiert.

Die Inspector-Ausgabe muss exakt die geschlossene neutrale Struktur tragen.

## Geschlossene Finalisierungsmatrix

Vier Inspector-Zustände werden fest abgebildet:

- vorhandene Continuation-Evidence →
  `generation_continuation_evidence_confirmed`;
- nicht gestarteter Versuch → `generation_continuation_attempt_finalized`;
- Application-Network entfernt → `later_prefix_finalized`;
- Runtime vollständig entfernt →
  `runtime_removal_ready_for_cleanup_finalization`.

`not_found` bleibt neutral `not_found`; `conflict` wird neutral zu
`investigation_required`.

Andere Zustände bleiben technisch unavailable.

## Evidence-first-Freigabe

Bei einem finalisierbaren Zustand schreibt der Finalizer zuerst private,
kanonische und immutable Finalization-Evidence.

Sie bindet die vollständige aktuelle Autorisierung, ihren SHA-256, Generation,
direkten Vorgänger, frisch beobachteten Zustand, geschlossenen Ausgang sowie
Start- und Abschlusszeit.

Erst nach atomarem Write, Verzeichnis-Sync und vollständigem Rücklesen darf der
aktuelle Claim entfernt und dessen Entfernung synchronisiert werden.

Ein Schreib- oder Rücklesefehler lässt den Claim offen und endet unavailable.

## Neutrale Ausgänge

`not_found` und `investigation_required` schreiben keine
Finalization-Evidence und lösen keinen Claim.

Sie verändern weder Cleanup-Claim noch aktuellen Claim oder historische
Lineage-Artefakte.

Neutrale Abwesenheit wird nicht als Runtime- oder Cleanup-Abschluss
umgedeutet.

Technische Nichtverfügbarkeit bleibt ohne neutrales Ergebnisobjekt getrennt.

## Sicherer Retry

Ist exakte aktuelle Finalization-Evidence bereits vorhanden, wird sie
vollständig validiert und ihr gespeicherter Ausgang wiederverwendet.

Der Retry überspringt LQ-379 und damit jeden Dockerzugriff.

Nur ein noch vorhandener exakt gebundener aktueller Claim wird freigegeben.
Historische Claims oder Lineage-Dateien bleiben unverändert.

Damit kann ein unbekannter Ausgang der Claimfreigabe ohne neue Beobachtung
sicher beendet werden.

## Terminaler Handoff

`generation_continuation_evidence_confirmed` und
`runtime_removal_ready_for_cleanup_finalization` führen ausschließlich zum
bestehenden LQ-343-Abschlussweg.

`generation_continuation_attempt_finalized` und `later_prefix_finalized`
dürfen eine neue separat autorisierte Generation begründen, sofern die
Obergrenze nicht erreicht ist.

Kein Ausgang startet den nächsten Schritt automatisch.

## CLI

Die bestehende CLI erhält dieselben zwei wiederholbaren Lineage-Optionen wie
Continuation und Inspector.

Generation eins und zwei weisen Lineage-Optionen zurück. Ab Generation drei
werden die bisherigen einzelnen Vorgängeroptionen zurückgewiesen.

Erfolg gibt nur Schema-Version, Operation und geschlossenen Ausgang aus;
technische Nichtverfügbarkeit endet detailfrei mit Exitcode 2.

## Tests

Sieben neue Tests decken vier finalisierbare Generation-3-Zustände, zwei
neutrale Zustände und den Evidence-first-Retry nach unbekanntem
Claimfreigabeausgang ab.

Sie prüfen Generation drei in der Evidence, unveränderte historische Lineage,
Erhalt des Cleanup-Claims und Freigabe ausschließlich des aktuellen Claims.

Zusammen mit Generation eins und zwei bestehen 21 fokussierte
Finalizer-Tests und 63 Prüfungen der vollständigen Generation-Kette.

## Bundle und Nichtziele

LQ-380 erweitert nur das bestehende Finalizer-Modul und dessen bestehenden
Entry Point. Bundle-Gates bleiben bei 49 Entry Points, 53 Operatormodulen, 27
Migrationen und Head `20260819_0027`.

Keine automatische Folgegeneration, LQ-343-Ausführung, Ressourcenmutation,
Volume-Löschung, Migration, Persistenz, Port-, Modell-, Compose- oder
Production-Wiring-Entscheidung wird ergänzt.

## Nächster Slice

LQ-381 sollte die vollständige begrenzte Generation-Lineage-Kette auditieren,
einschließlich Generation drei und der nachgewiesenen Wiederholbarkeit bis zur
festen Obergrenze.
