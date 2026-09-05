# LQ-338 — Runtime-only Disposable PostgreSQL Cleanup Contract

## Zweck

LQ-338 definiert den mutierenden Cleanupvertrag für einen vollständig
isolierten LQ-330-PostgreSQL-Bestand mit Scope exakt `runtime_only`.

Er umfasst nur den exakt gebundenen Container und seine zwei exklusiven
internen Runnetze. Das Datenvolume bleibt erhalten. Dieser Slice implementiert
keinen Command, Dockeraufruf, Claim, Evidencewriter oder Ressourceneffekt.

## Keine übertragene Löschentscheidung

Ein früherer LQ-337-Ausgang `ready` wird weder gespeichert noch als
Delete-Ticket akzeptiert.

Der spätere Operator muss dieselbe Cleanup-Autorisierung, alle gebundenen
Evidenceobjekte und den vollständigen LQ-337-Preflight unmittelbar vor dem
ersten möglichen Effekt erneut ausführen.

Nur ein dabei neu abgeleitetes `ready` für exakt `runtime_only` darf die
Claimanlage erreichen. `already_absent`, `rejected` und technische
Nichtverfügbarkeit erlauben keine Docker-Mutation.

Caller liefern weder Allow-Boolean, Ressourcennamen noch Dockerargumente.

## Geschlossenes Mutationsbudget

Das Mutationsbudget enthält ausschließlich:

- den exakt aus Run und Composemodell abgeleiteten PostgreSQL-Container;
- das exakt abgeleitete interne Application-Netz;
- das exakt abgeleitete interne Data-Netz.

Das rungebundene Datenvolume ist ausdrücklich nicht Teil des Budgets. Es darf
nicht entfernt, umbenannt, ersetzt, geleert oder anderweitig verändert werden.

Andere Ressourcen liegen trotz ähnlicher Namen oder Labels außerhalb.

## Letzte Isolation vor dem Claim

Zusätzlich zum erneut ausgeführten LQ-337-Preflight muss unmittelbar vor dem
Claim read-only feststehen:

- beide Netze sind intern, nicht extern und exakt dem Run zugeordnet;
- jedes Netz hat ausschließlich den gebundenen PostgreSQL-Container als
  Endpoint;
- kein fremder Container und kein anderer Service ist verbunden;
- Container, Netze und Volume entsprechen weiterhin derselben Run-, Image-
  und Composebindung;
- das Volume ist genau am gebundenen Container und am erwarteten Ziel
  zugeordnet;
- kein Cleanup- oder Reconciliation-Claim ist offen.

Teilbestand, zusätzliche Endpoints oder klare Fremdbindung ergibt neutral
`rejected` vor jeder Mutation. Uneindeutige oder technisch nicht lesbare
Beobachtung bleibt detailfrei unavailable.

## Evidence-first Cleanup-Claim

Der stabile Cleanup-Claimname wird intern aus dem vollständigen SHA-256 der
nicht wiederverwendbaren Cleanup-ID abgeleitet.

Er wird erst nach dem frischen `ready` owner-only mit exklusiver Neuanlage
geschrieben. Der Claim bindet mindestens Cleanup-ID, Run-ID, Scope,
Evidencehashes, Autorisierungshash und den Startzeitpunkt.

Datei und Verzeichnis sind privat. Exklusive Anlage, Flush und
Verzeichnissynchronisation müssen vor dem ersten Docker-Effekt erfolgreich
sein.

Ein bereits vorhandener Claim beendet den Versuch technisch unavailable. Er
wird weder überschrieben noch nach Alter entfernt.

## Exakte Reihenfolge

Nach erfolgreichem Claim ist nur diese Reihenfolge zulässig:

1. den exakten PostgreSQL-Container einmal kontrolliert mit festem begrenztem
   Grace-Zeitfenster stoppen;
2. read-only bestätigen, dass der Container gestoppt oder beendet ist;
3. den exakten Container einmal ohne Force- oder Volumeoption entfernen;
4. read-only seine vollständige Abwesenheit bestätigen;
5. das exakte Application-Netz einmal entfernen;
6. read-only seine vollständige Abwesenheit bestätigen;
7. das exakte Data-Netz einmal entfernen;
8. read-only seine vollständige Abwesenheit bestätigen;
9. das exakte Datenvolume inspizieren und unveränderte rungebundene Existenz
   bestätigen.

Jeder Schritt verwendet einen absoluten Dockerpfad, leeres temporäres CWD,
`LANG=C`, `LC_ALL=C`, keine Shell sowie feste Zeit- und Outputgrenzen.

