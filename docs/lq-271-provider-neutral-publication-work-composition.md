# LQ-271 — Provider-neutral Publication Work Composition

## Ergebnis

LQ-271 implementiert die providerneutral testbare Einzelarbeits-Composition
für den in LQ-270 eingefrorenen Offline-Worker-Vertrag.

`ProcessReleasePublicationWork` führt genau eine geschlossene Publication-
Arbeitseinheit entlang der bereits vorhandenen persistenten Ports weiter.

Der Slice erzeugt keinen CLI-Befehl, keine Datenbankabfrage und keinen echten
Providerzugriff.

## Geschlossener Request

`ReleasePublicationWorkRequest` enthält ausschließlich:

- Execution-ID;
- Handoff-ID;
- Publisher-Authority-ID;
- Channel-ID;
- erwartete Channel-Policy-Revision.

Alle Felder verwenden bereits bestehende stabile interne ID-Typen und sind
`repr`-frei.

Der Request enthält keine Phase, Attempt-ID, Attempt-Nummer, Rolle, Allow-
Entscheidung, Providerkonfiguration, URL, Credential, Artefakte oder Hashes.

## Aktueller Zustand als Port

`ReleasePublicationWorkStateLookup` erhält den vollständigen geschlossenen
Request und bindet damit die aktuelle Execution an alle fünf Referenzen.

Der Port liefert neutral `None`, wenn noch keine passende Execution existiert.

Andernfalls liefert er genau einen typisierten Zustand:

- Attempt 1 vorbereitet;
- Attempt 1 unknown;
- Attempt-1-Abwesenheit abgeschlossen;
- Attempt 2 vorbereitet;
- Attempt 2 unknown;
- terminal.

Die Composition akzeptiert keinen freien Statusstring und kein caller-
geliefertes Zustandsobjekt.

## Strikte State-Bindung

Jeder nicht terminale Zustand muss genau eine persistiert aufgelöste Attempt-ID
tragen.

Ein terminaler Zustand trägt keine Attempt-ID und genau eine terminale
Ergebnisfamilie.

`pending_reconciliation` und `not_actionable` sind keine terminalen Fakten und
können deshalb nicht als terminaler State zurückgegeben werden.

Inkonsistente State-Objekte werden bereits im unveränderlichen Modell
abgelehnt.

## Initiale Arbeit

Liefert der State-Lookup `None`, ruft die Composition genau einmal den
bestehenden Attempt-1-Preflight mit allen fünf Requestreferenzen auf.

Ein neutrales Preflight-Ergebnis endet als `not_actionable` und erreicht
weder Creator noch Finalizer.

Ein typisierter vorbereiteter Attempt muss Attempt-Nummer 1 tragen. Andere
Resultate werden detailfrei als technische Nichtverfügbarkeit abgelehnt.

## Vorbereiteter Attempt 1

Für einen vorbereiteten Attempt 1 wird ausschließlich der bestehende
`ReleasePublicationImmutableCreate` aufgerufen.

Die Composition erzeugt keine neue Attempt-ID und führt keine eigene Target-
Inspection oder Artefaktprüfung aus; diese Verantwortlichkeiten verbleiben in
der geprüften Persistenzkette.

Ein neutrales Create-Ergebnis endet ohne Finalizer als `not_actionable`.

## Unknown Attempt 1

Ein bereits unbekannter Attempt 1 erreicht keinen Preflight und keinen
Creator.

Die Composition ruft ausschließlich den Current-Outcome-Finalizer mit der aus
dem System of Record gelieferten Attempt-ID auf.

Damit kann Prozesswiederaufnahme keinen ersten Upload wiederholen.

## Attempt-1-Abwesenheit

Nur der explizite persistente Zustand
`attempt_one_absence_recovered` erreicht den bestehenden Attempt-2-Preflight.

Die persistierte Attempt-1-ID wird als Recovery-Bindung übergeben.

Nur ein typisierter neuer Prepared-Attempt mit Attempt-Nummer 2 erreicht den
Retry-Creator.

Ein neutrales Ergebnis endet als `not_actionable`; die Composition konstruiert
keine eigene Retry-Berechtigung.

## Attempt 2

Ein vorbereiteter Attempt 2 erreicht ausschließlich
`ReleasePublicationRetryImmutableCreate`.

Ein Unknown-Attempt 2 erreicht ausschließlich den Current-Outcome-Finalizer.

Attempt 1 und Attempt 2 besitzen damit disjunkte Creatorpfade. Kein Aufruf kann
beide Creator erreichen.

Es gibt keinen Zustand und keinen Port für Attempt 3.

## Pending-Bindung

Ein Creator-Ergebnis muss exakt dieselbe Execution-, Attempt- und Handoff-ID
wie der vorbereitete Attempt tragen.

Abweichende, untypisierte oder inkonsistente Ergebnisse werden nicht
weiterverarbeitet.

