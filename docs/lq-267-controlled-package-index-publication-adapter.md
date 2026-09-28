# LQ-267 — Controlled Package-Index Publication Adapter

## Ergebnis

LQ-267 implementiert einen providerneutral testbaren Package-Index-Inspector
und immutable Creator über einem schmalen injizierten Transport.

Der Slice validiert lokale Providerkonfiguration, kontrolliertes Ziel,
Observation, Create-Acknowledgement und Idempotenzidentität. Er implementiert
noch keinen HTTP-Transport, Worker, Credential-Datei-Leser, CLI oder
Production-Wiring.

## Lokale Providerkonfiguration

`PackageIndexProviderConfiguration` bindet genau:

- einen kanonischen HTTPS-Origin;
- einen kanonischen internen Zielnamen;
- ein kurzlebiges Credential.

Das immutable, geslottete Wertobjekt hält alle drei Werte aus `repr` heraus.

## Kanonischer Origin

Akzeptiert wird ausschließlich ein einzelner kanonischer Origin der Form:

```text
https://host
https://host:port
```

Abgelehnt werden:

- HTTP;
- Userinfo oder Passwort in der URL;
- Pfad oder abschließender Slash;
- Query oder Fragment;
- nicht kanonische Hostschreibweise;
- führende oder folgende Leerzeichen;
- ungültige Ports.

Damit kann ein späterer Transport keinen Callerpfad oder zweiten Origin aus
der Konfiguration ableiten.

## Credential-Grenze

Das Credential muss nicht leer, frei von Steuerzeichen und auf 4096 UTF-8-
Bytes begrenzt sein.

Es wird weder normalisiert noch in Observation, Acknowledgement, Exception
oder `repr` übernommen.

LQ-267 entscheidet noch keine Secret-Datei oder Secret-Manager-Anbindung. Die
Configuration wird ausschließlich durch spätere kontrollierte Composition
erzeugt.

## Providertransport als schmaler Port

`PackageIndexProviderTransport` besitzt genau zwei Methoden:

- `inspect_package` für einen read-only Lookup;
- `create_package` für genau einen immutable Create.

Der Transport erhält die bereits validierte Configuration und den vollständig
kontrollierten `ReleasePublicationTarget`.

Der Create erhält zusätzlich die verifizierten Artefakte und den primitiven
Wert der stabilen Idempotenzidentität.

## Keine freie Netzwerkschnittstelle

Der Transportport akzeptiert keine freie URL, Methode, Headerliste,
Redirectentscheidung oder beliebigen Requestbody.

Konkrete HTTP-Routen, Authentisierungsschemata und Herstellerantworten bleiben
einem späteren Transportadapter vorbehalten.

So kann LQ-267 keine ungesicherte oder erfundene Provider-API normativ machen.

## Kontrollierter Adapter

`PackageIndexReleasePublicationAdapter` implementiert zugleich:

- den bestehenden read-only `ReleasePublicationTargetInspector`;
- den bestehenden Attempt-1-Creator;
- den bestehenden Attempt-2-Creator.

Es gibt keine zusätzliche fachliche Providerentscheidung und keinen neuen
Publication-Zustand.

## Exakte Zielbindung

Vor jedem Transportaufruf verlangt der Adapter:

- Providerart exakt `package-index`;
- Zielname exakt gleich der lokalen Configuration;
- Paketname exakt `liquent`;
- vollständig typisierten `ReleasePublicationTarget`.

Abweichende Providerart, Ziel oder Paket werden vor dem Transport detailfrei
abgelehnt.

Channel- und Revisionsbindung bleiben Aufgabe der bereits vorgelagerten
persistenten Preflight- und Create-Grenzen.

## Read-only Inspection

Ein `None` des Transportports ist die einzige bestätigte Abwesenheit.

Eine sichtbare Antwort muss ein exaktes `PackageIndexArtifactRecord` sein und
bindet:

- kanonische externe Artefaktidentität;
- unveränderliche Providerrevision;
- Paketname und Version;
- Wheel-SHA-256;
- explizite Sichtbarkeit.

Der Adapter überführt diesen Fakt ohne Normalisierung in die bestehende
`ReleasePublicationTargetObservation`.

## Keine implizite Erfolgsprüfung

Der Adapter entscheidet nicht selbst, ob eine Observation bytegleich,
konfliktär oder reconciliation-pflichtig ist.

Diese Klassifikation bleibt den bestehenden LQ-256-, LQ-258- und LQ-263-
Grenzen vorbehalten, die Observation gegen persistent erwartete Hashes und
Zielwerte prüfen.

## Immutable Create

Vor dem Create verlangt der Adapter:

