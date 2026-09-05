# LQ-337 — Read-only Disposable PostgreSQL Cleanup Preflight

## Ergebnis

LQ-337 installiert `liquent-disposable-postgres-cleanup-preflight` als
read-only Preflight für eine explizit autorisierte Cleanupprüfung.

Der Command validiert die gesamte Evidence- und Autorisierungskette, leitet
LQ-335 erneut ab und klassifiziert den aktuellen Dockerbestand als `ready`,
`already_absent` oder `rejected`.

Er erzeugt keinen Claim und stoppt oder entfernt keine Ressource.

## Cleanup-Autorisierung

Die owner-only Cleanup-Datei bindet geschlossen:

- Cleanup-ID, Run-ID und Phase `disposable_postgres`;
- Source-Commit, Application-Image-Digest und Compose-SHA-256;
- Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- SHA-256 von Staging-, LQ-332- und LQ-333-Evidence;
- SHA-256 der vollständigen Dispositionsautorisierung;
- Operation `remove_disposable_postgres_resources`;
- Scope `runtime_only` oder `runtime_and_data_volume`;
- getrennte Cleanup-Identitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Sie akzeptiert keine Ressourcennamen, Dockerargumente, Allow-Booleans oder
freien Scope.

## Vollständige Bindungsprüfung

Historische Run- und Reconciliation-Autorisierungen sowie aktuelle
Disposition und Cleanup-Autorisierung müssen Run, Source, Image, Compose und
IDs exakt konsistent binden.

Der SHA-256 der Dispositionsdatei muss bytegenau dem Cleanuprecord
entsprechen. Die drei Evidencehashes müssen unverändert aus der
Dispositionsautorisierung übernommen sein.

Jede Abweichung, unbekannte Struktur, doppelte Schlüssel, falsche Rechte,
stale Zeit oder technisch nicht lesbare Datei endet unavailable.

## Claimfreiheit

Der Cleanup-Claimname wird intern ausschließlich aus dem vollständigen
SHA-256 der Cleanup-ID abgeleitet.

Existiert dieser Claim bereits, endet der Preflight vor Docker unavailable.
Er liest kein Alter und entfernt den Claim nicht.

Die ursprünglichen Reconciliation-Claims werden erneut durch den aufgerufenen
LQ-335-Resolver geprüft. Ein offener Claim kann nicht durch Cleanup umgangen
werden.

## Erneute Disposition

Der Preflight ruft den reinen LQ-335-Resolver mit denselben gebundenen Dateien
und derselben injizierten Uhr erneut auf.

Nur exakt `cleanup_review_eligible` erreicht die aktuelle Ressourcenprüfung.

Ein caller-gelieferter früherer Output, `retain`, `new_run_eligible`,
`investigation_required` oder technische Nichtverfügbarkeit wird nicht in
Cleanup-Eignung umgedeutet.

## Aktuelle Ressourcenbeobachtung

Die bestehende LQ-331-Klassifikation wird erneut mit historisch validierter
Reconciliation-Autorisierung ausgeführt.

Sie rendert das SHA-gebundene Composemodell, leitet Container, beide internen
Netze und Volume ausschließlich aus dem Run ab und verwendet nur feste
read-only Listen und Inspects.

Alle Prozesse erhalten absoluten Dockerpfad, temporäres leeres CWD,
`LANG=C`, `LC_ALL=C`, feste Zeit- und Outputgrenzen sowie keine Shell.

Der Preflight verwendet kein `up`, `down`, Start, Stop, Remove, Prune oder
SQL.

## Geschlossene Ausgänge

Vollständige aktuelle Abwesenheit ergibt `already_absent`.

Teilbestand, fremde Bindung oder vollständig lesbarer Isolationsbruch ergibt
`rejected`.

Vollständig vorhandener exakt isolierter Bestand mit Scope `runtime_only`
ergibt `ready`.

Malformed Dockeroutput, Nonzero, stderr, Timeout, Truncation oder Hard Kill
bleibt technisch unavailable und wird nicht als `rejected` ausgegeben.

## Konservative Volumengrenze

Scope `runtime_and_data_volume` ergibt in LQ-337 selbst bei exakt isoliertem
Bestand `rejected`.

Grund ist das weiterhin fehlende autoritative System-of-Record für
Retention-, Legal-Hold-, Backup-, Investigation- und manuelle
Datenbankzugriffsfreigaben.

Die Scopeangabe in der Cleanup-Autorisierung beweist diese Abwesenheit nicht.
Staging-Evidence allein kann keine außerhalb des kontrollierten Executors
erfolgte Datenhaltung ausschließen.

Der Preflight prüft weder Volumeinhalt noch PostgreSQL-Dateien oder SQL und
erfindet keine Clearance aus Alter, Größe oder vermeintlicher Leere.

Es gibt keine automatische Herabstufung auf `runtime_only`. Dafür ist eine
neue Cleanup-ID und separate `runtime_only`-Autorisierung erforderlich.

## Bedeutung von `ready`

`ready` bedeutet nur, dass der Scope `runtime_only` unter den aktuellen
gebundenen Beobachtungen in einem späteren Operator erneut geprüft werden
darf.

Es ist kein Delete-Ticket und wird nicht persistiert. Ein späterer mutierender
Operator muss alle Inputs und den Preflight unmittelbar vor dem ersten Effekt
erneut validieren.

`ready` autorisiert insbesondere keine Volumenlöschung, keinen neuen Run,
keine Migration und kein Deployment.

## Neutrale Ausgabe

Erfolg schreibt nur Schema-Version, Operation
`disposable_postgres_cleanup_preflight` und den geschlossenen Ausgang.

Scope, IDs, Hashes, Ressourcen, Pfade, Images, Identitäten, Zeitwerte und
Ablehnungsgründe bleiben privat.

Technische Nichtverfügbarkeit endet still mit Exitcode zwei und ohne
stdout/stderr.

## Tests

Tests prüfen `ready` für exakten `runtime_only`-Bestand,
`already_absent`, `rejected` für Teilbestand und die konservative Sperre des
Volumenscopes.

Hashabweichung und vorhandener Cleanup-Claim stoppen vor Docker. Alle
beobachteten Commands bleiben frei von Up, Down, Remove und Prune. Die CLI
gibt ausschließlich den kanonischen Handoff oder nichts aus.

Kein Test startet oder entfernt Dockerressourcen.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 34 Entry Points und 38
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-337 implementiert keinen Cleanup-Claim, Evidencewriter, Stop, Remove,
Volumen-Clearance-Store oder Unknown-Outcome-Reconciliation.

Es gibt keine Schema-, SQL-, Migration-, Port-, Domainmodell-, Compose- oder
Production-Wiring-Änderung.

## Nächster Slice

LQ-338 sollte den mutierenden `runtime_only`-Cleanup-Vertrag definieren:
exakte Einzelressourcen, Reihenfolge, Evidence-first Claim, Unknown Outcome
und spätere Reconciliation. Das Datenvolume muss ausdrücklich außerhalb des
Mutationsbudgets bleiben.
