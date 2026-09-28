# LQ-500 — Closed Cleanup Revision Mutation Commands, Results and Ports

## Ergebnis

LQ-500 implementiert die geschlossenen Commands, Resultate, den detailfreien
Mutationskonflikt und fünf minimale Ports aus dem LQ-499-Vertrag.

Der Slice implementiert keine Persistenz, Authorityauflösung oder physische
Cleanupwirkung.

## Eigenes Domainmodul

Die Mutationswerte liegen in
`manifest_handoff_supervisor_control_directory_cleanup_clearance_mutation.py`.

Sie erweitern die bestehenden read-only Clearancewerte, ohne deren Signaturen
zu verändern.

## Vier Change-IDs

Management, Hold, Recovery und Referenzen besitzen jeweils eine eigene stabile
nichtwiederverwendbare Change-ID.

Alle vier IDs sind repr-frei, nicht leer und ohne äußeren Whitespace.

Ihre Typen sind nicht austauschbar.

## Change-ID ist keine Revision-ID

Die Change-ID identifiziert den idempotenten Mutationsintent.

Die resultierende Revision-ID identifiziert den neuen dauerhaften Zustand.

Keine der beiden Identitäten wird aus Ziel, Status, Zeit oder Actor abgeleitet.

## Managementcommand

`ChangeManifestHandoffSupervisorControlDirectoryCleanupManagement` trägt:

- Management-Change-ID;
- internen Target-User;
- internen Handoffscope;
- optional erwartete aktuelle Managementrevision;
- den geschlossenen gewünschten Status Active oder Inactive.

Der Command trägt keinen aufrufenden Actor und keine Authoritybehauptung.

## Erwartete Managementrevision

`expected_revision_id=None` bezeichnet ausschließlich den erwarteten leeren
First-write-Zustand.

Eine vorhandene Quelle muss später mit ihrer exakten aktuellen Revision
gebunden werden.

Der Wert selbst erteilt keine Management-Lifecycle-Authority.

## Drei getrennte Zielcommands

Hold, Recovery und Referenzen besitzen je einen eigenen Commandtyp.

Jeder bindet seine eigene Change-ID, die interne Directory-ID, seine optional
erwartete typgleiche Vorgängerrevision und Clear oder Blocked.

Ein Holdcommand kann keine Recovery- oder Referenzrevision tragen.

## Kein Retired-Snapshot im Command

Die Zielcommands akzeptieren nur die stabile interne Directory-ID.

Der spätere Store muss den aktuellen vollständigen Retired-Wert selbst aus dem
System of Record rekonstruieren.

Handle, Leaf, Scope, Pfad und Lifecyclezeit sind keine Callerinputs.

## Kein Callerzeitpunkt

Kein Command enthält `resolved_at`, `decided_at` oder eine andere Zeit.

Sequenz, neue Revision-ID und UTC-Zeit bleiben Aufgaben der späteren
kontrollierten Persistenzgrenze.

Caller können keine Reihenfolge bestimmen.

## Geschlossene Resultate

Jede erfolgreiche Mutation liefert einen eigenen committed Resulttyp.

Das Result bindet die ursprüngliche typgleiche Change-ID an den vollständigen
persistierten Authority- oder Decisionwert.

Damit kann ein exakter Retry denselben fachlichen Wert zurückgeben.

## Managementresultat

Das Managementresultat bindet die Management-Change-ID an eine vollständige
`ManifestHandoffSupervisorControlDirectoryCleanupManagementAuthority`.

Target-User, Scope, Status, Revision und Zeit stammen damit aus dem committed
Domainwert.

Das Result ist kein übertragbares Authoritytoken.

## Zielresultate

Hold-, Recovery- und Referenzresultat binden jeweils ihre Change-ID an ihren
eigenen vollständigen Decisiontyp.

Die Decision enthält Revision, vollständiges Retired-Ziel, Disposition und
serverseitige Entscheidungszeit.

Cross-Source-Resultate scheitern an der Laufzeitvalidierung.

## Detailfreier Konflikt

`ManifestHandoffSupervisorControlDirectoryCleanupRevisionMutationConflict`
deckt verweigerte Authority, stale Vorgänger, ID-Kollision und inkompatiblen
Retry detailfrei ab.

Er trägt keine Felder und offenbart weder aktuelle Revision noch Zielbestand.

Technische Unverfügbarkeit bleibt an der bestehenden Persistenzgrenze getrennt.

## Principal außerhalb der Commands

Alle vier Mutationsports erhalten den `SessionPrincipal` als separates
Argument.

Der Principal identifiziert nur den authentifizierten Actor.

