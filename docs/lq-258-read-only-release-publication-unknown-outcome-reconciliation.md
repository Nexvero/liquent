# LQ-258 — Read-only Release Publication Unknown-Outcome Reconciliation

## Ergebnis

LQ-258 implementiert die verpflichtende read-only Reconciliation eines
möglichen externen Publication-Effekts.

Der Slice inspiziert ausschließlich Executions und Attempts im persistenten
Status `outcome_unknown`. Er unterscheidet bestätigten bytegleichen Erfolg,
bestätigte Abwesenheit, Konflikt und technisch weiterhin unbekannten Zustand.

Er lädt niemals erneut hoch und persistiert noch kein Receipt.

## Öffentliche Grenze

`reconcile_unknown_outcome` akzeptiert ausschließlich:

- bestehende Execution-ID;
- bestehende Attempt-ID.

Der Aufrufer liefert keine URL, Providerart, Zielbezeichnung, Hashwerte,
Observation, Rolle, Allow-Entscheidung oder Retry-Freigabe.

## Zulässiger Ausgangszustand

Die Reconciliation läuft nur für exakt passende Fakten:

- Execution `outcome_unknown`;
- Attempt `outcome_unknown`;
- Attempt-Nummer 1;
- keine Finish-Zeit;
- Attempt gehört zur Execution;
- Execution gehört zum Handoff;
- noch kein Receipt für den Handoff.

Andere oder unbekannte Zustände enden neutral vor Providerzugriff.

## Historisch gebundenes Ziel

Die externe Realität muss auch dann festgestellt werden können, wenn Authority
nach dem möglichen Write entzogen wurde.

Deshalb löst LQ-258 das Ziel aus der historischen Handoff-Bindung und der
damaligen Channel-Revision auf:

- Channel-ID und Revision;
- Providerart;
- kanonischer Zielname;
- Paketname;
- Paketversion;
- erwarteter Wheel-Hash.

Der Caller kann keinen Ersatzpfad oder anderen Provider vorgeben.

## Read-only Providergrenze

LQ-258 verwendet denselben schmalen `ReleasePublicationTargetInspector` wie
LQ-256.

Der Inspector besitzt keine Create-, Upload-, Delete-, Yank- oder
Overwrite-Methode.

Pro Aufruf wird das historisch gebundene Ziel höchstens einmal inspiziert.

## Geschlossene Ergebnisse

`ReleasePublicationReconciliationKind` besitzt exakt drei bestätigte Werte:

- `PUBLISHED_CONFIRMED`;
- `ABSENCE_CONFIRMED`;
- `CONFLICT`.

Technisch weiterhin unbekannt ist kein vierter positiver Wert, sondern
detailfreie technische Nichtverfügbarkeit. Der persistente Unknown-Zustand
bleibt dabei unverändert.

## Bytegleich veröffentlicht

`PUBLISHED_CONFIRMED` verlangt:

- extern tatsächlich sichtbar;
- exakt erwarteter Paketname;
- exakt erwartete Paketversion;
- exakt erwarteter Wheel-SHA-256.

Die Observation bindet zusätzlich kanonische externe Artefaktidentität und
unveränderliche Providerrevision.

Das Ergebnis ist noch kein Receipt. Erst ein atomarer persistenter Folgeslice
darf den externen Fakt abschließen.

## Bestätigte Abwesenheit

`None` vom kontrollierten Inspector bedeutet bestätigte Abwesenheit und wird
als `ABSENCE_CONFIRMED` dargestellt.

Dies löst in LQ-258 keinen Retry und keinen neuen Attempt aus.

Ein späterer Slice muss vor einem möglichen Attempt 2 Authority, Zielzustand,
Konkurrenz und Idempotenz erneut prüfen. Blindes Wiederholen bleibt verboten.

## Konflikt

Ein sichtbares Ziel mit abweichendem Wheel-Hash, Paketnamen oder Version ergibt
`CONFLICT`.

Eine Observation, die das erwartete Artefakt nicht als sichtbar bestätigt,
ist ebenfalls Konflikt und nicht Abwesenheit.

LQ-258 überschreibt, löscht oder verändert das externe Ziel nicht.

## Aktuelle Authority als Begleitfakt

Parallel zur historischen Zielauflösung prüft LQ-258 read-only, ob weiterhin
aktuell sind:

