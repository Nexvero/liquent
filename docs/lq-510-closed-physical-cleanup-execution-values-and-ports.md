# LQ-510 — Closed Physical Cleanup Execution Values and Ports

## Ergebnis

LQ-510 implementiert geschlossene Werte und vier minimale Ports für
Preflight, persistenten Write-Claim, einmalige physische Wirkung und read-only
Reconciliation des LQ-509-Vertrags.

Der Slice implementiert weder Persistenz noch Dateisystemzugriff.

## Stabile Preflight-ID

Die Preflight-ID ist eine stabile, nichtleere und repr-freie interne
Identität genau einer unmittelbar gelesenen Inventur.

Sie ist kein Pfad, kein Dateidescriptor und keine Authority.

Ein späterer Adapter erzeugt sie intern; Caller wählen sie nicht.

## Stabile Write-Claim-ID

Jeder dauerhafte Write-Claim besitzt eine eigene stabile, nichtleere und
repr-freie Identität.

Sie wird nicht aus Attempt, Directory, Actor oder Zeit abgeleitet.

Eine Claim-ID darf niemals für einen zweiten physischen Aufruf verwendet
werden.

## Preflightrequest

`PreflightManifestHandoffSupervisorControlDirectoryCleanup` trägt exakt die
interne Attempt-ID und Directory-ID.

Er enthält keinen Actor, Principal, Allowwert, Pfad, Leaf, Root,
Artefaktnamen oder Caller-Inventar.

Der spätere Preflight löst Attempt, Clearance, Authority, Retired-Ziel und
physische Fakten selbst aktuell auf.

## Prepared

Ein positiver Prepared-Wert bindet Preflight-ID, Attempt-ID, Directory-ID,
Clearance-ID und aware UTC Vorbereitungszeit.

Er veröffentlicht keine Inventur-, Pfad-, Descriptor-, Inode- oder
Artefaktdetails.

Prepared belegt nur eine erfolgreiche unmittelbare read-only Vorbereitung
und erteilt allein noch kein Recht auf Dateiwirkung.

## Sicher belegte Abwesenheit

Ein eigener Absent-Preflight-Wert bindet Attempt, Directory, aktuelle
Clearance und aware UTC Beobachtungszeit.

Er öffnet keinen Write-Claim und keine physische Operation.

Nur eine spätere kontrollierte Composition darf daraus den bestehenden
`already_absent`-Abschluss persistieren.

## Claimcommand

`ClaimPreparedManifestHandoffSupervisorControlDirectoryCleanup` trägt genau
einen vollständigen Prepared-Wert.

Es gibt kein `claim(bool)`, keine freie Claim-ID und keine separat
caller-gelieferte Clearance.

Der Command selbst ist keine Authority und darf nur intern komponiert werden.

## Claimed

Der geschlossene Claimed-Wert bindet die intern persistierte Claim-ID, den
vollständigen Prepared-Wert und eine monotone aware UTC Claimzeit.

Die Claimzeit darf nicht vor der Prepared-Zeit liegen.

Attempt-ID und Directory-ID werden ausschließlich aus Prepared projiziert und
nicht doppelt caller-geliefert.

## Letzte persistente Entscheidung

Der Write-Claim-Port muss später Attempt, aktuelle Clearance und exakten
Prepared-Bestand atomar revalidieren.

Nur der Übergang aus `started` in einen eigenen write-geclaimten Zustand darf
Claimed liefern.

Ein positiver Retry löst höchstens denselben bereits committierten Claim auf;
er erteilt niemals einen zweiten physischen Aufruf.

## Physischer Removed-Wert

`RemovedManifestHandoffSupervisorControlDirectory` bindet Claim-ID,
Attempt-ID, Directory-ID und aware UTC Bestätigungszeit.

Er behauptet bestätigte Leafabwesenheit nach vollständiger Wirkung und
Dauerhaftigkeit, aber noch keinen persistenten Completed-Übergang.

Er enthält weder Zahl noch Namen der entfernten Artefakte.

## Unbekannter physischer Effekt

Der geschlossene Unknown-Wert bindet ausschließlich Claim-ID, Attempt-ID und
Directory-ID.

Er behauptet weder Wirkung noch Nichtwirkung und autorisiert keinen Retry.

Timeout, Abbruch, partielle Wirkung und fehlende Dauerhaftigkeitsbestätigung
werden an dieser Grenze gleich behandelt.

## Reconciliationinspection