Er erteilt keine Management-, Hold-, Recovery- oder Referenzauthority.

## Management-Mutationsport

`AuthorizedManifestHandoffSupervisorControlDirectoryCleanupManagementMutation`
akzeptiert Principal und ausschließlich den Managementcommand.

Das Result ist committed Managementchange, detailfreier Mutationskonflikt oder
neutrales None.

Der Port akzeptiert keine Rolle oder Allowentscheidung.

## Hold-Mutationsport

Der Holdport akzeptiert ausschließlich Principal und Holdcommand.

Seine spätere Implementation muss die dedizierte Holdauthority aktuell
auflösen.

Cleanupmanagement allein darf diesen Port nicht autorisieren.

## Recovery-Mutationsport

Der Recoveryport verwendet ausschließlich den Recoverycommand und sein eigenes
Resultat.

Er akzeptiert keinen Journalterminal-Snapshot als Ersatz für
Recoveryauthority.

Blocked und Clear bleiben explizite geschlossene Intents.

## Referenz-Mutationsport

Der Referenzport akzeptiert ausschließlich den Referenzcommand.

Die spätere Implementation verantwortet die vollständige autoritative
Referenzprüfung.

Der Command enthält keine Caller-Liste angeblich fehlender Referenzen.

## Atomarer Clearance-Creation-Port

`AuthorizedManifestHandoffSupervisorControlDirectoryCleanupClearanceCreation`
akzeptiert nur Principal und den bestehenden geschlossenen Cleanuprequest.

Er liefert einen vollständigen
`ClearedManifestHandoffSupervisorControlDirectoryCleanup`, bestehenden
Cleanupkonflikt oder neutrales None.

## Keine Caller-Clearance-ID

Der Clearance-Creation-Port akzeptiert keine Clearance-ID, Revisionen,
Decision, Scope, Journal oder Evidence vom Caller.

Die spätere Composition erzeugt die Clearance-ID intern und liest sämtliche
Fakten aktuell aus ihren Systemen of Record.

Die Attempt-ID bleibt die Retryidentität des geschlossenen Requests.

## Principal-/Request-Bindung

Die spätere Implementation muss `principal.user_id` exakt an
`request.actor_user_id` binden.

Die Typen behaupten diese Authority nicht vorab.

Ein Actorwechsel bei gleicher Attempt-ID ist Konflikt.

## Atomarität bleibt Implementationspflicht

Der Portname öffnet nur die fachliche Creationgrenze.

Die spätere Persistenzimplementation muss Attempt und Clearance in derselben
serialisierten Transaktion erzeugen und alle aktuellen Revisionen erneut lesen.

Ein unabhängiger Aufruf des LQ-494-Startports erfüllt diesen Vertrag nicht.

## Neutrales None

None kann unbekannte Targets oder fehlende nichtoffenlegbare Authority an der
jeweiligen kontrollierten Grenze repräsentieren.

Es ist weder Clear noch erfolgreiche Mutation.

Der konkrete Store muss None, Konflikt und technische Unverfügbarkeit
konsistent mit LQ-499 unterscheiden.

## Keine generische Mutation

Es gibt keinen Port mit frei wählbarer Quellart, Tabelle oder Statuszeichenkette.

Vier getrennte Command- und Porttypen verhindern eine versehentliche
Authorityzusammenlegung.

Ein gemeinsamer Adapter darf sie später implementieren, nicht aber fachlich
vereinheitlichen.

## Keine Persistenceentscheidung

LQ-500 ergänzt keine Tabelle, Migration, Spalte, SQL oder Lockstrategie.

Revision 0036 und die 36 Migrationen bleiben unverändert.

Revision-ID- und Clearance-ID-Erzeugung werden noch nicht entschieden.

## Keine Datei oder Verdrahtung

Es gibt keinen Pfad, Dateinamen, Filesystemread, Unlink oder Rmdir.

Settings, Appfactory, CLI, Route, Operator, Compose und Deployment bleiben
unverändert.

Die Ports werden nicht automatisch aktiviert.

## Tests

Fokussierte Prüfungen belegen vier repr-freie Change-IDs, vier strikt typisierte
Commands, optionale typgleiche Vorgängerrevisionen, vier validierte committed
Resultate, den feldlosen Konflikt, Principaltrennung und fünf minimale Ports.

Sie belegen außerdem das Fehlen von SQL, Pfaden, Callerzeiten, Rollen,
Allowbooleans und Wiring.

## Nächster Slice

LQ-501 sollte die persistente append-only Mutations- und atomare
Attempt-/Clearanceimplementation gegen Revision 0036 entwerfen und umsetzen.

Production-Wiring und physischer Cleanup bleiben getrennt.
