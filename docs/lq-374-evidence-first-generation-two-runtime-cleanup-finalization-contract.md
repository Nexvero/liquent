# LQ-374 — Evidence-first Generation-two Runtime Cleanup Finalization Contract
## Zweck
LQ-374 definiert die kontrollierte Finalisierung eines durch LQ-373
reconcilierten generationengebundenen Cleanup-Versuchs.
Sie persistiert private Finalization-Evidence vor möglicher Freigabe des
exakten aktuellen Generation-2-Claims und implementiert keinen Command.
## Separate Finalisierungsautorisierung
Mutation und Reconciliation gewähren kein Finalisierungsrecht.
Ein späterer Finalizer benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Generation-Finalization-ID.
Sie bindet mindestens:
- Generation-Finalization-, Reconciliation- und Continuation-ID;
- Generation, Vorgängerart und Vorgängergeneration;
- LQ-369-, LQ-358-, Recontinuation-, Continuation-, Cleanup- und Run-Kette;
- Phase `disposable_postgres`, Source-Commit, Image-Digest und Compose-Hash;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- sämtliche Root-Evidence- und Autorisierungshashes;
- SHA-256 der LQ-371- und LQ-373-Autorisierung;
- SHA-256 der direkten Vorgängerautorisierung und Finalization-Evidence;
- `predecessor_resume_from` und effektives `resume_from`;
- Scope exakt `runtime_only`;
- Operation exakt `finalize_disposable_postgres_cleanup_generation_continuation`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.
Caller liefern weder Zustand, Generation, Claimstatus noch Zielausgang.
## Vollständige historische Bindung
Der Finalizer validiert Root-, LQ-369-, LQ-371- und LQ-373-Kette erneut.
Historische Autorisierungen werden nur an ihrem ursprünglich gültigen
Fenstermittelpunkt ausgewertet.
Die neue Finalisierungsautorisierung muss aktuell sein und verlängert keine
frühere Mutations- oder Reconciliation-Autorität.
Generation, Vorgänger, beide Präfixe, IDs, Hashes, Ressourcen und Projektname
müssen exakt dieselbe unveränderte Kette beschreiben.
## Aktuelle Generationsgrenze
Der erweiterte Finalizer akzeptiert Generation zwei mit direktem
LQ-369-Vorgänger, `predecessor_kind=repeatable_generation` und
Vorgängergeneration eins.
LQ-369-Finalization-Evidence muss weiterhin owner-only, kanonisch, bytegenau
gebunden und nichtterminal sein.
Andere Generationen bleiben bis zu einem implementierten kanonischen
Vorgänger-Finalization-Typ technisch unavailable.
LQ-374 definiert bereits das wiederverwendbare Evidenceformat, öffnet aber
keine Folgegeneration automatisch.
## Claim-Gates
Der LQ-339-Cleanup-Claim muss offen, kanonisch und exakt gebunden sein.
Seine Abwesenheit ergibt `investigation_required`; malformed Bindung bleibt
technisch unavailable.
LQ-345-, LQ-351-, LQ-358- und Generation-1-Claim müssen exakt abwesend sein.
Ein vorhandener historischer Claim bleibt unavailable und wird nicht entfernt.
Nur der aktuelle Generation-2-Claim liegt in der Freigabegrenze.
## Evidence vor frischer Reconciliation
Der finale Evidencename wird ausschließlich aus SHA-256 der
Generation-Finalization-ID abgeleitet.
Exakt gebundene Finalization-Evidence wird vor LQ-373 geprüft und steuert den
idempotenten Retry.
Sie muss owner-only, regulär, einfach verlinkt und vollständig kanonisch sein.
Beschädigte, widersprüchliche oder anders gebundene Evidence ist technisch
unavailable und wird nicht überschrieben.
## Frische LQ-373-Entscheidung
Ohne Finalization-Evidence muss der Finalizer LQ-373 unmittelbar mit derselben
historischen Reconciliation-Autorisierung neu ausführen.
Ein gespeicherter oder caller-gelieferter früherer Ausgang genügt nicht.
Die Ausgabe muss kanonisches JSON mit exakter Operation, Schema-Version und
einem geschlossenen LQ-373-Ausgang sein.
LQ-373 darf nur bei offenem Cleanup- und aktuellem Claim ohne Evidence
read-only über LQ-341 beobachten.

## Finalisierbare Ausgänge

Die frisch abgeleitete Zuordnung lautet:

