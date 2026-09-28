# LQ-275 — Owner-only Release Publication Worker Operator

## Ergebnis

LQ-275 implementiert den in LQ-274 eingefrorenen kurzlebigen Offline-Operator
für genau eine persistente Release-Publication-Arbeitseinheit.

Der neue Console Entry Point `liquent-release-publication` komponiert den
vollständigen LQ-273-Worker, führt ihn genau einmal aus und endet danach.

Es gibt weiterhin keinen Scheduler, Watcher, Daemon oder automatischen Start.

## Prozessgrenze

Der Operator ist ausschließlich für ein dediziertes nicht interaktives
Publication-Prozesskonto bestimmt.

Er wird explizit mit sechs Dateipfaden aufgerufen:

- Datenbank-URL-Datei;
- Work-Request-Datei;
- Artifact-Source-Datei;
- Providerkonfigurationsdatei;
- Executor-ID-Datei;
- Promotion-Verifier-ID-Datei.

Direkte IDs, Credentials, Origins, Hashes oder Allow-Werte sind keine
Kommandozeilenoptionen. Es existiert kein Environment-Fallback.

## Sichere private Eingaben

Alle sechs Eingabedateien werden descriptor-basiert mit `O_NOFOLLOW` und
`O_CLOEXEC` geöffnet und anschließend mit `fstat` geprüft.

Akzeptiert werden nur absolute Pfade auf reguläre Dateien, die dem effektiven
Prozessnutzer gehören, genau einen Hardlink und exakt Modus `0400` oder `0600`
besitzen sowie innerhalb der jeweiligen Größengrenze bleiben.

Symlinks, fremdes Eigentum, weitere Links, zu offene Rechte, unpassende
Dateitypen und fehlende sichere Plattformflags enden fail-closed technisch
nicht verfügbar.

Textquellen verlangen gültiges UTF-8. Leere oder fachlich ungültige Inhalte
werden als Input abgelehnt.

## Geschlossener Work-Request

Der Work-Request ist kanonisches, sortiertes und kompaktes JSON mit finalem LF
und exakt diesen fünf Feldern:

- `execution_id`;
- `handoff_id`;
- `publisher_authority_id`;
- `channel_id`;
- `expected_channel_revision`.

Fehlende, zusätzliche oder doppelte Felder sowie nicht kanonische Darstellung
werden vollständig abgelehnt.

Phase, Attempt, Provider, Artifact, Rolle, Capability und Allow-Behauptung
können nicht eingespeist werden. Der persistente aktuelle Zustand entscheidet.

## Artifact-Source

Die getrennte Artifact-Datei enthält nur Handoff-ID und absolute Pfade für
Bundle, detached SSHSIG und Promotion-Evidence.

Der Signaturdateiname muss exakt aus dem Bundle-Dateinamen plus `.sshsig`
bestehen. Die konfigurierte Handoff-ID muss exakt dem Work-Request entsprechen.

Der lokale Source akzeptiert ausschließlich das später aus dem System of
Record geladene vollständige Artifact-Binding derselben Handoff-ID.

Hashes, Signer, Key, Authority und Paketversion stammen nie aus dieser Datei.
Die vorhandene LQ-255-Grenze liest und prüft die Artifact-Bytes erneut.

## Providerkonfiguration

Die separate kanonische Providerdatei enthält exakt einen HTTPS-Origin, einen
lokalen Zielnamen, einen absoluten Credential-Pfad und positive Grenzen für
Connect-, Read- und Gesamtdauer sowie Request- und Responsegröße.

Origin und Zielname werden bereits beim Parsen durch die bestehende
Package-Index-Konfiguration validiert. Zusätzliche Providersteuerung,
Retryanzahl, Mirror oder Fallback werden abgelehnt.

Das Credential wird erst durch die LQ-269-Composition sicher und genau einmal
geladen. Es erscheint weder in Request noch Ausgabe oder Fehlertext.

## Getrennte technische Identitäten

Executor-ID und Promotion-Verifier-ID werden jeweils aus einer eigenen
privaten Datei gelesen. Genau ein optionales finales LF ist zulässig.

Beide IDs sind technische Identitäten und erteilen keine Publisher-Authority.
Der Work-Request kann sie nicht bestimmen oder überschreiben.

Attempt-, Receipt-, Recovery- und Reassessment-IDs entstehen intern mit einem
kryptografisch sicheren opaken Generator.

