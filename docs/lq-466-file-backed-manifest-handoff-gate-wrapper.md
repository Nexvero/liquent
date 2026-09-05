# LQ-466 — File-backed Manifest Handoff Gate Wrapper

## Ergebnis

LQ-466 implementiert die vier LQ-465-Gateoperationen über LQ-464-Codec,
Publisher und Reader.

Der Adapter führt noch keinen Writer- oder Recoverycode aus.

## Abhängigkeiten

Codec, Publisher und Reader werden vollständig konstruktiv injiziert.

Keine Abhängigkeit kann durch einen Gate-Request ersetzt werden.

Unvollständige Composition scheitert beim Adapteraufbau detailfrei.

Der Adapter öffnet selbst keine Datei.

## Ready-Dokument

`publish_ready` akzeptiert ausschließlich die geschlossene Startbindung.

Es erzeugt ein Ready-Dokument aus gebundener Ready-ID, Handle und
Gated-Observation-ID.

Rolle und Dokumentform sind durch den Dokumenttyp festgelegt.

Es gibt keine freie Payload oder Callerrolle.

## Ready-Publikation

Der Codec erzeugt kanonische Bytes und Fakten.

Der Publisher veröffentlicht sie unter derselben Control-Directory-ID.

Nur ein passender dauerhafter Publikationsbeleg konstruiert den Ready-Zustand.

Filekonflikt wird in den feldlosen Wrapperkonflikt übersetzt.

## Kein Code vor Ready

Die Implementation importiert oder ruft keinen Writer, Reconciler oder
Capabilityexecutor auf.

Sie erzeugt nach Publikation nur den typisierten Ready-Marker.

Engine-Running wird nicht behauptet oder geprüft.

Persistentes Gated-Journal folgt im späteren Supervisorservice.

## Await Release

`await_release` akzeptiert ausschließlich einen Ready-Marker.

Der Reader wird nur für dieselbe Control-Directory-ID und die feste
release_token-Rolle aufgerufen.

Neutrale Rollenabwesenheit liefert `None` und bewirkt keine weitere Aktion.

Es gibt keinen Timeout-, Polling- oder Sleepparameter.

## Token-Decode

Ein vorhandener Record wird vollständig über den kanonischen Codec dekodiert.

Nur `ManifestHandoffSupervisorReleaseTokenDocument` wird akzeptiert.

Der Dokumenthandle muss exakt dem Ready-Handle entsprechen.

Falsche Rolle, beschädigte Bytes oder fremder Handle sind technische
Unverfügbarkeit, nicht Tokenabwesenheit.

## Tokenzustand

Der akzeptierte Zustand übernimmt Artefakt-ID und Release-ID ausschließlich
aus dem gelesenen Dokument.

Der Startcaller kann diese Werte nicht vorgeben.

Die LQ-465-Konstruktoren prüfen Token-ID-Separation erneut.

Das Token allein ist weiterhin kein Ausführungsmarker.

## Persistenter Release-Commit

Der Wrapper besitzt absichtlich keinen Datenbankzugriff.

Nur der Supervisorservice darf nach durablem Release-Commit das Token
publizieren.

Der kontrollierte Wrapper lädt vor Token und Ack keinen Capabilitycode, sodass
er das privilegierte Token nicht selbst aus untrusted Code erzeugen lässt.

Servicekorrelation und Dateibesitzprofile bleiben getrennte
Compositionvoraussetzungen.

## Consumed-Dokument

`publish_consumed` akzeptiert ausschließlich den typisierten Tokenzustand.

Es erzeugt das Consumed-Dokument aus vorab gebundener Consumed-ID, demselben
Handle und exakt gelesener Release-ID.

Eine andere Release-ID kann nicht als Parameter eingeschleust werden.

Token und Ack bleiben verschiedene Artefakt-IDs und Rollen.

## Consumed-Publikation

Codec und Publisher werden über dieselbe private Control-Directory-ID
aufgerufen.

Nur ein passender dauerhafter release_consumed-Beleg konstruiert Released.

Filekonflikt liefert Wrapperkonflikt ohne Ersatz-Ack.

Technisch unklarer Write-Ausgang bleibt retrybar mit denselben Bytes und IDs.

## Ausführungsmarker

