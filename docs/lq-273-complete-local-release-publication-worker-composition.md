# LQ-273 — Complete Local Release Publication Worker Composition

## Ergebnis

LQ-273 implementiert die vollständige lokale Dependency-Composition für genau
einen kontrollierten Offline-Publication-Worker.

Die Composition verbindet die persistente LQ-249- bis LQ-265-Kette, den
LQ-271-Work-Prozessor, die persistenten LQ-272-Ports und die konkrete
LQ-269-Package-Index-Composition.

Der Slice aktiviert keinen CLI-Befehl, Scheduler oder Production-Prozess.

## Composition-Grenze

`compose_release_publication_worker` erhält gemeinsam:

- genau eine Datenbankengine;
- genau eine vollständig konfigurierte Package-Index-Composition;
- genau eine gebundene lokale Artifact-Source;
- stabile Publication-Executor-Identität;
- stabile Promotion-Verifier-Identität;
- kontrollierte Generatoren für Attempt-, Receipt-, Recovery- und
  Reassessment-IDs;
- optional eine gemeinsame Wall-Clock;
- den fest gewählten lokalen `ssh-keygen`-Programmnamen.

Teilkonfiguration oder ein untypisierter sicherheitsrelevanter Wert scheitert
beim Aufbau detailfrei.

## Expliziter Ressourcenbesitz

Mit erfolgreichem oder begonnenem Aufruf überträgt der Caller den Besitz an
Engine und Package-Index-Composition.

`ReleasePublicationWorkerComposition` besitzt anschließend:

- den synchronen Package-Index-HTTP-Client samt Credential;
- die Datenbankengine samt Connection-Pool;
- den fertig komponierten `ProcessReleasePublicationWork`.

Andere Prozesse oder Komponenten dürfen dieselben Ressourcen nicht parallel
als eigene Worker-Abhängigkeit behandeln.

## Aufbau ohne operatives I/O

LQ-273 führt beim Aufbau keinen Datenbank-Lookup, Preflight, Artifact-Read,
Provider-Read oder Provider-Write aus.

Das Credential wurde bereits beim expliziten Aufbau der übergebenen LQ-269-
Composition geladen.

Erst ein späterer Aufruf von `worker.process(request)` beginnt die persistente
Arbeitseinheit.

## Registry-Projektion

Die Composition erzeugt genau eine
`DatabaseCurrentReleaseAuthorityRegistryProjection` für die explizit
übergebene Promotion-Verifier-Identität.

Die Projektion liest bei jeder Integritätsprüfung den aktuellen vollständigen
Registrybestand erneut.

Es gibt keinen eingefrorenen Signer-, Key- oder Policy-Snapshot in der
Composition.

## Artifact-Integrity

Genau ein `DatabaseReleasePublicationArtifactIntegrityCheck` verbindet:

- dieselbe Worker-Engine;
- die kontrolliert gebundene Artifact-Source;
- die aktuelle Registry-Projektion;
- dieselbe explizite Clock;
- das fest gewählte lokale SSH-Verifikationsprogramm.

Attempt 1 und Attempt 2 verwenden dieselbe Integritätsgrenze. Weder Creator
noch Provideradapter laden Artefakte aus freien Pfaden nach.

## Attempt-1-Preflight

Die Composition erzeugt genau einen
`DatabaseReleasePublicationAttemptPreflight`.

Er bindet die explizite Executor-ID, den gemeinsamen Attempt-ID-Generator und
die gemeinsame Clock an dieselbe Engine.

Die Executor-ID ist keine Publisher-Authority. Der Preflight liest alle
aktuellen Authority-Fakten weiterhin aus dem System of Record.

## Gemeinsame Target-Inspection

`DatabaseReleasePublicationTargetInspection` verbindet die gemeinsame
Artifact-Integrity-Grenze mit dem konkreten Package-Index-Adapter.

Der Adapter dient dabei als read-only Inspector für exakt das persistierte
Ziel.

Caller können weder Providerart, Origin, Zielname noch Paketversion in die
Inspection einschleusen.

## Attempt-1-Create

`DatabaseReleasePublicationImmutableCreate` verwendet:

- dieselbe Engine;
- dieselbe Target-Inspection;
- denselben Package-Index-Adapter als immutable Creator.

Write-Start wird damit weiterhin vor exakt einem externen Create persistiert.

Die stabile Execution-ID bleibt die Attempt-1-Idempotenzidentität.

## Gemeinsame Reconciliation

Genau eine
`DatabaseReleasePublicationUnknownOutcomeReconciliation` verwendet dieselbe
Engine und denselben Package-Index-Adapter als read-only Inspector.

Receipt- und Recovery-Finalizer teilen dieses Reconciliation-Objekt.

Der LQ-272-Current-Outcome-Finalizer stellt dennoch sicher, dass pro neuem
Abschluss nur genau ein read-only Provideraufruf ausgeführt wird.

## Receipt- und Recovery-Abschluss

Die Composition erzeugt genau einen Receipt-Finalizer und genau einen Recovery-
Finalizer.

Beide verwenden:

- dieselbe Engine;
- dieselbe Reconciliation;
- die kontrolliert injizierten ID-Generatoren;
- dieselbe Clock.

