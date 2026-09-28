# LQ-346 — Read-only Runtime Cleanup Continuation Reconciliation Contract

## Zweck

LQ-346 definiert die strikt read-only Reconciliation eines offenen
LQ-345-Continuation-Claims nach unbekanntem Ausgang.

Sie klassifiziert den Präfix relativ zu `resume_from`, ohne Mutation. Dieser
Slice implementiert keinen Command oder Write.

## Separate Reconciliation-Autorisierung

Die Continuation-Autorisierung gewährt keine nachträgliche
Reconciliation-Autorität.

Ein späterer Inspector benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Continuation-Reconciliation-ID.

Sie muss mindestens geschlossen binden:

- Continuation-Reconciliation-, Continuation-, Cleanup-Reconciliation- und
  Cleanup-ID;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, Application-Image-Digest und Compose-SHA-256;
- ursprüngliche Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- alle Cleanup-, Dispositions- und Evidencehashes;
- SHA-256 der LQ-341- und LQ-345-Autorisierung;
- Scope exakt `runtime_only` und dasselbe `resume_from`;
- Operation exakt `inspect_disposable_postgres_cleanup_continuation`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Status, Fortschritt noch Ausgang.

## Vollständige Bindung

Der Inspector validiert historische Run-, Dispositions-, Cleanup-, LQ-341-
und Continuation-Autorisierung erneut.

Historische Zeitfenster werden nur an ihrem ursprünglichen gültigen
Mittelpunkt ausgewertet. Die neue Reconciliation-Autorisierung muss aktuell
sein.

Der ursprüngliche LQ-339-Cleanup-Claim muss weiterhin offen, kanonisch und
exakt an dieselbe Kette gebunden sein.

Claim und Evidence werden nur aus dem SHA-256 der Continuation-ID abgeleitet.

## Evidence vor Ressourcenbeobachtung

Exakt gebundene LQ-345-Continuation-Evidence wird vor Docker geprüft.

Ist sie vorhanden, lautet der Ausgang `continuation_evidence_present`. Ein
gleichzeitig offener Continuation-Claim wird nicht entfernt.

Fehlen Continuation-Evidence und exakter Continuation-Claim gemeinsam, lautet
der neutrale Ausgang `not_found` ohne Dockerzugriff.

Evidence ohne Claim ist ebenfalls `continuation_evidence_present`; der
Inspector erzeugt keinen Claim nachträglich.

Beschädigte, widersprüchliche oder anders gebundene Artefakte bleiben
technisch unavailable.

## Kanonischer Continuation-Claim

Ein vorhandener Claim muss regulär, owner-only, einfach verlinkt und
kanonisches JSON sein.

Er bindet Continuation-Autorisierung, `resume_from`, exakte Ressourcen,
Restbudget, Identitäten, alle Hashes und eine zeitzonenbehaftete Startzeit.

Alter oder Dateiname beweist keinen Zustand. Fremder Claim ist nicht
`not_found`.

## Frische LQ-341-Klassifikation

Nur bei offenem Continuation- und Cleanup-Claim ohne Continuation-Evidence
wird LQ-341 erneut ausgeführt.

LQ-341 rendert Compose read-only, verwendet exakte Listen und inspiziert nur
vorhandene erwartete Ressourcen.

Ein früherer oder caller-gelieferter LQ-341-Ausgang wird nicht akzeptiert.

Das Datenvolume muss in jedem zulässigen Präfix unverändert rungebunden
vorhanden sein.

## Zulässige Präfixordnung

Die globale Reihenfolge ist:

1. `container_stopped`;
2. `container_removed`;
3. `application_network_removed`;
4. `runtime_removed_evidence_missing`.

Für `resume_from=container_stopped` sind alle vier Zustände zulässig.
Für `resume_from=container_removed` sind nur Zustände zwei bis vier zulässig.
Für `resume_from=application_network_removed` sind nur Zustände drei und vier
zulässig.

Der exakt gleiche Zustand bedeutet `continuation_not_started`.

Ein späterer noch nicht finaler Präfix wird mit seinem exakten Zustand
`container_removed` oder `application_network_removed` ausgegeben.

Vollständige Runtimeentfernung ergibt `runtime_removed_evidence_missing`.

Diese Beobachtung beweist keine verlorene Prozessbestätigung und erteilt kein
Fortsetzungsrecht.

## Konfliktzustände

Jeder lesbare Zustand vor `resume_from` oder außerhalb der Präfixordnung
ergibt `conflict`.

Dazu gehören `runtime_intact`, fehlender ursprünglicher Cleanup-Claim,
`final_evidence_present`, unmögliche Ressourcenreihenfolge, fremde Endpoints
und jede Volume-Abweichung.

Conflict erlaubt weder Claimfreigabe, Fortsetzung, Finalisierung noch
Ressourcenbereinigung.

## Technische Nichtverfügbarkeit

Malformed Output, Nonzero, stderr, Timeout, Truncation, Hard Kill, doppelte
JSON-Schlüssel oder uneindeutige Namenslisten bleiben unavailable.

Unavailable wird nicht als Konflikt, Abwesenheit oder Fortschritt
umgedeutet.

Der Inspector liest keine Docker-Events, Logs, Historie, SQL- oder
Volumeinhalte.

## Strikte Read-only-Grenze

Erlaubt sind nur private Dateireads sowie die bereits read-only LQ-341-
Composition.

Claimanlage, Claimfreigabe, Evidencewrite, Stop, Start, Remove, Disconnect,
Down, Kill, Prune und Volumezugriff sind verboten.

Auch bei vollständiger Runtimeentfernung bleiben beide Claims unverändert.

Kein Ausgang autorisiert einen weiteren Mutationsversuch automatisch.

## Neutrale Ausgabe

Der spätere Command liefert ausschließlich:

- `not_found` oder `continuation_evidence_present`;
- `continuation_not_started`;
- `container_removed` oder `application_network_removed`;
- `runtime_removed_evidence_missing`;
- `conflict`;
- technisch unavailable ohne Ergebnisobjekt.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_cleanup_continuation_reconciliation` und Ausgang.
Private Details bleiben verborgen.

## Retention und Nichtwiederverwendung

Continuation-Reconciliation-, Continuation-, Cleanup- und Run-ID, Claims,
Autorisierungen und Evidence bleiben mindestens so lange unterscheidbar, wie
Audit, Retry, Reconciliation oder Finalisierung sie benötigen.

Keine ID oder Evidence darf unter anderer Bindung wiederverwendet werden. Das
Volume bleibt dem ursprünglichen Run zugeordnet.

Dieser Vertrag bestimmt keine konkrete Retentionfrist oder Ablagestrategie.

## Nichtziele

LQ-346 implementiert keinen Inspector, Entry Point, Test, Claim-, Evidence-
oder Ressourcemutator.

Es gibt keine Volume-Löschung, Schema-, Tabellen-, SQL-, Migration-, Port-,
Domainmodell-, Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 38 Entry Points, 42 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-347 sollte den read-only Continuation-Claim-Inspector samt geschlossener
Präfixmatrix und Fake-basierten Tests implementieren.
Claimfinalisierung, erneute Fortsetzung und jede Volumenlöschung bleiben
separate spätere Slices.
