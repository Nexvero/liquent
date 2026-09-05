# LQ-324 — Controlled Artifact Probe Recovery Claim Reconciliation Contract

## Zweck

LQ-324 definiert den kontrollierten Reconciliationvertrag für einen
verbliebenen LQ-323-Recovery-Claim ohne eindeutig abgeschlossenen normalen
Operator-Handoff.

Reconciliation entscheidet ausschließlich, ob der Claim durch bereits
vorhandene exakte Evidence oder durch neu bestätigte Prefixabwesenheit sicher
finalisiert werden kann.

Sie wiederholt weder LQ-318 noch LQ-321, entfernt keine Probeobjekte und trifft
keine Readiness- oder Capabilityentscheidung.

Dieser Slice implementiert noch keinen Command, Container oder Dateizugriff.

## Separate Reconciliation-Autorisierung

Der ursprüngliche Recoveryauftrag und sein Claim gewähren kein Force-Unlock.
Reconciliation verlangt eine neue owner-only, zeitlich begrenzte
Autorisierungsdatei für genau einen Claim.

Sie bindet mindestens:

- eine neue stabile opake Reconciliation-ID;
- die ursprüngliche stabile Recovery-ID;
- Run-ID und Phase `artifact_capabilities`;
- Source-Commit, Image-Digest und Compose-SHA-256;
- ursprüngliche Recovery-Executor-/Autorisiereridentitäten;
- getrennte Reconciliation-Executor-/Autorisiereridentitäten;
- ein enges aktuelles UTC-Zeitfenster;
- ausschließlich `reconcile_claim`.

Reconciliation-Executor und -Autorisierer müssen verschieden sein. Die neue
Autorisierung akzeptiert keinen gewünschten Ausgang, Token, Prefix,
Volume-Namen, Pfad, Delete-Boolean, Cleanuprecht oder Evidenceinhalt.

Sie ist keine Produktrolle, Membership, Researchpermission oder allgemeine
Staging-Administration.

## Exakte historische Bindung

Vor jeder Entscheidung werden ursprüngliche Staging-Autorisierung,
Recovery-Autorisierung, Reconciliation-Autorisierung, Claim und gegebenenfalls
finale Evidence erneut über private owner-only Grenzen geladen.

Recovery-ID, Run, Phase, Source, Image, Compose und ursprüngliche Identitäten
müssen überall exakt übereinstimmen. Der Claim-Dateiname und mögliche
Evidence-Dateiname werden ausschließlich aus dem Hash derselben Recovery-ID
abgeleitet.

Der 64-Hex-Probe-Token und das benannte Artifactvolume werden erneut intern aus
der historischen Run-/Compose-Bindung bestimmt. Caller-gelieferte Ziele sind
unzulässig.

Jede Abweichung, beschädigte Datei oder nicht eindeutige Zuordnung endet
detailfrei unavailable und lässt Claim sowie Evidence unverändert.

## Zulässiger Ausgangszustand

Reconciliation läuft nur, wenn der exakte Claim vorhanden und regulär,
owner-only, Linkcount eins sowie inhaltlich der festen LQ-323-Claimform
entsprechend ist.

Fehlt der Claim und existiert exakte finale Evidence, lautet der neutrale
Ausgang `already_finalized` ohne Mutation.

Fehlen Claim und finale Evidence gemeinsam, gibt es keinen recoverbaren Fall.
Das Ergebnis ist neutral `not_found`; es wird weder Claim noch Evidence
erzeugt.

Ein unbekanntes oder ähnlich benanntes Claimobjekt wird nicht übernommen,
umbenannt oder entfernt.

## Fall A: Finale Evidence existiert

Existiert finale LQ-323-Evidence, muss sie vollständig gegen die historischen
Bindungen und die aktuelle Reconciliation-Autorisierung geprüft werden.

Zulässig sind ausschließlich die unveränderten LQ-323-Ausgänge
`already_absent`, `removed` oder `conflict` mit gültiger UTC-Abschlusszeit,
Modus 0600, aktuellem Owner und Linkcount eins.

Bei exakter Evidence ist der Claim lediglich ein nach Evidence-Finalisierung
verbliebener Ordnungsrest. Reconciliation darf dann:

1. eine eigene atomare Reconciliation-Evidence mit Ausgang
   `evidence_confirmed` veröffentlichen;
2. erst nach deren Fsync und Read-back exakt den Claim entfernen;
3. das Evidenceverzeichnis fsyncen und Claim-Abwesenheit bestätigen.

Die bestehende finale Recovery-Evidence wird nicht umgeschrieben. Ihr Ausgang
bleibt maßgeblich und wird beim Handoff unverändert wiedergegeben.

## Fall B: Keine finale Evidence, Prefix eindeutig abwesend

Fehlt finale Recovery-Evidence, muss zuerst LQ-320 in einer erneut gebundenen
gehärteten read-only Docker-Composition ausgeführt werden.

Nur der exakte neutrale Ausgang `absent` beweist, dass kein rungebundener
Probe-Prefix mehr sichtbar ist. Er beweist nicht, ob der frühere Zustand schon
abwesend war oder LQ-321 vollständig entfernt hat.

