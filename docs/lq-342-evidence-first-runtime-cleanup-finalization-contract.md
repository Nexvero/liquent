# LQ-342 — Evidence-first Runtime Cleanup Finalization Contract

## Zweck

LQ-342 definiert die kontrollierte Finalisierung eindeutig beobachteter
LQ-341-Cleanupzustände.

Finalisierung persistiert private Evidence vor möglicher Freigabe des
LQ-339-Claims. Dieser Slice implementiert keinen Command oder Write.

## Separate Finalisierungsautorisierung

Cleanup- und Cleanup-Reconciliation-Autorisierung gewähren kein
Finalisierungsrecht.

Ein späterer Operator benötigt eine neue owner-only Autorisierung mit stabiler,
nicht wiederverwendbarer Cleanup-Finalization-ID.

Sie muss mindestens geschlossen binden:

- Finalization-, Cleanup-Reconciliation- und Cleanup-ID;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, Application-Image-Digest und Compose-SHA-256;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- alle Cleanup-, Dispositions- und Evidencehashes;
- SHA-256 der vollständigen LQ-341-Reconciliation-Autorisierung;
- Operation exakt `finalize_disposable_postgres_runtime_cleanup`;
- Scope exakt `runtime_only`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Zustand, Ressourcennamen noch gewünschte Finalisierung.

## Vollständige Neuprüfung

Der spätere Finalizer muss die gesamte historische Run-, Dispositions-,
Cleanup-, Claim- und Evidencekette erneut validieren.

Die LQ-341-Reconciliation-Autorisierung wird bytegenau gegen ihren gebundenen
SHA-256 geprüft und nur an ihrem ursprünglichen gültigen Mittelpunkt geladen.

Die neue Finalisierungsautorisierung muss aktuell gültig sein. Historische
Autorisierungen werden dadurch nicht verlängert.

Unmittelbar vor jeder Evidenceanlage muss der Finalizer LQ-341 mit denselben
autoritativen Inputs erneut ausführen.

Ein gespeicherter oder caller-gelieferter früherer LQ-341-Ausgang genügt nicht.

## Drei finalisierbare Beobachtungen

Nur diese frisch abgeleiteten Zustände dürfen Evidence-first finalisiert
werden:

- `runtime_intact`: der Bestand ist wieder vollständig und exakt isoliert;
- `runtime_removed_evidence_missing`: Container und beide Netze fehlen, das
  exakte Datenvolume ist erhalten;
- `final_evidence_present`: kanonische LQ-339-Abschlussevidence ist bereits
  exakt gebunden vorhanden.

`not_found` benötigt keine Finalisierung und erzeugt keinen Write.

`container_stopped`, `container_removed` und
`application_network_removed` sind echte Teilzustände. Sie bleiben
`continuation_required` mit offenem Cleanup-Claim.

`conflict` bleibt `investigation_required`. Technische Nichtverfügbarkeit
bleibt ohne Ergebnis und ohne Mutation.

## Keine gefälschte LQ-339-Evidence

Der Finalizer darf fehlende LQ-339-Cleanup-Evidence nicht nachträglich als
originalen `removed_runtime`-Record erzeugen.

Eine aktuelle Ressourcenbeobachtung beweist nicht, welche einzelnen
LQ-339-Prozessbestätigungen vor dem unbekannten Ausgang empfangen wurden.

Stattdessen entsteht eine getrennte Cleanup-Finalization-Evidence mit eigenem
Schema und eigener Finalization-ID.

Sie schreibt historische Schrittbestätigung nicht um.

## Evidence-first Konkurrenzordnung

Der finale Evidencename wird ausschließlich aus dem vollständigen SHA-256 der
Cleanup-Finalization-ID abgeleitet.

Vor LQ-341 wird bereits vorhandene finale Reconciliation-Evidence vollständig
gegen die autoritative Bindung geprüft.

Exakt vorhandene Evidence steuert einen idempotenten Retry. Widersprüchliche,
beschädigte oder anders gebundene Evidence ist technisch unavailable.