- `generation_continuation_evidence_present` wird
  `generation_continuation_evidence_confirmed`;
- `generation_continuation_not_started` wird
  `generation_continuation_attempt_finalized`;
- `application_network_removed` wird `later_prefix_finalized`;
- `runtime_removed_evidence_missing` wird
  `runtime_removal_ready_for_cleanup_finalization`.

`not_found` bleibt neutral und erzeugt keinen Write.

`conflict` wird `investigation_required` ohne Evidence- oder Claimänderung.

Technische Nichtverfügbarkeit bleibt ohne Ergebnis und Mutation.

## Bedeutung der Ausgänge

`generation_continuation_attempt_finalized` bestätigt nur fehlenden Fortschritt
der aktuellen Generation.

`later_prefix_finalized` hält exakt `application_network_removed` fest.

Beide nichtterminalen Ausgänge dürfen eine direkte Folgegeneration begründen,
erteilen aber selbst kein Mutationsrecht.

Die beiden terminalen Ausgänge führen ausschließlich zur separaten
LQ-343-Cleanup-Finalisierung.

## Kanonische Generation-Finalization-Evidence

Der Record bindet Generation-Finalization-, Reconciliation- und
Continuation-ID, Generation, Vorgängerart und Vorgängergeneration.

Er bindet direkte Vorgängerevidence, vollständige Root-Kette, beide Präfixe,
frisch beobachteten Zustand, Ausgang, Identitäten und UTC-Zeitpunkte.

Die Datei wird owner-only exklusiv geschrieben, synchronisiert, atomar final
angelegt und vollständig zurückgelesen.

Sie ist der einzige zulässige direkte Vorgängeranker für Generation drei.

LQ-374 erzeugt keine Generation-Continuation- oder Cleanup-Evidence
nachträglich.

## Exakte aktuelle Claimfreigabe

Der Claimname wird ausschließlich aus SHA-256 der
Generation-Continuation-ID abgeleitet.

Ein vorhandener Claim muss vollständig gegen dieselbe LQ-371-Bindung geprüft
werden, bevor genau dieser Claim entfernt wird.

Ein bereits abwesender Claim gilt als idempotent freigegeben.

Suche, Alter, Präfix-, Label- oder Gruppenauswahl sind ausgeschlossen.

Cleanup-Claim, Ressourcen und historische Evidence bleiben unverändert.

## Unbekannte Claimfreigabe

Ist die Freigabe nach persistierter Finalization-Evidence mehrdeutig, bleibt
die Evidence maßgeblich und der Ausgang technisch unavailable.

Ein Retry validiert zuerst dieselbe Evidence und prüft danach nur den exakten
aktuellen Claim.

Vorhanden bedeutet erneuten einzelnen Freigabeversuch; abwesend bedeutet
bereits freigegeben.

Der Retry führt weder LQ-373 noch Docker erneut aus und schreibt keine zweite
Evidence.

Ein fremder oder beschädigter Claim wird niemals entfernt.

## Folgegeneration und harte Grenze

Generation drei muss eine neue ID, Generation exakt drei,
`predecessor_kind=repeatable_generation`, Vorgängergeneration zwei und SHA-256
dieser exakten Finalization-Evidence binden.

Nur `generation_continuation_attempt_finalized` oder `later_prefix_finalized`
darf diese Folgeautorität begründen.

Kein Ausgang startet Folgearbeit automatisch.

Stop, Start, Remove, Disconnect, Down, Kill, Prune, SQL, Volumezugriff und
Cleanup-Claimfreigabe sind im Finalizer verboten.

## Neutrale Ausgabe

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_cleanup_generation_continuation_finalization` und den
geschlossenen Ausgang.

Private Generation, IDs, Hashes, Pfade, Ressourcen und Fehlerdetails bleiben
verborgen.

## Retention, Nichtziele und Bundle

Alle Generationen, IDs, Claims, Autorisierungen und Evidence bleiben mindestens
für Audit, Retry, Fortsetzung und LQ-343 unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden; eine
konkrete Retentionfrist wird nicht festgelegt.

LQ-374 implementiert keinen Finalizer, Entry Point, Test, Folgeoperator,
Ressourcenmutator oder Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 48 Entry Points, 52 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-375 sollte den bestehenden evidence-first Finalizer um den direkten
Generation-2-Pfad und Fake-basierte Tests erweitern.

Die Ausführung von Generation drei bleibt ein separater späterer Slice.
