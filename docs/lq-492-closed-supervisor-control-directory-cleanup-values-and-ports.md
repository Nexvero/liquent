# LQ-492 — Closed Supervisor Control-Directory Cleanup Values and Ports

## Ergebnis

LQ-492 implementiert geschlossene Entscheidungs-, Request-, Ergebnis- und
Reconciliationwerte sowie drei minimale Ports für den LQ-491-Vertrag.

Der Slice implementiert keine Persistenz oder Dateisystemlöschung.

## Stabile Cleanup-Attempt-ID

`ManifestHandoffSupervisorControlDirectoryCleanupAttemptId` ist eine stabile,
repr-freie und nichtleere interne Identität eines Cleanupversuchs.

Sie wird nicht aus Directory-ID, Actor, Zeit, Leaf oder Pfad abgeleitet.

Ein Retry und seine Reconciliation verwenden exakt dieselbe Attempt-ID.

## Retention-Decision-ID

Die Retentionentscheidung besitzt eine eigene stabile repr-freie ID.

Sie ist weder Cleanup-Attempt noch Authorityentscheidung.

Caller können sie nicht als Allowboolean interpretieren.

## Policyrevision

Eine separate stabile Policyrevision bindet die fachliche Retentiongrundlage.

Der Wert enthält keine lokale Fristberechnung.

LQ-492 legt keine Dauer oder Policysemantik fest.

## Geschlossene Disposition

Die Retentiondisposition besitzt exakt `retain` und `eligible`.

Freie Strings, Wahrheitswerte und Rollen sind ausgeschlossen.

`eligible` ist nur ein aktueller Retentionfakt und keine Actorauthority.

## Cleanupentscheidung

Die geschlossene Cleanupentscheidung bindet den vollständigen Retired-Wert,
Decision-ID, Policyrevision, Disposition und aware UTC Entscheidungszeit.

Ihre Zeit darf nicht vor der dauerhaften Retirementzeit liegen.

Directory-ID, Handle und Leaf stammen ausschließlich aus Retired.

## Kein Active oder Reserved

Die Entscheidung kann konstruktiv nur einen exakten
`RetiredManifestHandoffSupervisorControlDirectory` tragen.

Reserved, Active oder freie Lifecycleprojektionen sind unzulässig.

Die Entscheidung führt selbst keine Mutation aus.

## Cleanuprequest

`CleanupManifestHandoffSupervisorControlDirectory` bindet genau Attempt-ID,
Actor-User-ID und interne Directory-ID.

Der Actor wird identifiziert, aber noch nicht autorisiert.

Der Request enthält kein Leaf, Root, Handle, Path, Retentionobjekt, Rolle,
Permission oder Allowboolean.

## Warum keine Entscheidung im Request liegt

Ein früherer `eligible`-Wert darf nicht als Mutationsauthority weitergereicht
werden.

Die spätere Execution muss Registry, Actor-Authority, Retention, Hold,
Recovery, Referenzen und physische Fakten aktuell selbst auflösen.

Widerruf bleibt dadurch für spätere Entscheidungen wirksam.

## Geschlossene Cleanupausgänge

Ein dauerhafter erfolgreicher Abschluss besitzt exakt `removed` oder
`already_absent`.

`removed` behauptet die vollständig belegte geordnete Entfernung.

`already_absent` behauptet nur autoritativ reconcilierten physischen
Nichtbestand eines weiterhin persistenten Retired-Tombstones.

## Completed-Wert

Completed bindet Attempt-ID, Directory-ID, geschlossenen Ausgang und aware UTC
Abschlusszeit.

Er enthält weder Pfad, Leaf, Dateinamen, Anzahl noch interne Fehlerdetails.

Completed erteilt keine Wiederverwendung oder weitere Cleanupauthority.

## Unklare Wirkung

Ein technischer Fehler nach möglicherweise wirksamer Mutation wird als
`ManifestHandoffSupervisorControlDirectoryCleanupReconciliationRequired`
gebunden.

Der Wert trägt ausschließlich dieselbe Attempt-ID und Directory-ID.

Er behauptet weder Erfolg noch Nichtwirkung und autorisiert keinen blinden
Retry.

## Reconciliationrequest

Reconciliation akzeptiert ausschließlich Attempt-ID und Directory-ID.

Caller liefern keinen erwarteten Ausgang oder physischen Status.

