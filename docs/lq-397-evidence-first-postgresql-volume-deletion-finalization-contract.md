# LQ-397 — Evidence-first PostgreSQL Volume Deletion Finalization Contract

## Zweck

LQ-397 definiert die kontrollierte Finalisierung eindeutig beobachteter
LQ-396-Volume-Deletion-Zustände.

Finalisierung persistiert eigene private Evidence vor möglicher Freigabe des
exakten LQ-394-Volume-Deletion-Claims.

Dieser Slice implementiert keinen Command, Evidencewriter, Claimrelease,
Dockerzugriff oder Ressourceneffekt.

## Separate Finalisierungsauthority

Volume-Deletion- und Reconciliation-Autorisierung gewähren kein
Finalisierungsrecht.

Ein späterer Finalizer benötigt eine neue owner-only Autorisierung mit
stabiler, nicht wiederverwendbarer Volume-Deletion-Finalization-ID.

Sie muss mindestens geschlossen binden:

- Schemaversion und Finalization-ID;
- Volume-Deletion-Reconciliation-, Volume-Deletion- und Claim-ID;
- ursprüngliche Volume-Disposition-ID;
- Retention-, Legal-Hold- und Recoveryentscheidungs-IDs;
- Run-ID und Phase `disposable_postgres`;
- Source-Commit, immutable Image-Referenz und Compose-SHA-256;
- intern abgeleitete exakte Volumeidentität;
- SHA-256 der Reconciliation-, Lösch- und Resolverautorisierung;
- Lineage-, Retention-, Hold- und Recoveryhashes;
- Operation exakt Finalisierung einer disposable PostgreSQL-Volume-Deletion;
- Scope exakt `data_volume_only`;
- neue getrennte Executor-, Authorizer- und Revieweridentitäten;
- positives aktuelles UTC-Fenster von höchstens einer Stunde.

Caller liefern weder beobachteten Zustand, Claimstatus, gewünschte
Finalisierung, Volumename noch Allow-Boolean.

## Keine neue Ressourcenauthority

Die Finalisierungsautorisierung erlaubt ausschließlich eigene Evidence und die
spätere Freigabe genau des gebundenen Claims.

Sie verlängert weder Lösch- noch Reconciliation-Authority und erlaubt keinen
zweiten Volume-Remove.

Ein neuer Hold oder Widerruf sperrt jede spätere Ressourcenmutation, ändert
aber nicht die historische Frage, ob das lokale Volume bereits entfernt
wurde.

Membership, Researchpermission, SessionPrincipal, Rollenname und Besitz des
Prozesskontos sind keine Finalisierungsauthority.

Kein positiver Finalisierungsausgang ist eine allgemeine Aussage vollständiger
Datenentsorgung.

## Vollständige historische Bindung

Der Finalizer validiert ursprüngliche Resolver-, Lösch- und
Reconciliation-Autorisierungen sowie Lineage-, Retention-, Hold- und
Recoverydateien erneut.

Historische Autorisierungen werden nur in ihren damaligen gültigen Kontexten
strukturell geprüft.

Die aktuelle Finalisierungsautorisierung muss aktuell gültig sein und den
bytegenauen SHA-256 der vollständigen LQ-396-Reconciliation-Autorisierung
binden.

IDs, Run, Source, Image, Compose, Volume, Operation, Scope, Identitäten und
sämtliche Hashbeziehungen müssen exakt übereinstimmen.

Eine neue Finalisierungsautorisierung repariert keine beschädigte historische
Evidence und verlängert kein altes Zeitfenster.

## Getrennte Finalisierungsidentitäten

Finalization-Executor, -Authorizer und -Reviewer müssen drei verschiedene
aktive Identitäten sein.

Sie bleiben von den zwölf bereits gebundenen Reconciliation-, Lösch-,
Resolver- und Clearance-Identitäten getrennt.

Damit sind insgesamt fünfzehn verschiedene beteiligte Identitäten
nachzuweisen.

Deaktivierung, Widerruf, Fehlen oder widersprüchliche Bindung stoppt
fail-closed.

Der ausführende Actor identifiziert den Finalizer, gewährt aber allein keine
Authority.

## Finalization-Evidence vor Inspector

Der finale Evidencepfad wird ausschließlich aus dem vollständigen SHA-256 der
stabilen Volume-Deletion-Finalization-ID abgeleitet.

Vor LQ-396 und vor jedem Dockerzugriff prüft der Finalizer dort vorhandene
Evidence vollständig.

Exakt gebundene Finalization-Evidence steuert ausschließlich den idempotenten
Evidence-Retry der Claimfreigabe.

Malformed, teilweise, fremde oder anders gebundene Evidence ist technische
Nichtverfügbarkeit und wird nicht überschrieben oder ignoriert.

Ohne Finalization-Evidence beginnt der normale Weg mit einer frischen
LQ-396-Entscheidung.

## Frische LQ-396-Entscheidung

Der Finalizer führt den LQ-396-Inspector unmittelbar vor jeder neuen
Evidenceanlage mit denselben autoritativen Inputs erneut aus.

