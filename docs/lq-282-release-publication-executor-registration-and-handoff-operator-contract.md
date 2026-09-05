# LQ-282 — Release Publication Executor Registration and Handoff Operator Contract

## Ergebnis

LQ-282 entscheidet die letzten internen Vorbereitungsschritte vor dem bereits
implementierten LQ-275-Publication-Worker:

- persistente Registrierung einer technischen Publication-Executor-Identität;
- owner-only Operator für den autorisierten LQ-251-Publication-Handoff;
- stabile Übergabe einer neuen Execution-ID an den bewahrten Worker-Request.

Die drei Identitäten bleiben getrennte Fakten. Dieser Slice implementiert noch
keinen Port, Adapter, Operator, Entry Point, Schema oder Migration.

## Warum Executor-Registrierung erforderlich ist

LQ-253 erzeugte ein leeres `release_publication_executors`-Inventar.

LQ-254 verlangt vor Attempt 1 eine bereits bekannte
`ReleasePublicationExecutorId`. LQ-275 liest diese ID aus einer privaten Datei,
registriert sie aber absichtlich nicht.

Tests konnten den Fakt direkt seeden. Direkter SQL-Seed ist kein unterstützter
Betriebsweg und bleibt verboten.

## Technische Identität, keine Publication-Authority

Ein registrierter Executor identifiziert ausschließlich den technischen
Prozess, der einen Attempt vorbereitet und ausführt.

Die Registrierung gewährt keine:

- Publisher-Authority;
- Channel-Membership;
- Release-Signer- oder Registry-Lifecycle-Authority;
- Signing-, Promotion- oder Reviewer-Authority;
- Provider-, Deployment- oder Produktberechtigung.

Jeder Attempt prüft Publisher, Channel, Registry, Signer und Key weiterhin
aktuell aus dem System of Record.

## Stabile Registrierungsentscheidung

Jede Executor-Registrierung besitzt eine eigene stabile
`ReleasePublicationExecutorRegistrationId`.

Die Executor-ID wird innerhalb der atomaren Persistenzgrenze kryptografisch
sicher erzeugt und in einer unveränderlichen Registrierungsentscheidung
gebunden.

Die Registration-ID ist der bewahrte Retry-Anker. Sie ist nicht selbst der
Executor und gewährt keine Authority.

## Geschlossener Registrierungsport

Der spätere Port akzeptiert ausschließlich die stabile Registration-ID.

Er akzeptiert keine caller-gelieferte:

- Executor-ID;
- Rolle, Capability oder Allow-Entscheidung;
- Publisher-, Channel- oder Workspacebindung;
- Hostname, Prozess-ID, Serviceaccount oder Credential;
- Status-, Revision- oder Ergebnisbehauptung.

Die resultierende Executor-ID entsteht ausschließlich intern.

## Atomare Registrierung

Ein erfolgreicher Erstaufruf persistiert in einer Transaktion:

- genau einen stabilen Executor-Fakt;
- genau eine unveränderliche Registration-ID-/Executor-ID-Bindung.

Ohne committete Entscheidung wird keine Executor-ID ausgegeben.

Es wird kein Handoff, keine Execution, kein Attempt und kein Providerzugriff
erzeugt.

## Exakter Registrierungsretry

Ein Retry derselben Registration-ID liefert dieselbe Executor-ID ohne neuen
Generatorzug oder zweite Mutation.

Eine andere Registration-ID erzeugt einen weiteren getrennten technischen
Executor, sofern keine spätere explizite Policy dies begrenzt.

Registration- und Executor-ID werden nie neu zugeordnet oder unter anderer
Bedeutung wiederverwendet.

## Executor-Lifecycle bleibt separat

LQ-282 entscheidet nur additive Registrierung.

Aktivierung, Deaktivierung, Rotation, Hostbindung, Attestation und Recovery
eines Executors benötigen einen späteren expliziten Lifecycle-Vertrag.

Die heutige Existenzzeile besitzt keinen caller-mutierbaren Status. Ein
späterer Lifecycle darf historische Attempts und Registrierungen nicht löschen.

## Executor-Operator

Der spätere Entry Point lautet:

```text
liquent-release-publication-executor
```

Der Modus `register` akzeptiert ausschließlich:

