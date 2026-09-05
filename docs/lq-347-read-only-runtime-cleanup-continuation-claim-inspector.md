# LQ-347 — Read-only Runtime Cleanup Continuation Claim Inspector

## Ergebnis

LQ-347 implementiert den in LQ-346 definierten strikt read-only Inspector
für einen offenen LQ-345-Continuation-Claim.

Der Operator klassifiziert ausschließlich den beobachteten Cleanup-Präfix.
Er setzt weder Cleanup noch Finalisierung fort.
## Kommando

Der neue Entry Point lautet
`liquent-disposable-postgres-cleanup-continue-reconcile`.

Er verlangt explizite Pfade für die vollständige historische Kette, die neue
Continuation-Reconciliation-Autorisierung, Docker, Compose, beide
Environment-Dateien und das private Evidence-Verzeichnis.

Es gibt keine implizite Pfadauflösung und keinen caller-gelieferten Zustand.
## Neue Autorisierung

Die Autorisierung bindet geschlossen:

- eine stabile Continuation-Reconciliation-ID;
- Continuation-, Cleanup-Reconciliation-, Cleanup- und Run-ID;
- Phase, Source-Commit, Image-Referenz und Compose-Hash;
- Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- sämtliche vorgelagerten Evidence- und Autorisierungshashes;
- den SHA-256 der exakten LQ-345-Autorisierungsdatei;
- Scope `runtime_only` und das historische `resume_from`;
- Operation `inspect_disposable_postgres_cleanup_continuation`;
- getrennte Executor- und Autorisiereridentitäten;
- ein aktuelles UTC-Zeitfenster von höchstens einer Stunde.

Unbekannte, fehlende oder zusätzliche Felder werden nicht toleriert.
## Historische Bindung

LQ-347 validiert die LQ-345- und LQ-341-Autorisierungen an ihrem jeweiligen
historischen Fenstermittelpunkt erneut.

Die neue Autorisierung wird dagegen mit der aktuellen Clock geprüft.

Ihre gebundenen IDs, Artefakthashes und `resume_from` müssen exakt mit der
historischen Continuation übereinstimmen.

Auch Run-ID, Cleanup-ID, Cleanup-Reconciliation-ID und Projektname werden
gegen die ursprüngliche Kette geprüft.

Eine Datei oder ein Dateiname allein schafft keine Autorität.
## Ursprünglicher Cleanup-Claim

Vor jeder Continuation-Auswertung wird der ursprüngliche LQ-339-Cleanup-Claim
aus dem SHA-256 der Cleanup-ID abgeleitet.

Er muss regulär, owner-only, einfach verlinkt und vollständig an die
kanonische Cleanup-Bindung gebunden sein.

Seine neutrale Abwesenheit ergibt `conflict`, weil ein Continuation-Claim
ohne den weiterhin offenen Ursprungsclaim keine zulässige Kette darstellt.

Ein beschädigter oder fremd gebundener Claim bleibt technisch unavailable.
## Evidence-first-Auswertung

Continuation-Claim und -Evidence werden ausschließlich aus dem SHA-256 der
Continuation-ID abgeleitet.

Exakt gebundene LQ-345-Evidence wird zuerst geprüft.

Ist sie vorhanden, lautet der Ausgang `continuation_evidence_present`.

Ein gleichzeitig offener Continuation-Claim wird dabei bewusst nicht
freigegeben oder verändert.

Fehlen Evidence und Claim gemeinsam, lautet der Ausgang `not_found`.

In beiden Fällen wird LQ-341 nicht ausgeführt und Docker nicht aufgerufen.

Malformed oder widersprüchliche Artefakte sind keine neutrale Abwesenheit.
## Doppelclaim-Gate

Nur ein exakter ursprünglicher Cleanup-Claim zusammen mit einem exakten
Continuation-Claim öffnet die read-only Ressourcenbeobachtung.

Der Continuation-Claim muss die vollständige LQ-345-Evidence-Bindung und eine
zeitzonenbehaftete Startzeit enthalten.

Der Inspector schreibt keinen fehlenden Claim nach.

Er repariert, ersetzt, löscht oder übernimmt keinen vorhandenen Claim.
## Frische LQ-341-Beobachtung

Bei offenem Doppelclaim ohne Continuation-Evidence komponiert LQ-347 den
bestehenden LQ-341-Inspector neu.

