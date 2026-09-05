# LQ-399 — Authorized PostgreSQL Volume Deletion Continuation Contract

## Zweck

LQ-399 definiert die streng autorisierte Fortsetzung einer LQ-394-Löschung,
deren frische LQ-398-Finalisierung `continuation_required` ergibt.

Die Fortsetzung darf höchstens einen weiteren exakten Volume-Remove versuchen.
Dieser Slice implementiert keinen Command, Claim, Writer oder Dockeraufruf.

## Separate Continuation-Authority

Lösch-, Reconciliation- und Finalisierungsautorisierung gewähren kein
Fortsetzungsrecht.

Ein späterer Operator benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Volume-Deletion-Continuation-ID und einer
vorab gebundenen untergeordneten Continuation-Claim-ID.

Sie muss mindestens geschlossen binden:

- Continuation-, Continuation-Claim- und Finalization-ID;
- Reconciliation-, Volume-Deletion- und ursprüngliche Claim-ID;
- ursprüngliche Volume-Disposition-ID;
- Retention-, Legal-Hold- und Recoveryentscheidungs-IDs;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, immutable Image-Referenz und Compose-SHA-256;
- intern abgeleitete exakte Volumeidentität;
- SHA-256 der Finalisierungs-, Reconciliation-, Lösch- und
  Resolverautorisierung;
- Lineage-, Retention-, Hold- und Recoveryhashes;
- Operation exakt `continue_disposable_postgres_volume_deletion`;
- Scope exakt `data_volume_only`;
- neue getrennte Executor-, Authorizer- und Revieweridentitäten;
- positives aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder Zustand, Volumename, Claimstatus, Rolle noch
Allow-Boolean.

## Keine geerbte Authority

Ein früheres positives Preflight-, Inspector- oder Finalizerergebnis ist keine
Continuation-Authority.

SessionPrincipal, Membership, Researchpermission, Rollenname und Besitz des
Prozesskontos gewähren ebenfalls kein Fortsetzungsrecht.

Der ausführende Actor identifiziert den Operator, erlaubt aber allein keine
Mutation.

Deaktivierung, Widerruf, fehlende Bindung oder Identitätsüberschneidung stoppt
fail-closed.

## Vollständige historische Bindung

Der Operator validiert alle ursprünglichen Resolver-, Lösch-, Reconciliation-
und Finalisierungsautorisierungen sowie Lineage-, Retention-, Hold- und
Recoveryartefakte erneut.

Historische Autorisierungen werden nur in ihrem damaligen gültigen Kontext
strukturell geprüft. Die neue Continuation-Autorisierung muss aktuell sein.

IDs, Run, Source, Image, Compose, Volume, Operation, Scope, Identitäten und
sämtliche Hashbeziehungen müssen exakt übereinstimmen.

Neue Authority repariert keine beschädigte historische Evidence und
verlängert kein früheres Zeitfenster.

## Evidence-Retry vor neuer Entscheidung

Der private Continuation-Evidencepfad wird ausschließlich aus dem
vollständigen SHA-256 der Continuation-ID abgeleitet.

Vor LQ-398 und vor jedem Dockerzugriff wird vorhandene Evidence vollständig
geprüft.

Exakt gebundene Evidence erlaubt ausschließlich den idempotenten Retry der
Freigabe des untergeordneten Continuation-Claims.

Malformed, teilweise oder fremd gebundene Evidence ist technische
Nichtverfügbarkeit und wird weder überschrieben noch ignoriert.

## Frische LQ-398-Entscheidung

Ohne Continuation-Evidence führt der Operator LQ-398 unmittelbar vor jeder
neuen Claimanlage mit denselben autoritativen Inputs erneut aus.

Gespeicherter stdout, Tickettext, caller-gelieferter Zustand oder ein früheres
Ergebnisobjekt genügt nicht.

Nur `continuation_required` erlaubt den Fortsetzungsweg.

`volume_removal_finalized` und `deletion_evidence_confirmed` werden ohne neuen
Claim oder Ressourceneffekt zu `already_finalized`.

`not_found` bleibt neutral, `investigation_required` bleibt nichtterminal und
technische Nichtverfügbarkeit bleibt ohne Ergebnisobjekt.

## Ursprünglicher Claim bleibt offen

Der originale LQ-394-Volume-Deletion-Claim muss vorhanden, kanonisch und
vollständig an dieselbe historische Kette gebunden sein.

Fehlen, Beschädigung oder Fremdbindung erlaubt keine Fortsetzung.

Dieser Claim bleibt vor, während und nach jeder Continuation offen.

Auch bestätigte Volumeabwesenheit erlaubt diesem Operator nicht, ihn
freizugeben. Das bleibt einer späteren frischen LQ-398-Finalisierung
vorbehalten.

## Untergeordneter Continuation-Claim

Nach frischem `continuation_required` wird der Continuation-Claim owner-only
per exklusiver Neuanlage vollständig geschrieben und durable synchronisiert.

Sein Pfad wird ausschließlich aus dem vollständigen SHA-256 der vorab
gebundenen Continuation-Claim-ID abgeleitet.

