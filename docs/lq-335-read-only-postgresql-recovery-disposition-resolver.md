# LQ-335 — Read-only PostgreSQL Recovery Disposition Resolver

## Ergebnis

LQ-335 installiert `liquent-disposable-postgres-disposition` als strikt
lokalen read-only Resolver für finalisierte LQ-332/333-Evidence.

Der Command leitet ausschließlich `retain`, `new_run_eligible`,
`cleanup_review_eligible` oder `investigation_required` aus dem privaten
System of Record ab.

Er führt keinen Dockerzugriff, keinen neuen Run und kein Cleanup aus.

## Eigene Dispositionsautorisierung

Der Resolver verlangt eine aktuelle owner-only Dispositionsdatei. Sie bindet:

- Schema-Version und stabile Disposition-ID;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, Application-Image-Digest und Compose-SHA-256;
- ursprüngliche Reconciliation-ID;
- Claim-Reconciliation-ID;
- SHA-256 der vollständigen Staging-Evidence;
- SHA-256 der vollständigen LQ-332-Evidence;
- SHA-256 der vollständigen LQ-333-Evidence;
- getrennte Executor-/Autorisiereridentitäten;
- ein aktuelles UTC-Zeitfenster von höchstens einer Stunde.

Sie enthält keinen gewünschten Ausgang, Cleanup-Boolean, Ressourcennamen,
neue Run-ID oder Rollenwert.

## Vollständige historische Bindung

Historische Staging-, Reconciliation- und Claim-Reconciliation-
Autorisierungen werden in ihren damaligen gültigen Zeitfenstern strukturell
vollständig rekonstruiert.

Run, Phase, Source, Image, Compose, Reconciliation-IDs und ursprüngliche
Identitäten müssen über die gesamte Kette exakt übereinstimmen.

Die aktuelle Dispositionsautorisierung muss dieselben Werte und die exakten
Evidencehashes binden.

Eine abweichende, beschädigte, breite, doppelt geschlüsselte oder technisch
nicht lesbare Datei endet detailfrei unavailable.

## Privates Evidence-System

Das Evidenceverzeichnis muss absolut, nicht verlinkt, aktueller-Owner-
besessen und ohne Group-/World-Rechte sein.

LQ-332- und LQ-333-Evidencepfade werden ausschließlich aus den validierten
IDs über vollständigen SHA-256 abgeleitet.

Beide Dateien müssen regulär, 0600, Linkcount eins, vollständig gebunden und
bytegenau durch die Dispositionsautorisierung gehasht sein.

Der zugrunde liegende LQ-332-Ausgang ist ausschließlich `absent`, `isolated`
oder `conflict`.

Der LQ-333-Ausgang muss semantisch dazu passen. Beispielsweise darf
`absence_finalized` nicht gemeinsam mit `isolated` auftreten.

## Geschlossene Claims

Vor jeder Disposition müssen der ursprüngliche LQ-332-Claim und der
LQ-333-Claim fehlen.

Ein vorhandener Claim ist technisch unavailable. Der Resolver liest weder
Alter noch Inhalt, entfernt ihn nicht und startet keine Claim-Reconciliation.

Damit kann ein unbekannter oder konkurrierender Abschluss nicht durch eine
Disposition übergangen werden.

## Gebundene Staging-Evidence

Die owner-only Staging-Evidence wird bytegenau gegen ihren autorisierten
SHA-256 geprüft.

Sie muss das geschlossene LQ-306-Schema mit exakt allen 29 Phasen besitzen und
Run, staging Environment, Source, Image, Compose, Migration-Head sowie
ursprüngliche Executor-/Autorisiereridentitäten binden.

Jeder Check besitzt ausschließlich Status, Evidence-Referenz und SHA-256.
`unavailable` verlangt beide Evidencewerte `null`; ausgeführte Checks
verlangen gültige opake Referenz und Digest.

Für `new_run_eligible` oder `cleanup_review_eligible` müssen
`disposable_postgres` und sämtliche späteren Phasen exakt unavailable sein.

Damit ist nachgewiesen, dass der ursprüngliche Executor nach dem unklaren
PostgreSQL-Ausgang weder Rollback, Migration-Gate, Worker, Control Plane,
Researchjob, Revocation noch Signalphase ausgeführt hat.

## Dispositionsabbildung

Finales `conflict` ergibt ausschließlich `investigation_required`.

Finales `absent` plus vollständig unavailable gebliebene Restphasen ergibt
`new_run_eligible`.

Finales `isolated` plus vollständig unavailable gebliebene Restphasen ergibt
`cleanup_review_eligible`.

Bei `absent` oder `isolated` mit strukturell gültiger Evidence eines späteren
Effekts lautet die sichere Disposition `retain`.

Fehlende oder widersprüchliche Evidence, offene Claims und technische Fehler
bleiben unavailable und werden nicht zu `retain` umgedeutet.

## Bedeutung der Ausgänge

`retain` verbietet jede Änderung und sagt nichts über spätere Eignung aus.

`new_run_eligible` startet keinen Run. Eine neue nicht wiederverwendete Run-ID
und vollständig neue Staging-Autorisierung bleiben zwingend.

`cleanup_review_eligible` ist kein Löschrecht. Es erlaubt nur, in einem
späteren Slice eine separate Cleanup-Autorisierung zu prüfen.

`investigation_required` gewährt weder Cleanup noch neuen Run und verändert
keine Evidence.

Kein Ausgang ist eine Staging-, Deployment-, Readiness- oder
Productionfreigabe.

## Neutrale CLI-Ausgabe

Erfolg schreibt nur kanonische Schema-Version, Operation
`disposable_postgres_disposition` und einen geschlossenen Ausgang.

IDs, Hashes, Pfade, Claims, Ressourcen, Identitäten, Zeitwerte und interne
Entscheidungsgründe bleiben privat.

Technische Nichtverfügbarkeit endet still mit Exitcode zwei und ohne
stdout/stderr.

## Tests

Tests erzeugen vollständige LQ-332/333-Evidenceketten für `absent`, `isolated`
und `conflict` und prüfen die drei strengeren Dispositionen.

Eine spätere ausgeführte Phase stuft isolierten Bestand auf `retain` zurück.
Hashabweichung und ein neu sichtbarer Claim enden unavailable. Die CLI gibt
nur den kanonischen Handoff oder nichts aus.

Kein Test startet Docker oder entfernt Ressourcen.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 33 Entry Points und 37
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-335 erzeugt oder persistiert keine neue Dispositionsevidence und
implementiert keine Cleanup-Autorisierung, Ressourceninspektion oder
Ressourcenentfernung.

Es gibt keine Schema-, SQL-, Migration-, Port-, Domainmodell-, Compose- oder
Production-Wiring-Änderung.

## Nächster Slice

LQ-336 sollte den separaten Cleanup-Autorisierungs- und
Preflight-Vertrag für `cleanup_review_eligible` definieren. Container, Netze
und insbesondere das Datenvolume bleiben auch in diesem Vertrag zunächst
unangetastet.
