# LQ-325 — Owner-controlled Artifact Probe Recovery Claim Reconciliation

## Ergebnis

LQ-325 installiert `liquent-artifact-probe-recovery-reconcile` als getrennten
owner-only Operator für verbliebene LQ-323-Recovery-Claims.

Der Operator folgt dem LQ-324-Vertrag evidence-first. Ohne finale
Recovery-Evidence verwendet er ausschließlich LQ-320 mit read-only
Artifactvolume; LQ-321 wird niemals aufgerufen.

Alle lokalen Tests injizieren Prozessbeobachtungen. Es findet kein realer
Docker- oder Volumezugriff statt.

## Autorisierungsbindung

Der Operator lädt drei private Dateien:

- historische ursprüngliche Staging-Autorisierung;
- historische Recovery-Autorisierung;
- aktuelle Reconciliation-Autorisierung von höchstens einer Stunde.

Die Reconciliation bindet stabile Reconciliation- und Recovery-ID, Run, Phase,
Source-Commit, Image-Digest, Compose-SHA-256, ursprüngliche
Recoveryidentitäten sowie getrennte Reconciliationidentitäten.

Alle Bindungen müssen bytegenau übereinstimmen. Token, Prefix, Volume,
gewünschter Ausgang oder Cleanup-Boolean sind keine Eingaben.

## Private Dateigrenze

Das bestehende owner-only Evidenceverzeichnis wird über dieselbe no-follow
Grenze wie LQ-323 geöffnet.

Recovery-Claim und finale Recovery-Evidence werden ausschließlich aus dem
SHA-256 der Recovery-ID abgeleitet. Reconciliation-Claim und -Evidence werden
separat aus dem SHA-256 der Reconciliation-ID abgeleitet.

Claims müssen regulär, Owner des aktuellen Prozesses, Modus 0600, Linkcount eins
und exakt inhaltlich an ihre feste Operatorart gebunden sein.

Beschädigte oder ähnlich benannte Dateien werden nicht entfernt.

## Reconciliation-Konkurrenz

Fehlt finale Reconciliation-Evidence, erzeugt der Operator exklusiv einen
stabilen Reconciliation-Claim und fsynct das Verzeichnis vor weiterer Arbeit.

Ein vorhandener Claim verhindert einen zweiten konkurrierenden Lauf. Es gibt
kein Warten, Claim-Stealing, Timeout-Reaping oder Force-Unlock.

Nach bestätigter Reconciliation-Evidence wird der Reconciliation-Claim gezielt
entfernt und das Verzeichnis erneut fsynct.

## Bereits finale Recovery

Existiert gültige finale Recovery-Evidence, wird kein Compose- oder
Dockerprozess gestartet.

Mit vorhandenem Recovery-Claim lautet die Reconciliation
`evidence_confirmed`; ohne Claim `already_finalized`.

Die bestehende Recovery-Evidence bleibt unverändert. Reconciliation publiziert
eine getrennte atomare Evidence und entfernt erst danach einen exakt gültigen
verbliebenen Recovery-Claim.

## Fehlender Recoveryfall

Fehlen finale Recovery-Evidence und Recovery-Claim gemeinsam, lautet der
Ausgang `not_found`.

Es wird keine Recovery-Evidence erfunden und kein Dockerprozess gestartet. Die
neutrale Reconciliation-Evidence hält ausschließlich diesen beobachteten
Abschluss fest.

## Read-only Prefixinspektion

Nur bei vorhandenem gültigem Recovery-Claim ohne finale Recovery-Evidence
werden Compose und das Artifactvolume geprüft.

Composefile und Environmentdateien werden erneut gebunden. Alle statischen
Workergrenzen und das autorisierte Image müssen passen; Volume und Token werden
intern bestimmt.

Der einzige Container nutzt Netzwerk `none`, read-only Root, UID/GID 10001,
Capability-Drop, feste Ressourcenlimits und genau das Artifactvolume read-only.
Er startet ausschließlich den absoluten LQ-320-Entrypoint.

Secrets, Workerinputs, Researchdaten, Ports und read-write Mounts fehlen.

## Bestätigte Abwesenheit

Nur LQ-320-`absent` erzeugt atomar finale Recovery-Evidence mit dem neuen
neutralen Ausgang `absence_confirmed_after_unknown`.

Danach wird getrennte Reconciliation-Evidence `absence_finalized` publiziert.
Erst nach Fsync und Read-back beider Evidenceobjekte wird der Recovery-Claim
entfernt.

Der Ausgang behauptet weder einen früheren Remove-Erfolg noch ursprüngliche
Abwesenheit. Die Stagingphase bleibt unavailable.

## Retained-Zustände

LQ-320-`recoverable` und `conflict` werden einheitlich als `retained`
finalisiert.

Der Recovery-Claim und das Artifactvolume bleiben unverändert. Es gibt keinen
Remove-Entrypoint, keinen zweiten Container und kein read-write Volume.

Technische Nichtverfügbarkeit erzeugt keine scheinbare Reconciliation-Evidence
und behält den Reconciliation-Claim für kontrollierte spätere Auflösung.

## Atomare Evidence

Recovery- und Reconciliation-Evidence werden kanonisch in exklusive 0600-
Temporärdateien geschrieben, fsynct, per Hardlink veröffentlicht, auf Linkcount
eins reduziert und vollständig zurückgelesen.

Bestehende Ziele werden nie ersetzt. Abweichende Wiederverwendung derselben ID
endet detailfrei unavailable.

Reconciliation-Evidence bindet alle historischen Werte, beide IDs, beide
Identitätspaare, neutralen Ausgang und aware-UTC-Abschlusszeit.

## Evidence-first-Konvergenz

Exakte technische Wiederholung liest finale Reconciliation-Evidence vor Claim,
Compose und Docker und liefert denselben Ausgang ohne neue externe Wirkung.

Sind nach einem Crash bereits Evidence, aber Recovery- oder Reconciliation-
Claim noch vorhanden, validiert und entfernt der Retry ausschließlich diese
exakten Claims und fsynct das Verzeichnis.

Damit konvergiert ein Crash zwischen Evidencepublikation und Claimentfernung
ohne erneute Volumeinspektion.

## Ausgabe und Fehler

stdout enthält nur Schema-Version, Operation
`artifact_probe_recovery_reconcile` und einen Ausgang:

- `already_finalized`;
- `evidence_confirmed`;
- `absence_finalized`;
- `retained`;
- `not_found`.

Malformed Input, Bindungskonflikt, beschädigte Datei, vorhandener
Reconciliation-Claim oder technischer Prozess-/I/O-Ausgang endet still mit
detailfreiem Exitcode zwei.

## Bundle und Nichtziele

Der neue Entry Point und das Operatormodul erhöhen die Gates auf 29 Entry
Points und 32 Operatormodule. Migrationen bleiben 27 mit Head
`20260819_0027`.

Es gibt keine Persistenztabelle, SQL-, Migration-, Port-, Domainmodell-,
Compose-, Production-Wiring-, LQ-321- oder reale Stagingwirkung.

## Nächster Slice

LQ-326 sollte die vollständige Artifact-Capability- und Recoverykette von
LQ-316 bis LQ-325 als End-to-End-Audit prüfen, Bundle-/CLI-Inventar abgleichen
und verbleibende operative Blocker für einen ausdrücklich autorisierten realen
Staginglauf benennen.
