# LQ-332 — Private PostgreSQL Reconciliation Evidence Handoff

## Ergebnis

LQ-332 ergänzt `liquent-disposable-postgres-reconcile` um private atomare
Evidence, eine stabile Konkurrenzordnung und einen detailarmen
Operator-Handoff.

Jede Reconciliation-ID kann genau ein Ergebnis für genau eine historische
Runbindung veröffentlichen. Exakte technische Wiederholung liest bestätigte
Evidence vor jedem Dockerzugriff zurück.

Ein unbekannter Ausgang nach Claim-Erzeugung wird nicht wiederholt oder
überschrieben.

## Privates Evidenceverzeichnis

Der installierte Command verlangt zusätzlich `--evidence-directory`.

Das Verzeichnis muss absolut, ein echtes nicht verlinktes Verzeichnis,
aktueller-Owner-besessen und ohne Group-/World-Rechte sein.

Der Command erzeugt darin ausschließlich Dateien, deren Namen intern aus dem
vollständigen SHA-256 der validierten Reconciliation-ID abgeleitet werden.

Caller können weder Evidence-Dateiname, Claimname, Ergebnis, Inhalt noch
Overwrite- oder Cleanup-Boolean angeben.

## Evidencebindung

Jeder Record bindet unveränderlich:

- Schema-Version;
- stabile Reconciliation-ID;
- ursprüngliche Run-ID und Phase `disposable_postgres`;
- Source-Commit und Application-Kandidatendigest;
- Compose-SHA-256;
- getrennte Reconciliation-Executor- und Autorisiereridentitäten;
- neutralen Ausgang `absent`, `isolated` oder `conflict`;
- UTC-Abschlusszeit.

Die Bindung wird aus der historischen Staging-Autorisierung und der aktuellen
LQ-331-Reconciliation-Autorisierung rekonstruiert. Es gibt keinen
caller-gelieferten Evidenceinhalt.

## Evidence-first Wiederholung

Nach vollständiger Autorisierungs- und Bindungsprüfung öffnet der Operator das
private Evidenceverzeichnis und sucht zuerst ausschließlich den exakt aus der
Reconciliation-ID abgeleiteten Record.

Eine reguläre 0600-Datei mit aktuellem Owner, Linkcount eins, geschlossener
Feldmenge und exakt passender Bindung liefert ihren neutralen Ausgang ohne
Compose- oder weiteren Dockerzugriff zurück.

Beschädigte Evidence, unbekannte Felder, Duplikatschlüssel, abweichender
Record, falsche Rechte oder Wiederverwendung derselben ID unter anderer
Bindung ist technisch unavailable.

Eine ähnliche oder anders benannte Datei wird nicht übernommen.

## Exklusiver Claim

Fehlt finale Evidence, erzeugt der Operator genau einen intern benannten
Claim mit `O_EXCL`, `O_NOFOLLOW`, Modus 0600 und festem detailarmem Inhalt.

Claimdatei und Verzeichnis werden vor der read-only Dockerklassifikation
fsynct.

Ein bereits vorhandener Claim ohne finale Evidence bedeutet einen früheren
oder konkurrierenden unbekannten Versuch. Der Operator startet dann keinen
zweiten Compose-Render oder Inspect und endet unavailable.

Der Claim ist weder Lock-Lease noch Force-Unlock-Ticket. Er läuft nicht
zeitgesteuert ab und darf nicht anhand seines Alters entfernt werden.

## Atomare Evidencepublikation

Nach vollständig bestätigtem LQ-331-Ausgang baut der Operator den Record
intern kanonisch auf.

Die Veröffentlichungsfolge ist:

1. neue intern benannte 0600-Tempdatei exklusiv öffnen;
2. vollständige kanonische Bytes schreiben;
3. Datei fsyncen und schließen;
4. exklusiv auf den finalen Evidencepfad hardlinken;
5. Tempnamen entfernen und Verzeichnis fsyncen;
6. finale Metadaten, Bindung und Ausgang vollständig zurücklesen;
7. erst danach den exakten Claim entfernen;
8. Verzeichnis erneut fsyncen.

Ein bestehender finaler Record wird niemals ersetzt, gekürzt oder umbenannt.

## Crash- und Unknown-Outcome-Grenze

Scheitert Compose-Render, Präsenzliste oder Inspect nach Claim-Erzeugung,
bleibt der Claim bestehen und finale Evidence fehlt.

Es gibt keinen automatischen zweiten LQ-331-Aufruf, kein Löschen des Claims,
kein erfundenes `conflict` und keine Ressourcemutation.

Scheitert die lokale Evidencepublikation nach möglichem finalem Link, muss ein
späterer kontrollierter Aufruf zuerst die sichtbare Evidence prüfen.

Existiert exakte finale Evidence gemeinsam mit einem übrig gebliebenen exakt
gültigen Claim, darf Evidence-first-Wiederholung nur diesen Claim entfernen,
das Verzeichnis fsyncen und denselben Ausgang zurückgeben.

Ein beschädigter Claim wird nie still entfernt.

## Neutraler Handoff

stdout bleibt das unveränderte LQ-331-Schema mit ausschließlich:

- `absent`;
- `isolated`;
- `conflict`.

Evidence- und Claimpfade, Reconciliation-ID, Run-ID, Digests, Identitäten,
Zeitwerte, Ressourcennamen und Fehlerdetails werden nicht ausgegeben.

Technische Nichtverfügbarkeit bleibt still mit Exitcode zwei.

Kein Ausgang ändert den ursprünglichen LQ-330-Phasenstatus oder gewährt
Fortsetzung, Cleanup, Deployment oder Productionzugriff.

## Retention und Nichtwiederverwendung

Reconciliation-ID, Autorisierungen, Claim und finale Evidence müssen
mindestens so lange unterscheidbar bleiben, wie Audit, Retry oder Interpretation
des unbekannten Ausgangs darauf angewiesen sind.

Eine Reconciliation-ID und ihr Evidencepfad dürfen nie unter neuer Runbindung
oder Bedeutung wiederverwendet werden.

Dieser Slice legt keine konkrete Frist, Tabelle, Archiv- oder Löschstrategie
fest.

## Tests

Tests beweisen private Evidencepublikation, Evidence-first-Wiederholung ohne
Docker, sichere Entfernung eines exakten übrig gebliebenen Claims und
Bindungskonflikt bei ID-Wiederverwendung.

Ein simulierter technischer Beobachtungsfehler hinterlässt Claim ohne Evidence;
der direkte Retry endet vor Docker. Breite Verzeichnisrechte scheitern vor
jedem Prozesszugriff.

## Bundle und Nichtziele

LQ-332 ergänzt weder Entry Point noch Operatormodul. Die Gates bleiben bei 31
Entry Points, 35 Operatormodulen, 27 Migrationen und Head `20260819_0027`.

Es gibt keine Claim-Reconciliation, Ressourcencleanup-, Resume-, SQL-,
Migration-, Schema-, Port-, Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-333 sollte einen separat autorisierten Claim-Reconciliation-Vertrag
implementieren. Er darf vorhandene exakte Evidence bestätigen oder den
aktuellen Ressourcenbestand erneut read-only klassifizieren, aber weder
LQ-330 wiederholen noch PostgreSQL-Ressourcen entfernen.
