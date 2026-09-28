# LQ-359 — Read-only Runtime Cleanup Chained Continuation Reconciliation Contract

## Zweck
LQ-359 definiert die strikt read-only Reconciliation eines offenen
LQ-358-Chained-Continuation-Claims nach unbekanntem Ausgang.

Sie klassifiziert den aktuellen Präfix relativ zum autoritativ aus LQ-355
abgeleiteten `resume_from`. Dieser Slice implementiert keinen Command.
## Separate Reconciliation-Autorisierung
Die LQ-358-Autorisierung gewährt keine nachträgliche Reconciliation-Autorität.

Ein späterer Inspector benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Chained-Reconciliation-ID.

Sie muss mindestens geschlossen binden:

- Chained-Reconciliation- und Chained-Continuation-ID;
- Recontinuation-Finalization-, Recontinuation-Reconciliation-,
  Recontinuation-, Continuation-Finalization-, alte Continuation-,
  Cleanup-Reconciliation-, Cleanup- und Run-ID;
- Phase `disposable_postgres`, Source-Commit, Image-Digest und Compose-Hash;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- sämtliche vorgelagerten Evidence- und Autorisierungshashes;
- SHA-256 der LQ-341-, LQ-345-, LQ-347-, LQ-349-, LQ-351-, LQ-353-,
  LQ-355- und LQ-358-Autorisierung;
- SHA-256 der exakten LQ-349- und LQ-355-Finalization-Evidence;
- historischen `previous_resume_from` und effektiven `resume_from`;
- Scope exakt `runtime_only`;
- Operation exakt `inspect_disposable_postgres_cleanup_chained_continuation`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Zustand, Fortschritt noch Ausgang.
## Vollständige Bindung
Der Inspector validiert Run-, Dispositions-, Cleanup-, Continuation-, LQ-349-,
LQ-351-, LQ-353-, LQ-355- und LQ-358-Kette erneut.

Historische Zeitfenster werden nur an ihrem ursprünglich gültigen Mittelpunkt
ausgewertet. Die neue Reconciliation-Autorisierung muss aktuell sein.

Die LQ-355-Evidence muss weiterhin einen nichtterminalen Ausgang und denselben
effektiv abgeleiteten Startpräfix binden.

Keine neue Autorisierung verlängert frühere Mutationsrechte.
## Claim-Gates
Der ursprüngliche LQ-339-Cleanup-Claim muss offen, kanonisch und exakt an
dieselbe Kette gebunden sein.

Der alte LQ-345-Continuation-Claim und der LQ-351-Recontinuation-Claim müssen
weiterhin exakt abwesend sein.

Ein vorhandener historischer Claim ist technisch unavailable und wird weder
freigegeben noch ersetzt.

Der aktuelle Claim wird ausschließlich aus dem vollständigen SHA-256 der
Chained-Continuation-ID abgeleitet.
## Evidence vor Ressourcenbeobachtung
Exakt gebundene LQ-358-Chained-Continuation-Evidence wird vor Docker geprüft.

Ist sie vorhanden, lautet der Ausgang
`chained_continuation_evidence_present`.

Ein gleichzeitig offener aktueller Claim wird nicht entfernt.

Fehlen Evidence und exakter Claim gemeinsam, lautet der neutrale Ausgang
`not_found` ohne Dockerzugriff.

Evidence ohne Claim bleibt ebenfalls
`chained_continuation_evidence_present`; der Inspector erzeugt keinen Claim.

Malformed oder widersprüchliche Evidence bleibt technisch unavailable.
## Kanonischer aktueller Claim
Ein vorhandener Claim muss regulär, owner-only, einfach verlinkt und
kanonisches JSON sein.

Er bindet die gesamte historische Kette, beide Finalization-Evidencehashes,
beide Startpräfixe, LQ-358-Autorisierung, Restbudget, exakte Ressourcen,
Identitäten und eine zeitzonenbehaftete Startzeit.