Published, Absence und Conflict bleiben disjunkte atomare Commitpfade.

## Attempt 2

`DatabaseReleasePublicationRetryAttemptPreflight` verwendet dieselbe Engine,
Artifact-Integrity, Providerinspection, Clock und denselben Attempt-ID-
Generator wie der erste Pfad.

`DatabaseReleasePublicationRetryImmutableCreate` verwendet dieselbe Engine,
Integrity und denselben Package-Index-Adapter.

Die persistente Recovery-Bindung entscheidet allein, ob Attempt 2 vorbereitet
werden darf.

Der Adapter erhält für Attempt 2 unverändert die stabile Attempt-ID als
Idempotenzidentität.

## Work-State und Prozessor

`DatabaseReleasePublicationWorkStateLookup` und
`DatabaseReleasePublicationCurrentOutcomeFinalizer` werden in denselben
`ProcessReleasePublicationWork` injiziert.

Der resultierende Worker besitzt damit genau eine vollständige Route für:

- initiale Arbeit;
- vorbereiteten und unbekannten Attempt 1;
- bestätigte Attempt-1-Abwesenheit;
- vorbereiteten und unbekannten Attempt 2;
- terminale Wiederholung.

Es gibt keine zweite Composition oder alternative Zustandsauflösung.

## Genau ein Providerkontext

Inspection, Attempt-1-Create, Reconciliation, Attempt-2-Preflight und Attempt-
2-Create verwenden exakt dasselbe `PackageIndexReleasePublicationAdapter`-
Objekt.

Read und Write können deshalb nicht unbemerkt unterschiedliche Origins,
Credentials oder Zielnamen verwenden.

Die lokale Konfiguration bleibt für die gesamte kurzlebige Worker-Laufzeit
unverändert.

## Clock- und Generatorgrenzen

Die gemeinsame Clock wird beim Aufbau nicht gelesen.

Sie wird erst von den bestehenden persistenten Adaptern bei tatsächlich
wirksamen Entscheidungen verwendet.

Generatoren werden ebenfalls nicht beim Aufbau aufgerufen. Neutrale oder
exakte Retry-Pfade erzeugen keine ungenutzten neuen IDs.

Attempt 1 und Attempt 2 teilen absichtlich denselben kontrollierten Attempt-ID-
Generator, behalten aber ihre persistent getrennten IDs.

## Context Manager und Close

Die Composition ist ein Context Manager und besitzt einen idempotenten
`close`-Pfad.

Close versucht immer:

1. den Package-Index-Client und sein Credential zu schließen;
2. anschließend die Datenbankengine zu disposen.

Ein Fehler im ersten Schritt verhindert den zweiten Schritt nicht.

Close-Fehler werden als detailfreie
`ReleasePublicationWorkerCompositionUnavailable` gemeldet.

## Partieller Aufbau

Scheitert der Aufbau nach Übernahme der Ressourcen, werden Provider-Composition
und Engine bestmöglich geschlossen.

Der ursprüngliche interne Fehler wird nicht mit Provider-, Credential-, Pfad-
oder Datenbankdetails weitergegeben.

Es entsteht kein teilweise nutzbarer Worker und kein Fallback auf eine
unvollständige Abhängigkeitsgruppe.

## End-to-End-Nachweis

Der integrierte Test komponiert die vollständige Kette mit:

- echter migrierter lokaler Datenbank;
- echtem gebundenem Release-Bundle, Signatur und Promotion-Evidence;
- echter Registry-Projektion und detached-signature-Verifikation;
- echtem Package-Index-HTTPS-Transport über `MockTransport`;
- owner-only Credential-Datei.

Der beobachtete Providerpfad ist exakt:

```text
GET absent -> PUT create-only -> GET exact visible
```

Danach ist genau ein Receipt atomar persistiert und die Execution terminal
`published`.

Der Client wird beim Verlassen des Context Managers geschlossen.

## Fehlerpfad-Nachweis

Ein simulierter Providerfehler bleibt innerhalb der bestehenden detailfreien
Work-Grenze.

Auch wenn `worker.process` fehlschlägt, schließt der Context Manager den
Providerclient und disposed die Engine.

Es wird kein zweiter Create durch Close oder Fehlerbehandlung ausgelöst.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht mit 3330 Tests und
581 Warnungen ohne übersprungene PostgreSQL-Pfade.

## Keine betriebliche Aktivierung

LQ-273 ergänzt keine:

- CLI-Argumente, Requestdatei, Standardausgabe oder Exitcodes;
- Datenbank-URL-, Credential- oder ID-Datei-Auflösung;
- UUID-/ID-Generatorimplementierung;
- Scheduler-, Queue-, Daemon- oder Service-Unit-Konfiguration;
- HTTP-, OIDC-, Browser-Session- oder Research-Verdrahtung;
- Tabelle, SQL, Schema, Migration oder Seed;
- echten Provider-, Git- oder Deploymentwrite.

Der Migration-Head bleibt `20260819_0024` mit 24 Migrationen.

## Nächster Slice

LQ-274 entscheidet den owner-only Offline-Worker-Operatorvertrag für Request-,
Engine-, Artifact-, Credential- und ID-Quellen sowie detailfreie Ausgabe und
Exitcodes, bevor eine CLI aktiviert wird.
