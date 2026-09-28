# LQ-475 — Persistent Supervisor Prepare Orchestration

## Ergebnis

LQ-475 implementiert den restart-sicheren Preparepräfix des persistenten
Manifest-Handoff-Supervisorservice.

Writer und Recovery verwenden denselben geschlossenen Ablauf, bleiben aber an
ihren Command-, Journal-, Prozess- und Resulttypen strikt getrennt.

## Servicegrenze

`PersistentManifestHandoffSupervisorPrepareService` bietet ausschließlich
`prepare_writer` und `prepare_recovery`.

Release, Inspect, Terminate, Capabilityausführung und Terminalisierung sind
nicht Teil dieses Slices.

Der Service ist noch kein Productioncomposer und kein Entry Point.

## Abhängigkeiten

Der Prepareservice komponiert das bestehende profilspezifische Journal,
Runtimebinding-Store/-Lookup, Control-Artefaktstore, Gatebinding-Store,
die geschlossene Engine und den Gatewrapper.

Keine Grenze wird ersetzt oder um eine Signatur erweitert.

Fehlende Abhängigkeiten scheitern beim Aufbau detailfrei.

## Commandprüfung

Writer akzeptiert nur `PrepareManifestHandoffWriterService`.

Recovery akzeptiert nur `PrepareManifestHandoffRecoveryService`.

Die bestehenden Commandinvarianten binden Registrierung, Handle,
Control-Directory und Gateprofil vor dem Serviceaufruf.

## Keine Caller-Authority

Der Service akzeptiert keine Session, User-ID, Workspace-ID, Rolle,
Permission oder Allowentscheidung.

Claim und Owner stammen ausschließlich aus der kontrollierten persistenten
Journalregistrierung.

Prepare-IDs und Handles erteilen keine allgemeine Authority.

## Registrierung zuerst

Jeder Prepareaufruf registriert zuerst exakt den profilspezifischen
Journaljob.

Exakter Retry rekonstruiert denselben View.

Neutrale Ablehnung vor erster Wirkung bleibt `None`.

Journaldivergenz wird zum detailfreien Servicekonflikt.

## Launch-Commit vor Enginewirkung

Ein `prepare_registered`-Job wird mit seiner bereits gebundenen
Launch-Commit-ID dauerhaft nach `launch_committed` überführt.

Create, Inspect, Start und Ready erfolgen niemals vor diesem Commit.

Unklare Commitwirkung wird nicht als fehlender Commit behandelt.

Es wird keine neue Transition-ID erzeugt.

## Zulässige Restartzustände

Prepare verarbeitet nur `prepare_registered`, `launch_committed` und
`prepared_gated`.

Release-, Running-, Termination- oder Terminalzustände werden durch Prepare
nicht fortgeschrieben.

Ein solcher Command-Retry liefert einen detailfreien Servicekonflikt.

Prepare übernimmt keine Aufgaben späterer Serviceoperationen.

## Runtimeauflösung

Nach Launch-Commit wird das Runtimebinding zuerst nach Handle aufgelöst.

Vorhandene Binding muss Handle, Creation-ID, Control-Directory und
Image-Digest vollständig mit dem Command verbinden.

Abweichung wird nicht überschrieben und nicht adoptiert.

Ein `prepared_gated`-Job ohne Runtime ist technische Unverfügbarkeit.

## Create und Reconcile

Fehlt Runtime im Zustand `launch_committed`, wird die Engine mit derselben
stabilen Creation-ID aufgerufen.

Die Engine entscheidet selbst zwischen autoritativem Create und exaktem
Reconcile.

Ein unklarer Createausgang erzeugt keinen zweiten Container.

Enginekonflikt wird zum Servicekonflikt.

## Runtimebinding vor Start

Der von der Engine zurückgegebene Container wird vor Start dauerhaft an
Handle, Creation-ID, Control-Directory und Image-Digest gebunden.

Neutrales oder technisch fehlendes Binding nach Enginewirkung ist nicht mehr
neutrale Serviceabwesenheit.

Bindingkonflikt verhindert jede weitere Startwirkung.

Die persistierte Container-ID ist die einzige Startadresse.

## Gatebinding vor Start

Die vollständige Gatebinding wird vor Start über LQ-474 dauerhaft gebunden.

Exakter Retry akzeptiert nur vollständige Gleichheit.

Fehlende Voraussetzung nach Runtimebinding ist technische Unverfügbarkeit.

Gatebindingkonflikt verhindert Start und Ready.

## Direkte Engineinspektion

Vor jedem möglichen Start wird die persistierte Container-ID direkt
inspiziert.

Container-ID, Creation-ID, Image-Digest und Profil müssen Runtime und Command
exakt entsprechen.

Abwesenheit oder technisch unklarer Bestand ist nicht neutral.

Exited, dead oder divergenter Bestand wird nicht neu gestartet.

## Genau ein kontrollierter Start

Nur ein direkt beobachteter Zustand `created` darf gestartet werden.