Er bindet sämtliche IDs, Hashes, die exakte Volumeidentität, drei getrennte
Identitäten, das einzelne Mutationsbudget und die UTC-Startzeit.

Vorhandener, kollidierender oder technisch unklarer Claim stoppt vor Docker.
Alter, Prefix oder vermutete Aufgabe erlauben keine Übernahme oder Ersetzung.

## Letzte read-only Prüfung

Nach durabler Claimanlage und unmittelbar vor dem Effekt wird das exakte
Volume noch einmal read-only über seine intern abgeleitete Identität geprüft.

Die Prüfung darf keinen caller-gelieferten Namen, keine Suche, kein Label und
keine Projektgruppenauswahl verwenden.

Abwesenheit oder Bindungsabweichung nach Claimanlage führt ohne Mutation zu
technischer Nichtverfügbarkeit; beide Claims bleiben zur Aufklärung bestehen.

## Ein einzelnes Mutationsbudget

Der spätere Operator darf genau einen Aufruf zum Entfernen des exakten
gebundenen Volumes ausführen.

Force, Prune, Compose-Down, Container- oder Networkmutation, Mount, Export,
SQL, Wildcard, Prefix und Labelselektion sind verboten.

Nach dem Remove muss eine exakte read-only Namensabfrage die Abwesenheit
desselben Volumes bestätigen.

Ein zweiter Remove, alternativer Befehl oder heuristisch abgeleiteter Erfolg
ist in jedem Fall ausgeschlossen.

## Unknown Outcome

Ab dem ersten möglichen Ressourceneffekt führt Nonzero, stderr, Timeout,
Truncation, Hard Kill, verlorene Antwort oder fehlende eindeutige
Abwesenheitsbestätigung zum sofortigen Abbruch.

Ursprünglicher und untergeordneter Claim bleiben offen; neue Evidence entsteht
nicht.

Es gibt keinen Blind-Retry. Ein späterer separater read-only Inspector muss den
Zustand erneut auflösen.

## Continuation-Evidence

Nach eindeutig bestätigter Abwesenheit wird getrennte private
Continuation-Evidence atomar persistiert.

Sie bindet mindestens alle fachlichen IDs und Hashes, exaktes Volume,
Mutationsschritt, bestätigte Abwesenheit, drei Identitäten sowie UTC-Start und
-Abschluss.

Ihr kanonischer Ausgang lautet `volume_removal_pending_finalization`.

Sie ist weder nachträglich erzeugte LQ-394-Evidence noch LQ-398-
Finalization-Evidence und behauptet keine vollständige Datenentsorgung.

## Evidence-first Claimfreigabe

Erst vollständig zurückgelesene Continuation-Evidence erlaubt die Freigabe
genau des untergeordneten Continuation-Claims.

Der ursprüngliche LQ-394-Claim bleibt immer offen.

Bei technisch mehrdeutiger Freigabe bleibt die Evidence erhalten. Der exakte
Retry prüft nur Evidence und Continuation-Claim, führt weder LQ-398 noch Docker
erneut aus und entfernt niemals einen fremden Claim.

## Geschlossene Ausgänge

Der spätere Operator darf ausschließlich liefern:

- `volume_removal_pending_finalization`;
- `already_finalized`;
- `not_found`;
- `investigation_required`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Die öffentliche Ausgabe enthält nur kanonische Schemaversion, feste
Continuation-Operation und Ausgang. Private IDs, Hashes, Pfade und Zeiten
werden nicht offengelegt.

## Retention und Nichtwiederverwendung

Continuation-, Continuation-Claim-, Finalization-, Reconciliation-, Lösch-
und ursprüngliche Claim-ID sowie alle Autorisierungen, Claims, Evidence und
Quellartefakte bleiben mindestens so lange unterscheidbar, wie Audit,
Idempotenz, Retry, Reconciliation oder Finalisierung davon abhängen.

Keine ID, Claimdatei, Evidence oder Volumeidentität darf unter neuer Bindung,
anderem Scope oder neuer Bedeutung wiederverwendet werden.

Volumeabwesenheit oder Freigabe des untergeordneten Claims beendet diese
Untergrenze nicht. Eine konkrete Frist oder Ablageform wird nicht festgelegt.

## Nichtziele und Bundle

LQ-399 entscheidet keine konkrete JSON-Struktur, Signatur, Exception,
Funktionssignatur, CLI, Docker-argv, Timeout-, Claim- oder
Evidenceimplementierung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP-, Monitoring-, Test- oder Production-Wiring-
Änderung.

Der Slice implementiert keinen Continuation-Operator, Inspector,
Evidencewriter, Claimrelease oder Volume-Remove.

Bundle-Gates bleiben bei 54 Entry Points, 58 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-400 sollte den owner-kontrollierten Volume-Deletion-Continuation-Operator
gemäß diesem Vertrag implementieren.

Fake-basierte Tests müssen frische LQ-398-Entscheidung, exklusiven
Continuation-Claim, Einzelmutation, Abwesenheitsbestätigung, Unknown Outcome,
atomare Evidence und Evidence-Retry ohne zweiten Dockeraufruf prüfen.

Reconciliation offener Continuation-Claims und reguläre Finalisierung des
ursprünglichen Claims bleiben separate spätere Slices.