```text
--database-url-file PATH
--request PATH
```

Die kanonische Requestdatei enthält exakt die Registration-ID.

## Geschützte Executor-Ausgabe

Erfolg und exakter Retry liefern kanonisches JSON mit:

- `outcome` gleich `registered`;
- Registration-ID;
- Executor-ID.

Die Executor-ID wird anschließend unverändert in der privaten
`--executor-id-file` des LQ-275-Operators bewahrt.

stdout enthält keine Authority-, Channel-, DSN- oder Hostdetails.

## Handoff-Prozessgrenze

Der spätere Handoff-Entry-Point lautet:

```text
liquent-release-publication-handoff
```

Er ist ein expliziter kurzlebiger owner-only Offline-Prozess und keine Route,
Startup-Funktion, CI-Aktion oder automatische Folge von Promotion.

Positive LQ-247-Evidence allein startet keinen Handoff.

## Private Handoff-Eingaben

Der Command akzeptiert ausschließlich Pfade zu:

- privater Datenbank-URL-Datei;
- kanonischer Handoff-Requestdatei.

Bundle, detached SSHSIG und Promotion-Evidence werden über absolute Pfade in
der Requestdatei identifiziert und von LQ-251 erneut als unveränderliche
Snapshots gelesen.

Alle Dateien bleiben regulär, symlinkfrei, owner-only, einfach verlinkt und
begrenzt. Der Operator repariert keine Dateirechte.

## Geschlossener Handoff-Request

Der Request enthält exakt:

- stabile Handoff-ID;
- stabile Publication-Decision-ID;
- identifizierende Publisher-Authority-ID;
- Channel-ID;
- exakt erwartete Channel-Revision;
- absoluten Bundle-Pfad;
- absoluten detached-SSHSIG-Pfad;
- absoluten Promotion-Evidence-Pfad;
- stabile neue Execution-ID.

Die Execution-ID ist ein Übergabefakt für den Worker und noch kein
persistierter Attempt.

## Warum die Execution-ID im Request liegt

LQ-275 benötigt sie vor seinem ersten Aufruf. LQ-254 persistiert sie erst beim
atomaren Attempt-Preflight.

Würde der Handoff-Operator sie nach Commit nur flüchtig erzeugen, könnte ein
verlorenes Resultat beim Retry eine andere ID liefern.

Deshalb wird die Execution-ID vor dem ersten Handoff-Aufruf kryptografisch
sicher erzeugt, gemeinsam mit dem unveränderten Request bewahrt und bei jedem
Retry bytegleich wiederverwendet.

Sie erteilt keine Authority und wird von LQ-251 nicht als Handoffentscheidung
interpretiert.

## Keine offene Handoff-Steuerung

Der Request enthält keine:

- Registry-, Signer-, Key- oder Policybehauptung;
- Rolle, Capability oder Allow-Entscheidung;
- Providerorigin, Credential oder Ziel-URL;
- Hash-, Paketversions- oder Promotionstatusbehauptung;
- Attempt-ID, Attempt-Nummer, Phase oder Ergebnis;
- Executor-ID oder Reviewer-Identität.

Alle Authority- und Hashfakten stammen weiterhin aus LQ-251 und dem System of
Record.

## Handoff-Composition

Nach exakter Migration-Readiness komponiert der Operator:

- aktuelle persistente Registry-Projektion;
- unabhängige Promotion-Verifier-ID aus einer getrennten privaten Datei oder
  fest gebundenen Prozesskonfiguration;
- bestehenden LQ-244-Promotion-Check;
- `DatabaseAuthorizedReleasePublicationHandoff`;
- sichere Clock.

Die konkrete Wiederverwendung der bereits bewährten LQ-247-/LQ-251-
Composition wird im Implementierungsslice entschieden.

## Aktuelle Autorisierung

Jeder neue Handoff prüft erneut:

- aktuellen Registry-Pointer und aktive Policy;
- aktiven Signer und Key;
- unveränderte Promotion-Evidence;
- aktiven Current-Channel;
- exakt erwartete Channel-Revision;
- aktiven Publisher-Member derselben Revision.

Publisher-ID identifiziert den Actor, gewährt allein aber keine Authority.

## Handoff-Erfolg

