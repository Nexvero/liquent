# LQ-254 — Persistent Release Publication Attempt Preflight

## Ergebnis

LQ-254 implementiert den persistenten, aktuellen Authority-Preflight vor dem
ersten externen Publication-Zugriff.

Der Slice erzeugt atomar genau eine vorbereitete Execution mit Attempt 1. Er
liest keine Artefaktdatei, kontaktiert keinen Provider und führt keinen Upload
aus.

## Kontrolliert gebundener Executor

Die `ReleasePublicationExecutorId` wird beim Aufbau des Adapters gebunden.

Ein Aufrufer kann deshalb weder einen anderen Executor vorgeben noch aus einer
Session, Produktrolle oder Publisher-ID Executor-Authority ableiten.

Die Executor-ID muss als bestehender interner Fakt registriert sein. Ihre
Existenz gewährt allein keine Publication-Berechtigung.

## Geschlossener Request

`prepare_attempt` akzeptiert ausschließlich:

- stabile Execution-ID;
- bestehenden Handoff;
- identifizierte Publisher-Authority;
- Zielchannel;
- exakt erwartete Channel-Policy-Revision.

Der Request enthält keinen Allow-Wert, keine Rolle, keine URL, keinen
Providernamen, keine Credentials, keine Artefaktbytes und keine
Hashüberschreibung.

## Persistente System-of-Record-Auflösung

Der Preflight löst innerhalb einer Transaktion aktuell auf:

- den unveränderten Handoff;
- den kontrolliert gebundenen Executor;
- den aktuellen Channel und seine Revision;
- den für diese Revision aktiven Publisher;
- die aktuelle Release-Registry;
- den aktuell aktiven Signer;
- den aktuell aktiven Signing-Key;
- vorhandene Receipts;
- offene Reassessments;
- bestehende Executions und Attempts.

Caller-gelieferte Authority-Snapshots werden nicht akzeptiert.

## Aktuelle Release-Authority

Der im Handoff gebundene Signer und Key müssen in der aktuellen Registry
weiterhin aktiv sein. Auch die aktuelle Registry-Policy muss aktiv sein.

Der historische Handoff bleibt erhalten, wenn sich die Registry inzwischen
geändert hat. Er berechtigt aber nur dann zu einem neuen Attempt, wenn seine
Signer-/Key-Bindung in der aktuellen Revision noch aktiv ist.

Revocation, Expiry, Deaktivierung oder fehlende aktuelle Membership sperren
den neuen Attempt fail-closed.

## Aktueller Channel und Publisher

Der Handoff muss weiterhin auf den aktuellen Channel zeigen. Die erwartete
Revision muss exakt der aktuell aktiven Channel-Revision entsprechen.

Artifact-Class und Paketname bleiben `operational_bundle` und `liquent`.

Der im Handoff gebundene Publisher muss in genau dieser Revision aktuell aktiv
sein. Publisher-ID oder Executor-ID werden nicht als Ersatz für diese aktuelle
Zuordnung verwendet.

## Hashbindung

Bundle-, Wheel-, Checksum-, Signatur- und Promotion-Evidence-Hash werden aus
dem persistenten Handoff gelesen.

Alle fünf Werte müssen kanonische kleingeschriebene SHA-256-Hexwerte sein.
Beschädigte Persistenz ist keine fachliche Ablehnung, sondern detailfreie
technische Nichtverfügbarkeit.

Execution und Attempt referenzieren den unveränderlichen Handoff. Zusätzlich
kopiert die Execution Bundle- und Signaturhash als schnelle normative
Kontrollbindung.

LQ-254 liest noch keine Bytes und behauptet deshalb keine erneute
Artefaktintegritätsprüfung. Diese bleibt vor einem späteren Provider-Write
verpflichtend.

## Sperrende Fakten

Ein bestehendes Receipt sperrt einen neuen write-fähigen Preflight für denselben
Handoff.

Ein `pending` Reassessment sperrt ihn ebenfalls. `reassess` und `withdraw`
werden nicht als Publication-Freigabe interpretiert.

Receipt und Reassessment werden weder geändert noch gelöscht.

## Atomare Erzeugung

Bei vollständig aktueller Authority erzeugt dieselbe Transaktion:

- eine Execution im Status `prepared`;
- Attempt 1 im Status `prepared`;
- dieselbe UTC-Startzeit für beide Fakten.

