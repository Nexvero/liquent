# LQ-503 — Closed Cleanup Mutation Authority Values and Ports

## Ergebnis

LQ-503 implementiert die geschlossenen Authority-Set-, Lifecycle-, Bootstrap-
und Recoverywerte sowie die minimalen Ports aus LQ-502.

Der Slice implementiert keine Persistenz, SQL, Operatoren oder
Revisionsmutation.

## Eigenes Authoritymodul

Alle neuen Werte liegen in
`manifest_handoff_supervisor_cleanup_mutation_authority.py`.

Das Modul ist von den fachlichen Cleanup-Revisionscommands aus LQ-500 getrennt.

Authority-Lifecycle und Quellmutation bleiben unterschiedliche Typgrenzen.

## Sechzehn stabile IDs

Jede der vier Authority-Domänen besitzt eigene Typen für:

- Authority-Set-Revision;
- Lifecycle-Change;
- Bootstrapentscheidung;
- Recoveryentscheidung.

Damit entstehen sechzehn nicht austauschbare ID-Typen.

## Repr und Validierung

Alle IDs tragen einen repr-freien Stringwert.

Leere oder außen mit Whitespace versehene Werte sind ungültig.

Validierungsfehler geben keinen konkreten Identifier wieder.

## Gemeinsamer geschlossener Status

Authority-Mitglieder verwenden ausschließlich `active` oder `inactive`.

Der Status ist kein freier Rollen- oder Permissionstring.

Ein Member bindet genau einen nichtleeren internen User an einen Status.

## Geschlossene Lifecycle-Intents

Regulärer Lifecycle kennt ausschließlich `grant`, `deactivate` und
`reactivate`.

Es gibt kein Upsert, Delete, Transfer oder frei benanntes Intent.

Die Werte führen selbst keine Transition aus.

## Vier vollständige Settypen

Management, Hold, Recovery und Referenzen besitzen jeweils einen eigenen
Authority-Set-Typ.

Jeder Setwert bindet seine eigene Revisions-ID, einen Handoffscope und einen
vollständigen frozenset von Authority-Mitgliedern.

Settypen und Revisions-IDs sind nicht quellenübergreifend austauschbar.

## Set-Invarianten

Ein Set muss mindestens ein Mitglied enthalten.

Jede User-ID darf höchstens einmal vorkommen.

Mindestens eine Zuordnung muss Active sein, damit ein regulär erzeugter Setwert
keinen Lockout konstruiert.

## Effektive Authority

Ein Active-Member im Domainwert allein behauptet noch keine effektive
Authority.

Der spätere persistente Lookup muss zusätzlich aktuellen User-, Scope- und
Current-Pointer-Status prüfen.

Die Setprojektion ist kein übertragbares Token.

## Vier Lifecycle-Commands

Jede Domäne besitzt einen eigenen Changecommand aus:

- domänenspezifischer Lifecycle-Change-ID;
- Target-User-ID;
- Handoffscope-ID;
- exakt erwarteter domänenspezifischer Set-Revision;
- geschlossenem Intent.

Der Principal ist kein Feld des Commands.

## Principaltrennung

Die vier regulären Lifecycle-Ports erhalten den `SessionPrincipal` separat.

Er identifiziert nur den handelnden Actor.

Die spätere Implementation muss dessen aktuelle Authority derselben Domäne und
desselben Scopes atomar auflösen.

## Vier Bootstrap-Commands

Jede Domäne besitzt einen eigenen Bootstrapcommand aus Bootstrap-ID,
Target-User-ID und Scope-ID.

Es gibt keine erwartete Vorgängerrevision, weil Bootstrap ausschließlich leere
Historie adressiert.

Der Command selbst ist kein Bootstrap-Credential.

## Kontrollierte Bootstrap-Ports

Die vier Bootstrap-Ports sind domänenspezifisch und liefern ihren jeweiligen
ersten vollständigen Setwert oder neutrales None.

Sie dürfen später nur hinter einer separaten kontrollierten Bootstrapgrenze
erreichbar sein.

Ihre bloße Python-Erreichbarkeit autorisiert keinen Productionbootstrap.

## Vier Recovery-Commands

Jeder Recoverycommand bindet eigene Recovery-ID, historisch autorisierten
Target-User, Scope und exakt erwartete typgleiche Set-Revision.

Er enthält keinen neuen Userstatus, Authoritysatz oder Recovery-Allowwert.

Die Values prüfen Form, nicht historische Eligibility.

