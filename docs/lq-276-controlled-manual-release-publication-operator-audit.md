# LQ-276 — Controlled Manual Release Publication Operator Audit

## Ergebnis

LQ-276 schließt die manuelle Betriebsgrenze des LQ-275-Operators mit einem
konkreten owner-only Runbook und einem integrierten End-to-End-Audit.

Der Audit führt die echte Prozessfunktion durch sichere Dateiparser, Readiness,
eine neu aufgebaute Engine, LQ-269, LQ-273 und die persistente Zustandsmaschine.

Es entsteht keine automatische Production-Aktivierung.

## Auditumfang

Gemeinsam geprüft werden:

- sechs private Prozessdateien und eine private Credential-Datei;
- geschlossener kanonischer Work-, Artifact- und Providerinput;
- exakte Handoff-Bindung aus dem System of Record;
- Migration-Readiness vor Provideraufbau;
- vollständige lokale Worker-Composition;
- kontrollierter Package-Index-Transport;
- genau eine immutable Create-Sequenz;
- read-only Sichtbarkeitsbestätigung;
- atomarer Receipt- und Published-Abschluss;
- stdout-, Exitcode- und Ressourcenabschluss;
- identisches Verhalten auf SQLite und echtem PostgreSQL 16.

## Integrierter erfolgreicher Pfad

Der Test beginnt mit einer bereits kontrolliert vorbereiteten Execution und
den gebundenen signierten Release-Artefakten.

Der Operator liest ausschließlich die sieben owner-only Quellen, prüft den
Migration-Head und komponiert einen einzelnen Providerclient.

Die beobachtete Providerfolge ist exakt:

```text
GET absent -> PUT create-only -> GET bytegleich sichtbar
```

Danach sind Execution und Attempt persistent abgeschlossen, genau ein Receipt
existiert und stdout enthält ausschließlich `{"outcome":"published"}`.

## Keine offene Autorisierung

Der Request enthält weiterhin nur Execution-, Handoff-, Publisher-, Channel-
und erwartete Channel-Revision.

Er enthält keine Phase, Attempt-ID, Rolle, Capability, Allow-Entscheidung,
Providerantwort, Observation, Hash- oder Artifactbehauptung.

Current State, Registry, Signer, Key, Channel und Publisher werden durch die
persistente Composition neu aufgelöst. Ein früherer positiver Zustand ist kein
Grace-Ticket für einen späteren Lauf.

## Provider- und Credentialgrenze

Der integrierte Audit verwendet den realen Package-Index-Adapter und die reale
begrenzte HTTP-Transportlogik über einen kontrollierten In-Process-Transport.

Dadurch werden Requestfolge, Bearer-Credential-Bindung, create-only Verhalten
und Responseparser geprüft, ohne einen externen Provider zu verändern.

Das Credential wird genau einmal aus seiner privaten Datei geladen und der
Client nach dem Work-Aufruf geschlossen.

## Persistenter Abschluss

Ein positiver PUT-Return ist nicht der Published-Nachweis. Erst der nachfolgende
GET und der atomare Finalizer erzeugen das Receipt und den terminalen Status.

Der Audit bestätigt genau einen Attempt, genau ein Receipt und keinen weiteren
Create nach dem terminalen Ergebnis.

Die bereits geprüfte LQ-265-Grenze bleibt bei höchstens zwei Creates über den
gesamten Recovery-Lebenszyklus bestehen. LQ-276 erweitert sie nicht.

## PostgreSQL-Gegenprüfung

Der gleiche Operatoraudit wird gegen einen isolierten, auf Head migrierten
PostgreSQL-16-Bestand ausgeführt.

Die Operatorengine ist dabei eine zweite unabhängige Engine auf denselben
Store. Damit ist die Prozessgrenze nicht durch ein geteiltes In-Memory-Objekt
oder SQLite-Verbindungswissen vorgetäuscht.

## Manuelles Runbook

`operations/runbooks/release-publication-worker.md` definiert:

- kontrollierte Vorbedingungen und Prozesskonto;
- exakte kanonische Eingabeformen;
- private Datei- und Retentionsregeln;
- einen einzelnen pfadbasierten Command;
- die acht Exit- und Fehlerfamilien;
- sichere Fortsetzung bei `pending_reconciliation` oder verlorenem Ergebnis;
- Verbot manueller Ersatzuploads und automatischer Retries;
- getrennte Behandlung von Revocation, Konflikt und Reassessment;
- minimale Auditdaten und sichere lokale Bereinigung.

## Keine Schleife oder Serviceaktivierung

Das Runbook verbietet Shell-Loops, Timer, Queue-Consumer, Restart-Policies,
Daemon, CI-, Deployment- und App-Startup-Hooks ausdrücklich.

Jeder weitere Aufruf ist eine neue beaufsichtigte Betriebsentscheidung mit
dem unveränderten Request. Die persistente Zustandsmaschine entscheidet, ob
Preflight, Create, Reconciliation, Recovery oder kein Schritt zulässig ist.

## Unknown Outcome

Nach möglichem Providerwrite werden Timeout, Verbindungsverlust und verlorene
Prozessausgabe niemals als bestätigte Abwesenheit behandelt.

Das Runbook verlangt die unveränderte Wiederaufnahme. Der Worker wählt dann
read-only Reconciliation und führt keinen blinden Ersatz-PUT aus.

Providerdetails oder interne Exceptions werden nicht als Entscheidungsersatz
in stderr veröffentlicht.

## Retention und Nichtwiederverwendung

Work-Request und Artifact-Quelle bleiben mindestens bis zum terminalen
Abschluss sowie für erforderliche Reconciliation- und Auditzeiträume stabil.

Execution-, Handoff-, Attempt-, Receipt-, Recovery- und Reassessment-IDs
werden nicht ersetzt, neu zugeordnet oder für andere Fakten wiederverwendet.

Lokale Dateien sind keine normative Historie. Persistente Fakten und gebundene
Release-Evidence bleiben die System-of-Record-Nachweise.

## Bewusst unverändert

LQ-276 ändert keinen Produktionscode, Port, Signatur, Domain-Typ, Provider-
Vertrag, Schema, SQL oder Migration.

Es entstehen keine neue Authority, kein Bootstrap, keine Admission, kein User,
Workspace, Membership oder Rolle und keine Withdrawal-, Yank-, Delete- oder
Rollbackfunktion.

Der Migration-Head bleibt `20260819_0024` mit 24 linearen Migrationen. Das
operative Bundle bleibt bei 15 Console Entry Points.

## Nachweis und Entscheidung

Die neuen Audit-Tests belegen den vollständigen manuellen Published-Pfad auf
SQLite und PostgreSQL 16, exakt einen Client, `GET → PUT → GET`, genau ein
Receipt, terminale Persistenz, minimale Ausgabe und sicheren Clientabschluss.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit:

```text
3348 passed, 588 warnings
```

LQ-276 gibt damit die kontrollierte manuelle Prozesskette als geprüft frei,
nicht jedoch einen unbeaufsichtigten oder automatisch aktivierten Betrieb.

LQ-277 sollte als getrennten nächsten Slice die Release-Publication-
Betriebsbereitschaft und den verbleibenden Gesamt-Release-Handoff auditieren,
ohne die manuelle Aktivierungsgrenze zu erweitern.
