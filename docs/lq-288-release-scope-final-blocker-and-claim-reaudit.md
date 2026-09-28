# LQ-288 — Release Scope Final Blocker and Claim Reaudit

## Ergebnis

LQ-288 auditiert den vollständigen Release-Bereich nach LQ-280 bis LQ-287 auf
verbleibende interne Blocker, widersprüchliche Runbooks und ungeschützte
Productionclaims.

Die beaufsichtigte Offline-Kette für Package-Publication besitzt keinen
verbleibenden internen Implementierungsblocker.

Ein echter Productionzugriff bleibt dennoch fail-closed, solange der
environmentbezogene LQ-287-Evidence-Record nicht aktuell `approved` ist.

## Auditumfang

Geprüft werden gemeinsam:

- alle installierten Release-Entry-Points;
- Registry-, Key-, Signing-, Promotion-, Publication- und Worker-Reihenfolge;
- Migration-Head und Operational-Bundle-Inventar;
- Handoff-/Worker-Referenzbrücke;
- Runtime-, Compose- und CI-Isolation;
- Environment-Readiness und detailarme Outcomes;
- aktuelle Aussagen gegenüber historischen Slice-Snapshots;
- Deployment-, Rollback- und Withdrawal-Abgrenzung.

## Interne Publication-Kette

Die folgenden acht Offline-Prozessgrenzen sind installiert:

1. `liquent-release-registry-bootstrap`;
2. `liquent-release-key-activation`;
3. `liquent-release-publication-bootstrap`;
4. `liquent-release-signing`;
5. `liquent-release-promotion`;
6. `liquent-release-publication-executor`;
7. `liquent-release-publication-handoff`;
8. `liquent-release-publication`.

Zusammen decken sie den Weg vom leeren migrierten Authority-Bestand bis zum
persistenten Publication-Receipt ab.

Kein direkter SQL-, Fixture-, Python-REPL- oder App-Startup-Zugriff ist für
diese interne Kette erforderlich.

## Authority- und Prozessgrenzen

Registry-Lifecycle-Authority, Signer, Activation-Reviewer,
Promotion-Verifier, Publisher-Authority und Publication-Executor bleiben
getrennte Identitäten.

Kein Request akzeptiert eine allgemeine Rolle, Capability oder caller-
gelieferte Allow-Entscheidung als Ersatz für aktuelle Persistenz.

Bootstrap, Aktivierung, Signing, Promotion, Handoff und Workerstart bleiben
separate beaufsichtigte Entscheidungen. Kein positiver Ausgang startet den
nächsten Prozess automatisch.

## Handoff- und Worker-Brücke

Der akzeptierte Handoff und sein bewahrter Request liefern exakt die stabilen
Referenzen für den fünfteiligen Worker-Request.

Execution-ID wird erst im Worker-Preflight persistiert. Ein verlorenes Ergebnis
erzeugt weder neue Execution-ID noch Ersatzupload.

Der Worker bleibt auf eine Arbeitseinheit pro Prozess begrenzt und verwendet
die persistente Zustandsmaschine für Reconciliation, Recovery und terminalen
Abschluss.

## Migration und Bundle

Die erzwungenen aktuellen Werte stimmen über Code, Tests und Dokumentation:

- Migration-Head `20260819_0025`;
- 25 lineare Migrationen;
- 20 Console Entry Points;
- 19 Operatormodule.

LQ-288 verändert keinen dieser Werte.

## Runtime- und CI-Isolation

HTTP-App und Production-Control-Plane importieren oder starten keinen
Release-Bootstrap-, Key-Aktivierungs-, Handoff- oder Publication-Operator.

Compose referenziert keinen dieser Offline-Commands als Service.

GitHub Workflows rufen den Package-Publication-Operator nicht auf. Der
bestehende Artifact-/Container-Releasebereich ist keine automatische
Package-Provider-Publication.

Damit bleibt jede echte Publication ein expliziter beaufsichtigter Prozess.

## Environment-Gate

