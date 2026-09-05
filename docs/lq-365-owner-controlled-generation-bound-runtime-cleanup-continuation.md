# LQ-365 — Owner-controlled Generation-bound Runtime Cleanup Continuation

## Ergebnis

LQ-365 installiert
`liquent-disposable-postgres-cleanup-generation-continue` für die erste
wiederholbare Generation nach nichtterminaler LQ-362-Finalization-Evidence.

Der Operator übernimmt die gehärtete minimale LQ-358-Mutationsgrenze und
ersetzt den statischen LQ-355-Anker durch die direkte LQ-362-Bindung.

## Ausführbare Generation

Generation eins ist aktuell die einzige ausführbare Generation.

Sie verlangt `predecessor_kind=lq362`, `predecessor_generation=0` und bindet
LQ-362-Autorisierung sowie exakte Finalization-Evidence bytegenau.

Eine andere Generation oder Vorgängerart bleibt fail-closed unavailable.

Spätere Generationen werden erst nach eigener Reconciliation- und
Finalization-Evidence als sicherer Vorgängertyp geöffnet.

## Autorisierung

Die owner-only Autorisierung bindet Generation-Continuation-ID, Generation,
Vorgängerart, Vorgängergeneration und vollständige historische Root-Kette.

Sie bindet getrennt den historischen `predecessor_resume_from` und den aus dem
Vorgängerausgang abgeleiteten effektiven `resume_from`.

Operation ist exakt `continue_disposable_postgres_cleanup_from_generation`,
Scope exakt `runtime_only` und das aktuelle UTC-Fenster höchstens eine Stunde.

Executor und Autorisierer sind getrennt. Caller liefern keine Generation,
Vorgängerentscheidung, Ressourcen, Zustände oder Restbudgets.

## Direkte LQ-362-Evidence

Nur `chained_continuation_attempt_finalized` und `later_prefix_finalized`
begründen Generation eins.

Bei Nichtstart bleibt der historische Startpräfix erhalten. Bei späterem
Fortschritt wird der effektive Präfix `application_network_removed`.

Terminale, neutrale, konfliktbehaftete, beschädigte oder anders gebundene
Evidence bleibt detailfrei unavailable.

## Claim-Gates

Der ursprüngliche Cleanup-Claim muss vollständig gebunden offen sein.

Historische LQ-345- und LQ-351-Claims müssen exakt fehlen. Der durch LQ-362
freigegebene LQ-358-Claim bleibt ebenfalls außerhalb der Mutationsgrenze.

Der neue Claimname stammt ausschließlich aus SHA-256 der
Generation-Continuation-ID.

Vorhandene oder malformed Claims werden weder ersetzt noch freigegeben.

## Frische Zustandsbestätigung

Vor Claimanlage führt der Operator LQ-341 mit historischer
Cleanup-Reconciliation-Autorisierung frisch und read-only aus.

Nur exakte Übereinstimmung mit dem autoritativ abgeleiteten `resume_from`
erreicht die Mutation.

Ein lesbarer Mismatch ergibt `rejected` ohne Claim oder Dockeraufruf.
Technische Nichtverfügbarkeit bleibt ohne Ergebnis.

## Minimale Mutation

Ab `container_removed` werden ausschließlich Application- und Data-Network
einzeln entfernt und jeweils exakt als abwesend bestätigt.

Ab `application_network_removed` wird nur das Data-Network bearbeitet.

Danach wird das unveränderte rungebundene Datenvolume read-only geprüft.

Containeroperationen, Compose-Down, Force, Disconnect, Prune, Volumezugriff,
SQL sowie Wildcard-, Präfix-, Label- und Gruppencleanup sind ausgeschlossen.

## Claim und Evidence

Der neue Claim wird owner-only exklusiv angelegt und synchronisiert. Er bindet
Generation, Vorgänger, Root-Kette, Präfix, Restbudget und Ressourcen.

Nach bestätigter Runtimeentfernung entsteht private generationengebundene
Evidence mit `runtime_removed_pending_cleanup_finalization`.

Sie wird exklusiv geschrieben, synchronisiert, atomar final verlinkt und
vollständig zurückgelesen.

Erst danach wird ausschließlich der aktuelle Generation-Claim freigegeben.

## Unknown Outcome und Retry

Jeder mehrdeutige technische Ausgang nach Claimanlage stoppt sofort. Cleanup-
und Generation-Claim bleiben offen.

Es gibt keinen Blind-Retry, Ersatzbefehl, heuristischen Erfolg oder
automatischen Folgeschritt.

Vorhandene exakte Evidence steuert den idempotenten Retry ausschließlich zur
Freigabe des aktuellen Claims; Docker wird nicht erneut ausgeführt.

## Neutrale CLI

Die CLI liefert nur Schema-Version, Operation
`disposable_postgres_runtime_cleanup_generation_continuation` und
`runtime_removed_pending_cleanup_finalization` oder `rejected`.

Technische Nichtverfügbarkeit endet mit Exitcode 2 ohne stdout, stderr oder
private Details.

## Tests

Vier Fake-basierte Tests decken beide aus LQ-362 abgeleiteten Restbudgets,
Zustandsmismatch und unzulässige Generationsbindung ab.

Sie belegen, dass bestätigte Schritte nicht wiederholt und keine
Containeroperationen ausgeführt werden.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 47 Entry Points und 51
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-365 implementiert keine Generation-Reconciliation, Finalisierung,
automatische Schleife, LQ-343-Ausführung oder Volume-Löschung.

## Nächster Slice

LQ-366 sollte den read-only Reconciliation-Vertrag für einen offenen
generationengebundenen Claim definieren.

Erst dessen spätere Finalization-Evidence kann die direkte Vorgängerbasis für
Generation zwei und weitere Generationen bilden.