Schritte dürfen nicht vertauscht, parallelisiert oder gebündelt werden.

## Verbotene Befehlsformen

`docker compose down`, `--volumes`, `--force`, Container-Kill, Network-
Disconnect, Projekt- oder System-Prune bleiben verboten.

Ebenso verboten sind Wildcards, Prefix-, Label- oder ungebundene
Projektselektion und alternative Fallbackbefehle.

Der Operator führt weder SQL noch Host- oder Volumedateisystemzugriff aus. Er
startet keinen Ersatzcontainer und keinen neuen Run.

## Unknown Outcome nach dem ersten Effekt

Ab dem ersten Stopaufruf gilt jede nicht eindeutig bestätigte Aktion als
Unknown Outcome.

Nonzero, stderr, Timeout, Truncation, Hard Kill, verlorene Bestätigung,
malformed Output oder widersprüchliche Nachbeobachtung stoppen sofort.

Es gibt keinen Retry, keine Fortsetzung, keinen Ersatzbefehl und keine
heuristische Erfolgsableitung durch nachträgliches Blind-Inspect.

Der Cleanup-Claim bleibt bestehen. Ein späterer separater
Reconciliation-Vertrag muss den exakten Teilzustand ausschließlich read-only
auflösen, bevor weitere Mutation denkbar ist.

Teilcleanup ist niemals vollständiger Erfolg.

## Finale Cleanup-Evidence

Nach vollständig bestätigter Sequenz wird private owner-only Evidence atomar
persistiert, bevor der Cleanup-Claim entfernt werden darf.

Sie bindet mindestens Cleanup-ID, Run-ID, Operation, Scope `runtime_only`,
alle Autorisierungs- und Evidencehashes, die exakt adressierten Ressourcen,
bestätigte Schrittfolge, erhaltenes Volume, getrennte Identitäten sowie UTC-
Start- und Abschlusszeit.

Der Evidencehash wird vor Claimfreigabe stabilisiert. Claimfreigabe benötigt
Flush und Verzeichnissynchronisation; ihr unbekannter Ausgang ist selbst ein
späterer Reconciliationfall.

Ein exakter Wiederholungsaufruf liest finale Evidence vor Dockerzugriff und
liefert denselben neutralen Abschluss, ohne erneut zu mutieren.

## Geschlossene Ausgänge

Der spätere Operator darf ausschließlich liefern:

- `removed_runtime` nach bestätigter Entfernung aller drei Runtimeobjekte und
  bestätigtem Erhalt des Volumes;
- `already_absent`, wenn der frische Preflight vollständige Abwesenheit
  feststellt und keine Mutation erfolgt;
- `rejected` bei vollständig lesbarer fehlender Cleanup-Eignung vor Mutation;
- technisch unavailable ohne Ergebnisobjekt.

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_runtime_cleanup` und Ausgang. IDs, Ressourcen, Hashes,
Pfade, Zeitwerte, Identitäten und Fehlerdetails bleiben privat.

## Retention und Nichtwiederverwendung

Cleanup-ID, Claim, Autorisierung, finale oder partielle Evidence und die
gesamte Run- und Reconciliationkette bleiben mindestens so lange eindeutig
erhalten, wie Audit, Idempotenz oder Unknown-Outcome-Reconciliation sie
benötigen.

Keine ID, kein Claimname und keine Evidence darf für anderen Scope, Run oder
neue Bedeutung wiederverwendet werden. Das erhaltene Volume darf nicht einem
neuen Run als dessen Datenvolume umgedeutet werden.

Dieser Vertrag legt keine konkrete Frist, Tabelle, Ablage- oder
Archivierungsstrategie fest.

## Nichtziele

LQ-338 implementiert keinen Cleanupoperator, Entry Point, Test, Claim,
Evidencewriter oder Reconciliationoperator.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 34 Entry Points, 38 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

`runtime_and_data_volume` bleibt vollständig gesperrt und außerhalb dieses
Slices.

## Nächster Slice

LQ-339 sollte den owner-kontrollierten `runtime_only`-Cleanupoperator samt
Claim, privater Evidence, exakter Docker-Sequenz und Tests implementieren.
Die Tests müssen jeden Mutationsschritt fake-basiert prüfen und dürfen kein
echtes Dockerobjekt verändern. Unknown-Outcome-Reconciliation und jede
Volumenlöschung bleiben auch dort separate spätere Slices.
