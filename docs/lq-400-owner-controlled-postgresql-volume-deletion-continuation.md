# LQ-400 — Owner-controlled PostgreSQL Volume Deletion Continuation

## Ergebnis

LQ-400 installiert `liquent-disposable-postgres-volume-delete-continue` für
die streng begrenzte Fortsetzung eines offenen LQ-394-Volume-Deletion-Claims.

Der Operator kann nach frischem `continuation_required` genau einen weiteren
Remove des exakten PostgreSQL-Datenvolumes ausführen.

## Geschlossene Continuation-Authority

Die neue owner-only Autorisierung bindet stabile Continuation- und
Continuation-Claim-IDs an Finalization, Reconciliation, Löschung,
Disposition, Retention, Hold, Recovery, Run und das exakte Volume.

Operation ist exakt `continue_disposable_postgres_volume_deletion`, Scope
exakt `data_volume_only` und das aktuelle UTC-Fenster höchstens eine Stunde.

Executor, Authorizer und Reviewer sind getrennt. Historische Autorisierungen,
Hashbeziehungen, Identitäten und Ressourcenbindungen werden geschlossen
validiert; caller-gelieferte Zustände oder Volumenamen existieren nicht.

## Frische Finalisierung

Ohne vorhandene Continuation-Evidence führt der Operator LQ-398 mit denselben
autoritativen Dateien unmittelbar erneut aus.

Nur `continuation_required` erreicht die neue Claimanlage.

Die terminalen LQ-398-Ausgänge werden write-frei als `already_finalized`
abgebildet. `not_found` und `investigation_required` bleiben geschlossen und
erzeugen weder Continuation-Claim noch Ressourceneffekt.

## Zwei getrennte Claims

Der ursprüngliche LQ-394-Claim muss vor der Fortsetzung vollständig und exakt
gebunden offen sein.

Der neue untergeordnete Claim wird aus dem vollständigen SHA-256 seiner
vorab autorisierten ID abgeleitet, owner-only exklusiv geschrieben und vor
Docker durable synchronisiert.

Ein vorhandener oder fremder Continuation-Claim stoppt ohne Übernahme oder
Ersetzung. Der ursprüngliche Claim wird von LQ-400 niemals freigegeben.

## Letzte Prüfung und Einzelmutation

Nach Claimanlage inspiziert der Operator das intern abgeleitete Volume ein
letztes Mal read-only und verlangt die exakte rungebundene Compose-Zuordnung.

Danach ist genau ein `docker volume rm` für dieses Volume erreichbar.

Eine exakte gefilterte Namensliste muss anschließend Abwesenheit bestätigen.
Force, Prune, Compose-Down, Mount, SQL, Wildcards sowie Container- und
Networkmutation bleiben ausgeschlossen.

## Unknown Outcome

Nonzero, stderr, Timeout, Truncation, verlorene Antwort, fremde letzte Bindung
oder nicht bestätigte Abwesenheit endet technisch detailfrei.

Nach möglichem Effekt bleiben ursprünglicher und untergeordneter Claim offen.
Es gibt keinen zweiten Remove und keinen Blind-Retry.

## Separate Continuation-Evidence

Nach bestätigter Abwesenheit schreibt der Operator private owner-only
Continuation-Evidence atomar und liest sie vollständig zurück.

Sie bindet sämtliche Autorisierungs- und Fach-IDs, Hashes, das exakte Volume,
den einzelnen Schritt, bestätigte Abwesenheit, Identitäten und UTC-Zeiten.

Der Ausgang lautet `volume_removal_pending_finalization`. Die Evidence ist
weder originale LQ-394-Löschevidence noch LQ-398-Finalization-Evidence.

Erst danach wird ausschließlich der Continuation-Claim freigegeben. Der
ursprüngliche LQ-394-Claim bleibt für eine spätere frische Finalisierung offen.

## Evidence-Retry

Vorhandene exakt gebundene Continuation-Evidence wird vor LQ-398 und Docker
erkannt.

Der Retry gibt nur einen gegebenenfalls verbliebenen exakten
Continuation-Claim frei und liefert denselben Erfolg erneut.

Malformed oder fremde Evidence wird nicht überschrieben. Der Retry führt
weder Inspector, Finalizer noch Docker aus.

## Neutrale Ausgabe

Die CLI liefert ausschließlich Schema-Version, Operation
`disposable_postgres_volume_deletion_continuation` und einen der Ausgänge:

- `volume_removal_pending_finalization`;
- `already_finalized`;
- `not_found`;
- `investigation_required`;
- technisch unavailable ohne stdout oder stderr.

Private IDs, Hashes, Pfade, Ressourcen, Identitäten und Zeiten bleiben
verborgen.

## Tests

Fünfzehn Testfälle belegen frische LQ-398-Auswertung, den exklusiven
Continuation-Claim, letzte Volumebindung, genau einen Remove und die
Abwesenheitsbestätigung.

Weitere Fälle prüfen Unknown Outcome, offenen Doppelclaim, Hashabweichung,
geschlossene Finalizerausgänge, Evidence-Retry ohne Docker sowie die
detailfreie CLI.

Kein Test verändert reale Dockerressourcen.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 55 Entry Points und 59
Operatormodule. Migrationen bleiben bei 27 mit Head `20260819_0027`.

LQ-400 implementiert keine Reconciliation offener Continuation-Claims und
keine automatische abschließende LQ-398-Ausführung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-401 sollte den strikt read-only Reconciliationvertrag für offene
Volume-Deletion-Continuation-Claims definieren.

Er muss Evidencepriorität, Claimbindung und exakte Volumeanwesenheit ohne
Claim-, Evidence- oder Ressourcemutation klassifizieren.