Nur ein gültiges `ReleasePublicationWritePendingReconciliation` erreicht den
Finalizer.

Eine enthaltene Provider-Acknowledgement beeinflusst keine Ergebnisentscheidung
der Composition.

## Genau ein Outcome-Finalizer

`ReleasePublicationCurrentOutcomeFinalizer` ist die neue schmale Grenze für
genau eine aktuelle Providerinspektion und den dazu passenden persistenten
Abschluss.

Er liefert ausschließlich:

- `FinalizedReleasePublication`;
- `FinalizedReleasePublicationRecovery`;
- neutral `None` bei weiterhin ausstehendem oder nicht abschließbarem Zustand.

Die Composition ruft nicht nacheinander Success- und Recovery-Finalizer auf.
Dadurch entsteht keine doppelte Providerinspektion zur Auswahl des passenden
Abschlusses.

Die persistente Implementierung dieser Grenze bleibt LQ-272 vorbehalten.

## Ergebnisabbildung

Die Composition gibt ausschließlich `ReleasePublicationWorkResult` mit einer
begrenzten Familie zurück:

- bestätigter Receipt wird `published`;
- bestätigter Receipt nach Revocation wird
  `published_reassessment_required`;
- Attempt-2-Abwesenheit wird `not_published`;
- bestätigter Konflikt wird `publication_conflict`;
- noch nicht finalisierter Unknown-Zustand wird `pending_reconciliation`;
- neutrale Ablehnung oder retry-fähige Attempt-1-Abwesenheit wird
  `not_actionable`.

Receipt-, Recovery-, Reassessment-, Attempt- und Handoff-IDs werden nicht in
das Resultat übernommen.

## Terminale Wiederholung

Ein terminaler State wird direkt in dieselbe terminale Ergebnisfamilie
übersetzt.

Preflight, Creator und Finalizer werden dabei nicht aufgerufen.

Damit kann ein exakter späterer Worker-Aufruf den bekannten Abschluss
detailarm wiedergeben, ohne neuen Providerzugriff oder neue ID.

## Höchstens ein Create

Jeder `process`-Aufruf erreicht entweder:

- keinen Creator;
- den Attempt-1-Creator genau einmal; oder
- den Attempt-2-Creator genau einmal.

Es existiert kein Pfad vom Abschluss einer Attempt-1-Abwesenheit zum
Attempt-2-Preflight innerhalb desselben Aufrufs.

Ein weiterer Attempt benötigt einen späteren Aufruf und erneut aufgelösten
persistenten Zustand.

## Detailfreie technische Grenze

`ReleasePublicationWorkUnavailable` vereinheitlicht:

- untypisierte oder inkonsistente Portresultate;
- Fehler aus State-Lookup, Preflight, Creator oder Finalizer;
- ungültige Requesttypen;
- unzulässige State- und Attemptkombinationen.

Die Exception enthält nur den stabilen Fehlercode und keine IDs, Providertexte,
Hashes, Credentials oder Ursachen.

Fachlich neutrale `None`-Ergebnisse werden nicht in technische Fehler
umgewandelt.

## Keine Providerabhängigkeit

Das Application-Modul importiert keine Package-Index-, HTTP-, SQLAlchemy- oder
Dateisystemimplementierung.

Inspector und Creator werden ausschließlich hinter den bestehenden Ports
erreicht.

Die Tests verwenden einfache kontrollierte Portdoubles und führen weder
Netzwerk- noch Datenbankzugriffe aus.

## Bewusst nicht enthalten

LQ-271 ergänzt keine:

- persistente Work-State-Abfrage;
- atomare Current-Outcome-Finalizer-Implementierung;
- Engine-, Artifact- oder Package-Index-Composition;
- CLI-, Requestdatei- oder Exitcodeentscheidung;
- Scheduler-, Queue-, Daemon- oder Production-Aktivierung;
- Tabelle, SQL, Schema, Migration oder Seed;
- Provider-, Git- oder Deploymentmutation.

Der Migration-Head bleibt `20260819_0024` mit 24 Migrationen.

## Nachweis

Tests belegen:

- initialen Attempt-1-Pfad mit genau einem Create und einem Finalizer;
- Unknown-Wiederaufnahme ohne Creator;
- Attempt-1-Absence als einzige Attempt-2-Vorbereitung;
- vorbereiteten Attempt 2 ohne erneuten Preflight;
- disjunkte Creatorpfade;
- Published-, Reassessment-, Conflict- und Absence-Abbildung;
- terminalen Retry ohne weitere Abhängigkeit;
- neutrale Ablehnung vor Providerzugriff;
- detailfreie Ablehnung beschädigter Portresultate und Requests.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht mit 3320 Tests und
534 Warnungen.

LQ-272 implementiert als nächsten Slice den persistenten gebundenen Work-State-
Lookup und den atomaren Current-Outcome-Finalizer auf Basis der bestehenden
Reconciliation- und Abschlusslogik.
