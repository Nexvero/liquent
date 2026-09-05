# LQ-340 — Read-only Runtime Cleanup Claim Reconciliation Contract

## Zweck

LQ-340 definiert die strikt read-only Reconciliation eines offenen
LQ-339-Cleanup-Claims nach unbekanntem `runtime_only`-Ausgang.

Sie klassifiziert den aktuellen Teilzustand von Container, Runnetzen und
erhaltenem Datenvolume. Dieser Slice implementiert keinen Command,
Dockerzugriff, Claim-, Evidence- oder Ressourcenwrite.

## Separate Reconciliation-Autorisierung

Die ursprüngliche Cleanup-Autorisierung gewährt keine zeitlich unbegrenzte
Reconciliation-Autorität.

Ein späterer Inspector benötigt eine neue private owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Cleanup-Reconciliation-ID.

Sie muss mindestens geschlossen binden:

- Cleanup-Reconciliation-ID und ursprüngliche Cleanup-ID;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, Application-Image-Digest und Compose-SHA-256;
- Reconciliation-, Claim-Reconciliation- und Disposition-ID;
- alle in LQ-339 gebundenen Autorisierungs- und Evidencehashes;
- Operation exakt `inspect_disposable_postgres_runtime_cleanup`;
- Scope exakt `runtime_only`;
- neue getrennte Executor- und Autorisiereridentitäten;
- aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Ressourcennamen, Ausgang noch letzten Schritt.

## Autoritative lokale Bindung

Der Inspector muss ursprüngliche Run-, Reconciliation-, Dispositions- und
Cleanup-Autorisierungen sowie alle gebundenen Evidenceobjekte erneut laden.

Hashes, IDs, Scope, Source, Image, Compose und Identitätsrelationen müssen
bytegenau mit der neuen Reconciliation-Autorisierung übereinstimmen.

Der erwartete Claimname und der Name finaler Cleanup-Evidence werden nur aus
dem vollständigen SHA-256 der Cleanup-ID abgeleitet.

Ein vorhandener Claim muss owner-only, regulär, einfach verlinkt und als
vollständiger kanonischer LQ-339-Claim lesbar sein. Seine Bindung muss exakt
der validierten Kette entsprechen.

Alter oder Dateiname allein beweist keinen Cleanupzustand.

## Evidence vor Docker

Finale LQ-339-Evidence wird vor jedem Dockerzugriff geprüft.

Ist sie vollständig und exakt gebunden, lautet der read-only Ausgang
`final_evidence_present`. Ein gleichzeitig offener Claim wird nicht entfernt.

Fehlt sowohl finale Evidence als auch der exakte Cleanup-Claim, lautet der
neutrale Ausgang `not_found` ohne Dockerzugriff.

Finale Evidence ohne Claim ist ebenfalls `final_evidence_present`; der
Inspector erzeugt keinen Claim nachträglich.

Beschädigte, widersprüchliche oder anders gebundene Evidence beziehungsweise
ein technisch unklarer Claim bleibt detailfrei unavailable.

## Erneute Ressourcenableitung

Nur bei exakt offenem Claim ohne finale Evidence rendert der Inspector das
SHA-gebundene Composemodell erneut read-only.

Container, Application-Netz, Data-Netz und Datenvolume werden ausschließlich
aus Run und geschlossenem Modell abgeleitet.

Absoluter Dockerpfad, beide owner-only Environmentdateien, explizites Projekt
und festes Composefile werden erneut validiert.

Listen verwenden ausschließlich exakte verankerte Namen. Inspects erfolgen
nur für tatsächlich vorhandene erwartete Ressourcen.

## Zulässige Sequenzzustände

Das Volume muss in jedem klassifizierbaren Zustand vorhanden, intern
rungebunden und unverändert sein.

Der Inspector darf genau diese Zustände ableiten:

- `runtime_intact`: Container läuft und beide Netze existieren mit jeweils
  ausschließlich diesem Container als Endpoint;
- `container_stopped`: Container ist eindeutig gestoppt oder beendet, beide
  Netze und ihre exakten Endpoints bestehen noch;
- `container_removed`: Container fehlt, beide Netze bestehen rungebunden und
  endpointfrei;
- `application_network_removed`: Container und Application-Netz fehlen, das
  Data-Netz besteht rungebunden und endpointfrei;