Der read-only Inspection-Wert bindet den vollständigen bestehenden
Reconciliationrequest, genau einen geschlossenen Ausgang und aware UTC
Inspektionszeit.

Seine Ausgänge bleiben exakt `absent`, `present` und `conflict`.

Er trägt keine Pfade, Namen, Dateifakten oder Reparaturanweisung.

## Preflight-Port

`ManifestHandoffSupervisorControlDirectoryCleanupPreflight` besitzt nur
`prepare_control_directory_cleanup`.

Er akzeptiert den minimalen Preflightrequest und liefert Prepared,
sicher belegte Abwesenheit, detailfreien Konflikt oder neutrales `None`.

Der Port besitzt keine Mutation und keinen frei wählbaren Inventoryinput.

## Write-Claim-Port

`ManifestHandoffSupervisorControlDirectoryCleanupWriteClaim` besitzt nur
`claim_control_directory_cleanup_write`.

Er akzeptiert ausschließlich den Prepared-gebundenen Claimcommand und liefert
Claimed, detailfreien Konflikt oder neutrales `None`.

Er führt selbst keine Dateioperation aus.

## Physischer Port

`ManifestHandoffSupervisorControlDirectoryPhysicalCleanup` besitzt nur
`remove_control_directory`.

Er akzeptiert ausschließlich den vollständigen Claimed-Wert und liefert
bestätigtes Removed, Unknown oder detailfreien Konflikt.

Neutrales `None` ist nach einem gültigen Claim nicht zulässig, weil jeder
Aufruf einen bestimmten oder unklaren Wirkungsausgang besitzen muss.

## Physischer Reconciliation-Port

`ManifestHandoffSupervisorControlDirectoryPhysicalCleanupReconciliation`
besitzt nur `inspect_control_directory_cleanup`.

Er akzeptiert ausschließlich den bestehenden Attempt-/Directory-gebundenen
Reconciliationrequest und liefert Inspection, Konflikt oder neutrales `None`.

Er entfernt, repariert oder erzeugt keine Datei und startet keinen Attempt.

## Keine freie Pfadoperation

Kein Wert und kein Port akzeptiert `Path`, Root, Leaf, Dateiname, Liste, Dict,
JSON, Rolle, Permission oder Allowboolean.

Es gibt kein rekursives Delete, Batch, Prune, TTL oder best-effort Cleanup.

Descriptor- und Artefaktbindung bleiben interne Pflichten des späteren lokalen
Adapters und werden nicht zur Calleroberfläche.

## Neutrale Abwesenheit und Konflikt

`None` bleibt ausschließlich autoritativer Unbekanntheit vor einer erwarteten
Bindung oder Wirkung vorbehalten.

Falscher Zustand, Cross-Binding, Widerruf, Drift und unsichere physische Fakten
liefern den bestehenden feldlosen detailarmen Cleanupkonflikt.

Unknown nach Claim bleibt davon getrennt und erzwingt Reconciliation.

## Technische Unverfügbarkeit

Infrastruktur- und unerwartete Plattformfehler bleiben an der bestehenden
detailfreien technischen Exceptiongrenze.

Sie werden weder als `None`, Konflikt, Removed noch Present normalisiert.

LQ-510 benennt keinen neuen Exceptiontyp.

## Repr und Validierung

Preflight-, Claim-, Attempt-, Clearance- und Directoryidentitäten bleiben
repr-frei.

Alle Zeiten müssen aware UTC sein; Claimzeit ist konstruktiv monoton zur
Prepared-Zeit.

Validierungsfehler nennen keine konkreten IDs oder physischen Details.

## Keine Implementation

Das neue Domainmodul importiert weder `Path` noch `os` und führt kein I/O aus.

LQ-510 ergänzt keine Tabelle, Migration, SQL, Zustandsmutation,
Dateisystemprimitive, Adaptercomposition oder Productionverdrahtung.

Head bleibt `20260826_0039` mit 39 linearen Migrationen.

## Tests

Fokussierte Prüfungen belegen zwei repr-freie IDs, minimale gebundene Requests,
Prepared/Absent/Claimed/Removed/Unknown/Inspection, monotone Zeiten, vier
minimale Ports und fehlende Pfad-, Persistenz- und Wiringmacht.

## Nächster Slice

LQ-511 sollte die persistente Write-Claim-Foundation und den atomaren
`started`-zu-write-geclaimt-Übergang ergänzen.

Lokaler Preflight, physische Wirkung, Reconciliation und Production-Wiring
bleiben danach getrennte Slices.