Deshalb darf Reconciliation weder `removed` noch `already_absent` erfinden.
Sie finalisiert stattdessen einen neuen neutralen Recoveryausgang
`absence_confirmed_after_unknown`.

Die atomare Reihenfolge lautet:

1. private finale Recovery-Evidence mit der vollständigen historischen Bindung,
   Ausgang `absence_confirmed_after_unknown` und Reconciliation-ID erzeugen;
2. Datei fsyncen, exklusiv veröffentlichen und vollständig zurücklesen;
3. getrennte Reconciliation-Evidence `absence_confirmed` veröffentlichen;
4. erst danach den exakten Claim entfernen;
5. Evidenceverzeichnis fsyncen und Claim-Abwesenheit bestätigen.

Ein Crash zwischen Evidence und Claimentfernung konvergiert beim nächsten
exakten Reconciliation-Aufruf auf Fall A.

## Nicht finalisierbare Prefixzustände

LQ-320-`recoverable` bedeutet, dass weiterhin ausschließlich bekannte
Probeobjekte existieren. Es beweist aber keinen abgeschlossenen Remove-Ausgang
und autorisiert in LQ-324 weder LQ-321 noch Claimlöschung.

`conflict` bedeutet, dass der Bestand nicht ausschließlich der Probe
zugeordnet werden kann. Claim und Volume bleiben unangetastet.

Technisch `unavailable` bedeutet, dass keine sichere Aussage möglich ist.
Auch dann bleiben Claim und Evidence unverändert.

Alle drei Fälle liefern außerhalb der technischen Fehlergrenze nur den
detailarmen neutralen Ausgang `retained`. Interne Untergründe werden nicht
offengelegt.

## Keine Remove-Fähigkeit

LQ-324 besitzt keinen LQ-321-Aufruf und mountet das Artifactvolume niemals
read-write.

Es gibt keinen Unlink innerhalb des Volumes, kein rekursives Cleanup, keinen
Retry der Capability-Probe, keinen Remove-Container, kein Volume-Remove,
Compose-Down oder Prune.

Der einzige zulässige Unlink betrifft den exakt gebundenen Claim im privaten
Evidenceverzeichnis und erfolgt erst nach atomar bestätigter finaler Evidence.

## Konkurrenz und Wiederholung

Eine stabile Reconciliation-ID bindet genau Recovery-ID, Run, Actoren und
erwartete historische Werte.

Ein eigener exklusiver Reconciliation-Claim serialisiert konkurrierende
Versuche. Nach dem Warten oder bei technischer Wiederholung wird zuerst nach
bereits finaler Reconciliation-Evidence gesucht.

Exakte Wiederholung liefert denselben neutralen Ausgang ohne Docker oder neue
Dateiwirkung. Dieselbe Reconciliation-ID mit anderer Bindung ist detailfreier
Konflikt.

Ein unbekannter Ausgang nach möglicher Evidence- oder Claimmutation wird nicht
automatisch wiederholt. Die unveränderlichen Dateien müssen beim nächsten
kontrollierten Versuch erneut vollständig abgeglichen werden.

## Neutrale Ergebnisse

Öffentlich sichtbar sind ausschließlich:

- `already_finalized`;
- `evidence_confirmed`;
- `absence_finalized`;
- `retained`;
- `not_found`;
- technisch `unavailable` ohne Ergebnisobjekt.

Kein Ergebnis nennt Recovery-/Reconciliation-ID, Run, Token, Volume, Prefix,
Datei, Identität, Image, Composewert oder technischen Grund.

`absence_finalized` ist keine Aussage über den früheren Writepfad. Kein
Ergebnis ändert die ursprüngliche Stagingphase oder gewährt Deployment.

## Retention und Nichtwiederverwendung

Recovery- und Reconciliation-ID, ursprüngliche Autorisierungen, finale
Recovery-Evidence und Reconciliation-Evidence müssen mindestens so lange
unterscheidbar bleiben, wie Audit, Retry oder Interpretation des unbekannten
Ausgangs darauf angewiesen sind.

IDs und Evidence dürfen nicht unter neuer Bindung oder Bedeutung
wiederverwendet werden. Dieser Vertrag legt keine konkrete Frist, Tabelle oder
Archivierungsstrategie fest.

## Nichtziele

LQ-324 entscheidet keinen CLI-Namen, JSON-Dateinamen, Docker-argv, Timeout,
Lockmechanismus, Credentialanbieter oder konkretes Retentionverfahren.

Es gibt keine Implementierung, keinen realen Dockerzugriff, keine Schema-,
SQL-, Migration-, Port-, Domainmodell-, Compose-, Produkt- oder
Production-Wiring-Änderung.

## Nächster Slice

LQ-325 sollte den owner-only Claim-Reconciliation-Operator gemäß diesem Vertrag
implementieren. Tests müssen Evidence-first-Konvergenz, read-only
Prefixabwesenheit, retained-Zustände, Konkurrenz und unbekannte Dateiausgänge
ohne realen Dockerzugriff beweisen.
