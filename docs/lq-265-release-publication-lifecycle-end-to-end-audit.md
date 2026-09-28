# LQ-265 — Release Publication Lifecycle End-to-End Audit

## Ergebnis

LQ-265 auditiert den vollständigen persistenten Publication-Lebenszyklus von
Attempt 1 bis zum terminalen Abschluss von Attempt 2.

Der Audit bestätigt eine endliche, fail-closed Zustandsmaschine mit höchstens
zwei kontrollierten immutable Provider-Creates. Es wurde keine weitere
Produktmutation, Migration oder Runtime-Verdrahtung ergänzt.

## Auditumfang

Geprüft wurden gemeinsam:

- persistenter Handoff und Execution-Start;
- Attempt-1-Artefaktintegrität und Read-before-write;
- atomarer erster Write-Start und Unknown-Outcome-Sicherung;
- read-only Reconciliation und Absence-Recovery;
- frischer Attempt-2-Preflight;
- atomarer zweiter Write-Start mit eigener Idempotenzidentität;
- Attempt-2-Reconciliation;
- Published-, Absence- und Conflict-Abschluss;
- aktuelle Authority-Revocation;
- harte Grenze gegen Attempt 3;
- SQLite- und PostgreSQL-Verhalten.

## Unterstützte Zustandsfolge

Der vollständige erfolgreiche Zwei-Attempt-Pfad lautet:

```text
execution prepared
  -> attempt 1 prepared
  -> attempt 1 write_started
  -> execution + attempt 1 outcome_unknown
  -> attempt 1 absence_confirmed / reconciled
  -> execution prepared
  -> attempt 2 prepared
  -> attempt 2 write_started
  -> execution + attempt 2 outcome_unknown
  -> attempt 2 published_confirmed / reconciled
  -> execution published + receipt
```

Kein Übergang wird aus einer Provider-Acknowledgement allein abgeleitet.

## Genau zwei Create-Identitäten

Der End-to-End-Nachweis beobachtet genau zwei Creator-Aufrufe:

- Attempt 1 verwendet die stabile Execution-ID als historische LQ-257-
  Idempotenzidentität;
- Attempt 2 verwendet seine eigene stabile Attempt-ID.

Damit kollidieren beide erlaubten Create-Versuche nicht miteinander.
Wiederholungen eines bereits möglichen Effekts rufen den Creator nicht erneut
auf.

## Attempt-1-Abwesenheit als einzige Retry-Öffnung

Nur ein persistenter `absence_confirmed`-Abschluss für Attempt 1 kann den
Attempt-2-Preflight erreichen.

Vor Attempt 2 werden erneut geprüft:

- lokale Artefaktintegrität;
- aktuelle Registry-, Signer- und Key-Authority;
- aktueller Channel und Publisher;
- fehlendes Receipt und fehlendes `pending` Reassessment;
- erneut bestätigte externe Zielabwesenheit.

Der frühere Recovery-Boolean ist kein Write-Ticket.

## Published-Endzustand

Bestätigt der Read-back nach Attempt 2 ein bytegleich sichtbares Artefakt,
entstehen atomar:

- genau ein Receipt;
- genau eine Receipt-Reconciliation für Attempt 2;
- zwei historisch `reconciled` Attempts;
- Execution-Status `published`.

Nach Revocation bleibt der externe Fakt erhalten und endet stattdessen als
`published_reassessment_required` mit `pending` Reassessment.

## Terminale Abwesenheit

Bleibt das Ziel nach Attempt 2 bestätigt abwesend, endet die Execution als
`not_published`.

Der Audit bestätigt:

- beide Attempts sind `reconciled`;
- beide Recovery-Fakten bleiben getrennt erhalten;
- Attempt-2-`retry_eligible` ist immer falsch;
- es existieren genau zwei Attempts;
- ein weiterer Preflight erreicht weder Provider noch Generator;
- es entsteht kein Receipt, Reassessment oder Attempt 3.

## Terminaler Konflikt

Weicht der sichtbare externe Zustand nach Attempt 2 ab, endet die Execution
als `publication_conflict`.

Der Konflikt bewahrt externe Evidence und erzeugt genau ein `pending`
Reassessment. Er erzeugt weder Receipt noch Attempt 3 oder weiteren Create.

