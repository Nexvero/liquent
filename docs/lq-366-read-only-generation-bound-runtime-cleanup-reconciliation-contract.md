# LQ-366 — Read-only Generation-bound Runtime Cleanup Reconciliation Contract
## Zweck
LQ-366 definiert die strikt read-only Reconciliation eines offenen
LQ-365-Generation-Continuation-Claims nach unbekanntem Ausgang.
Sie klassifiziert den aktuellen Runtimepräfix relativ zum autoritativ
gebundenen effektiven `resume_from` und implementiert keinen Command.
## Separate Reconciliation-Autorisierung
Die LQ-365-Mutationsautorisierung gewährt keine Reconciliation-Autorität.
Ein späterer Inspector benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Generation-Reconciliation-ID.
Sie bindet mindestens:
- Generation-Reconciliation- und Generation-Continuation-ID;
- Generation, Vorgängerart und Vorgängergeneration;
- LQ-362-Finalization-, LQ-358-, Recontinuation-, Continuation-, Cleanup- und
  Run-Kette;
- Phase `disposable_postgres`, Source-Commit, Image-Digest und Compose-Hash;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- sämtliche Root-Evidence- und Autorisierungshashes;
- SHA-256 der LQ-365-Generation-Continuation-Autorisierung;
- SHA-256 der direkten Vorgängerautorisierung und Finalization-Evidence;
- `predecessor_resume_from` und effektives `resume_from`;
- Scope exakt `runtime_only`;
- Operation exakt `inspect_disposable_postgres_cleanup_generation_continuation`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.
Caller liefern weder Zustand, Generation, Fortschritt noch Ausgang.
## Vollständige historische Bindung
Der Inspector validiert die gesamte Root-, LQ-362- und LQ-365-Kette erneut.
Historische Autorisierungen werden ausschließlich an ihrem ursprünglich
gültigen Fenstermittelpunkt ausgewertet.
Die neue Reconciliation-Autorisierung muss aktuell sein und verlängert keine
frühere Mutations- oder Finalisierungsautorität.
Generation, Vorgänger, beide Präfixe, IDs, Hashes, Ressourcen und Projektname
müssen exakt dieselbe unveränderte Kette beschreiben.
## Aktuell ausführbare Generation
Der erste Inspector akzeptiert ausschließlich Generation eins mit
`predecessor_kind=lq362` und `predecessor_generation=0`.
Die direkte LQ-362-Finalization-Evidence muss weiterhin kanonisch, owner-only
und nichtterminal gebunden sein.
Andere Generationen bleiben bis zu ihrem eigenen finalisierten Vorgängertyp
fail-closed technisch unavailable.
Der Vertrag legt bereits dieselbe Klassifikationssemantik für spätere
Generationen fest, erfindet aber keine noch fehlende Evidence.
## Claim-Gates
Der ursprüngliche LQ-339-Cleanup-Claim muss offen, kanonisch und exakt gebunden
sein.
LQ-345-, LQ-351- und LQ-358-Claims sowie Claims abgeschlossener Generationen
müssen exakt abwesend sein.
Ein vorhandener historischer oder malformed Claim bleibt technisch unavailable
und wird weder freigegeben noch ersetzt.
Der aktuelle Claimname wird ausschließlich aus SHA-256 der
Generation-Continuation-ID abgeleitet.
## Evidence vor Ressourcenbeobachtung
Exakt gebundene LQ-365-Generation-Evidence wird vor Docker geprüft.
Ist sie vorhanden, lautet der Ausgang
`generation_continuation_evidence_present`.
Ein gleichzeitig offener aktueller Claim wird nicht entfernt.

Fehlen Evidence und exakter Claim gemeinsam, lautet der neutrale Ausgang
`not_found` ohne Dockerzugriff.

Evidence ohne Claim bleibt ebenfalls Evidence-present. Malformed oder
widersprüchliche Evidence ist technisch unavailable.

## Kanonischer aktueller Claim

Ein vorhandener Claim muss regulär, owner-only, einfach verlinkt und
kanonisches JSON sein.

Er bindet Generation, direkte Vorgängerevidence, Root-Kette, beide Präfixe,
LQ-365-Autorisierung, Restbudget, Ressourcen, Identitäten und UTC-Startzeit.