- vollständig typisierte verifizierte Artefakte;
- exakt passende Paketversion von Target und Artefakten;
- stabile Execution-ID oder Attempt-ID als Idempotenzidentität;
- exakt gebundenes Package-Index-Ziel.

Er erzeugt, transformiert oder lädt keine Artefaktbytes nach.

## Idempotenz für beide Attempts

Der Adapter akzeptiert die bestehenden unterschiedlichen Identitätstypen:

- `ReleasePublicationExecutionId` für Attempt 1;
- `ReleasePublicationAttemptId` für Attempt 2.

Dem Transport wird exakt deren unveränderter Stringwert übergeben. Der Adapter
erzeugt keinen Zufallswert, Zeitstempel oder neuen Requestschlüssel.

## Minimale Create-Acknowledgement

Der Transport darf nur ein `PackageIndexCreateRecord` mit nicht leerer
Provider-Request-ID zurückgeben.

Der Adapter überführt diesen Wert in die bestehende repr-freie
`ReleasePublicationCreateAcknowledgement`.

Sie bleibt ausdrücklich kein Receipt. Der persistente Create-Pfad wechselt
auch nach positiver Antwort zu `outcome_unknown`.

## Strikte Transportresultate

Untypisierte Providerantworten, freie Dictionaries, Response-Bodies oder
Strings werden nicht tolerant interpretiert.

Nur `None`, `PackageIndexArtifactRecord` oder `PackageIndexCreateRecord` sind
an der jeweils passenden Grenze zulässig.

Damit gelangen rohe Providerdetails nicht in die Domain.

## Detailfreie technische Nichtverfügbarkeit

`ReleasePublicationProviderUnavailable` vereinheitlicht detailfrei:

- Transport-, Timeout- und Providerfehler;
- ungültige oder untypisierte Transportresultate;
- nicht passende Configuration, Target, Payload oder Idempotenzidentität;
- strukturell nicht sicher abbildbare Werte.

Die Exception enthält ausschließlich den stabilen Fehlercode und weder
Credential-, Origin-, Ziel-, Provider- noch Response-Details.

## Keine automatische Wiederholung

Der Adapter ruft jede Transportmethode höchstens einmal pro Methodenaufruf
auf.

Er implementiert keine Retry-Schleife, kein Fallback und keinen zweiten
Create. Die bestehende Persistenzschicht bewahrt mögliche externe Effekte als
`outcome_unknown`.

## Integration mit dem bestehenden Create-Pfad

Ein Integrationstest komponiert denselben Adapter als Inspector und Creator
mit LQ-255, LQ-256 und LQ-257.

Der Ablauf bestätigt:

- genau einen read-only Transportaufruf;
- genau einen Create-Transportaufruf;
- unveränderte Execution-ID als Idempotenzwert;
- positive Acknowledgement;
- Execution und Attempt anschließend `outcome_unknown`.

Der Adapter kann deshalb keinen Receipt oder Published-Status umgehen.

## Keine Persistenz oder Migration

LQ-267 ergänzt keine Tabelle, Spalte, SQL-Abfrage, Migration oder Seed.

Der einzige Head bleibt `20260819_0024` mit 24 linearen Migrationen.

## Bewusst nicht enthalten

LQ-267 implementiert keine:

- HTTP- oder SDK-Transportklasse;
- konkrete Providerroute oder Hersteller-API;
- Credential-Datei- oder Secret-Manager-Quelle;
- TLS-, Timeout-, Redirect- oder Antwortgrößenpolicy im Netzwerkclient;
- Worker-Composition, CLI oder Service-Unit;
- Runtime-, Compose-, CI-, Git- oder Deploymentverdrahtung;
- Delete-, Yank-, Replace- oder Upsert-Operation.

Es erfolgt kein echter Provider-, Git- oder Deploymentwrite.

## Nachweis

Tests belegen:

- strikte kanonische HTTPS-Origin-Validierung;
- immutable und repr-freie lokale Configuration;
- Credential-Steuerzeichen- und Größenbegrenzung;
- bestätigte Abwesenheit nur über `None`;
- exakte Observation-Abbildung;
- Zielbindung vor jedem Transportzugriff;
- Execution- und Attempt-ID als unveränderte Idempotenzwerte;
- Payload-/Versionsbindung vor Create;
- detailfreie technische Fehler ohne Retry;
- untypisierte Resultate werden nicht interpretiert;
- Integration mit dem persistenten Unknown-Outcome-Pfad.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3255 passed, 534 warnings
```

Der nächste Slice LQ-268 implementiert den begrenzten HTTPS-Transport für die
eingefrorene Package-Index-Schnittstelle. Credential-Source, Worker-CLI und
Production-Wiring bleiben weiterhin getrennt.
