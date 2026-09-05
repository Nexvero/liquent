# LQ-392 — Read-only PostgreSQL Volume Deletion Preflight

## Ergebnis

LQ-392 implementiert den in LQ-391 definierten read-only Preflight als
`liquent-disposable-postgres-volume-deletion-preflight`.

Der Command prüft eine neue owner-only Löschautorisierung und führt den
LQ-390-Resolver mit den gebundenen System-of-Record-Dateien frisch aus.

Er legt keinen Claim an und verändert kein Volume.

## Geschlossene Löschautorisierung

Die private Autorisierung bindet stabile, nicht wiederverwendbare Volume-
Deletion- und Claim-IDs.

Run, Phase, Source, Image, Compose, intern abgeleitetes Volume,
Resolverautorisierung, Lineage sowie Retention-, Hold- und Recoveryentscheidung
sind bytegenau gebunden.

Operation ist exakt `remove_disposable_postgres_data_volume` und Scope exakt
`data_volume_only`.

Executor, Authorizer und Reviewer müssen drei verschiedene opake Identitäten
sein.

Das aktuelle UTC-Zeitfenster ist positiv und auf höchstens eine Stunde
begrenzt.

## Keine Authority aus dem Caller

Der Preflight akzeptiert keinen gewünschten Ausgang, Allow-Boolean,
Caller-Rollennamen, Volumeselector oder freien Scope.

Der Projektname muss exakt `liquent-<run-id>` sein.

Das einzige Ziel wird daraus als `<project-name>-postgres-data` abgeleitet und
gegen die Löschautorisierung geprüft.

Wildcard-, Prefix-, Labelgruppen-, Host- und Composeprojektauswahl bleiben
unerreichbar.

## Bytegenaue Vorgängerbindung

Der SHA-256 der vollständigen LQ-390-Resolverautorisierung muss exakt der
Löschautorisierung entsprechen.

Volume-Disposition-ID, Lineagehash sowie Hashes und stabile IDs der aktuellen
Retention-, Legal-Hold- und Recoveryentscheidungen müssen durchgängig
übereinstimmen.

Run, Source, Image und Compose werden zwischen Resolver- und Löschauthority
erneut verglichen.

Hashabweichung, doppelte Schlüssel, unbekannte Felder oder malformed Material
endet vor jeder Dockerbeobachtung technisch unavailable.

## Getrennte Identitäten

Die drei Löschidentitäten, drei Resolveridentitäten und drei fachlichen
Clearance-Authorizer müssen insgesamt neun verschiedene Identitäten sein.

Damit kann weder der Resolveractor noch einer der Retention-, Hold- oder
Recoveryentscheider allein eine positive Löschprüfung erzeugen.

Identitätskollision wird nicht als fachliche Ablehnung veröffentlicht, sondern
stoppt fail-closed.

## Claimfreiheit

Vor dem frischen Resolveraufruf prüft der Preflight das private
Evidenceverzeichnis auf jeden Volume-Deletion-Claim.

Ein erwarteter oder anderer Claim derselben Operationsklasse ist technische
Nichtverfügbarkeit.

Der Claim wird weder gelesen noch gelöscht oder ersetzt.

Die in der Autorisierung vorab gebundene Claim-ID wird erst in einem späteren
mutierenden Slice für die exklusive Neuanlage verwendet.

Auch der LQ-390-Resolver prüft weiterhin die historischen Cleanup-Claims.

## Frische LQ-390-Auflösung

Der Preflight ruft den Resolver intern mit exakt denselben gebundenen Dateien,
dem intern gebundenen Projekt und dem privaten Evidenceverzeichnis auf.

Dadurch werden aktuelle Retention-, Hold-, Recovery- und Lineagefakten erneut
validiert.

Es gibt keinen gespeicherten positiven Ausgang, Cache oder caller-gelieferten
Handoff.

Der Resolver führt genau eine read-only Inspektion des intern abgeleiteten
Volumes aus.

Der Preflight selbst führt keinen zusätzlichen Dockeraufruf aus.

## Geschlossene Ausgangsabbildung

LQ-390-`deletion_review_eligible` wird zu `ready`.

LQ-390-`retain` wird zu `rejected`.

LQ-390-`investigation_required` bleibt `investigation_required`.

Technische Nichtverfügbarkeit des Resolvers oder einer Preflightprüfung bleibt
detailfrei ohne Ergebnisobjekt.

Kein Ausgang wird aus Exitcode, fehlender Ausgabe oder Ressourcenabwesenheit
erraten.

## Bedeutung von ready

`ready` bestätigt nur den read-only Zustand am Ende dieses Aufrufs.

Es ist kein dauerhaftes Token, kein Claim, kein Deleteauftrag und keine
Mutationserlaubnis.

Ein späterer Operator muss dieselbe Löschautorisierung und sämtliche aktuellen
System-of-Record-Fakten unmittelbar vor dem ersten Effekt erneut prüfen.

Erst danach darf er die vorab gebundene Claim-ID exklusiv und durable anlegen.

## Keine Seiteneffekte

Der Preflight schreibt keine Evidence, Claims, Locks oder Marker.

Er ändert keine Rechte, Labels, Namen, Retention-, Hold- oder Recoveryfakten.

Er mountet, öffnet, exportiert oder entfernt das Volume nicht und führt kein
SQL aus.

Der einzige zulässige Ressourcenargv stammt aus LQ-390 und ist ein exakt
gebundenes `docker volume inspect`.

## Detailarme CLI

Erfolg schreibt ausschließlich Schemaversion, feste Operation
`disposable_postgres_volume_deletion_preflight` und einen der Ausgänge
`ready`, `rejected` oder `investigation_required`.

Technische Nichtverfügbarkeit endet mit Exitcode zwei ohne stdout oder stderr.

Interne Run-, Volume-, Claim-, Evidence-, Clearance-, Identitäts-, Hash-, Zeit-
und Pfaddetails bleiben privat.

## Tests

Siebzehn Tests prüfen:

- vollständig positiven frischen Resolverhandoff zu `ready`;
- unverändertes leeres Evidenceverzeichnis und exakt einen read-only Docker-
  argv;
- `rejected` bei Retain, aktivem Hold, pending Backup/Restore und späterer
  Nutzung;
- `investigation_required` bei Holdkonflikt, Volumeabwesenheit und
  Fremdbindung;
- fail-closed Hashabweichung und vorhandenen Volume-Deletion-Claim;
- unzulässigen Scope, Operation, Caller-Volume und Identitätskollision;
- detailarme CLI und installierten Entry Point.

Kein Test legt einen Claim an oder entfernt ein Volume.

## Bundle und Nichtziele

LQ-392 ergänzt ein Operatormodul und einen Console Entry Point.

Der Bundle-Bestand steigt auf 51 Entry Points und 55 Operatormodule.

Migrationen bleiben 27 mit Head `20260819_0027`.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose-, Service-, HTTP- oder Production-Wiring-Änderung.

Der Slice implementiert keinen Autorisierungsgenerator, Claimwriter,
Volume-Remove, Inspector, Finalizer oder Reconciliationprozess.

## Nächster Slice

LQ-393 sollte den owner-kontrollierten PostgreSQL-Volume-Deletion-Operator als
Evidence-first-Vertrag definieren.

Er muss den Preflight frisch wiederholen, den vorab gebundenen Claim exklusiv
vor dem ersten Effekt anlegen, genau ein Volume-Remove begrenzen und Unknown
Outcome ohne Blind-Retry erhalten.
