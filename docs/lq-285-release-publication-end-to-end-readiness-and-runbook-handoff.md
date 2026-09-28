# LQ-285 — Release Publication End-to-End Readiness and Runbook Handoff

## Ergebnis

LQ-285 wiederholt den LQ-277-Betriebsbereitschaftsaudit nach Schließung der
damals festgestellten Prozesslücken.

Der interne unterstützte Offline-Weg ist jetzt vollständig über installierte,
geschlossene Prozessgrenzen erreichbar:

```text
migrierter leerer Store
  -> Registry-Bootstrap
  -> Key-Challenge, Proof und Aktivierung
  -> Publication-Control-Plane-Bootstrap
  -> Signing und detached SSHSIG
  -> aktuelle Promotion-Evidence
  -> technische Executor-Registrierung
  -> autorisierter persistenter Handoff
  -> beaufsichtigter Publication-Worker
  -> Reconciliation und persistentes Receipt
```

LQ-285 erweitert keine Authority und führt keinen externen Providerwrite aus.

## Geschlossene frühere Blocker

LQ-277 identifizierte Registry-Bootstrap, Key-Aktivierung,
Publication-Control-Plane-Bootstrap und autorisierten Handoff als fehlende
owner-only Prozessgrenzen.

LQ-280 implementierte Registry-Bootstrap und zweistufige Key-Aktivierung.

LQ-281 implementierte den einmaligen Publication-Control-Plane-Bootstrap.

LQ-283/284 implementierten persistente Executor-Registrierung und den
autorisierten Handoff-Operator.

Damit ist kein direkter Adapter-, SQL-, Fixture- oder Python-REPL-Zugriff mehr
erforderlich, um die interne Prozesskette vorzubereiten.

## Aktualisiertes Runbook

`operations/runbooks/release-publication-worker.md` beschreibt jetzt den
vollständigen kontrollierten Handoff statt nur den bereits vorbereiteten
Worker-Aufruf.

Es dokumentiert in Authority-Reihenfolge:

- einmaligen Registry-Bootstrap mit getrenntem Public Key;
- Challenge-Materialisierung, unabhängigen Proof und Reviewer-Approval;
- getrennten einmaligen Publication-Channel-Bootstrap;
- Signing und Promotion ohne implizite Folgewirkung;
- persistente Executor-Registrierung mit intern erzeugter Executor-ID;
- aktuellen Handoff mit stabiler Execution-ID;
- unveränderte Übergabe an den bestehenden Worker;
- terminale Ergebnisse, Unknown Outcome und beaufsichtigte Fortsetzung.

## Keine Bootstrap-Wiederholung

Bootstrap-Kommandos sind kein Repair-, Rotate- oder Reactivate-Werkzeug.

Existiert der jeweilige Current-Bestand bereits, wird der Bootstrap-Schritt
übersprungen. Lifecycle-Änderungen benötigen weiterhin ihren eigenen Vertrag.

Ein anderer Bootstrap-Request darf bestehende Authority nicht ersetzen.

## Getrennte Actors und Evidenz

Registry-Lifecycle-Authority, Signer, Activation-Reviewer,
Promotion-Verifier, Publisher-Authority und Publication-Executor bleiben
getrennte Identitäten.

Keine ID allein ist eine Allow-Entscheidung. Jeder mutierende Schritt löst die
aktuelle persistente Authority erneut auf.

Proof und Approval werden nicht durch das Publication-Prozesskonto erzeugt.
Reviewer Trust bleibt environment-owned und außerhalb des Requests.

## Artifact- und Promotionbindung

Signing erzeugt ausschließlich den detached SSHSIG für den autorisierten
Kandidaten.

Promotion prüft Bundle, Signatur und Current Registry read-only. Für den
LQ-284-Handoff wird die prozessgebundene technische Verifier-ID
`liquent-release-publication-handoff-v1` verwendet.

Promotion-Evidence startet weder Handoff noch Worker und ersetzt keine spätere
aktuelle Registry-, Channel- oder Publisherprüfung.

## Executor und Handoff

Die stabile Executor-Registration-ID erzeugt genau eine intern generierte
Executor-ID. Registrierung gewährt keine Publication-Authority.

Der Handoff-Request bewahrt Handoff-, Decision- und Execution-ID sowie Actor,
Channel-Revision und absolute Artifactpfade.

Nur `accepted` erlaubt die Vorbereitung des Worker-Requests. Neutrales
`not_accepted`, Konflikt, Inputfehler und technische Nichtverfügbarkeit bleiben
getrennte Enden ohne automatischen Folgeschritt.

## Geschlossene Worker-Brücke

Der bewahrte Handoff-Request und das minimale Erfolgsergebnis enthalten alle
normativen Referenzen für den exakt fünfteiligen Worker-Request:

- Execution-ID;
- Handoff-ID;
- Publisher-Authority-ID;
- Channel-ID;
- erwartete Channel-Revision-ID.

Die Feldbezeichnung wird beim Worker ausschließlich von
`channel_revision_id` zu `expected_channel_revision` abgebildet; der Wert wird
nicht normalisiert oder ersetzt.

Der Handoff-Operator schreibt keine Worker-Datei und startet keinen Worker.
Diese bewusste manuelle Grenze verhindert eine implizite Publication.

## Persistente Ausführungsgrenze

Der Worker persistiert Execution und Attempt 1 erst beim aktuellen Preflight.

Danach gelten weiterhin die LQ-265-/LQ-276-Verträge für create-only Zugriff,
Unknown Outcome, read-only Reconciliation, höchstens zwei Attempts und
terminales Receipt.

Ein verlorenes Ergebnis erlaubt keinen Ersatz-Handoff, keine neue Execution-ID
und keinen manuellen Provider-PUT.

## Statischer Auditnachweis

Der neue Test bestätigt:

- alle acht benötigten Offline-Entry-Points;
- deren dokumentierte Reihenfolge;
- das Fehlen direkter Store-Abkürzungen;
- die vollständige Handoff-/Worker-Feldbrücke;
- die prozessgebundene, nicht request-gesteuerte Verifier-ID;
- die Isolation vom HTTP-Startup und von Automatisierung.

Die dynamischen Operator-, PostgreSQL- und Worker-Audits der Slices LQ-276,
LQ-280, LQ-281, LQ-283 und LQ-284 bleiben die ausführbaren Teilnachweise.

## Readiness-Entscheidung

Die interne Release-Publication-Prozesskette ist operativ geschlossen und
dokumentiert.

Dies ist keine Freigabe eines konkreten externen Paketproviders. Origin, TLS,
Credential-Scope, Paketnamensbesitz, Rate-Limits, Monitoring, Incidentweg und
Deploymentumgebung benötigen weiterhin eine environmentbezogene Abnahme.

Es ist ebenso keine Freigabe für Scheduler, Service, CI-Publication,
automatische Retries oder Runtime-Startup-Wiring.

## Technischer Bestand

LQ-285 ändert keinen Produktionscode, Port, Typ, Schema, SQL, Migration,
Entry Point oder Operational-Bundle-Format.

Der Head bleibt `20260819_0025` mit 25 linearen Migrationen. Das Bundle bleibt
bei 20 Console Entry Points und 19 Operatormodulen.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit 3391 Tests und 588
bestehenden Warnungen.

## Nächster Slice

LQ-286 sollte die verbleibende environmentbezogene Provider- und
Deployment-Freigabe als expliziten Vertrag abgrenzen, ohne einen echten Upload
oder automatische Aktivierung auszuführen.