## Offline-Recovery-Ports

Recovery besitzt vier eigene Ports ohne `SessionPrincipal`.

Damit wird eine gewöhnliche Browsersession nicht als Recoverycredential
missverstanden.

Die spätere Implementation benötigt weiterhin die kontrollierte owner-only
Offlinegrenze aus LQ-502.

## Vier Authority-Lookups

Für jede Domäne existiert ein eigener read-only Lookup aus Principal und
Handoffscope.

Er liefert ausschließlich ein serverseitig bestimmtes Bool-Ergebnis.

`False` umfasst neutral Abwesenheit, Inaktivität und Entzug; technische
Unverfügbarkeit bleibt separat.

## Kein caller-supplied Bool

Das Bool ist ein Resultat des Authority-Lookups und niemals Eingabe eines
Mutationsports.

Die LQ-500-Ports akzeptieren weiterhin nur Principal und typisierten Command.

Ein vorheriges True darf den atomaren Current-State-Check im späteren Store
nicht ersetzen.

## Lifecycle-Ergebnisse

Ein erfolgreicher Lifecycle-Port liefert den vollständigen neuen
domänenspezifischen Setwert.

Der Command trägt seine Change-ID für persistente Retrybindung.

Stale, verweigerte, lockoutgefährdende oder inkompatible Änderungen liefern den
gemeinsamen feldlosen Authoritykonflikt oder neutrales None gemäß späterer
Grenze.

## Bootstrap-Ergebnisse

Ein erfolgreicher Bootstrap liefert den ersten vollständigen Setwert seiner
Domäne und seines Scopes.

Die Bootstrap-ID bleibt im Command für die spätere persistente
Entscheidungsbindung erhalten.

Ein vorhandener Bestand darf kein zweites Set erzeugen.

## Recovery-Ergebnisse

Ein erfolgreicher Recoveryport liefert den neuen vollständigen Setwert.

Recovery-ID und erwartete Revision bleiben im Command gebunden.

Die spätere Persistenz muss exakte Retries vor aktueller Eligibility erneut
auflösen können.

## Detailfreier Authoritykonflikt

`ManifestHandoffSupervisorCleanupMutationAuthorityConflict` besitzt keine
Felder.

Er verrät weder User, Scope, Domain, Setrevision noch Setbestand.

Technische Unverfügbarkeit verwendet weiterhin die bestehende
Persistenzfehlergrenze.

## Keine generische Domainauswahl

Es gibt kein Authority-Kind-Enum und keinen Port mit frei wählbarer Quellart.

Gemeinsam sind nur Status, Lifecycle-Intent, Memberform und interne
Validierungshelfer.

IDs, Setwerte, Commands und Ports bleiben domänenspezifisch.

## Keine Caller-Snapshots

Fachliche LQ-500-Mutationsports akzeptieren keinen Setwert oder Lookup-Bool.

Der spätere Store liest Current-Pointer, Members, User und Scope innerhalb der
Schreibtransaktion erneut.

Ein Setwert dient Ausgabe, Audit und geschlossener Rekonstruktion.

## Keine Persistenzentscheidung

LQ-503 ergänzt keine Tabelle, Migration, Spalte, SQL, Pointer- oder
Lockstrategie.

Head und Migrationsanzahl bleiben `20260826_0037` und 37.

ID- und Zeitgenerierung bleiben dem Persistenzslice vorbehalten.

## Keine Datei oder Verdrahtung

Es gibt keine Pfade, Dateinamen, Filesystemoperationen oder physische
Cleanupwirkung.

CLI, Route, Settings, Appfactory, Compose und Deployment bleiben unverändert.

Kein Port wird automatisch aktiviert.

## Tests

Fokussierte Prüfungen belegen sechzehn getrennte repr-freie IDs, geschlossene
Status und Intents, vier Settypen mit Lockout-Invarianten, vier Lifecycle-, vier
Bootstrap- und vier Recoverycommands sowie sechzehn getrennte Ports.

Sie belegen außerdem Principaltrennung, feldlosen Konflikt und das Fehlen von
Schema-, Datei- und Wiringentscheidungen.

## Nächster Slice

LQ-504 sollte die additive persistente Foundation für vier Authority-Set-
Inventare, Current-Pointer, Mitglieder sowie Bootstrap-, Lifecycle- und
Recoveryentscheidungen ergänzen.

Autorisierter Revisionsadapter und physischer Cleanup folgen getrennt.
