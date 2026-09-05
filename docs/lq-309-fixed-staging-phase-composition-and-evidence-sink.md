# LQ-309 — Fixed Staging Phase Composition and Evidence Sink

## Ergebnis

LQ-309 komponiert die LQ-308-Prozess- und Parsergrenze zu einem vollständigen
injizierbaren `StagingPhaseRunner` für LQ-306.

Die Composition plant für jede der 29 Phasen einen festen Aufruf eines
expliziten Probe-Executables, reduziert dessen begrenzte Ausgabe und speichert
das neutrale Evidenceobjekt privat sowie atomar.

Es existiert weiterhin kein Probe-Executable und keine CLI; der Slice führt
keine Docker- oder Stagingoperation aus.

## Explizite Inputs

`StagingProcessInputs` bindet absolute Pfade für Probe- und Docker-Executable,
leeres privates Arbeitsverzeichnis, owner-only Autorisierungsdatei, Composefile
sowie owner-only Runtime- und Image-Environmentdateien.

Die beiden Executables müssen regulär und ausführbar sein. Environmentdateien
müssen regulär, aktueller-Owner-besessen, Linkcount eins, nicht verlinkt und
0400 oder 0600 sein.

Das Arbeitsverzeichnis muss dem aktuellen Owner gehören, keine Group-/World-
Rechte besitzen und vor jedem Phasenplan leer sein.

## Feste Commandcomposition

Jeder Request beginnt mit dem absoluten Probe-Executable und enthält exakt:

- `--phase` mit einem der 29 bekannten Namen;
- `--docker-executable` mit dem absoluten gebundenen Dockerpfad;
- `--authorization-file` mit der owner-only Runbindung;
- `--compose-file`;
- genau eine Runtime- und eine Image-Environmentdatei;
- `--project-name` als `liquent-<validierte-run-id>`.

Unbekannte Phasen oder Projekt-IDs über 63 Zeichen scheitern vor Prozessstart.

Die Umgebung besteht exakt aus `LANG=C` und `LC_ALL=C`. Es gibt keinen PATH,
Proxy, Dockeroverride, Credential-, Python-, Shell- oder Gitwert.

Read-only Prüfphasen erhalten 60 Sekunden; mutierende beziehungsweise wartende
Phasen 300 Sekunden. Output ist auf 65536 Bytes pro Kanal begrenzt und die
Terminate-Grace auf fünf Sekunden festgesetzt.

## EvidenceObjectSink

Der Sink verlangt ein absolutes, aktueller-Owner-besessenes privates
Verzeichnis ohne Symlink.

Er hasht ausschließlich den kanonischen reduzierten LQ-308-Output, schreibt ihn
vollständig in eine neue 0600-Tempdatei, fsynct, verlinkt atomar auf einen aus
Phase und Digest abgeleiteten Namen und fsynct das Verzeichnis.

Danach liest er das Objekt zurück und prüft SHA-256 erneut. Erst dann entsteht
`StagingPhaseEvidence` mit Status, opaker `evidence:<sha256>`-Referenz und
Digest.

Ein bestehendes gleiches oder anderes Ziel wird nicht ersetzt. Ein zweiter
Store derselben Phase/Evidence scheitert geschlossen.

Bei technischem Fehler wird die Tempdatei entfernt; bestehende Evidence bleibt
unverändert.

## Vollständige Composition

`ComposedStagingPhaseRunner` führt exakt Plan, begrenzten Prozessaufruf,
phasenspezifische Reduktion und privaten Store aus.

Jeder Fehler wird detailfrei zu `staging_phase_composition_unavailable`.
Insbesondere erzeugen Nonzero, stderr, Timeout, Truncation, Hard Kill,
Parserfehler oder privater Output kein Evidenceobjekt.

LQ-306 behandelt diese Exception als `unavailable` und stoppt alle späteren
Phaseaufrufe.

## Ressourcen- und Entscheidungsgrenze

Composition und Sink besitzen nur erzeugte Requests, kurzlebige reduzierte
Bytes und neu erzeugte Evidenceobjekte.

Sie entscheiden kein Approval, führen keinen Retry aus und besitzen keine
Docker-, Datenbank-, Image-, Container-, Volume- oder Netzwerkressource.

## Bundle

Das zusätzliche Operatormodul erhöht das Gate auf 24 Operatormodule. Die Zahl
der Console Entry Points bleibt 22, Migration-Head und Migrationszahl bleiben
`20260819_0027` und 27.

## Nichtziele

Kein reales Probe-Executable, keine Docker-Kommandos, SQL-/HTTP-Prüfungen,
Signaloperation, CLI oder Production-/Staging-Wiring werden implementiert.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell- oder
Composeänderung.

## Nächster Slice

LQ-310 sollte den geschlossenen staging-only Probe-Command-Vertrag definieren:
zulässige Inputs, feste Docker-Compose-Subcommands, phasenspezifische
Read-only-/Mutationsgrenzen und neutrale JSON-Ausgaben.