Alter oder Dateiname beweist keinen Fortschritt.

Der Inspector repariert, ersetzt oder übernimmt keinen Claim.
## Frische LQ-341-Klassifikation
Nur bei offenem Cleanup- und Chained-Continuation-Claim ohne aktuelle Evidence
wird LQ-341 erneut ausgeführt.

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

Für effektives `resume_from=container_removed` sind alle drei Zustände
zulässig.

Für effektives `resume_from=application_network_removed` sind nur Zustände
zwei und drei zulässig.

Der exakt gleiche Zustand bedeutet `chained_continuation_not_started`.

Der spätere nichtterminale Präfix wird exakt als
`application_network_removed` ausgegeben.

Vollständige Runtimeentfernung ergibt `runtime_removed_evidence_missing`.

Keine Klassifikation erteilt ein weiteres Mutationsrecht.
## Konfliktzustände
Jeder lesbare Zustand vor `resume_from` oder außerhalb der Präfixordnung
ergibt `conflict`.

Dazu gehören `container_stopped`, `runtime_intact`, fehlender Cleanup-Claim,
`final_evidence_present`, unmögliche Ressourcenreihenfolge und jede
Volume-Abweichung.

Ein vorhandener historischer Unterclaim ist technisch unavailable, nicht
`conflict` oder neutrale Abwesenheit.

Conflict erlaubt weder Claimfreigabe, Fortsetzung noch Finalisierung.
## Technische Nichtverfügbarkeit

Malformed Output, Nonzero, stderr, Timeout, Truncation, Hard Kill, doppelte
JSON-Schlüssel oder uneindeutige Namenslisten bleiben unavailable.

Unavailable wird nicht als Konflikt, Abwesenheit oder Fortschritt umgedeutet.

Der Inspector liest keine Docker-Events, Logs, Historie, SQL- oder
Volumeinhalte.
## Strikte Read-only-Grenze

Erlaubt sind nur private Dateireads sowie die bestehende read-only
LQ-341-Composition.

Claimanlage, Claimfreigabe, Evidencewrite, Stop, Start, Remove, Disconnect,
Down, Kill, Prune und Volumezugriff sind verboten.

Auch bei vollständiger Runtimeentfernung bleiben Cleanup- und aktueller Claim
unverändert.

Kein Ausgang autorisiert automatische Fortsetzung oder Finalisierung.
## Neutrale Ausgabe

Der spätere Command liefert ausschließlich:

- `not_found` oder `chained_continuation_evidence_present`;
- `chained_continuation_not_started`;
- `application_network_removed`;
- `runtime_removed_evidence_missing`;
- `conflict`;
- technisch unavailable ohne Ergebnisobjekt.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_cleanup_chained_continuation_reconciliation` und Ausgang.

Private IDs, Hashes, Pfade, Ressourcen und Fehlerdetails bleiben verborgen.
## Retention und Nichtwiederverwendung

Chained-Reconciliation-, Chained-Continuation-, Finalization-, Cleanup- und
Run-ID sowie Claims, Autorisierungen und Evidence bleiben mindestens für
Audit, Retry, Reconciliation und Finalisierung unterscheidbar.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden.

Das Datenvolume bleibt dem ursprünglichen Run zugeordnet. Eine konkrete
Retentionfrist oder Ablagestrategie wird nicht festgelegt.
## Nichtziele

LQ-359 implementiert keinen Inspector, Entry Point, Test, Claim-, Evidence-
oder Ressourcemutator.

Es gibt keine Volume-Löschung, Schema-, Tabellen-, SQL-, Migration-, Port-,
Domainmodell-, Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 44 Entry Points, 48 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.
## Nächster Slice

LQ-360 sollte den read-only Chained-Continuation-Claim-Inspector samt
geschlossener Präfixmatrix und Fake-basierten Tests implementieren.

Claimfinalisierung, weitere Fortsetzung und jede Volumenlöschung bleiben
separate spätere Slices.