- Channel und exakte Revision;
- Publisher-Zuordnung;
- Registry-Policy;
- Signer;
- Signing-Key;
- Abwesenheit eines `pending` Reassessments.

Das Ergebnis wird als `current_authority` mitgeführt.

## Revocation verschweigt externe Realität nicht

Ist aktuelle Authority entzogen, wird die externe Inspektion trotzdem
ausgeführt.

Ein bytegleiches sichtbares Artefakt ergibt weiterhin
`PUBLISHED_CONFIRMED`, jedoch mit `current_authority=False`.

Damit kann der spätere persistente Abschluss den externen Fakt bewahren und
zugleich ein Security-Reassessment verlangen.

## Reconciled Outcome

`ReconciledReleasePublicationOutcome` bindet:

- Execution, Attempt und Handoff;
- geschlossene Reconciliation-Art;
- historisch kontrolliertes Ziel;
- aktuellen Authority-Status;
- bei vorhandenem Ziel die konkrete Observation.

Nur `ABSENCE_CONFIRMED` besitzt keine Observation.

Das Objekt ist ein kurzlebiger read-only Entscheidungsfakt und keine
Publication-Authority.

## Technisch weiterhin unbekannt

Timeout, Verbindungsabbruch, untypisierte Providerantwort oder anderer
technisch unklarer Read-Zustand wird detailfrei als
`ReleasePublicationReconciliationUnavailable` gemeldet.

Technische Unklarheit ist niemals bestätigte Abwesenheit, Konflikt oder Erfolg.

Der Fehler enthält keine URL, Providerantwort, IDs, Hashwerte, SQL-, Netzwerk-
oder Credentialdetails.

## Keine Mutation

LQ-258 ändert keine Datenbankzeile.

Execution und Attempt bleiben `outcome_unknown`; Finish-Zeit bleibt leer.

Es entstehen kein Receipt, keine Receipt-Reconciliation, kein Reassessment und
kein Attempt 2.

Auch das externe Ziel wird ausschließlich gelesen.

## Retry-Sicherheit

Wiederholte LQ-258-Aufrufe dürfen ausschließlich erneut inspizieren.

Sie rufen niemals den LQ-257-Creator auf und verwenden keine positive
Observation als Upload-Freigabe.

Damit bleibt ein unklarer externer Effekt bis zum kontrollierten persistenten
Abschluss sichtbar und fail-closed.

## Persistenz und Migrationen

LQ-258 liest die bestehenden LQ-249- und LQ-253-Fakten.

Es gibt keine Migration, Tabelle oder Schemaänderung. Head bleibt
`20260817_0022` mit 22 Migrationen.

## Nachweis

Tests belegen:

- bytegleich sichtbarer Effekt ergibt `PUBLISHED_CONFIRMED`;
- bestätigte Abwesenheit ergibt `ABSENCE_CONFIRMED` ohne Retry;
- abweichender Hash, Name, Version oder Sichtbarkeit ergibt `CONFLICT`;
- Revocation verhindert nicht die Feststellung externer Realität;
- Revocation wird als `current_authority=False` mitgeführt;
- Nicht-Unknown- und unbekannte Attempts erreichen den Provider nicht;
- Providerfehler bleiben technische Nichtverfügbarkeit;
- Execution, Attempt und Receipt-Bestand bleiben unverändert;
- dieselbe read-only Semantik auf echtem PostgreSQL 16.

Die vollständige Pflichtsuite mit PostgreSQL 16 besteht:

```text
3177 passed, 220 warnings
```

Der temporäre PostgreSQL-Cluster wurde kontrolliert gestoppt und entfernt.

## Bewusst nicht enthalten

LQ-258 implementiert keine Receipt-ID-Erzeugung, Receipt- oder Reconciliation-
Mutation, Reassessment-Erzeugung, Attempt-Finish-Zeit, Attempt 2, Retry-
Freigabe, Create, Upload, Withdrawal, CLI, Git- oder Deploymentaktion.

## Nächster Slice

LQ-259 sollte den atomaren persistenten Reconciliation-Abschluss
implementieren. Bytegleich veröffentlichte Realität muss als Receipt bewahrt
werden; bei inzwischen entzogener Authority muss gleichzeitig ein `pending`
Reassessment entstehen. Bestätigte Abwesenheit und Konflikt benötigen getrennte
fail-closed Abschluss- beziehungsweise Recovery-Regeln.
