# LQ-323 — Private Artifact Probe Recovery Evidence Handoff

## Ergebnis

LQ-323 ergänzt die LQ-322-Recovery-Composition um private atomare Evidence,
stabile Konkurrenzordnung und einen finalen detailarmen Operator-Handoff.

Ein bestätigter Abschluss wird bei exakter technischer Wiederholung vor jedem
Compose- oder Dockerzugriff aus Evidence zurückgegeben. Ein unbekannter
Prozessausgang bleibt dagegen durch einen stabilen Claim geschlossen und wird
nicht automatisch erneut ausgeführt.

## Privates Evidenceziel

Der Recovery-Command verlangt ein absolutes, bereits vorhandenes, echtes
owner-besessenes Verzeichnis ohne Group-/World-Rechte und ohne Symlink.

Er erstellt das Verzeichnis nicht, durchsucht keine übergeordneten Pfade und
akzeptiert keinen Environmentfallback.

Der Evidence-Dateiname ist ausschließlich der lowercase SHA-256 der stabilen
Recovery-ID. Die Recovery-ID selbst erscheint weder im Dateinamen noch in der
Konsolenausgabe.

## Vollständig gebundener Evidenceinhalt

Die private Evidence bindet:

- Schema-Version und stabile Recovery-ID;
- ursprüngliche Run-ID und Phase `artifact_capabilities`;
- Source-Commit, Image-Digest und Compose-SHA-256;
- Recovery-Executor und getrennten Autorisierer;
- neutralen Ausgang `already_absent`, `removed` oder `conflict`;
- aware-UTC-Abschlusszeit.

Token, Prefix, Volume-Name, Hostpfad, Datei-, Inhalts-, Inode-, Modus- oder
Systemfehlerdetails werden nicht gespeichert.

Evidence ist keine Readiness- oder Capabilityentscheidung und verändert die
ursprüngliche unavailable Stagingphase nicht.

## Exklusive atomare Veröffentlichung

Der Operator schreibt kanonisches JSON vollständig in eine neue owner-only
Temporärdatei mit Modus 0600 und fsynct sie.

Ein exklusiver Hardlink veröffentlicht den finalen Namen nur bei Abwesenheit.
Danach wird der temporäre Name entfernt, das Verzeichnis fsynct und die finale
Datei vollständig zurückgelesen.

Der Read-back verlangt reguläre Datei, aktuellen Owner, Modus 0600, Linkcount
eins, exakte Feldmenge und bytegenaue Bindungswerte.

Bestehende Evidence wird nie überschrieben, ersetzt, gekürzt oder unter einer
neuen Bedeutung akzeptiert.

## Stabiler Recovery-Claim

Fehlt finale Evidence, erstellt der Operator vor Compose und Docker exklusiv
eine stabile owner-only Claim-Datei, ebenfalls aus dem Hash der Recovery-ID.

Ein vorhandener Claim stoppt jeden weiteren Versuch vor Prozesszugriff. Es
gibt kein Warten, Stehlen, Timeout-Reaping oder automatisches Löschen eines
vermeintlich stale Claims.

Damit können konkurrierende Recoveryprozesse nicht beide Inspect oder Remove
starten.

Nach atomar bestätigter Evidence wird der Claim entfernt und das Verzeichnis
erneut fsynct. Finale Evidence wird immer vor einem Claim geprüft, sodass ein
vollständig abgeschlossener Lauf reproduzierbar bleibt.

## Exakte technische Wiederholung

Existiert finale Evidence, werden sämtliche aktuellen Recovery-Bindungswerte
gegen ihren unveränderlichen Inhalt geprüft.

Bei exakter Übereinstimmung liefert der Operator denselben neutralen Ausgang
ohne Compose-Render, Inspector oder Remove-Container zurück. Weder Uhrzeit noch
Evidence werden verändert.

Dieselbe Recovery-ID mit anderem Run, Source, Image, Compose, Phase oder
Identitäten endet detailfrei unavailable. Es gibt kein Last-write-wins und
keine neue Evidence-Datei.

## Unknown Outcome

Scheitert Compose, Inspection, Remove oder Evidencefinalisierung nach Claim-
Erzeugung technisch, bleibt der Claim bestehen.

Der Operator entfernt ihn weder im Exceptionpfad noch bei einem späteren
Aufruf. Dadurch wird ein möglicher externer Remove-Effekt niemals automatisch
wiederholt oder als abgeschlossen erfunden.

Eine spätere Claim-Recovery benötigt einen eigenen ausdrücklich autorisierten
Vertrag, der Evidence- und Volumezustand unabhängig abgleicht. LQ-323
implementiert kein Force-Unlock.

## Detailarmer Handoff

stdout enthält weiterhin ausschließlich Schema-Version, Operation
`artifact_probe_recovery` und den neutralen Ausgang.

Malformed Input, Bindungskonflikt, vorhandener Claim, beschädigte Evidence,
I/O-Fehler und technische Prozessausgänge enden still mit dem bestehenden
detailfreien Exitcode zwei.

Weder Recovery-ID noch Run, Identitäten, Image, Compose, Pfade oder interne
Ursachen verlassen die Prozessgrenze.

## Tests

Tests beweisen private 0600-Evidence, genau eine finale JSON-Datei und exakten
Retry ohne Prozessaufruf.

Ein simulierter unbekannter Remove-Ausgang erzeugt keine finale Evidence und
lässt den Claim bestehen. Ein zweiter Aufruf stoppt deshalb vor Compose und
Docker.

Alle Dockerbeobachtungen bleiben injiziert; es wird kein realer Container oder
externes Volume verwendet.

## Bundle und Nichtziele

LQ-323 erweitert den bestehenden LQ-322-Operator. Bundle-Gates bleiben 28 Entry
Points, 31 Operatormodule und 27 Migrationen mit Head `20260819_0027`.

Es gibt keine Tabelle, SQL-, Migration-, Port-, Domainmodell-, Compose-,
Production-Wiring- oder reale Stagingänderung. Claim-Recovery, Force-Unlock,
Retentionlöschung und Evidenceexport sind nicht enthalten.

## Nächster Slice

LQ-324 sollte den kontrollierten Claim-Reconciliation-Vertrag definieren. Er
muss zuerst finale Evidence und den aktuellen Probe-Prefix read-only abgleichen
und darf einen Claim nur nach eindeutig bestätigtem Ausgang entfernen oder
finalisieren; unbekannte Zustände bleiben geschlossen.