Ihre Persistenzadapter stabilisieren die ID nur dann, wenn der jeweilige neue
Fakt tatsächlich angelegt wird. Bereits persistierte Fakten werden beim
erneuten Aufruf nicht ersetzt.

## Readiness und Composition

Die Datenbank-URL stammt ausschließlich aus ihrer privaten Datei. Der Operator
baut daraus genau eine Engine ohne Default- oder In-Memory-Fallback.

Vor Credential-Laden und Providerzugriff muss der bestehende Readiness-Probe
den exakten Migration-Head bestätigen. Der Operator migriert das Schema nicht.

Danach baut er genau eine LQ-269-Package-Index-Composition und übergibt Engine,
Provider, Artifact-Source, technische IDs und interne Generatoren an LQ-273.

Die LQ-273-Composition besitzt Engine und Providerclient. Teilweise aufgebaute
Ressourcen werden bei einem Fehler bestmöglich geschlossen.

## Genau eine Arbeitseinheit

Nach erfolgreichem Aufbau erfolgt exakt ein Aufruf von
`composition.worker.process(request)` innerhalb des Composition-Kontexts.

Es gibt keine Schleife, kein Polling und keinen automatischen Retry. Weitere
zulässige Zustandsübergänge erfordern einen neuen expliziten Prozessaufruf.

Der aktuelle persistente State-Lookup bindet Phase, Attempt und zulässigen
nächsten Schritt. Aktueller Authority-Entzug wirkt deshalb auf spätere Läufe.

## Normale Ausgaben

Ein normales Ergebnis erzeugt genau eine kompakte JSON-Zeile auf stdout mit
dem einzigen Feld `outcome`.

Die feste Abbildung lautet:

- `published`: Exit `0`;
- `published_reassessment_required`: Exit `6`;
- `not_published`: Exit `7`;
- `publication_conflict`: Exit `8`;
- `pending_reconciliation`: Exit `9`;
- `not_actionable`: Exit `5`.

Keine Ausgabe enthält IDs, Pfade, Hashes, Providerdetails oder Authority-Fakten.

## Fehlergrenze

Geschlossen abgelehnte Inhalte enden mit Exit `2` und ausschließlich:

```json
{"error":"release_publication_operator_input_rejected"}
```

Technische Nichtverfügbarkeit endet mit Exit `4` und ausschließlich:

```json
{"error":"release_publication_operator_unavailable"}
```

In Fehlerfällen bleibt stdout leer. Interne Exceptions, Datenbank-, Datei-,
Credential-, Provider- und Close-Details verlassen die Prozessgrenze nicht.

Reguläre Exceptions werden detailfrei vereinheitlicht; `BaseException` wird
nicht pauschal verschluckt.

## Besitz und Abschluss

Nach Übergabe an LQ-273 schließt deren Context Manager Client und Engine in
allen normalen, abgelehnten und technischen Pfaden.

Vor der Übergabe verbleibende Ressourcen werden im lokalen `finally`-Pfad
geschlossen. Der Operator schreibt, verschiebt oder löscht keine Eingabedatei.

Ein unklarer Providerausgang bleibt persistent `outcome_unknown`; der Operator
behauptet daraus weder Erfolg noch Abwesenheit.

## Bundle-Inventar

Der Console Entry Point ist additiv in `pyproject.toml` registriert.

Das versionierte operative Release-Bundle erwartet und prüft nun 15 Console
Entry Points. Bestehende Einträge und deren Vertragsprüfung bleiben erhalten.

Es gibt keine Service-Unit, Container-, Deployment- oder CI-Aktivierung.

## Bewusst unverändert

LQ-275 fügt keine Migration, Tabelle, SQL-, Port- oder Domainmodelländerung
hinzu. Der Head bleibt `20260819_0024` mit 24 linearen Migrationen.

Es entstehen keine HTTP-Route, Discovery-, Withdrawal-, Yank-, Delete- oder
Rollbackfunktion und kein echter Providerwrite in der Testsuite.

## Nachweis und Folgeordnung

Gezielte Tests belegen geschlossene Parser, private Dateiregeln, Handoff-
Bindung, Providergrenzen, alle sechs Outcomes und detailfreie Fehlerausgaben.

Die vollständige PostgreSQL-16-Pflichtsuite besteht mit:

```text
3346 passed, 581 warnings
```

LQ-276 sollte als nächsten getrennten Slice ein kontrolliertes manuelles
Runbook und einen End-to-End-Operator-Audit definieren, ohne Scheduler oder
automatische Production-Aktivierung einzuführen.