Ein gespeicherter stdout-Wert, Tickettext, caller-gelieferter Zustand oder
früheres Ergebnisobjekt genügt nicht.

Die Ausgabe muss kanonische Schemaversion, feste Reconciliationoperation und
einen geschlossenen LQ-396-Ausgang besitzen.

Unbekannter oder malformed Output ist technische Nichtverfügbarkeit.

Der Inspector selbst bleibt strikt read-only.

## Terminal finalisierbare Zustände

Nur zwei frisch beobachtete Zustände sind terminal finalisierbar:

- `volume_absent_evidence_missing` wird
  `volume_removal_finalized`;
- `final_evidence_present` wird
  `deletion_evidence_confirmed`.

Beide Zustände betreffen ausschließlich das exakte lokale Docker-Volumeobjekt.

Sie erlauben eigene Finalization-Evidence und danach die Freigabe des exakten
Volume-Deletion-Claims.

Der Finalizer erzeugt keine fehlende originale LQ-394-Evidence nachträglich.

## Keine gefälschte LQ-394-Evidence

`volume_absent_evidence_missing` beweist aktuelle Abwesenheit unter einem
exakten offenen Claim, aber nicht die vollständige ursprüngliche
Prozessbestätigung von LQ-394.

Der Finalizer darf deshalb keinen Record mit dem ursprünglichen LQ-394-Schema,
dem Schritt `remove_exact_volume_once` oder der Behauptung einer empfangenen
Removeantwort erfinden.

Stattdessen entsteht getrennte Volume-Deletion-Finalization-Evidence mit
eigener Finalization-ID und beobachtetem Reconciliationzustand.

Diese Evidence dokumentiert die evidence-first Auflösung des Unknown Outcome,
nicht eine Umschreibung der historischen Ausführung.

## Vorhandenes Volume bleibt nichtterminal

`volume_present` wird ausschließlich zu `continuation_required`.

Der Ausgang erzeugt keine Finalization-Evidence und gibt den ursprünglichen
Claim nicht frei.

Aktuelle Existenz beweist nicht, dass der frühere Remove keinen Effekt hatte
oder dass ein Objekt unter demselben Namen nicht ersetzt wurde.

Ein späterer Continuationvertrag benötigt eigene aktuelle Authority, eine
explizite Bindung an die frische Reconciliation und ein minimales einzelnes
Mutationsbudget.

Der Finalizer startet keine Continuation und erzeugt keine neue Claim-ID.

## Not found und Conflict

`not_found` wird neutral ohne Evidence- oder Claimwrite weitergegeben.

Ohne Claim und ohne finale Evidence existiert kein gebundener Abschluss, den
dieser Finalizer freigeben dürfte.

`conflict` wird zu `investigation_required` und lässt Claim, Evidence und
Ressourcen unverändert.

Fremdbindung wird nicht durch Relabeling, Übernahme, Umbenennung oder
Entfernung repariert.

Technische Nichtverfügbarkeit bleibt ohne Ergebnisobjekt.

## Getrennte Finalization-Evidence

Die eigene private Evidence bindet mindestens:

- Schemaversion und Finalization-ID;
- Reconciliation-, Volume-Deletion- und Claim-ID;
- Run, Phase, Source, Image, Compose und exakte Volumeidentität;
- Operation und Scope `data_volume_only`;
- SHA-256 der Finalisierungs-, Reconciliation-, Lösch- und
  Resolverautorisierung;
- Lineage-, Retention-, Hold- und Recoveryhashes;
- stabile IDs aller fachlichen Entscheidungen;
- frisch beobachteten LQ-396-Zustand;
- kanonischen Finalisierungsausgang;
- fünfzehn getrennte Identitätsbindungen;
- UTC-Start- und Abschlusszeit.

Private Details werden nicht in der öffentlichen Ausgabe wiederholt.

## Atomare Evidenceanlage

Finalization-Evidence wird owner-only über exklusive Temporäranlage
vollständig geschrieben und geflusht.

Die finale Datei entsteht atomar; anschließend wird das private
Evidenceverzeichnis synchronisiert.

Der Finalizer liest die Datei vollständig zurück und prüft ihre semantische
und bytegenaue Bindung, bevor Claimfreigabe erreichbar ist.

Teilgeschriebene Temporärdateien oder eine kollidierende finale Datei sind
keine gültige Evidence.

Abweichende vorhandene Evidence wird nie überschrieben.

## Claimfreigabe erst nach Evidence

Nur vollständig zurückgelesene terminale Finalization-Evidence darf die
Freigabe des exakten LQ-394-Claims erreichen.

Der Claimpfad wird weiterhin ausschließlich aus dem SHA-256 der ursprünglich
gebundenen Claim-ID abgeleitet.

Ein vorhandener Claim wird vollständig gegen die historische LQ-394-Bindung
validiert, bevor genau diese eine Datei entfernt werden darf.

Suche, Alter, Prefix, Wildcard und Gruppenauswahl existieren nicht.

