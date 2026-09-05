# LQ-371 — Owner-controlled Generation-two Runtime Cleanup Continuation

## Ergebnis

LQ-371 erweitert den bestehenden Command
`liquent-disposable-postgres-cleanup-generation-continue` um den direkten
LQ-369-Vorgängerresolver für Generation zwei.

Der Dockerpfad, das minimale Restbudget und die generationengebundene
Claim-/Evidencegrenze bleiben unverändert.

## Zwei geschlossene Vorgängertypen

Generation eins bleibt ausschließlich an nichtterminale LQ-362-Evidence
gebunden und akzeptiert keine Generation-Vorgängerdateien.

Generation zwei verlangt `predecessor_kind=repeatable_generation`,
Vorgängergeneration eins und zwei explizite private Vorgängerdateien.

Andere Generationen und Kombinationen bleiben fail-closed unavailable.

Der Operator wählt niemals anhand eines Caller-Flags zwischen mehreren
gültigen Vorgängern; die kanonische Generation bestimmt den einzigen Pfad.

## Direkte LQ-369-Bindung

Die Generation-1-Continuation-Autorisierung wird an ihrem historischen
Fenstermittelpunkt erneut validiert.

Die LQ-369-Finalisierungsautorisierung wird ebenfalls historisch vollständig
validiert und muss Generation eins beschreiben.

SHA-256 der vollständigen LQ-369-Autorisierung und der exakten
Finalization-Evidence müssen mit der Generation-2-Autorisierung übereinstimmen.

Nur `generation_continuation_attempt_finalized` oder
`later_prefix_finalized` begründen den neuen Versuch.

## Präfixableitung

`predecessor_resume_from` muss exakt dem effektiven Startpräfix der
Generation-1-Autorisierung entsprechen.

Bei `generation_continuation_attempt_finalized` bleibt dieser Präfix der neue
effektive `resume_from`.

Bei `later_prefix_finalized` ist der neue Präfix zwingend
`application_network_removed`.

Historischer und effektiver Präfix bleiben getrennt gebunden und können nicht
durch Callerwerte ersetzt werden.

## Historische Claim-Gates

Der ursprüngliche Cleanup-Claim muss offen und vollständig gebunden bleiben.

LQ-345- und LQ-351-Claims bleiben exakt abwesend. Die LQ-358-Bindung bleibt
Teil der unveränderten Root-Kette.

Der Generation-1-Claim wird aus seiner ID abgeleitet und muss exakt fehlen.

Ein vorhandener Claim wird vollständig validiert, aber weder entfernt noch als
neutraler Zustand behandelt.

Nur der neue Generation-2-Claim liegt innerhalb der Mutationsgrenze.

## Frische Zustandsbestätigung

Wie bei Generation eins führt der Operator LQ-341 unmittelbar vor Claimanlage
frisch und read-only aus.

Nur exakte Übereinstimmung mit dem aus LQ-369 abgeleiteten Präfix erreicht die
Mutation.

Ein lesbarer Mismatch ergibt `rejected` ohne Claim oder Dockeraufruf.

Technische Nichtverfügbarkeit bleibt ohne Ergebnis und Mutation.

## Unverändertes minimales Budget

Ab `container_removed` werden nur Application- und Data-Network einzeln
entfernt und jeweils exakt als abwesend bestätigt.

Ab `application_network_removed` wird ausschließlich das Data-Network
bearbeitet.

Danach wird nur die unveränderte rungebundene Volumeidentität read-only geprüft.

Containeroperationen, Compose-Down, Force, Disconnect, Prune, Volumezugriff,
SQL und gruppenbasierter Cleanup bleiben ausgeschlossen.

## Generation-2-Claim und Evidence

Claimname und Evidencename stammen ausschließlich aus SHA-256 der neuen
Generation-Continuation-ID.

Beide Artefakte binden Generation zwei, direkte LQ-369-Evidence, Root-Kette,
Präfixe, Restbudget, Ressourcen, Identitäten und UTC-Zeitpunkte.

Nach bestätigter Runtimeentfernung wird private Evidence exklusiv geschrieben,
synchronisiert, atomar final verlinkt und vollständig zurückgelesen.

Erst danach wird ausschließlich der aktuelle Generation-2-Claim freigegeben.

## Unknown Outcome und Retry

Jeder mehrdeutige Ausgang nach Claimanlage stoppt sofort mit offenem Cleanup-
und Generation-2-Claim.

Es gibt keinen Blind-Retry, Ersatzbefehl, heuristischen Erfolg oder
automatischen Folgeschritt.

Exakt vorhandene Generation-2-Evidence steuert ausschließlich den idempotenten
Claimrelease und führt kein Docker erneut aus.

## CLI und Tests

Die bestehende CLI erhält zwei optionale Pfade für Generation-Continuation- und
Finalization-Autorisierung des direkten Vorgängers.

Generation eins weist diese Pfade zurück; Generation zwei verlangt beide.

Vier neue Fake-basierte Tests decken beide nichtterminalen LQ-369-Ausgänge,
Zustandsmismatch und fehlenden direkten Vorgänger ab.

Zusammen mit Generation eins bestehen 15 fokussierte Continuation- und
Finalizer-Tests.

## Bundle und Nichtziele

Es entsteht kein neuer Entry Point oder Operatormodul. Bundle-Gates bleiben bei
49 Entry Points, 53 Operatormodulen, 27 Migrationen und Head `20260819_0027`.

LQ-371 implementiert keine Generation-2-Reconciliation oder Finalisierung,
keine automatische Schleife, LQ-343-Ausführung oder Volume-Löschung.

## Nächster Slice

LQ-372 sollte den read-only Reconciliation-Vertrag für einen offenen
Generation-2-Claim definieren.