Die interne Vollständigkeit ist keine Productionfreigabe.

Vor echtem Providerzugriff verlangt LQ-287 einen aktuellen Evidence-Record mit
gebundenem Origin, Package, Ziel, Credential-Identität, Bundle, Host,
Prozesskonto und Gültigkeitsfenster.

Provider-, Security-, Operations- und Release-Review müssen denselben
Evidence-Set-Digest attestieren.

Nur detailarmes `approved` erlaubt einen späteren separaten Operatorstart.
`rejected`, `expired`, `revoked` und `unavailable` schließen ihn fail-closed.

## Historische Blockerclaims

LQ-277 dokumentiert korrekt den damaligen Stand mit vier fehlenden
Prozessgrenzen.

Diese Aussage ist ein historischer Slice-Snapshot und wird durch LQ-280,
LQ-281, LQ-284 und die explizite Closure in LQ-285 chronologisch superseded.

Sie wird nicht rückwirkend umgeschrieben. Der aktuelle Status steht in den
späteren Roadmap-Einträgen und in diesem Reaudit.

## Gefundener aktueller Widerspruch

Der Compose-README und der Kopfkommentar behaupteten weiterhin, LQ-058 müsse
Control-Plane- und Worker-Commands erst liefern.

Die Control Plane und Migration existieren inzwischen. Der Compose-Vertrag
referenziert jedoch weiterhin den nicht implementierten allgemeinen Command
`liquent-research-worker`.

LQ-288 korrigiert die Aussage präzise: Der Stack bleibt aus diesem Grund nicht
runnable. Der kurzlebige Offline-Publication-Operator ist kein Ersatz für einen
lang laufenden Research-Worker.

Diese Korrektur startet keinen Service und verändert keine Compose-Semantik.

## Verbleibende Grenzen

Kein interner Publication-Codeblocker bleibt für einen beaufsichtigten Lauf.

Folgende Grenzen bleiben bewusst extern oder separat:

- konkrete LQ-287-Environmentfreigabe;
- Credentialausgabe und Providerkonto;
- DNS-, TLS-, Egress- und Hostbereitstellung;
- Monitoring- und Incidentbereitschaft;
- allgemeiner `liquent-research-worker` für den Compose-Stack;
- Production-Deploymentfreigabe;
- Package-Withdrawal, Yank, Delete oder Replace.

Diese Punkte dürfen nicht als ein einzelner neuer Publication-Slice oder
Runtime-Allow zusammengezogen werden.

## Productionclaim-Entscheidung

Zulässige aktuelle Aussage:

```text
Die interne beaufsichtigte Package-Publication-Kette ist implementiert und
geprüft; ein realer Environment-Start bleibt bis zur unabhängigen Evidence-
Freigabe geschlossen.
```

Nicht zulässig sind Aussagen wie „Production-ready“, „automatisch
veröffentlicht“, „Deployment aktiviert“ oder „Provider freigegeben“, solange
die konkreten externen Nachweise fehlen.

## Statischer Reaudit

Der neue Test bestätigt:

- alle acht installierten Offline-Commands;
- getrennte interne und environmentbezogene Readiness;
- fehlendes Runtime-, Compose- und CI-Wiring;
- exakte Migration-/Bundlewerte;
- chronologische Supersession des LQ-277-Blockerclaims;
- präzisen Compose-Status zum fehlenden Research-Worker.

## Technischer Bestand

LQ-288 ändert keinen Produktionscode, Port, Typ, Schema, SQL, Migration, CLI,
Entry Point oder Operational-Bundle-Format.

Es erfolgt kein Credential-, Datenbank-, Netzwerk-, Provider-, Git-, Service-
oder Deploymentzugriff.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit 3407 Tests und 588
bestehenden Warnungen.

## Nächster Slice

LQ-289 sollte den verbleibenden allgemeinen Compose-Blocker
`liquent-research-worker` getrennt vom Release-Publication-Bereich auditieren
und dessen kleinsten sicheren Worker-Vertrag entscheiden.
