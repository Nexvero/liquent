# LQ-339 — Owner-controlled Runtime-only PostgreSQL Cleanup

## Ergebnis

LQ-339 installiert `liquent-disposable-postgres-runtime-cleanup` als
owner-kontrollierten Operator für den Scope exakt `runtime_only`.

Er entfernt ausschließlich den gebundenen disposable PostgreSQL-Container und
seine zwei exklusiven internen Runnetze. Das Datenvolume bleibt bestehen.

## Vollständige Neuprüfung

Der Operator lädt die ursprüngliche Runautorisierung und die aktuelle
Cleanup-Autorisierung erneut aus privaten owner-only Dateien.

Run, Phase, Source, Image, Compose, Reconciliationkette, Disposition,
Evidencehashes, getrennte Identitäten und aktuelles UTC-Fenster werden über
den bestehenden LQ-337-Preflight vollständig neu geprüft.

Ein caller-geliefertes `ready`, Allow-Boolean, Ressourcenname oder
Dockerargument wird nicht akzeptiert.

Nur ein frisch abgeleitetes `ready` erreicht weitere Ressourcenbeobachtung.
`already_absent` und `rejected` bleiben neutrale Ausgänge ohne Claim oder
Mutation.

Scope `runtime_and_data_volume` endet vor Preflight und Docker technisch
unavailable.

## Letzte Endpoint-Isolation

Nach dem Preflight rendert der Operator das SHA-gebundene Composemodell erneut
und leitet Container, Application-Netz, Data-Netz und Volume daraus ab.

Er inspiziert alle vier Ressourcen erneut read-only. Zusätzlich zu den
LQ-337-Invarianten muss jedes Netz exakt einen Endpoint enthalten, dessen Name
dem gebundenen PostgreSQL-Container entspricht.

Ein zusätzlicher Endpoint, fremde Zuordnung oder vollständig lesbare
Abweichung ergibt `rejected`, bevor ein Claim entsteht.

Malformed Output, Nonzero, stderr, Timeout, Truncation oder Hard Kill bleibt
detailfrei unavailable.

## Evidence-first Claim

Der Claimname wird ausschließlich aus dem vollständigen SHA-256 der stabilen
Cleanup-ID abgeleitet.

Der Operator prüft finale Evidence vor jedem Dockerzugriff. Exakt gebundene
finale Evidence liefert idempotent erneut `removed_runtime`.

Ohne finale Evidence muss der Claim fehlen. Er wird owner-only mit `O_EXCL`
angelegt und bindet Run, Scope, Autorisierungs- und Evidencehashes,
Identitäten, Ressourcennamen sowie Startzeit.

Datei und Evidenceverzeichnis werden vor dem ersten Effekt synchronisiert.
Ein vorhandener, kollidierender oder technisch unklarer Claim wird weder
überschrieben noch entfernt.

## Exakte Mutation

Nach erfolgreichem Claim führt der Operator ausschließlich diese feste Folge
aus:

1. exakten Container einmal mit 30 Sekunden Grace stoppen;
2. gestoppten oder beendeten Zustand read-only bestätigen;
3. exakten Container einmal ohne Force und ohne Volumeoption entfernen;
4. Containerabwesenheit per exakter Namensliste bestätigen;
5. Application-Netz einmal entfernen und Abwesenheit bestätigen;
6. Data-Netz einmal entfernen und Abwesenheit bestätigen;
7. das exakte Volume inspizieren und unveränderte Runzuordnung bestätigen.

Alle Aufrufe verwenden absoluten Dockerpfad, temporäres leeres CWD,
`LANG=C`, `LC_ALL=C`, keine Shell und feste Zeit- und Outputgrenzen.

Die Netzreihenfolge stammt aus dem geschlossenen Composemodell und ist
deterministisch Application vor Data.

## Harte Verbote

Der Operator verwendet kein Compose-Down, Kill, Force, Disconnect,
`--volumes`, Prune, Wildcard-, Prefix-, Label- oder Projektgruppencleanup.

Er entfernt kein Image, Volume oder anderes Objekt, führt kein SQL aus und
öffnet weder Host- noch Volumedateisystem.

Es gibt keinen Ersatzcontainer, neuen Run, Retry oder alternativen
Fallbackbefehl.

## Unknown Outcome

Ab dem ersten Stopaufruf führt jede technische Mehrdeutigkeit zum sofortigen
Abbruch.

Der Claim bleibt bestehen, finale Evidence fehlt und kein späterer
Mutationsschritt wird ausgeführt.

Auch ein unerwarteter gestoppter Zustand, nicht bestätigte Abwesenheit oder
nicht bestätigtes erhaltenes Volume ist unavailable und niemals Erfolg.

Ein Wiederholungsaufruf stoppt wegen des offenen Claims vor Preflight und
Docker. LQ-339 versucht keine Zustandsableitung und keine Claimheilung.

## Finale private Evidence

Nach bestätigtem Volume-Erhalt schreibt der Operator atomar owner-only
Cleanup-Evidence.

Sie bindet Cleanup-, Run-, Reconciliation-, Claim-Reconciliation- und
Disposition-ID, alle maßgeblichen Hashes, Scope, Identitäten, exakte
Ressourcen, bestätigte Schritte sowie UTC-Start und Abschluss.

Temporärdatei, finale Hardlinkanlage und Evidenceverzeichnis werden
synchronisiert. Die Evidence wird vollständig zurückgelesen, bevor der Claim
entfernt werden darf.

Erst nach erfolgreicher Claimfreigabe lautet der Ausgang `removed_runtime`.
Ein unbekannter Claimfreigabeausgang bleibt ein späterer Reconciliationfall.

## Neutrale Ausgabe

Der Command gibt ausschließlich Schema-Version, Operation
`disposable_postgres_runtime_cleanup` und einen Ausgang aus:

- `removed_runtime`;
- `already_absent`;
- `rejected`;
- technisch unavailable ohne stdout oder stderr.

IDs, Hashes, Ressourcennamen, Pfade, Zeitwerte, Identitäten und Fehlerdetails
bleiben privat.

## Tests

Fake-basierte Tests prüfen die vollständige feste Dockerreihenfolge und dass
kein Force-, Volume- oder Sammelcleanupargument erreichbar ist.

Sie prüfen Endpointkonflikt vor Claim, Volume-Scope vor Preflight, neutralen
Abwesenheits-Handoff, offenen Claim nach unbekanntem ersten Effekt,
idempotenten Evidence-Retry und die detailfreie CLI-Grenze.

Kein Test startet, stoppt oder entfernt echte Dockerressourcen.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 35 Entry Points und 39
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-339 implementiert keine Unknown-Outcome-Reconciliation und keine
Fortsetzung eines Teilcleanup.

Es gibt keine Volume-Löschung, Schema-, Tabellen-, SQL-, Migration-, Port-,
Domainmodell-, Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-340 sollte den strikt read-only Reconciliationvertrag für offene
LQ-339-Cleanup-Claims definieren.

Er muss die möglichen Teilzustände von Container und Netzen gegen private
Claim- und Evidencebindung klassifizieren, ohne Claim oder Ressource zu
verändern. Volumenlöschung bleibt weiterhin ausgeschlossen.
