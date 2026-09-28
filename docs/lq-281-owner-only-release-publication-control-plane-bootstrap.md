# LQ-281 — Owner-only Release Publication Control-Plane Bootstrap

## Ergebnis

LQ-281 implementiert den owner-only Offline-Prozess für den einmaligen
LQ-250-Publication-Control-Plane-Bootstrap.

Der neue Entry Point lautet:

```text
liquent-release-publication-bootstrap
```

Er erzeugt Channel, Publisher-Authority und erste Current-Revision, aber keinen
Handoff, Executor, Attempt, Providerzugriff oder Upload.

## Private Prozessgrenze

Der Command akzeptiert ausschließlich zwei absolute private Dateipfade:

- Datenbank-URL-Datei;
- Bootstrap-Requestdatei.

Beide Quellen verwenden die bestehende owner-only descriptor-basierte Grenze
mit `O_NOFOLLOW`, `O_CLOEXEC`, `fstat`, Eigentümer-, Link-, Modus- und
Größenprüfung.

Es gibt keinen Environment-, SQLite-, In-Memory- oder Default-DSN-Fallback.

## Geschlossener Request

Der Request ist kanonisches kompaktes JSON mit sortierten Schlüsseln, finalem
LF und exakt:

```json
{"bootstrap_id":"STABLE_BOOTSTRAP_ID","package_name":"liquent","provider_kind":"package-index","target_name":"stable"}
```

Zusätzliche Publisher-, Channel-, Revision-, Executor-, Allow-, Credential-
oder Statusfelder werden vollständig abgelehnt.

## Feste Produkt- und Providergrenze

Der Operator akzeptiert ausschließlich Paketname `liquent` und Providerkind
`package-index`.

Der Zielname ist ein begrenzter kanonischer interner Name aus Buchstaben,
Ziffern, Punkt, Unterstrich und Bindestrich. Pfade, URLs und Traversalwerte
sind nicht zulässig.

Origin und Credential gehören weiterhin erst zur lokalen Worker-Composition.

## Interne Identitäten

Publisher-Authority-ID, Channel-ID und Channel-Policy-Revision-ID werden
ausschließlich intern über den kryptografisch sicheren Materialgenerator
erzeugt.

Sie werden erst gezogen, nachdem der persistente LQ-250-Adapter vollständige
Leere bestätigt hat.

Keine ID wird aus Bootstrap-ID, Zielname, Paket, Provider oder Zeit abgeleitet.

## Atomarer Bootstrap

Nach exakter Migration-Readiness ruft der Operator den bestehenden
`DatabaseInitialReleasePublicationControlPlaneBootstrap` genau einmal auf.

Ein erfolgreicher Commit erzeugt atomar:

- aktive Publisher-Authority;
- Publication-Channel;
- aktive vollständige Channel-Revision;
- aktiven Publisher-Member;
- Current-Pointer;
- unveränderliche Bootstrap-Entscheidung.

Handoff-, Receipt- und Reassessment-Inventare bleiben leer.

## Geschützte Ausgabe

Ein neuer oder exakt rekonstruierter Bootstrap liefert kanonisches JSON mit:

- `outcome` gleich `bootstrapped`;
- Bootstrap-ID;
- Publisher-Authority-ID;
- Channel-ID;
- Channel-Revision-ID.

Diese vier IDs sind der kontrollierte Übergabefakt für den späteren Handoff-
Prozess. Die Ausgabe enthält keine DSN, Pfade, Providerorigin oder Credentials.

## Exakter Retry

Nach verlorenem oder unklarem Ergebnis wird dieselbe private Requestdatei
unverändert wiederverwendet.

Bei identischer Bootstrap-ID und Channeldefinition liefert der Adapter dieselben
vier IDs ohne neue Generatorzüge oder Mutation.

Eine neue Bootstrap-ID ist kein Retry.

## Neutrale Schließung und Konflikt

Eine andere Bootstrap-ID nach irgendeiner Publication-Historie endet neutral
`not_bootstrapped` mit Exit `5`.

Dieselbe Bootstrap-ID mit anderer Paket-, Provider- oder Zieldefinition endet
detailfrei Konflikt mit Exit `3`.

Inputablehnung verwendet Exit `2`, technische Nichtverfügbarkeit Exit `4`.
Erfolg verwendet Exit `0`.

## Readiness und Ressourcen

Der Operator baut genau eine Engine und bestätigt den exakten Migration-Head,
bevor der Bootstrapadapter ausgeführt wird.

Er migriert, adoptiert und repariert keinen Bestand. Die Engine wird in allen
normalen, neutralen, Konflikt- und Fehlerpfaden geschlossen.

Technische Fehler reflektieren keine SQL-, Tabellen-, DSN- oder ursprünglichen
Exceptiondetails.

## Bundle-Inventar

`liquent-release-publication-bootstrap` ist additiv als Console Entry Point
registriert.

Das operative Bundle erwartet nun 18 Entry Points und 17 Operatormodule
einschließlich Package-Initialisierung und Worker-Composition.

Der Migration-Head bleibt `20260819_0024` mit 24 linearen Migrationen.

## Nachweis

Tests führen den echten Operator gegen einen leeren migrierten Store aus und
bestätigen:

- exakten stabilen Retry;
- geschützten Fünf-Felder-Output einschließlich Outcome;
- aktiven kanonischen Channel und Publisher;
- leere Handoff-, Executor- und Execution-Inventare;
- Ablehnung offener Authorityfelder und nicht unterstützter Channelwerte;
- getrennte neutrale, Input- und technische Prozessausgaben;
- aktualisiertes Bundle- und Architekturinventar.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit:

```text
3366 passed, 588 warnings
```

## Neu bestätigte Executor-Lücke

LQ-250 und LQ-281 erzeugen vertragsgemäß keinen Publication-Executor.

Die spätere LQ-254-/LQ-275-Kette verlangt jedoch eine bereits persistierte
`ReleasePublicationExecutorId`. Aktuell existiert dafür kein Bootstrap-,
Registrierungs- oder Lifecycle-Operator.

Tests konnten diesen Fakt bisher direkt seeden. Das ist kein unterstützter
Betriebsweg.

LQ-281 erweitert den einmaligen Channel-Bootstrap nicht nachträglich um eine
technisch und fachlich getrennte Executor-Authority.

## Bewusst nicht enthalten

LQ-281 implementiert keinen autorisierten Publication-Handoff, keine Executor-
Registrierung, Channel- oder Publisher-Mutation und keinen Providerzugriff.

Es entstehen keine Migration, Route, Service-Unit, Scheduler-, CI-, Signing-,
Promotion-, Publication- oder Deploymentautomation.

## Folgeordnung

LQ-282 sollte den owner-only Handoff-Prozessvertrag und die fehlende
Publication-Executor-Registrierung gemeinsam auditieren und entscheiden.

Beide Grenzen müssen getrennte stabile IDs, Authority, Retry und geschützte
Übergaben bewahren; direkter SQL-Seed bleibt unzulässig.
