# LQ-253 — Persistent Release Publication Execution Foundation

## Ergebnis

LQ-253 implementiert die leere persistente Foundation für den in LQ-252
entschiedenen Publication-Executor.

Der Slice ergänzt stabile Executor-, Execution- und Attempt-Identitäten sowie
historienerhaltende Strukturen für Attempts, Unknown Outcomes,
Receipt-Reconciliation und Reassessment-Zuordnung.

Er führt keinen Providerzugriff und keinen Upload aus.

## Stabile Identitäten

Drei neue repr-freie, immutable und geslottete Typen unterscheiden:

- `ReleasePublicationExecutorId`;
- `ReleasePublicationExecutionId`;
- `ReleasePublicationAttemptId`.

Sie sind nicht untereinander oder mit Handoff-, Decision-, Receipt- und
Publisher-IDs austauschbar.

Alle akzeptieren ausschließlich nicht leere Strings.

## Sichere Materialerzeugung

`SecureIdentityAuthorityMaterialGenerator` erzeugt jede neue ID über einen
eigenen unabhängigen Zug aus mindestens 32 Byte Betriebssystementropie.

Keine ID wird aus Handoff, Channel, Paketversion, Providerantwort, Hash, Zeit
oder Environment abgeleitet. ID-Erzeugung gewährt keine Authority.

## Additive Migration

Migration `20260817_0022` baut linear auf `20260817_0021` auf und ist der
einzige neue Head.

Sie erzeugt fünf leere Tabellen:

- `release_publication_executors`;
- `release_publication_executions`;
- `release_publication_execution_attempts`;
- `release_publication_receipt_reconciliations`;
- `release_publication_execution_reassessments`.

Es gibt keinen Executor-, Attempt-, Receipt- oder Provider-Seed.

## Executor-Fakten

`release_publication_executors` hält ausschließlich stabile interne
Executor-Identitäten.

Die Tabelle bindet noch keine Publisher-Authority und erzeugt keine
Capability. Ein späterer Adapter muss aktuelle Authority für jeden Attempt
separat aus dem Publication-System of Record auflösen.

Signing- und Promotion-Identitäten werden nicht als Executor übernommen.

## Execution-Inventar

Eine Execution bindet:

- stabile Execution-ID;
- genau einen bekannten Handoff;
- bekannten Executor;
- identifizierten Publisher;
- Channel und exakte Channel-Revision;
- Bundle- und Signaturhash;
- Startzeit;
- geschlossenen Execution-Status.

Pro Handoff ist höchstens eine normative Execution vorgesehen. Retry und
weitere Providerkontakte werden als Attempts derselben Execution modelliert.

## Geschlossene Execution-Status

Zulässig sind ausschließlich:

- `prepared`;
- `outcome_unknown`;
- `published`;
- `published_reassessment_required`.

Die Foundation implementiert noch keine Transition. Direkte Statusänderungen
sind kein unterstützter Operatorweg.

## Attempt-Inventar

Jeder Attempt besitzt eine stabile ID, gehört zu genau einer bekannten
Execution und trägt eine positive fortlaufende Attempt-Nummer.

Das Paar aus Execution und Attempt-Nummer ist eindeutig. Zwei Prozesse können
dadurch nicht denselben ordinalen Versuch unter verschiedenen IDs verbuchen.

Zulässige Attempt-Status sind:

- `prepared`;
- `write_started`;
- `outcome_unknown`;
- `reconciled`.

## Zeit- und Finish-Invariante

Jeder Attempt besitzt eine Startzeit.

`prepared`, `write_started` und `outcome_unknown` dürfen noch keine
Finish-Zeit tragen. `reconciled` verlangt eine Finish-Zeit.

Damit kann ein unklarer möglicher Providereffekt nicht als normal
abgeschlossener Versuch dargestellt werden.

## Receipt-Reconciliation

