# LQ-345 — Owner-controlled Runtime Cleanup Continuation

## Ergebnis

LQ-345 installiert `liquent-disposable-postgres-cleanup-continue` für die
streng begrenzte Fortsetzung eines LQ-339-Teilcleanup.

Der Operator führt nur das vom autorisierten `resume_from` verbleibende
Restbudget aus. Das Datenvolume bleibt erhalten.

## Geschlossene Autorisierung

Die owner-only Continuation-Datei bindet Continuation-,
Cleanup-Reconciliation- und Cleanup-ID, Run, Phase, Source, Image, Compose,
Reconciliationkette, alle Evidence- und Autorisierungshashes sowie den
SHA-256 der vollständigen LQ-341-Autorisierung.

Operation ist exakt `continue_disposable_postgres_runtime_cleanup`, Scope
exakt `runtime_only` und `resume_from` einer von `container_stopped`,
`container_removed` oder `application_network_removed`.

Executor und Autorisierer sind getrennt; das UTC-Fenster ist höchstens eine
Stunde. Unbekannte Felder oder Abweichungen bleiben unavailable.

## Historische Bindung und frische Beobachtung

Cleanup- und LQ-341-Autorisierung werden nur historisch validiert. Die neue
Continuation-Autorisierung muss aktuell sein.

Der ursprüngliche LQ-339-Cleanup-Claim wird vollständig gegen dieselbe
kanonische Ressourcen-, Identitäts- und Hashbindung geprüft.

Ohne vorhandene Continuation-Evidence führt der Operator LQ-341 unmittelbar
neu aus. Nur ein Ausgang exakt gleich `resume_from` erreicht den
Continuation-Claim.

Jeder andere lesbare Ausgang ergibt `rejected` ohne Claim oder Dockerwirkung.

## Evidence-first Continuation-Claim

Claim- und Evidencename werden aus dem vollständigen SHA-256 der
Cleanup-Continuation-ID abgeleitet.

Der Claim bindet Autorisierung, `resume_from`, exakte Ressourcen,
verbleibende Schritte, getrennte Identitäten und UTC-Startzeit.

Er wird owner-only exklusiv geschrieben und samt Evidenceverzeichnis vor dem
ersten Remove synchronisiert.

Ein vorhandener Claim stoppt vor Inspector und Docker. Er wird weder
überschrieben noch aufgrund von Alter entfernt.

Der ursprüngliche Cleanup-Claim bleibt jederzeit bestehen.

## Minimale Restbudgets

Bei `container_stopped` entfernt der Operator genau:

- den bereits gestoppten Container;
- Application-Netz;
- Data-Netz.

Bei `container_removed` werden nur beide Netze entfernt.

Bei `application_network_removed` wird nur das Data-Netz entfernt.

Es gibt keinen Stop-, Kill-, Start-, Force- oder bereits abgeschlossenen
Remove-Aufruf.

Nach jedem einzelnen Remove bestätigt eine exakte Namensliste Abwesenheit.
Erst danach darf der nächste Schritt beginnen.

## Erhaltenes Volume

Nach dem letzten Network-Remove inspiziert der Operator ausschließlich das
exakte PostgreSQL-Datenvolume.

Name und Projektbindung müssen unverändert dem ursprünglichen Run
entsprechen. Fehlendes, fremdes oder technisch unklares Volume ist
unavailable.

Der Operator entfernt, öffnet, mountet, liest oder verändert das Volume nie.

## Unknown Outcome

Ab dem ersten Remove beendet jede technische Mehrdeutigkeit den Ablauf
sofort.

Continuation- und ursprünglicher Cleanup-Claim bleiben offen. Es gibt keinen
Retry, Ersatzbefehl, Folgeschritt oder heuristische Erfolgsableitung.

Ein Wiederholungsaufruf stoppt wegen des offenen Continuation-Claims vor
Inspector und Docker.

## Getrennte Continuation-Evidence

Nach bestätigter Runtimeentfernung und Volume-Erhalt schreibt der Operator
atomar private owner-only Evidence.

Sie bindet alle IDs und Hashes, `resume_from`, exaktes Restbudget,
Ressourcen, Identitäten, UTC-Start und Abschluss sowie Ausgang
`runtime_removed_pending_finalization`.

Die Datei wird exklusiv temporär angelegt, synchronisiert, atomar final
verlinkt und vollständig zurückgelesen.

Erst danach wird ausschließlich der exakte Continuation-Claim freigegeben.
Der ursprüngliche Cleanup-Claim bleibt für LQ-343 offen.

Ein exakter Evidence-Retry führt weder Inspector noch Docker aus und löst nur
eine gegebenenfalls verbliebene Continuation-Claimfreigabe.

## Verbotene Wege

Compose-Down, Stop, Start, Kill, Force, Disconnect, `--volumes`, Prune,
Wildcard-, Prefix-, Label- oder Projektgruppencleanup sind unerreichbar.

Der Operator schreibt keine LQ-339- oder Finalization-Evidence, gibt den
Cleanup-Claim nicht frei und führt kein SQL aus.

## Neutrale Ausgabe

Die CLI liefert ausschließlich Operation
`disposable_postgres_runtime_cleanup_continuation`, Schema-Version und:

- `runtime_removed_pending_finalization`;
- `rejected`;
- technisch unavailable ohne stdout oder stderr.

Private IDs, Hashes, Ressourcen, Pfade, Zeiten und Identitäten werden nicht
ausgegeben.

## Tests

Fake-basierte Tests prüfen die drei unterschiedlichen Restbudgets und das
vollständige Fehlen bereits abgeschlossener oder verbotener Befehle.

Weitere Tests prüfen Zustandsmismatch vor Claim, offenen Doppelclaim nach
unbekanntem Remove, blockierten Blind-Retry, Evidence-Retry ohne Inspector und
die detailfreie CLI.

Kein Test verändert echte Dockerressourcen.

## Bundle und Nichtziele

Entry Point und Operatormodul erhöhen die Gates auf 38 Entry Points und 42
Operatormodule. Migrationen bleiben 27 mit Head `20260819_0027`.

LQ-345 implementiert keine Reconciliation offener Continuation-Claims, keine
automatische LQ-343-Finalisierung und keine Volume-Löschung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Domainmodell-,
Compose- oder Production-Wiring-Änderung.

## Nächster Slice

LQ-346 sollte den strikt read-only Reconciliationvertrag für offene
Continuation-Claims definieren.

Er muss den neuen Präfixzustand ohne Claim-, Evidence- oder Ressourcemutation
klassifizieren; das Datenvolume bleibt ausgeschlossen.
