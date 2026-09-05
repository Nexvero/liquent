# LQ-437 — Manifest Handoff Composition Types and Closed Ports

## Ergebnis

LQ-437 konkretisiert LQ-436 mit geschlossener Scopebinding, Request-, Result-
und Konflikttypen sowie zwei minimalen Ports.

Der Slice implementiert weder Resolver noch Composer.

## Scopebinding

`ManifestHandoffScopeBinding` bindet unveränderlich:

- Registry-Scope-ID;
- absolute kontrollierte Sourcewurzel;
- absolute private Zielwurzel.

Beide Pfade sind aus `repr` ausgeschlossen.

Die Typvalidierung führt keinen Dateisystemzugriff aus.

## Lexikalische Trennung

Source und Ziel müssen bereits rein lexikalisch voneinander getrennt sein.

Gleiche Pfade sowie Source innerhalb Ziel oder Ziel innerhalb Source werden
abgelehnt.

Diese frühe Formprüfung ersetzt nicht die komponentenweise LQ-426-Prüfung auf
Existenz, Owner, Symlinks, echte Verzeichnisse und Zielmodus `0700`.

Pfadnormalisierung, Mountidentität und Inodes bleiben Aufgabe des direkten
Writeraufrufs.

## Keine Reassignmententscheidung

Der Typ trägt keine Revision, Statusänderung oder neue Zielauswahl.

Der spätere Resolver muss garantieren, dass derselbe Scope während seiner
Lebensdauer dieselbe Binding bezeichnet.

Umzug oder Ersatz benötigt einen neuen Scope; LQ-437 führt keinen
Lifecycleport ein.

## Compositionrequest

`ManifestHandoffCompositionRequest` enthält ausschließlich:

- stabile Reservierungs-ID;
- Actor-UserId aus authentifiziertem Kontext;
- Registry-Scope-ID;
- validierten Handoffnamen.

Reservierung, Actor und Scope bleiben repr-frei.

Der Request akzeptiert keine Source-/Zielwurzel, Attempt-/Observation-ID,
Outcome, Digest, Dateizahl, Allow-Entscheidung oder Authoritysnapshot.

## Sichtbare Ergebnisarten

`ManifestHandoffCompositionKind` ist auf zwei nicht technische Arten begrenzt:

- `manifest_handed_off`;
- `reconciliation_required`.

Neutrale Ablehnung bleibt `None`, und technische Unverfügbarkeit bleibt einer
späteren detailfreien Adapterfehlergrenze vorbehalten.

## Bestätigter Handoff

`ManifestHandoffCompositionResult` verlangt für `manifest_handed_off`:

- repr-freie Attempt-ID;
- finalen einfachen `.json`-Basename ohne Verzeichniskomponente;
- validierte repr-freie Manifestfakten.

Filename und Fakten müssen gemeinsam vorhanden sein.

`staging_authorized` und `commit_authorized` sind fest `false` und können beim
Aufbau nicht überschrieben werden.

## Reconciliation erforderlich

`reconciliation_required` trägt nur die repr-freie Attempt-ID.

Filename und Manifestfakten sind dabei verboten, weil der Dateizustand nicht
abschließend bestätigt ist.

Der Ausgang erlaubt keinen Writerretry, Cleanup oder andere Mutation.

## Detailfreier Compositionkonflikt

`ManifestHandoffCompositionConflict` ist ein leerer unveränderlicher Wert.

Der spätere Composer vereinheitlicht darin divergente Reservierungs- und
Observation-ID-Konflikte, ohne interne Binding oder gespeicherte Fakten
auszugeben.

## Binding-Lookupport

`ManifestHandoffScopeBindingLookup.get_binding(scope_id)` erhält nur die
stabile Scope-ID.

Er liefert genau eine aktive Binding oder neutral `None`.

Der Port akzeptiert keine Pfade, Actor-, Name-, Environment- oder
Fallbackwerte.

Mehrdeutige oder beschädigte Konfiguration bleibt technische
Unverfügbarkeit.

## Compositionport

`ControlledManifestHandoffComposition.handoff(request)` erhält genau den
geschlossenen Request.

Er liefert bestätigtes/reconciliation-required Result, detailfreien
Compositionkonflikt oder neutrales `None`.

Es gibt keine generische Outcome-, Pfad-, Callback- oder Dependencyeingabe.

## Observation-IDs

Observation-IDs sind bewusst weder Requestfeld noch Compositionportparameter.

Der spätere Composer erhält getrennte kontrollierte Factories als
Konstruktorabhängigkeiten und erzeugt IDs unmittelbar vor dem jeweiligen
Append.

Ein unklarer Append wird innerhalb desselben aktiven Aufrufs mit derselben ID
wiederholt.

Recovery nach Prozessverlust bleibt wegen des offenen Execution-Claim-Themas
separat.

## Authority

Der Requestactor identifiziert nur die anfragende Person.

LQ-432 und der LQ-435-Startappend lösen aktuelle User-, Scope- und
Scopeauthority aus dem Persistenzsystem auf.

Die Binding selbst enthält keine Authority und kann fehlende oder entzogene
Authority nicht ersetzen.

## Keine Dateisystemoberfläche

Die Ports enthalten `Path` ausschließlich im intern gelieferten Bindingwert.

Der Compositioncaller kann keinen Pfad wählen.

LQ-437 öffnet, erzeugt, schreibt, bindet, benennt oder löscht keine Datei.

## Migration und Wiring

Revision und Head bleiben `20260819_0028`; keine Tabelle oder Constraint wird
geändert.

Es gibt keinen Adapter, Bootstrap, Entry Point, Operator, CLI, Route, CI-,
Compose- oder Production-Wiring.

## Tests

Fokussierte Tests belegen:

- absolute und lexikalisch getrennte repr-freie Wurzeln;
- geschlossenen Request ohne Pfad-/Outcomeinjektion;
- exakte Ergebnis-Faktenmatrix;
- nicht überschreibbare Nichtautorisierungsflags;
- leeren Compositionkonflikt;
- minimale Portsignaturen;
- Roadmap- und Folgeslicebindung.

## Nichtziele

LQ-437 implementiert keinen Resolver, Composer, Execution-Claim, Recovery,
Writer-/Reconciliationwrapper, Cleanup, Scope-Bootstrap,
Bestandsverankerung oder Retentiondeleter.

Es wird kein echter Handoff ausgeführt und keine Datei verändert.

## Nächster Slice

LQ-438 sollte einen explizit injizierten statischen Scopebinding-Resolver
implementieren, ohne Environment-Discovery, Persistenzmutation oder
Production-Wiring.

Composer, Execution-Recovery, Bootstrap, Bestandsverankerung, Cleanup und
finale Evidence-Retention bleiben separat.