Ein erfolgreicher neuer oder exakt wiederholter Handoff liefert kanonisches
JSON mit:

- `outcome` gleich `accepted`;
- Handoff-ID;
- Decision-ID;
- Channel-ID;
- Channel-Revision-ID;
- unveränderter Execution-ID.

Kein Ergebnis enthält Hashes, Signer, Key, Registryinventar oder lokale Pfade.

## Worker-Request-Übergabe

Aus dem geschützten Erfolg können exakt die fünf Felder des LQ-275-Work-
Requests aufgebaut werden:

- Execution-ID aus dem bewahrten Handoff-Request;
- Handoff-ID;
- Publisher-Authority-ID;
- Channel-ID;
- erwartete Channel-Revision.

Der Handoff-Operator schreibt diese Worker-Datei in diesem Slice nicht
automatisch. Exklusive Materialisierung kann im Implementierungsslice als
expliziter Outputpfad entschieden werden.

## Exakter Handoff-Retry

Ein Retry verwendet dieselbe Handoff-, Decision- und Execution-ID sowie
dieselben Artifact- und Evidence-Dateien.

Der bestehende LQ-251-Adapter liefert denselben akzeptierten Handoff ohne neue
Promotionprojektion, Clock oder Mutation.

Die Execution-ID bleibt aus dem bewahrten Request stabil und wird nicht neu
gezogen.

## Ablehnung, Konflikt und Nichtverfügbarkeit

Stale Revision, inaktiver Publisher, Revocation, falsche Signatur oder
abweichende Evidence enden neutral `not_accepted` mit Exit `5`.

Wiederverwendung von Handoff- oder Decision-ID mit abweichender Bindung endet
detailfrei Konflikt mit Exit `3`.

Ungültiger Input verwendet Exit `2`; technische Datei-, Promotion-,
Datenbank-, Clock- oder Compositionfehler Exit `4`.

Erfolg verwendet Exit `0`.

## Gemeinsame sichere Dateigrenze

Beide Operatoren übernehmen die LQ-275-Dateiregeln:

- ausschließlich absolute Pfade;
- `O_NOFOLLOW` und `O_CLOEXEC`;
- Prüfung des geöffneten Descriptors über `fstat`;
- effektiver Prozessnutzer als Eigentümer;
- genau ein Hardlink;
- exakt Modus `0400` oder `0600`;
- begrenzte Größe und gültiges UTF-8 für Text.

Unsichere Dateien enden fail-closed technisch nicht verfügbar.

## Readiness und Ownership

Jeder Prozess baut genau eine Engine, prüft den exakten Migration-Head und
schließt alle besessenen Ressourcen in jedem Pfad.

Kein Prozess migriert, seedet fremde Fakten, öffnet Providerzugriff oder führt
automatische Folgeschritte aus.

## Retention und Nichtwiederverwendung

Registration-Request und geschützte Executor-Ausgabe bleiben mindestens so
lange erhalten, wie Attempts, Incidents oder Audits auf den Executor verweisen.

Handoff-Request, Execution-ID und Artifactquellen bleiben mindestens bis zum
terminalen Publicationabschluss sowie für Reconciliation-, Release- und
Auditzeiträume stabil.

Persistente Registration-, Handoff-, Execution-, Attempt- und Receiptfakten
bleiben die normative Historie.

## Bewusst nicht entschieden

LQ-282 entscheidet keine konkrete Python-Signatur, Tabelle, Spalte, SQL,
Migration, Dateischema-Datei, Runbook- oder Entry-Point-Implementierung.

Es entscheidet keinen Executor-Lifecycle, Channel-/Publisher-Lifecycle,
Withdrawal, Yank, Delete, Provider-SDK, Scheduler, Service, CI, Deployment oder
Runtime-Wiring.

Es erfolgt kein Datei-, Provider-, Git- oder Deploymentwrite.

Die vollständige PostgreSQL-16-Pflichtsuite bleibt grün mit:

```text
3366 passed, 588 warnings
```

## Folgeordnung

LQ-283 sollte zuerst die persistente Executor-Registrierungsentscheidung und
ihren Port additiv implementieren.

LQ-284 kann danach Executor- und Handoff-Operator gemeinsam implementieren und
die geschützte Worker-Request-Übergabe schließen.