Die bestehende LQ-249-Receipt-Tabelle bleibt der öffentliche persistente
Publication-Fakt.

`release_publication_receipt_reconciliations` bindet jedes Receipt zusätzlich
eindeutig an:

- genau eine Execution;
- genau einen Attempt;
- externe kanonische Artefaktidentität;
- unveränderliche Providerrevision;
- Bestätigungszeit;
- Reconciliation-Status.

Execution und Attempt können jeweils höchstens ein Receipt abschließen.

## Reconciliation-Status

Zulässig sind ausschließlich:

- `published`;
- `published_reassessment_required`.

Der zweite Status bewahrt die externe Realität eines erfolgreichen Writes,
wenn aktuelle Revocation oder Channel-/Publisher-Änderung zugleich eine neue
Securityprüfung verlangt.

Er löscht oder relativiert das Receipt nicht.

## Reassessment-Verknüpfung

`release_publication_execution_reassessments` verbindet eine bekannte
Execution mit einer bekannten historischen LQ-249-Reassessment-Entscheidung.

Die Zuordnung ist zusammengesetzt eindeutig und überschreibt weder Execution,
Attempt, Handoff noch Receipt.

LQ-253 erzeugt kein Reassessment und führt kein Withdrawal aus.

## Referenzielle Grenzen

Foreign Keys verlangen:

- bekannten Handoff für jede Execution;
- bekannten Executor und Publisher;
- passende Channel-/Revision-Kombination;
- bekannte Execution für jeden Attempt;
- bekanntes Receipt, Execution und Attempt für jede Reconciliation;
- bekannte Execution und Reassessment für jede Verknüpfung.

Unbekannte oder frei erfundene Providerfakten können nicht isoliert in die
Foundation geschrieben werden.

## Konkurrenzvorbereitung

Die eindeutige Handoff-Bindung verhindert mehrere normative Executions für
denselben Handoff.

Die eindeutige Attempt-Nummer ermöglicht später atomare Serialisierung von
Retry und Unknown-Outcome-Reconciliation.

LQ-253 implementiert noch keine Locks, Leases, Timeouts oder
Execution-Adapter.

## Retention und Nichtwiederverwendung

Executor-, Execution- und Attempt-IDs, Statushistorie, Reconciliations und
Reassessment-Zuordnungen werden mindestens so lange erhalten, wie Release,
Deployment, Rollback, Incident oder Audit darauf verweist.

IDs und externe Artefakt-/Providerrevisionen werden nie gelöscht und unter
neuer Bedeutung wiederverwendet.

## Bundle-Gate

Das LQ-236-Wheelgate erwartet nun 22 lineare Migrationen bis Head
`20260817_0022`.

Bundle-Formatversion, vierzehn Console Entry Points und zwölf Operatormodule
bleiben unverändert.

## Nachweis

Tests belegen:

- alle drei stabilen repr-freien ID-Typen;
- unabhängige sichere Materialerzeugung;
- vollständig leere Execution-Inventare;
- Pflichtbindung an bekannte Handoffs, Executor und Channels;
- Pflichtbindung von Attempts an bekannte Executions;
- Pflichtbindung von Reconciliation an Receipt, Execution und Attempt;
- denselben leeren Foundation-Stand auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite besteht:

```text
3130 passed, 62 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-253 implementiert keine Ports, Exceptions, Execution- oder Attempt-
Adapter, Artifact Source, Provider, Reconciliation, Receipt-Mutation,
Reassessment, CLI, Credentials, Netzwerk-, Upload-, Git- oder
Deploymentaktion.

## Nächster Slice

LQ-254 sollte den kontrollierten persistenten Publication-Attempt-Preflight
implementieren. Er muss Handoff, Artefakthashes, aktuelle Release-Revocation,
Publisher und Channel prüfen und idempotent genau einen `prepared` Attempt
erzeugen, ohne Artifact-Provider oder Netzwerk aufzurufen.