- `runtime_removed_evidence_missing`: Container und beide Netze fehlen, das
  exakte Volume besteht weiterhin.

Diese Ausgänge beschreiben nur die aktuelle Beobachtung. Sie beweisen nicht,
welcher LQ-339-Aufruf zuletzt bestätigt wurde oder ob ein Dockeraufruf seine
Antwort verloren hat.

## Konfliktzustände

Ein vollständig lesbarer Zustand außerhalb der festen Reihenfolge ergibt
`conflict`.

Dazu gehören insbesondere:

- fehlendes, fremdes oder zusätzlich gebundenes Datenvolume;
- vorhandener Container bei fehlendem erwarteten Netz;
- fehlendes Data-Netz bei noch vorhandenem Application-Netz;
- fremde oder zusätzliche Netzwerkendpoints;
- laufender oder gestoppter Container mit abweichender Image-, Mount-, Port-
  oder Netzwerkbindung;
- externe, fremd gelabelte oder anders benannte Ressourcen;
- Teilbestand, der keiner zulässigen LQ-339-Präfixfolge entspricht.

Conflict autorisiert keine Bereinigung, Umbenennung, Übernahme oder
Volumenlöschung.

## Technische Nichtverfügbarkeit

Malformed Compose- oder Dockeroutput, Nonzero, stderr, Timeout, Truncation,
Hard Kill, doppelte JSON-Schlüssel oder uneindeutige exakte Namensliste bleibt
technisch unavailable.

Unavailable wird nicht als `conflict`, Abwesenheit oder erfolgreicher
Teilzustand umgedeutet.

Der Inspector liest keine Docker-Events, Logs, Laufzeithistorie oder
Zeitstempelheuristik und rekonstruiert keine verlorene Bestätigung.

## Strikte Read-only-Grenze

Der spätere Command darf ausschließlich Compose-Render, exakte Listen und
Inspects ausführen.

Stop, Start, Remove, Disconnect, Down, Prune, Kill, SQL, Claimänderung,
Evidencewrite und Dateisystembereinigung bleiben verboten.

Er entfernt auch dann keinen Claim, wenn finale Evidence vorhanden oder die
Runtime vollständig entfernt ist.

Kein Ausgang ist selbst eine Fortsetzungs-, Finalisierungs- oder
Cleanup-Autorisierung.

## Neutrale Ausgabe

Die Ausgabe enthält nur Schema-Version, Operation
`disposable_postgres_runtime_cleanup_reconciliation` und einen Ausgang:

- `not_found` oder `final_evidence_present`;
- einen der fünf zulässigen Sequenzzustände;
- `conflict`;
- technisch unavailable ohne Ergebnisobjekt.

IDs, Hashes, Ressourcennamen, Pfade, Zeitwerte, Identitäten und technische
Details bleiben privat.

## Retention und Nichtwiederverwendung

Cleanup- und Cleanup-Reconciliation-ID, Claim, Autorisierungen, Evidence und
Runbindung bleiben mindestens so lange eindeutig erhalten, wie Audit,
Reconciliation, Finalisierung oder eine spätere Fortsetzungsentscheidung sie
benötigen.

Keine ID, kein Claimname und keine Evidence darf unter anderer Bindung oder
Bedeutung wiederverwendet werden. Beobachtete Abwesenheit erlaubt keine
Wiederverwendung der Run-ID oder Übernahme des Volumes.

Dieser Vertrag legt keine konkrete Retentionfrist oder Ablagestrategie fest.

## Nichtziele

LQ-340 implementiert keinen Inspector, Entry Point, Test, Claim- oder
Evidencewriter und keinen Fortsetzungsoperator.

Es gibt keine Volume-Löschung, Schema-, Tabellen-, SQL-, Migration-, Port-,
Domainmodell-, Signatur-, Compose-, CLI- oder Production-Wiring-Entscheidung.

Bundle-Gates bleiben bei 35 Entry Points, 39 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-341 sollte den read-only Cleanup-Claim-Inspector und Fake-basierte Tests
für die vollständige geschlossene Zustandsmatrix implementieren.
Claimfinalisierung, Fortsetzung eines eindeutig beobachteten Teilcleanup und
jede Volumenmutation bleiben separate spätere Slices.