Nach Startannahme wird derselbe Container erneut direkt inspiziert.

Erst direkt beobachtetes `running` erlaubt Ready.

Ein bereits `running` beobachteter Container wird beim Retry nicht erneut
gestartet.

## Prepared-Restart

Ein bereits `prepared_gated`-Job darf niemals einen `created`-Container
starten.

Er verlangt die bestehende Runtimebinding und direkte Running-Beobachtung.

Damit wird ein inkonsistenter Preparedbestand nicht durch den Retry repariert.

Der Retry erzeugt keine zweite Enginewirkung.

## Kanonisches Ready

Nach direkter Running-Beobachtung publiziert beziehungsweise reconciliert der
Gatewrapper das kanonische Ready-Dokument aus der persistenten Gatebinding.

Handle, Control-Directory, Ready-ID und Gated-Observation-ID stammen nicht aus
transient neu erzeugten Werten.

Wrapperkonflikt wird zum Servicekonflikt.

Ein anderer Rückgabetyp ist technische Unverfügbarkeit.

## Persistierte Ready-Fakten

Artefakt-ID, Handle, Gated-Observation-ID und publizierte Digest-/Größenfakten
werden über den bestehenden Runtime-Artefaktstore korreliert.

Ein exakter Retry rekonstruiert denselben Record.

Abweichende Artefaktfakten werden nicht überschrieben.

Ready-Publikation allein erzeugt noch kein Prepared-Ergebnis.

## Gated zuletzt

Nur aus `launch_committed` wird nach persistierter Ready-Korrelation dieselbe
Gated-Observation-ID appendiert.

Ein bereits `prepared_gated`-View wird nicht erneut transitioniert.

Erst ein bestätigter `prepared_gated`-View darf das Ergebnis bilden.

Die Reihenfolge Commit, Runtime, Gate, Running, Ready, Readyrecord und Gated ist
geschlossen.

## Persistentes Ergebnis

Writer erzeugt ausschließlich `PreparedManifestHandoffWriterProcess` und
`ManifestHandoffWriterServiceResult`.

Recovery erzeugt ausschließlich die entsprechenden Recoverytypen.

Handle, Claim und Owner stammen aus der Journalregistrierung.

`prepared_at` ist die persistierte Beobachtungszeit des Gated-Journalviews.

## Konfliktvereinheitlichung

Journal-, Runtime-, Engine-, Gatewrapper- und Gatebindingkonflikte werden an
der Servicegrenze als `ManifestHandoffSupervisorServiceConflict` sichtbar.

Konkrete Infrastruktur- oder Identitätsdetails werden nicht transportiert.

Konflikt erteilt keine Rebind-, Cleanup- oder Restartfähigkeit.

Persistente Divergenz bleibt unverändert erhalten.

## Technische Unverfügbarkeit

Fehlender erwarteter Bestand nach Launch-Commit, ungültige Rückgabetypen und
unerwartete technische Fehler werden über die bestehende detailfreie
`ManifestHandoffRegistryUnavailable`-Grenze vereinheitlicht.

Der Slice benennt keinen neuen technischen Exceptiontyp.

Unklare Wirkung wird niemals zu neutralem `None` normalisiert.

## Keine versteckte Wiederholung

Der Service erzeugt keine neue Prepare-, Launch-, Creation-, Gate-, Artefakt-
oder Observation-ID.

Er startet einen Runningcontainer nicht erneut.

Er repariert keine partielle Persistenz und löscht keinen Bestand.

Er führt keinen automatischen Release aus.

## Keine zusätzlichen Wirkungen

Es gibt kein Update, Delete, Rebind, Cleanup oder Retentionkommando.

Der Service erstellt keine Control-Directory und kennt keinen freien Pfad.

Engine- und Dateiwirkung erfolgen ausschließlich über die bestehenden
geschlossenen Ports.

Es gibt keine Threads, Worker oder Hintergrundschleifen.

## Kein Schema oder Wiring

LQ-475 ergänzt keine Migration, Tabelle, SQL- oder Portsignatur.

Head bleibt `20260825_0033` mit 33 linearen Migrationen.

Es gibt keinen Seed, Backfill, CLI-, Route-, Compose- oder Production-Wiring.

Die konkrete Dependency-Composition bleibt separat.

## Tests

Fokussierte Prüfungen belegen die geschlossene Reihenfolge, profilspezifische
Methoden, Restartzustände, Runtime-/Enginevergleich, Start-vor-Ready-Sperre,
persistierte Ready-Fakten, Gated-zuletzt, Konfliktvereinheitlichung und fehlende
Authority-, Release-, Terminal- und Wiringwirkung.

## Nächster Slice

LQ-476 sollte die restart-sichere Release-Orchestrierung vom persistenten
Preparedbestand über Release-Commit, Token, Consumed, direkte Running-
Beobachtung und Journal-Running implementieren.

Terminalisierung und Terminate folgen danach getrennt.
