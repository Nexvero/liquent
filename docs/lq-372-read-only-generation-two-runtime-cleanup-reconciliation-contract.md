# LQ-372 — Read-only Generation-two Runtime Cleanup Reconciliation Contract
## Zweck
LQ-372 definiert die strikt read-only Reconciliation eines offenen
Generation-2-Claims nach unbekanntem LQ-371-Ausgang.
Sie klassifiziert den aktuellen Runtimepräfix relativ zum direkt aus LQ-369
abgeleiteten `resume_from` und implementiert keinen Command.
## Separate Reconciliation-Autorisierung
Die LQ-371-Autorisierung gewährt keine nachträgliche Reconciliation-Autorität.
Der Inspector benötigt eine neue owner-only Autorisierung mit stabiler,
nicht wiederverwendbarer Generation-Reconciliation-ID.
Sie bindet mindestens:
- Generation-Reconciliation- und Generation-2-Continuation-ID;
- Generation exakt zwei, Vorgängerart `repeatable_generation` und
  Vorgängergeneration eins;
- Generation-1-Continuation-, Reconciliation- und Finalization-ID;
- LQ-362-, LQ-358-, Recontinuation-, Continuation-, Cleanup- und Run-Kette;
- Phase `disposable_postgres`, Source-Commit, Image-Digest und Compose-Hash;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- sämtliche Root-Evidence- und Autorisierungshashes;
- SHA-256 der LQ-371-Generation-2-Autorisierung;
- SHA-256 der vollständigen LQ-369-Autorisierung und exakten Evidence;
- `predecessor_resume_from` und effektives `resume_from`;
- Scope exakt `runtime_only`;
- Operation exakt `inspect_disposable_postgres_cleanup_generation_continuation`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.
Caller liefern weder Zustand, Generation, Vorgänger, Fortschritt noch Ausgang.
## Direkte LQ-369-Bindung
Generation-1-Autorisierung und LQ-369-Finalisierungsautorisierung werden an
ihren ursprünglichen Fenstermittelpunkten erneut validiert.
Die kanonische LQ-369-Evidence muss owner-only, bytegenau gebunden und mit
`generation_continuation_attempt_finalized` oder `later_prefix_finalized`
abgeschlossen sein.
Eine ältere Generation, LQ-362 als direkter Vorgänger, terminale Evidence oder
abweichende Hashbindung bleibt technisch unavailable.
Die neue Reconciliation-Autorisierung verlängert keine frühere Autorität.
## Vollständige historische Bindung
Der Inspector validiert Root-, LQ-362-, Generation-1-, LQ-369- und
Generation-2-Kette geschlossen.
Generation, Vorgänger, beide Präfixe, IDs, Hashes, Ressourcen, Run und
Projektname müssen dieselbe unveränderte Kette beschreiben.
`predecessor_resume_from` muss dem effektiven Startpräfix der Generation eins
entsprechen.
`resume_from` wird ausschließlich aus dem nichtterminalen LQ-369-Ausgang
abgeleitet und nicht aus Callerinput übernommen.
## Claim-Gates
Der LQ-339-Cleanup-Claim muss offen, kanonisch und exakt gebunden sein.
LQ-345-, LQ-351-, LQ-358- und Generation-1-Claim müssen exakt abwesend sein.
Ein vorhandener historischer oder malformed Claim bleibt technisch unavailable
und wird weder freigegeben noch ersetzt.
Der aktuelle Claimname wird ausschließlich aus SHA-256 der
Generation-2-Continuation-ID abgeleitet.
Nur dieser Claim wird als aktueller Reconciliation-Gegenstand akzeptiert.
## Evidence vor Ressourcenbeobachtung

Exakt gebundene Generation-2-Continuation-Evidence wird vor Docker geprüft.

Ist sie vorhanden, lautet der Ausgang
`generation_continuation_evidence_present`.

Ein gleichzeitig offener aktueller Claim bleibt unverändert.

Fehlen Evidence und exakter Claim gemeinsam, lautet der neutrale Ausgang
`not_found` ohne Dockerzugriff.

Evidence ohne Claim bleibt Evidence-present; malformed oder widersprüchliche
Evidence bleibt technisch unavailable.

## Kanonischer aktueller Claim

Der Claim muss regulär, owner-only, einfach verlinkt und kanonisches JSON sein.

Er bindet Generation zwei, direkte LQ-369-Evidence, Root-Kette, beide Präfixe,
LQ-371-Autorisierung, Restbudget, Ressourcen, Identitäten und UTC-Startzeit.

Alter, Dateiname oder offene Dauer beweist keinen Fortschritt.

Der Inspector repariert, übernimmt oder verändert keinen Claim.

## Frische LQ-341-Klassifikation

Nur bei offenem Cleanup- und Generation-2-Claim ohne Evidence wird LQ-341
frisch und read-only ausgeführt.

LQ-341 rendert Compose read-only, verwendet exakte Namenslisten und inspiziert
nur vorhandene erwartete Ressourcen.

Ein gespeicherter oder caller-gelieferter Ausgang wird nicht akzeptiert.

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
Down, Kill, Prune, SQL und Volumezugriff sind verboten.

Cleanup- und Generation-2-Claim bleiben in jedem Ausgang unverändert.

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

Alle Generationen, IDs, Claims, Autorisierungen und Evidence bleiben mindestens
für Audit, Retry, Reconciliation, Finalisierung und LQ-343 unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden; eine
konkrete Retentionfrist wird nicht festgelegt.

LQ-372 implementiert keinen Inspector, Entry Point, Test, Claim-, Evidence-
oder Ressourcemutator und keine Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 49 Entry Points, 53 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-373 sollte den bestehenden read-only Generation-Inspector um den direkten
LQ-369-Vorgängerresolver und Generation-2-Matrixtests erweitern.

Finalisierung und jede Volume-Löschung bleiben separate spätere Slices.
