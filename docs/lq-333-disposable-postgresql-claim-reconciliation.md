# LQ-333 — Disposable PostgreSQL Claim Reconciliation

## Ergebnis

LQ-333 installiert `liquent-disposable-postgres-claim-reconcile` als
separat autorisierten Evidence-first-Operator für einen nach LQ-332
verbliebenen Reconciliation-Claim.

Der Operator bestätigt bereits vorhandene exakte Evidence oder klassifiziert
den aktuellen Runbestand erneut ausschließlich read-only.

Er entfernt nur private Claims nach bestätigter Evidence. PostgreSQL-
Container, Netze und Volumes bleiben unverändert.

## Dritte Autorisierungsgrenze

Historische Staging- und Reconciliation-Autorisierungen gewähren kein
Force-Unlock oder späteres Reconciliationrecht.

Der Operator verlangt eine neue owner-only Claim-Reconciliation-Datei mit:

- Schema-Version und stabiler Claim-Reconciliation-ID;
- ursprünglicher Reconciliation-ID und Run-ID;
- Phase `disposable_postgres`;
- Source-Commit, Application-Image-Digest und Compose-SHA-256;
- ursprünglichen Reconciliation-Executor-/Autorisiereridentitäten;
- getrennten neuen Executor-/Autorisiereridentitäten;
- aktuellem UTC-Zeitfenster von höchstens einer Stunde.

Sie enthält keinen gewünschten Ausgang, Claimpfad, Ressourcennamen,
Delete-Boolean, Resume-, Cleanup- oder Deploymentrecht.

## Historische Bindung

Die ursprüngliche Staging-Autorisierung und LQ-331-Reconciliation-
Autorisierung werden strukturell vollständig an ihrem damaligen gültigen
Zeitpunkt rekonstruiert.

Run, Phase, Source, Image, Composehash und ursprüngliche Identitäten müssen in
allen drei Autorisierungen exakt übereinstimmen.

Der Projektname wird erneut nur aus der ursprünglichen Run-ID akzeptiert.

Jede Abweichung endet vor Evidence-, Claim- oder Dockerzugriff detailfrei
unavailable.

## Eigene Konkurrenzordnung

Die Claim-Reconciliation-ID leitet intern einen eigenen Evidencepfad und
einen eigenen Claim über vollständigen SHA-256 ab.

Vor neuer Arbeit wird exakte bestehende Claim-Reconciliation-Evidence geprüft.
Sie muss regulär, 0600, aktueller-Owner-besessen, Linkcount eins und vollständig
an alle historischen und neuen Werte gebunden sein.

Exakte Evidence liefert denselben neutralen Handoff vor Docker zurück. Ein
gültiger eigener Restclaim darf danach entfernt werden.

Ohne Evidence wird der eigene Claim exklusiv, no-follow und 0600 erzeugt,
inhaltlich fest geschrieben und fsynct. Ein vorhandener eigener Claim ohne
Evidence verhindert jede automatische Wiederholung.

## Ausgangszustände

Fehlen ursprünglicher LQ-332-Claim und ursprüngliche Evidence gemeinsam, wird
`not_found` ohne Docker klassifiziert.

Fehlt der Claim, aber exakte ursprüngliche Evidence existiert, wird
`already_finalized` klassifiziert.

Existieren ursprünglicher Claim und exakte Evidence gemeinsam, ist der Claim
nur ein nach Evidencepublikation verbliebener Ordnungsrest. Der Operator
publiziert zuerst eigene Evidence mit `evidence_confirmed` und entfernt danach
den exakt validierten ursprünglichen Claim.

Beschädigte, ähnlich benannte oder anders gebundene Claims und Evidence werden
nicht übernommen oder entfernt.

## Read-only Neuklassifikation

Existiert der exakte ursprüngliche Claim ohne finale LQ-332-Evidence, führt
LQ-333 die reine LQ-331-Klassifikation erneut aus.

Die historische Reconciliation-Datei wird dazu in ihrem ursprünglichen
Zeitfenster validiert; die neue Claim-Reconciliation-Autorisierung muss
gleichzeitig aktuell sein.

Der Operator rendert Compose erneut, listet die vier abgeleiteten Ressourcen
und inspiziert vollständigen Bestand read-only. Er führt kein `up`, `down`,
Start, Stop, Remove oder Prune aus.

Der aktuelle neutrale Zustand wird als ursprüngliche LQ-332-Evidence
atomar festgehalten:

- `absent`;
- `isolated`;
- `conflict`.

Diese Evidence beschreibt die bestätigte aktuelle Reconciliation, nicht den
unbeobachtbaren exakten Zwischenzustand des früheren Unknown Outcomes.

## Evidence-first Finalisierung

Nach aktueller Klassifikation gilt die Reihenfolge:

1. ursprüngliche LQ-332-Evidence atomar publizieren und zurücklesen;
2. eigene Claim-Reconciliation-Evidence atomar publizieren und zurücklesen;
3. erst danach den ursprünglichen Claim entfernen und fsyncen;
4. zuletzt den eigenen Claim entfernen und fsyncen.

Eigene Handoff-Ausgänge sind:

- `absence_finalized`;
- `isolation_finalized`;
- `conflict_finalized`.

Ein Crash zwischen den Evidenceobjekten oder Claimschritten konvergiert beim
nächsten separat autorisierten Lauf über die jeweils sichtbare exakte
Evidence.

## Unknown Outcome

Jeder technische Fehler nach Erzeugung des eigenen Claims lässt vorhandene
Claims und Evidence unverändert soweit bereits dauerhaft sichtbar.

Es gibt keinen automatischen Retry, kein Claim-Ablaufdatum, kein
Altersheuristik-Unlock und kein erfundenes Ergebnis.

Ein zweiter direkter Aufruf mit vorhandenem Claim und ohne eigene Evidence
endet vor Docker unavailable.

## Neutraler Handoff

stdout enthält nur Schema-Version, Operation
`disposable_postgres_claim_reconciliation` und einen Ausgang:

- `already_finalized`;
- `evidence_confirmed`;
- `absence_finalized`;
- `isolation_finalized`;
- `conflict_finalized`;
- `not_found`.

IDs, Claims, Pfade, Digests, Ressourcen, Identitäten, Zeiten und Fehlerdetails
bleiben privat. Technische Fehler enden still mit Exitcode zwei.

Kein Ausgang ändert rückwirkend den LQ-330-Status oder autorisiert Migration,
Resume, Cleanup, Deployment oder Production.

## Tests

Tests beweisen Finalisierung aktueller Abwesenheit, Bestätigung vorhandener
Evidence ohne Docker, `not_found`, Unknown Outcome mit beiden verbleibenden
Claims und exakte Evidence-first-Wiederholung.

Abweichende aktuelle Autorisierung stoppt vor Docker. Die CLI gibt nur den
kanonischen Handoff oder bei technischem Fehler gar nichts aus.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 32 Entry Points und 36
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

Es gibt keine PostgreSQL-Ressourcenentfernung, keinen erneuten Start, keine
Migration, SQL-, Schema-, Port-, Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-334 sollte den separaten Dispositionsvertrag für finalisierte
Reconciliation-Evidence definieren. Er muss Retain, einen vollständig neuen
autorisierten Run und gegebenenfalls eng begrenztes Cleanup trennen, bevor
irgendeine Ressourcenentfernung implementiert wird.