Der spätere Adapter liest Registry- und Dateisystemfakten ausschließlich
read-only neu.

## Reconciliationausgänge

Die geschlossene Reconciliation besitzt exakt `absent`, `present` und
`conflict`.

`absent` und `present` sind aktuelle physische Klassifikationen, keine neue
Mutation.

`conflict` fasst partielle, unbekannte oder unsichere Fakten detailfrei
zusammen.

## Reconciled-Wert

Reconciled bindet Attempt-ID, Directory-ID, geschlossenen Ausgang und aware
UTC Reconciliationzeit.

Er enthält keine Inventur- oder Pfaddetails.

Nur eine spätere kontrollierte Composition darf aus dem Ergebnis einen neuen
fachlichen Schritt ableiten.

## Cleanupkonflikt

`ManifestHandoffSupervisorControlDirectoryCleanupConflict` ist feldlos und
detailfrei.

Er vereinheitlicht verweigerte, retained, divergente oder unsichere
Voraussetzungen ohne interne Ursache.

Er ist kein technischer Exceptiontyp.

## Decision-Lookupport

Der read-only Decision-Port löst ausschließlich nach interner Directory-ID
auf.

Er liefert den aktuellen geschlossenen Entscheid oder neutral `None` für
autoritative Unbekanntheit.

Er besitzt keine Listen-, Mutations-, Policy- oder Authoritymethode.

## Execution-Port

Der Mutationsport besitzt genau `cleanup_control_directory`.

Er akzeptiert ausschließlich den geschlossenen Cleanuprequest.

Er liefert Completed, Reconciliation-required, detailfreien Konflikt oder
neutral `None` ausschließlich vor erwarteter Bindung und Wirkung.

## Reconciliation-Port

Der read-only Reconciliation-Port besitzt genau
`reconcile_control_directory_cleanup`.

Er liefert Reconciled, detailfreien Konflikt oder neutral `None` für eine
autoritativ unbekannte Attemptbindung.

Er darf keine Datei entfernen oder einen zweiten Attempt erzeugen.

## Keine freie Cleanupoperation

Es gibt kein `delete(path)`, `remove(leaf)`, `cleanup(bool)` oder
`set_disposition`.

Kein Port akzeptiert Dict, JSON, Root, Path, Dateinamen oder freien Status.

Batch-, List-, TTL-, Prune- und Rekursionsmethoden fehlen.

## Technische Unverfügbarkeit

Technische Fehler bleiben an der bestehenden detailfreien Exceptiongrenze.

LQ-492 benennt keinen neuen technischen Exceptiontyp.

Konflikt, neutrale Abwesenheit und technische Unverfügbarkeit bleiben
getrennt.

## Repr und Fehler

Attempt-, Decision-, Policy-, User- und Directoryidentitäten bleiben repr-frei.

Validierungsfehler nennen keine konkreten Werte.

Ergebniswerte tragen keine sensitiven Infrastrukturdetails.

## Keine Dateisystemimplementation

Das neue Domainmodul importiert weder `Path` noch `os`.

Es öffnet, inventarisiert, synchronisiert oder entfernt keine Datei.

Die Ports behaupten keine physische Wirkung ohne spätere Implementation.

## Keine Persistenz

LQ-492 ergänzt keine Tabelle, SQL, Migration, Retentionquelle, Holdsystem oder
Attempt-Registry.

Head bleibt `20260825_0034` mit 34 linearen Migrationen.

Nichtwiederverwendung und durable Attemptbindung folgen in einer separaten
Foundation.

## Kein Wiring

Service-Facade, Settings, Appfactory, CLI, Route, Compose, Environment und
Deployment bleiben unverändert.

Productioncleanup bleibt geschlossen.

## Tests

Fokussierte Prüfungen belegen repr-freie IDs, Retired-gebundene Entscheidung,
zwei Dispositionen, minimalen actor-identifizierenden Request, zwei
Completed-Ausgänge, gebundene unklare Wirkung, drei read-only
Reconciliationausgänge, feldlosen Konflikt, drei minimale Ports und fehlende
Datei-/Persistenz-/Wiringmacht.

## Nächster Slice

LQ-493 sollte die persistente Cleanup-Attempt- und Decision-Foundation mit
nicht wiederverwendbaren IDs und unknown-outcome-Reconciliationbindung
definieren.

Resolver, Dateisystemlöschung und Production-Wiring folgen getrennt.