Die Implementation gibt erst nach erfolgreichem Consumed-Publish einen
`ReleasedManifestHandoffSupervisorGateWrapper` zurück.

Sie besitzt keinen separaten Allowpfad.

Ein Caller erhält Released weder aus Ready noch direkt aus Token.

Capabilityausführung bleibt ein späterer Wrapper-Orchestrierungsslice.

## Terminalbasis

`publish_terminal` akzeptiert ausschließlich einen bereits validierten
Complete-Request.

Ready wird als kontrollierter Vor-Release-Terminalpfad unterstützt.

Released wird als Post-Release-Terminalpfad unterstützt.

Andere Gatewerte scheitern detailfrei.

## Terminal-Dokument

Die Implementation nimmt Terminal-Artefakt-ID, Handle und
Terminal-Observation-ID ausschließlich aus der ursprünglichen Startbindung.

Der geschlossene Outcome stammt aus dem validierten Complete-Request.

Der Terminal-Dokumentkonstruktor prüft Handle und Outcome erneut.

Es gibt keine freie Ergebnis- oder Diagnosestruktur.

## Terminal-Publikation

Nach kanonischem Encoding wird das Envelope atomar unter derselben
Control-Directory-ID publiziert.

Nur ein passender terminal_envelope-Beleg konstruiert Completed.

Filekonflikt wird nicht überschrieben oder repariert.

Envelope-Erfolg behauptet weiterhin kein Engine-Terminal.

## Idempotente Retries

Ready, Consumed und Terminal verwenden bei Retry dieselben Dokumente und IDs.

LQ-464 liefert für byteidentischen Bestand denselben faktischen Erfolg.

Der Wrapper rekonstruiert daraus dieselbe typisierte Gatefolge.

Jede Byteabweichung bleibt Konflikt.

## Fehlerübersetzung

`ManifestHandoffSupervisorControlArtifactConflict` wird ausschließlich in
`ManifestHandoffSupervisorGateWrapperConflict` übersetzt.

Codec-, Reader-, Publisher- und Strukturfehler werden über die bestehende
`ManifestHandoffRegistryUnavailable` vereinheitlicht.

Ursachen, IDs, Rollen, Bytes und Pfade verlassen die Grenze nicht.

## Kein stilles None

Nur fehlendes Release-Token liefert neutral `None`.

Publishmethoden liefern Erfolg oder Konflikt; technische Fehler werden nicht
als Abwesenheit verborgen.

Fremde oder beschädigte Token werden nicht ignoriert.

Diese Trennung erhält die fail-closed Gatewirkung.

## Keine Authority

Der Adapter akzeptiert keine Session, User-ID, Permission, Managementrolle
oder Allowentscheidung.

Er löst keine Plattformauthority auf und cached sie nicht.

Das Token ist eine enge Gatekorrelation und keine allgemeine Berechtigung.

## Keine Engine- oder Prozesswirkung

Der Adapter importiert keine Docker-, Socket-, subprocess- oder Shellgrenze.

Er erstellt, startet, wartet und terminiert keinen Container.

Er lädt keinen Capabilitycode und interpretiert kein Outcome.

Enginezustand bleibt Sache des Supervisorservice.

## Keine direkte Dateiwirkung

Der Wrapper verwendet ausschließlich Publisher und Reader.

Er akzeptiert keinen Pfad, Dateinamen, Modus oder Filehandle.

Atomizität, Symlinkschutz und fsync bleiben vollständig in LQ-464 gekapselt.

## Kein Schema oder Wiring

LQ-466 ändert keine Tabelle, Migration oder Persistenzsignatur.

Head bleibt `20260824_0032` mit 32 linearen Migrationen.

Es gibt keinen Entry Point, CLI-, Route-, Compose-, Engine-, Service- oder
Production-Wiring.

## Tests

Fokussierte Prüfungen belegen exakte Dokumentkonstruktion, feste Tokenrolle,
neutrale Tokenabwesenheit, Handleprüfung, korreliertes Consumed-Ack,
Ready-/Released-Terminalpfad, Konfliktübersetzung und fehlende Prozessmacht.

## Nächster Slice

LQ-467 sollte den geschlossenen Capabilityexecutor-Vertrag definieren, der
ausschließlich einen Released-Marker akzeptiert und einen geschlossenen Outcome
liefert.

Supervisorservice und Productionentrypoint folgen separat.