Nach frischer finalisierbarer Beobachtung wird die Evidence owner-only mit
exklusiver Neuanlage, Flush, atomarer finaler Anlage und
Verzeichnissynchronisation persistiert.

Sie bindet mindestens alle IDs und Hashes, den frisch beobachteten Zustand,
den neutralen Finalisierungsausgang, getrennte Identitäten sowie UTC-Start und
Abschluss.

## Claimfreigabe erst nach Evidence

Erst vollständig zurückgelesene Finalization-Evidence darf die Freigabe des
exakt gebundenen LQ-339-Cleanup-Claims erreichen.

Bei `runtime_intact` lautet die Evidenceaussage `no_effect_finalized`. Eine
spätere Cleanupprüfung benötigt eine neue Cleanup-ID und neue Autorisierung.

Bei `runtime_removed_evidence_missing` lautet sie
`runtime_removal_finalized`. Das erhaltene Volume bleibt weiterhin an den
ursprünglichen Run gebunden.

Bei `final_evidence_present` lautet sie `cleanup_evidence_confirmed`.

Der Claim wird exakt einmal per verankertem Namen entfernt. Es gibt keine
Suche, Altersentscheidung oder Gruppenauswahl.

## Unbekannte Claimfreigabe

Ist die Claimfreigabe technisch mehrdeutig, bleibt die Finalization-Evidence
maßgeblich und der Ausgang unavailable.

Ein Retry validiert zuerst dieselbe Evidence und prüft anschließend nur den
exakten Claim: vorhanden bedeutet erneuter einzelner Freigabeversuch,
abwesend bedeutet bereits freigegeben.

Der Retry führt LQ-341 nicht erneut aus und verändert keine Ressource, sobald
die exakte Finalization-Evidence existiert.

Ein fremder oder beschädigter Claim wird niemals entfernt.

## Strikte Mutationsgrenze

Die einzigen erlaubten Writes sind Finalization-Evidence und die spätere
exakte Cleanup-Claimfreigabe.

Ressourcen und historische Artefakte bleiben unverändert.

Stop, Start, Remove, Disconnect, Down, Kill, Prune, SQL, Docker-Events und
Volumeinhaltszugriff sind verboten.

Teilzustände dürfen weder finalisiert noch automatisch fortgesetzt werden.

## Neutrale Ausgänge

Der spätere Operator darf nur liefern:

- `not_found`;
- `no_effect_finalized`;
- `runtime_removal_finalized`;
- `cleanup_evidence_confirmed`;
- `continuation_required`;
- `investigation_required`;
- technisch unavailable ohne Ergebnisobjekt.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_runtime_cleanup_finalization` und Ausgang. Alle privaten
Details bleiben verborgen.

## Retention und Nichtwiederverwendung

Finalization-, Cleanup-Reconciliation-, Cleanup- und Run-ID sowie Claims,
Autorisierungen und Evidence bleiben mindestens so lange unterscheidbar, wie
Audit, Retry, Fortsetzung oder Interpretation unbekannter Ausgänge sie
benötigen.

Keine ID oder Evidence darf für andere Bindung oder Bedeutung wiederverwendet
werden. Claimfreigabe erlaubt weder Run-ID-Wiederverwendung noch
Volumeübernahme.

Dieser Vertrag bestimmt keine konkrete Retentionfrist oder Ablagestrategie.

## Nichtziele

LQ-342 implementiert keinen Finalizer, Entry Point, Test, Evidencewriter,
Claimrelease oder Cleanupfortsetzung.

Es gibt keine Docker-, Volume-, Schema-, Tabellen-, SQL-, Migration-, Port-,
Domainmodell-, Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 36 Entry Points, 40 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-343 sollte den Evidence-first Cleanup-Finalizer und Fake-basierte Tests
für alle geschlossenen Ausgänge implementieren.
Fortsetzung der drei Teilzustände und jede Volume-Löschung bleiben separate
spätere Verträge und Implementierungen.