Alter, Dateiname oder offene Dauer beweist keinen Fortschritt.

Der Inspector repariert, übernimmt oder verändert keinen Claim.

## Frische LQ-341-Klassifikation

Nur bei offenem Cleanup- und aktuellem Generation-Claim ohne Generation-
Evidence wird LQ-341 frisch ausgeführt.

LQ-341 rendert Compose read-only, verwendet exakte Namenslisten und inspiziert
nur vorhandene erwartete Ressourcen.

Ein gespeicherter oder caller-gelieferter früherer Ausgang wird nicht
akzeptiert.

Das Datenvolume muss in jedem zulässigen Präfix unverändert rungebunden
vorhanden sein.

## Geschlossene Präfixordnung

Die relevante Reihenfolge lautet:

1. `container_removed`;
2. `application_network_removed`;
3. `runtime_removed_evidence_missing`.

Für `resume_from=container_removed` sind alle drei Zustände zulässig.

Für `resume_from=application_network_removed` sind nur Zustände zwei und drei
zulässig.

Der exakt gleiche Zustand ergibt `generation_continuation_not_started`.

Der spätere nichtterminale Präfix wird exakt als
`application_network_removed` ausgegeben.

Vollständige Runtimeentfernung ergibt `runtime_removed_evidence_missing`.

Keine Klassifikation erteilt ein weiteres Mutationsrecht.

## Konfliktzustände

Jeder lesbare Zustand vor `resume_from` oder außerhalb der Präfixordnung ergibt
`conflict`.

Dazu gehören `runtime_intact`, `container_stopped`, `final_evidence_present`,
unmögliche Ressourcenreihenfolge und jede Volume-Abweichung.

Ein fehlender Cleanup-Claim ergibt ebenfalls `conflict`; ein vorhandener
historischer Unterclaim bleibt dagegen technisch unavailable.

Conflict erlaubt weder Claimfreigabe, Fortsetzung noch Finalisierung.

## Technische Nichtverfügbarkeit

Malformed Output, Nonzero, stderr, Timeout, Truncation, Hard Kill, doppelte
JSON-Schlüssel und uneindeutige Namenslisten bleiben unavailable.

Unavailable wird nicht als Conflict, Abwesenheit oder Fortschritt umgedeutet.

Der Inspector liest keine Docker-Events, Logs, Historie, SQL- oder
Volumeinhalte.

## Strikte Read-only-Grenze

Erlaubt sind ausschließlich private Dateireads und die bestehende read-only
LQ-341-Composition.

Claimanlage, Claimfreigabe, Evidencewrite, Stop, Start, Remove, Disconnect,
Down, Kill, Prune und Volumezugriff sind verboten.

Cleanup- und Generation-Claim bleiben in jedem Ausgang unverändert.

Kein Ausgang autorisiert automatische Fortsetzung oder Finalisierung.

## Neutrale Ausgabe

Der spätere Command liefert ausschließlich:

- `not_found` oder `generation_continuation_evidence_present`;
- `generation_continuation_not_started`;
- `application_network_removed`;
- `runtime_removed_evidence_missing`;
- `conflict`;
- technisch unavailable ohne Ergebnisobjekt.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_cleanup_generation_continuation_reconciliation` und
Ausgang.

Private Generation, IDs, Hashes, Pfade, Ressourcen und Fehlerdetails bleiben
verborgen.

## Retention, Nichtziele und Bundle

Generation-, Reconciliation-, Finalization-, Cleanup- und Run-IDs sowie Claims,
Autorisierungen und Evidence bleiben mindestens für Audit, Retry,
Reconciliation und Finalisierung unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden. Eine
konkrete Retentionfrist oder Ablagestrategie wird nicht festgelegt.

LQ-366 implementiert keinen Inspector, Entry Point, Test, Claim-, Evidence-
oder Ressourcemutator und keine Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 47 Entry Points, 51 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-367 sollte den read-only Generation-Continuation-Claim-Inspector mit
geschlossener Präfixmatrix und Fake-basierten Tests implementieren.

Finalisierung, Folgegenerationen und jede Volume-Löschung bleiben separate
spätere Slices.