Dabei wird die historische LQ-341-Autorisierung ausschließlich an ihrem
ursprünglichen gültigen Mittelpunkt verwendet.

Der LQ-341-Ausgang muss kanonisches JSON mit exakter Operation und exakt drei
Feldern sein.

Ein gespeicherter oder caller-gelieferter Beobachtungsausgang wird nicht
akzeptiert.

LQ-341 bleibt zuständig für Compose-Modell, exakte Ressourcennamen,
Netzwerkisolation und unverändert rungebundenes Datenvolume.
## Geschlossene Präfixmatrix

Die implementierte Ordnung lautet: 1. `container_stopped`;
2. `container_removed`;
3. `application_network_removed`;
4. `runtime_removed_evidence_missing`.

Ein Zustand gleich `resume_from` ergibt `continuation_not_started`.

Ein späterer Teilzustand wird exakt als `container_removed` oder
`application_network_removed` ausgegeben.

Der terminal beobachtbare Präfix ergibt
`runtime_removed_evidence_missing`.

Ein früherer Zustand ist eine Regression und ergibt `conflict`.
## Zustände außerhalb der Ordnung

`runtime_intact`, `final_evidence_present`, `not_found` und jeder andere
lesbare LQ-341-Ausgang ergeben `conflict`.

Damit werden fehlende Ursprungsautorität, bereits finalisierte Ketten und
unmögliche Ressourcenbilder nicht als Fortschritt umgedeutet.

Keiner dieser Ausgänge autorisiert Mutation, Retry oder Finalisierung.
## Detailfreie technische Nichtverfügbarkeit

Ungültige Autorisierungen, falsche Hashbindungen, malformed private Dateien,
doppelte JSON-Schlüssel und nichtkanonische Inspector-Ausgabe bleiben
technisch unavailable.

Das Kommando liefert dann Exitcode 2 ohne Ergebnisobjekt oder interne Details.

LQ-347 führt dafür keinen neuen öffentlichen Fehlertyp oder Protokollstatus
ein.
## Strikte Read-only-Eigenschaft

Der Operator besitzt keinen Write-, Remove-, Stop-, Start-, Disconnect-,
Down-, Kill-, Prune- oder Volume-Mutationspfad.

Auch erfolgreiche Klassifikation verändert weder Cleanup- noch
Continuation-Claim und schreibt keine Evidence.

Die Tests prüfen Claims vor und nach jeder Matrixentscheidung bytegenau.

Evidence-first- und Abwesenheitsfälle beweisen zusätzlich, dass der
LQ-341-Inspector nicht aufgerufen wird.
## Neutrale Ausgabe

Die kanonische Ausgabe enthält nur `schema_version: 1`,
- Operation `disposable_postgres_cleanup_continuation_reconciliation`;
- einen geschlossenen Ausgang aus LQ-346.

Ressourcennamen, Pfade, IDs, Hashes und technische Fehlerdetails verlassen
die Operatorgrenze nicht.
## Retention und Nichtwiederverwendung

Reconciliation-, Continuation-, Cleanup- und Run-IDs sowie Claims,
Autorisierungen und Evidence müssen mindestens für Audit, Reconciliation,
Retry und Finalisierung unterscheidbar bleiben.

Keine ID und kein Artefakt darf unter einer anderen Bindung wiederverwendet
werden.

LQ-347 legt weder konkrete Speicherform noch Retentionfrist fest.
## Verifikation

Fake-basierte Tests decken die vollständige zulässige Präfixmatrix,
Regressionen, Evidence-first, neutrale Abwesenheit, fehlenden Ursprungsclaim,
malformed Claim und die detailfreie CLI-Grenze ab.
Das Bundle umfasst nun 39 Entry Points, 43 Operatormodule, 27 Migrationen und
weiterhin Head `20260819_0027`.
## Nichtziele
Dieser Slice enthält keine Claimfreigabe, Evidencepersistenz, erneute
Continuation, Ressourcenmutation oder Volume-Löschung.

Er entscheidet keine Schema-, Tabellen-, SQL-, Migration-, Port-,
Domainmodell-, Signatur-, Compose- oder Production-Wiring-Änderung.
## Nächster Slice

LQ-348 sollte die evidence-first Finalisierung eines reconcilierten
Continuation-Claims getrennt definieren.

Erneute Fortsetzung ab einem späteren Teilpräfix und jede Volumenlöschung
bleiben weiterhin eigenständige spätere Entscheidungen.