Ohne erfolgreichen Commit wird kein vorbereiteter Attempt zurückgegeben.

Es entsteht kein Receipt, kein Reassessment und kein Providerfakt.

## Konkurrenz

Auf PostgreSQL sperrt der Preflight die beteiligten Registry-, Channel-,
Handoff-, Receipt-, Reassessment-, Execution- und Attempt-Inventare in einer
kurzen Control-Plane-Transaktion.

Die Transaktion endet vor jedem späteren Datei- oder Netzwerkzugriff.

Die eindeutige Handoff-Execution-Bindung und Attempt-Nummer verhindern zwei
normative erste Attempts für denselben Handoff.

## Exakter Retry

Dieselbe Execution-ID mit exakt derselben Handoff-, Executor-, Publisher- und
Channel-Bindung liefert den bereits persistierten vorbereiteten Attempt 1.

Der Retry erzeugt keine neue Attempt-ID, liest keinen Provider und schreibt
keine zweite Zeile.

Eine bereits committete Entscheidung bleibt historisch abrufbar. Das ist keine
neue Publication-Authority und startet keinen externen Effekt.

## Konflikte

Wird dieselbe Execution-ID mit abweichender Bindung wiederverwendet, entsteht
ein detailarmer `ReleasePublicationAttemptConflict`.

Eine andere Execution-ID für einen bereits gebundenen Handoff ist ebenfalls
ein Konflikt. Bestehende Fakten werden nicht überschrieben.

Der Fehler trägt keine IDs, Hashes, Tabellen-, SQL- oder Providerdetails.

## Neutrale Ablehnung

`None` deckt insbesondere ab:

- unbekannten oder nicht bereiten Handoff;
- unbekannten Executor;
- stale oder inaktiven Channel;
- inaktiven Publisher;
- inaktive aktuelle Registry-Policy;
- inaktiven, abgelaufenen oder widerrufenen Key;
- inaktiven Signer;
- vorhandenes Receipt;
- offenes Reassessment.

Diese Fälle geben nicht preis, welcher Fakt fehlt oder gesperrt ist.

## Technische Nichtverfügbarkeit

`ReleasePublicationAttemptUnavailable` bleibt detailfrei getrennt von
neutraler Ablehnung und Konflikt.

Sie umfasst unter anderem unbenutzbare Eingabetypen, beschädigte persistente
Hashes, inkonsistente Retry-Fakten, eine unbenutzbare Clock, eine ungültige
generierte Attempt-ID und nicht sicher abschließbare Datenbanktransaktionen.

## Port und Adapter

`ReleasePublicationAttemptPreflight` beschreibt die schmale Anwendungsgrenze.

`DatabaseReleasePublicationAttemptPreflight` implementiert sie für SQLite und
PostgreSQL. Der Adapter besitzt nur Engine, gebundene Executor-ID,
Attempt-ID-Generator und Clock.

Er besitzt keine Artifact Source, keinen HTTP-Client und keinen
Provideradapter.

## Schema und Migrationen

LQ-254 verwendet ausschließlich die leeren LQ-253-Inventare.

Es gibt keine Migration, keine Tabelle, keinen Seed und keine Änderung am
LQ-236-Bundleformat. Head bleibt `20260817_0022` mit 22 Migrationen.

## Nachweis

Tests belegen:

- atomare Erzeugung genau einer Execution und eines Attempts;
- exakten Retry ohne neue ID-Erzeugung;
- Konflikt bei abweichender Execution- oder Handoff-Wiederverwendung;
- fail-closed Verhalten bei Publisher-, Channel-, Signer- und Key-Entzug;
- Sperre durch offenes Reassessment;
- technische Behandlung beschädigter Hashpersistenz;
- dieselbe Commit-Semantik auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3140 passed, 88 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-254 implementiert keine Artifact Source, Dateiauflösung, erneute
Byte-Hashprüfung, Providerinspektion, Read-before-write, Upload,
Write-Started-Transition, Unknown Outcome, Reconciliation, Receipt-Erzeugung,
Reassessment-Erzeugung, CLI, Credentials, Git- oder Deploymentaktion.

## Nächster Slice

LQ-255 sollte die kontrollierte unveränderliche Artifact Source und den
bytegenauen Pre-Provider-Integrity-Check implementieren. Sie muss ausschließlich
die Handoff-Bindung auflösen und darf weiterhin keinen Provider-Write ausführen.