Ist der Claim bereits abwesend, ist die Freigabe idempotent abgeschlossen.

## Unknown Outcome der Claimfreigabe

Ist die Claimfreigabe oder Verzeichnissynchronisation technisch mehrdeutig,
bleibt die Finalization-Evidence erhalten und der Ausgang unavailable.

Der exakte Retry liest zuerst dieselbe Evidence und prüft anschließend nur den
exakten Claim.

Vorhandener exakt gebundener Claim erlaubt einen einzelnen erneuten
Freigabeversuch; fehlender Claim bedeutet bereits abgeschlossen.

Der Retry führt LQ-396 nicht erneut aus und erreicht kein Docker.

Fremder oder beschädigter Claim wird niemals entfernt.

## Evidence-Retry

Evidence-Retry verwendet dieselbe Finalization-, Reconciliation-, Lösch- und
Resolverautorisierung sowie sämtliche ursprünglichen Quellartefakte.

Eine neue ID, neue Autorisierung oder veränderte Evidence ist kein Retry.

Der Retry darf nur den in der Evidence gespeicherten terminalen Ausgang
erneut ausgeben, nachdem die exakte Claimfreigabe abgeschlossen ist.

`continuation_required`, `not_found` und `investigation_required` erzeugen
keine Evidence und besitzen daher keinen Evidence-Retry in diesem Slice.

## Strikte Writegrenze

Die einzigen erlaubten Writes sind atomare Finalization-Evidence und die
spätere Freigabe ausschließlich des exakten Volume-Deletion-Claims.

Volume, andere Dockerobjekte, originale LQ-394-Evidence, Reconciliation-
Evidence, Autorisierungen und Clearanceartefakte bleiben unverändert.

Volume-Remove, Mount, Export, SQL, Compose-Down, Prune, Force, Relabeling und
Continuation sind verboten.

Der Finalizer erzeugt keinen neuen Claim und keine Ersatz-ID.

## Geschlossene Ausgänge

Der spätere Finalizer darf ausschließlich liefern:

- `not_found`;
- `volume_removal_finalized`;
- `deletion_evidence_confirmed`;
- `continuation_required`;
- `investigation_required`;
- technische Nichtverfügbarkeit ohne Ergebnisobjekt.

Die Ausgabe enthält nur kanonische Schemaversion, feste Operation für
Volume-Deletion-Finalization und den geschlossenen Ausgang.

Run-, Volume-, Claim-, Evidence-, Retention-, Hold-, Recovery-, Identitäts-,
Hash-, Zeit- und Pfaddetails bleiben privat.

## Retention und Nichtwiederverwendung

Finalization-, Reconciliation-, Volume-Deletion- und Claim-ID,
Autorisierungen, Finalization-Evidence und sämtliche Quellartefakte müssen
mindestens so lange unterscheidbar bleiben, wie Audit, Idempotenz,
Evidence-Retry, Continuation oder Unknown-Outcome-Aufklärung davon abhängen.

Keine ID, Claimdatei, Evidence oder Volumeidentität darf unter neuer Bindung,
anderem Scope oder neuer Bedeutung wiederverwendet werden.

Claimfreigabe und lokale Volumeabwesenheit beenden die Retention nicht.

Dieser Vertrag legt keine konkrete Frist, Tabelle oder Ablageform fest.

## Grenzen der Abschlussaussage

`volume_removal_finalized` und `deletion_evidence_confirmed` bestätigen nur die
evidence-first Finalisierung des exakten lokalen Volumeobjekts.

Backups, Exporte, Snapshots, Replikate, Logs und historische Evidence besitzen
eigene Retention- und Dispositionsgrenzen.

Der Finalizer darf keinen allgemeinen Ausgang „alle Daten entsorgt“ liefern.

Vollständige Datenentsorgung bleibt eine übergeordnete
System-of-Record-Aussage.

## Nichtziele und Bundle

LQ-397 entscheidet keine konkrete JSON-Struktur, Signatur, Exception,
Funktionssignatur, CLI, Docker-argv, Timeout-, Claim- oder
Evidenceimplementierung.

Es gibt keine Schema-, Tabellen-, SQL-, Migration-, Port-, Modell-, Compose-,
Service-, Scheduler-, HTTP-, Monitoring-, Test- oder Production-Wiring-
Änderung.

Der Slice implementiert keinen Finalizer, Evidencewriter, Claimrelease,
Continuation oder Volume-Remove.

Bundle-Gates bleiben bei 53 Entry Points, 57 Operatormodulen, 27 Migrationen
und Head `20260819_0027`.

## Nächster Slice

LQ-398 sollte den Evidence-first Volume-Deletion-Finalizer gemäß diesem
Vertrag implementieren.

Fake-basierte Tests müssen frischen LQ-396-Inspector, beide terminalen
Finalisierungen, nichtterminalen Handoff, Conflict, Not-found, atomare
Evidence, Claimfreigabe und Evidence-Retry ohne Ressourcenschreibpfad prüfen.

Eine mögliche Continuation für `volume_present` bleibt ein separater späterer
Slice.