## Revocation vor Attempt-2-Write

Der Audit entzieht Registry-Key-Authority nach dem erfolgreichen
Attempt-2-Preflight, aber vor dessen Write-Start.

Die erneute Transaktionsprüfung sperrt den Create neutral. Der Inspector wird
nicht mehr aufgerufen, und die Creator-Aufrufzahl bleibt bei genau einem.

Damit ist ein früher positives Preflight-Ergebnis kein Grace-Ticket.

## Unknown-Outcome bleibt fail-closed

Für beide Attempts gilt dieselbe Sicherheitsregel:

Sobald `write_started` persistiert wurde, wird jeder positive Return, Timeout,
Verbindungsabbruch oder Prozessverlust als möglicher externer Effekt behandelt.

Ein Retry führt keinen weiteren Upload aus, sondern verlangt read-only
Reconciliation. Technische Unklarheit wird nie als bestätigte Abwesenheit
interpretiert.

## Keine Caller-Authority

Die gesamte Kette akzeptiert keine caller-gelieferten:

- Allow- oder Retry-Booleans;
- Rollen oder Publisherbehauptungen;
- Providerziele oder URLs;
- Hashwerte oder Artefaktbytes;
- Observations oder Receiptbehauptungen;
- Attempt-Nummern als Autorisierung.

Authority, Ziel, Payload und historischer Zustand stammen aus kontrollierten
Ports und dem System of Record.

## Konkurrenz- und Retry-Eigenschaften

Die Einzel-Slices und der integrierte PostgreSQL-Pfad bestätigen gemeinsam:

- atomarer Write-Start vor jedem Provideraufruf;
- keine offene Datenbanktransaktion während externer Calls;
- eindeutige Attempt-Nummern pro Execution;
- eindeutige Recovery-Fakten pro Execution und Attempt;
- höchstens ein Receipt pro Handoff;
- Wiederverwendung eines bestehenden `pending` Reassessments;
- exakte Retries ohne neue IDs oder externe Writes.

## Persistente Historie

Nach dem vollständigen Zwei-Attempt-Pfad bleiben beobachtbar:

- stabile Execution und Handoff;
- Attempt 1 und Attempt 2 mit getrennten IDs und Zeiten;
- Attempt-1-Recovery;
- optionaler Attempt-2-Recovery oder Receipt-Abschluss;
- externe Evidence bei Published oder Conflict;
- Reassessment-Bindung bei erforderlicher Security-Folgearbeit.

IDs und historische Entscheidungen werden nicht überschrieben oder
wiederverwendet.

## Runtime- und Operatorgrenze

LQ-265 fügt keinen Netzwerkprovider, Credential-Lookup, HTTP-Endpunkt,
Offline-Operator, CLI-Befehl oder Startup-Wiring hinzu.

Der Audit bestätigt die interne Persistenz- und Portkette. Eine kontrollierte
betriebliche Composition mit realem Provideradapter bleibt eine getrennte
Freigabeentscheidung.

## Migration und Bundle

Es gibt keine LQ-265-Migration.

Der einzige Head bleibt `20260819_0024`, und das LQ-236-Wheelgate erwartet
weiterhin 24 lineare Migrationen.

## Nachweis

Neue integrierte Tests belegen:

- vollständigen Zwei-Create-Published-Pfad mit genau einem Receipt;
- Attempt-2-Abwesenheit als terminal `not_published` ohne Attempt 3;
- Attempt-2-Konflikt als terminal `publication_conflict` mit Reassessment;
- Revocation zwischen Preflight und Write sperrt Attempt 2;
- unterschiedliche Idempotenzidentitäten für Attempt 1 und Attempt 2;
- genau zwei persistente Attempts in jedem abgeschlossenen Zwei-Attempt-Pfad;
- denselben vollständigen Published-Pfad auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3234 passed, 530 warnings
```

## Auditentscheidung

Der interne zweistufige Publication-Lebenszyklus ist vollständig und
fail-closed geschlossen.

Der nächste sinnvolle Slice LQ-266 entscheidet die kontrollierte betriebliche
Composition eines konkreten immutable Provideradapters einschließlich
Credential-Ownership, Prozessisolation und Aktivierungsgrenze. Diese
Entscheidung darf die geprüfte Zwei-Attempt-Grenze nicht erweitern.
